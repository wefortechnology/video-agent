import json
import logging
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import db, pipeline
from app.config import BASE_DIR, DATA, settings
from app.formats import FORMATS
from app.pii import assert_clean
from app.services import library, llm, motion, stock, voice

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
app = FastAPI(title="Video Agent", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[f"http://127.0.0.1:{settings.PORT}", f"http://localhost:{settings.PORT}"],
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _recover():
    """A restart kills in-flight work; mark it failed so the UI never shows a job stuck forever.
    If another copy of the app is already serving (e.g. run.sh started twice), its jobs are alive: leave them alone."""
    import urllib.request
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{settings.PORT}/api/health", timeout=1.5)
        logging.getLogger("main").warning("Another server is already running on port %s; not touching its jobs.", settings.PORT)
        return
    except Exception:
        pass
    for v in db.query("SELECT id,status FROM videos WHERE status IN ('queued','scripting','rendering')"):
        db.update_video(v["id"], status="failed", error="Interrupted by a server restart. Use Retry.")


def _bad(e: Exception, code=400):
    raise HTTPException(status_code=code, detail=str(e))


# ---------------------------------------------------------------- status
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    return {
        "gemini": llm.configured(), "gemini_model": settings.GEMINI_MODEL,
        "stock_footage": stock.configured(),
        "pexels": bool(settings.PEXELS_API_KEY), "pixabay": bool(settings.PIXABAY_API_KEY),
        "voice_engine": settings.VOICE_ENGINE, "voice_engines": voice.engines(), "kokoro_voices": voice.KOKORO_VOICES,
        "formats": FORMATS, "motion": motion.available(), "arts": motion.ART_CHOICES, "icons": {k: True for k in motion.ICONS}, "themes": {k: v["for"] for k, v in __import__("app.services.design", fromlist=["PRESETS"]).PRESETS.items()},
    }


# ---------------------------------------------------------------- brands
class BrandIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    industry: str = ""
    about: str = ""
    audience: str = ""
    tone: str = "warm, clear, professional"
    language: str = Field("en", pattern="^(en|hi)$")
    voice: str = ""
    primary_color: str = Field("#1F4E79", pattern=r"^#[0-9a-fA-F]{6}$")
    accent_color: str = Field("#F2A900", pattern=r"^#[0-9a-fA-F]{6}$")
    avoid: str = ""
    cta: str = ""


@app.get("/api/brands")
def brands():
    return [{**b, "has_logo": bool(b["logo_path"])} for b in db.list_brands()]


@app.post("/api/brands")
def brand_create(b: BrandIn):
    try:
        assert_clean(b.about, b.audience, b.avoid, b.cta)
    except ValueError as e:
        _bad(e)
    return db.create_brand(b.model_dump())


@app.put("/api/brands/{bid}")
def brand_update(bid: int, b: BrandIn):
    if not db.get_brand(bid):
        _bad(Exception("Brand not found"), 404)
    try:
        assert_clean(b.about, b.audience, b.avoid, b.cta)
    except ValueError as e:
        _bad(e)
    return db.update_brand(bid, b.model_dump())


@app.delete("/api/brands/{bid}")
def brand_delete(bid: int):
    for v in db.list_videos(bid, 1000):
        shutil.rmtree(DATA / "videos" / str(v["id"]), ignore_errors=True)
    shutil.rmtree(DATA / "footage" / str(bid), ignore_errors=True)
    db.delete_brand(bid)
    return {"ok": True}


@app.post("/api/brands/{bid}/logo")
async def brand_logo(bid: int, file: UploadFile = File(...)):
    if not db.get_brand(bid):
        _bad(Exception("Brand not found"), 404)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        _bad(Exception("Logo must be PNG, JPG or WEBP (PNG with transparent background is best)"))
    data = await file.read()
    if len(data) > 5_000_000:
        _bad(Exception("Logo is larger than 5 MB"))
    dest = DATA / "logos" / f"brand_{bid}{ext}"
    for old in (DATA / "logos").glob(f"brand_{bid}.*"):
        old.unlink()
    dest.write_bytes(data)
    db.update_brand(bid, {"logo_path": str(dest)})
    return {"ok": True}


@app.get("/api/brands/{bid}/logo")
def brand_logo_get(bid: int):
    b = db.get_brand(bid)
    if not b or not b["logo_path"] or not Path(b["logo_path"]).exists():
        raise HTTPException(404, "No logo")
    return FileResponse(b["logo_path"])


# ---------------------------------------------------------------- own footage
@app.get("/api/brands/{bid}/footage")
def footage_list(bid: int):
    return db.list_footage(bid)


@app.post("/api/brands/{bid}/footage")
async def footage_add(bid: int, file: UploadFile = File(...), tags: str = Form("")):
    if not db.get_brand(bid):
        _bad(Exception("Brand not found"), 404)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".mp4", ".mov", ".webm", ".mkv", ".m4v"):
        _bad(Exception("Footage must be MP4, MOV, WEBM or MKV"))
    try:
        assert_clean(tags)
    except ValueError as e:
        _bad(e)
    folder = DATA / "footage" / str(bid)
    folder.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in Path(file.filename).stem)[:60] or "clip"
    dest = folder / f"{safe}_{uuid.uuid4().hex[:6]}{ext}"
    size = 0
    with open(dest, "wb") as f:  # stream to disk, never hold a big video in memory
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > 500_000_000:
                f.close()
                dest.unlink(missing_ok=True)
                _bad(Exception("File is larger than 500 MB. Trim or compress it first."))
            f.write(chunk)
    try:
        dur = library.probe_duration(str(dest))
    except ValueError as e:
        dest.unlink(missing_ok=True)
        _bad(e)
    return db.add_footage(bid, file.filename, str(dest), tags.strip(), dur)


@app.delete("/api/footage/{fid}")
def footage_delete(fid: int):
    c = db.get_footage(fid)
    if c:
        Path(c["path"]).unlink(missing_ok=True)
        db.delete_footage(fid)
    return {"ok": True}


# ---------------------------------------------------------------- memory
class MemoryIn(BaseModel):
    kind: str = Field("fact", pattern="^(fact|feedback)$")
    text: str = Field(min_length=3, max_length=500)


@app.get("/api/brands/{bid}/memories")
def memories(bid: int):
    return db.list_memories(bid)


@app.post("/api/brands/{bid}/memories")
def memory_add(bid: int, m: MemoryIn):
    if not db.get_brand(bid):
        _bad(Exception("Brand not found"), 404)
    try:
        assert_clean(m.text)
    except ValueError as e:
        _bad(e)
    return db.add_memory(bid, m.kind, m.text)


@app.delete("/api/memories/{mid}")
def memory_delete(mid: int):
    db.delete_memory(mid)
    return {"ok": True}


# ---------------------------------------------------------------- ideas
class IdeasIn(BaseModel):
    brand_id: int
    brief: str = Field(min_length=3, max_length=4000)
    format: str = "linkedin"
    language: str = Field("en", pattern="^(en|hi)$")
    count: int = Field(5, ge=1, le=8)


@app.post("/api/ideas")
def ideas(req: IdeasIn):
    brand = db.get_brand(req.brand_id)
    if not brand:
        _bad(Exception("Brand not found"), 404)
    if req.format not in FORMATS:
        _bad(Exception(f"Unknown format {req.format}"))
    try:
        assert_clean(req.brief)
        return llm.generate_ideas(brand, req.brief, req.format, req.language, req.count)
    except ValueError as e:
        _bad(e)
    except RuntimeError as e:
        _bad(e, 502)


# ---------------------------------------------------------------- videos
class VideoIn(BaseModel):
    brand_id: int
    brief: str = Field(min_length=3, max_length=4000)
    format: str = "linkedin"
    language: str = Field("en", pattern="^(en|hi)$")
    idea: Optional[dict] = None
    voice_engine: str = ""
    style: str = Field("motion", pattern="^(motion|footage)$")
    length_min: int = Field(0, ge=0, le=30)
    use_ai: bool = False
    structure: str = Field("", pattern="^(|story|list)$")


class SceneIn(BaseModel):
    title: str = ""
    narration: str = Field(min_length=1, max_length=600)
    caption: str = ""
    stock_query: str = ""
    must_match: str = ""
    art: str = ""
    points: List[str] = []
    icons: List[str] = []
    number: str = ""
    chapter: int = 0
    values: List[float] = []
    unit: str = ""
    ai_clip: bool = False
    ai_prompt: str = ""


class ScriptIn(BaseModel):
    title: str = ""
    scenes: List[SceneIn] = Field(min_length=1, max_length=300)
    theme: str = ""
    design: Optional[dict] = None
    cta: str = ""
    post_caption: str = ""
    pinned_comment: str = ""
    hashtags: List[str] = []


def _video(vid: int):
    v = db.get_video(vid)
    if not v:
        raise HTTPException(404, "Video not found")
    d = DATA / "videos" / str(vid)
    v["has_file"] = (d / "final.mp4").exists()
    v["clips"] = sorted(int(p.stem.split("_")[1]) for p in (d / "clips").glob("scene_*.mp4")) if (d / "clips").exists() else []
    v["post_text"] = (d / "post.txt").read_text(encoding="utf-8") if (d / "post.txt").exists() else ""
    v["pinned_comment"] = (d / "pinned_comment.txt").read_text(encoding="utf-8") if (d / "pinned_comment.txt").exists() else ""
    return v


@app.post("/api/videos")
def video_create(req: VideoIn):
    brand = db.get_brand(req.brand_id)
    if not brand:
        _bad(Exception("Brand not found"), 404)
    if req.format not in FORMATS:
        _bad(Exception(f"Unknown format {req.format}"))
    try:
        assert_clean(req.brief)
    except ValueError as e:
        _bad(e)
    v = db.create_video(brand_id=req.brand_id, brief=req.brief, format=req.format, language=req.language,
                        voice_engine=req.voice_engine, style=req.style, length_min=req.length_min if req.format == "youtube" else 0, use_ai=int(req.use_ai),
                        structure=req.structure if req.format == "youtube" else "", idea_json=json.dumps(req.idea or {}, ensure_ascii=False) if req.idea else "",
                        title=(req.idea or {}).get("title", req.brief[:60]), status="queued", step="Queued")
    pipeline.submit_script(v["id"])
    return v


@app.get("/api/videos")
def videos(brand_id: Optional[int] = None):
    return db.list_videos(brand_id)


@app.get("/api/videos/{vid}")
def video_get(vid: int):
    return _video(vid)


@app.put("/api/videos/{vid}/script")
def video_script_save(vid: int, s: ScriptIn):
    v = _video(vid)
    if v["status"] in ("scripting", "rendering"):
        _bad(Exception("Wait until the current step finishes"), 409)
    try:
        assert_clean(s.post_caption, *(sc.narration for sc in s.scenes))
    except ValueError as e:
        _bad(e)
    cur = v["script"] or {}
    cur.update({k: val for k, val in s.model_dump().items() if val not in (None, "")})
    db.update_video(vid, script_json=json.dumps(cur, ensure_ascii=False), title=s.title or v["title"],
                    status="script_ready", step="Script saved", approved=0)
    return _video(vid)


@app.post("/api/videos/{vid}/clips/{scene}")
async def video_clip_upload(vid: int, scene: int, file: UploadFile = File(...)):
    """Attach an AI clip you made elsewhere (e.g. in the Gemini app) to one scene. Used when 'AI video clips' is on."""
    _video(vid)
    if Path(file.filename or "").suffix.lower() not in (".mp4", ".mov", ".webm"):
        _bad(Exception("Clip must be MP4, MOV or WEBM"))
    d = DATA / "videos" / str(vid) / "clips"
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"scene_{scene}.mp4"
    tmp = d / f"upload_{scene}{Path(file.filename).suffix.lower()}"
    with open(tmp, "wb") as f:
        while chunk := await file.read(1 << 20):
            f.write(chunk)
    if tmp.suffix != ".mp4":
        import subprocess
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(dest)], check=True)
        tmp.unlink(missing_ok=True)
    else:
        tmp.replace(dest)
    return {"ok": True, "scene": scene}


@app.delete("/api/videos/{vid}/clips/{scene}")
def video_clip_delete(vid: int, scene: int):
    (DATA / "videos" / str(vid) / "clips" / f"scene_{scene}.mp4").unlink(missing_ok=True)
    return {"ok": True}


@app.post("/api/videos/{vid}/render")
def video_render(vid: int):
    v = _video(vid)
    if not v["script"]:
        _bad(Exception("No script yet"), 409)
    if v["status"] in ("scripting", "rendering"):
        _bad(Exception("Already running"), 409)
    db.update_video(vid, status="rendering", step="Queued for rendering", progress=1, error="")
    pipeline.submit_render(vid)
    return _video(vid)


@app.post("/api/videos/{vid}/script/redo")
def video_script_redo(vid: int):
    v = _video(vid)
    if v["status"] in ("scripting", "rendering"):
        _bad(Exception("Already running"), 409)
    db.update_video(vid, status="queued", step="Queued", progress=0, error="")
    pipeline.submit_script(vid)
    return _video(vid)


# ---------------------------------------------------------------- playlists (a series of videos on one topic)
class PlaylistIn(BaseModel):
    brand_id: int
    topic: str = Field(min_length=3, max_length=2000)
    format: str = "short"
    language: str = Field("en", pattern="^(en|hi)$")
    style: str = Field("motion", pattern="^(motion|footage)$")
    count: int = Field(5, ge=2, le=10)
    length_min: int = Field(5, ge=0, le=20)
    structure: str = Field("", pattern="^(|story|list)$")
    voice_engine: str = ""
    use_ai: bool = False


def _playlist(pid: int):
    p = db.get_playlist(pid)
    if not p:
        raise HTTPException(404, "Playlist not found")
    p["videos"] = [{k: v[k] for k in ("id", "episode", "title", "status", "step", "progress", "error")} for v in db.playlist_videos(pid)]
    return p


@app.post("/api/playlists")
def playlist_create(req: PlaylistIn):
    """Plan the series with one Gemini request, then queue every episode's script (they are written one after another)."""
    brand = db.get_brand(req.brand_id)
    if not brand:
        _bad(Exception("Brand not found"), 404)
    if req.format not in FORMATS:
        _bad(Exception(f"Unknown format {req.format}"))
    try:
        assert_clean(req.topic)
        plan = llm.plan_playlist(brand, req.topic, req.format, req.language, req.count,
                                 req.length_min if req.format == "youtube" else 0, req.structure)
    except ValueError as e:
        _bad(e)
    except Exception as e:
        _bad(Exception(f"Playlist planning failed: {e}"), 502)
    yt = req.format == "youtube"
    p = db.create_playlist(brand_id=req.brand_id, title=plan["series_title"], topic=req.topic, format=req.format, language=req.language,
                           style=req.style, length_min=req.length_min if yt else 0, structure=req.structure if yt else "",
                           plan_json=json.dumps(plan, ensure_ascii=False))
    for n, ep in enumerate(plan["episodes"], 1):
        v = db.create_video(brand_id=req.brand_id, brief=llm.episode_brief(req.topic, plan, n), format=req.format, language=req.language,
                            voice_engine=req.voice_engine, style=req.style, length_min=req.length_min if yt else 0, use_ai=int(req.use_ai),
                            structure=req.structure if yt else "", playlist_id=p["id"], episode=n,
                            idea_json=json.dumps(ep, ensure_ascii=False), title=ep["title"], status="queued", step="Queued")
        pipeline.submit_script(v["id"])
    return _playlist(p["id"])


@app.get("/api/playlists")
def playlists(brand_id: Optional[int] = None):
    return [_playlist(p["id"]) for p in db.list_playlists(brand_id)]


@app.get("/api/playlists/{pid}")
def playlist_get(pid: int):
    return _playlist(pid)


@app.post("/api/playlists/{pid}/render")
def playlist_render(pid: int):
    """Render every episode whose script is ready (review the scripts first)."""
    started = []
    for v in db.playlist_videos(_playlist(pid)["id"]):
        if v["status"] == "script_ready" and v["script"]:
            db.update_video(v["id"], status="rendering", step="Queued for rendering", progress=1, error="")
            pipeline.submit_render(v["id"])
            started.append(v["id"])
    return {"started": started}


class FeedbackIn(BaseModel):
    note: str = Field(min_length=3, max_length=400)


@app.post("/api/videos/{vid}/feedback")
def video_feedback(vid: int, f: FeedbackIn):
    """Your notes become brand memory: they shape every future script for this brand."""
    v = _video(vid)
    try:
        assert_clean(f.note)
    except ValueError as e:
        _bad(e)
    db.add_memory(v["brand_id"], "feedback", f.note)
    return {"ok": True}


@app.post("/api/videos/{vid}/approve")
def video_approve(vid: int):
    v = _video(vid)
    if v["status"] != "review":
        _bad(Exception("Only a rendered video can be approved"), 409)
    db.update_video(vid, approved=1, status="approved", step="Approved by a human. Download and post it yourself.")
    db.add_memory(v["brand_id"], "video", f"{v['title']} ({FORMATS[v['format']]['label']}, {v['language']})")
    return _video(vid)


@app.delete("/api/videos/{vid}")
def video_delete(vid: int):
    shutil.rmtree(DATA / "videos" / str(vid), ignore_errors=True)
    db.delete_video(vid)
    return {"ok": True}


def _file(vid: int, name: str, media: str, download: Optional[str] = None):
    p = DATA / "videos" / str(vid) / name
    if not p.exists():
        raise HTTPException(404, "Not available yet")
    return FileResponse(p, media_type=media, filename=download)


@app.get("/api/videos/{vid}/file")
def video_file(vid: int, download: bool = False):
    v = _video(vid)
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in v["title"])[:50] or f"video_{vid}"
    return _file(vid, "final.mp4", "video/mp4", f"{safe}.mp4" if download else None)


@app.get("/api/videos/{vid}/voice-only")
def video_voice_only(vid: int):
    """Same video without the music bed: add a licensed trending song in the YouTube Shorts / Instagram editor."""
    return _file(vid, "voice_only.mp4", "video/mp4", f"video_{vid}_voice_only.mp4")


@app.get("/api/videos/{vid}/thumb")
def video_thumb(vid: int, download: bool = False):
    return _file(vid, "thumb.jpg", "image/jpeg", f"thumbnail_{vid}.jpg" if download else None)


@app.get("/api/videos/{vid}/post", response_class=PlainTextResponse)
def video_post(vid: int):
    return _video(vid)["post_text"]


# ---------------------------------------------------------------- voice test
class VoiceTestIn(BaseModel):
    text: str = Field(min_length=2, max_length=300)
    language: str = Field("en", pattern="^(en|hi)$")
    engine: str = "kokoro"
    voice: str = ""


@app.post("/api/voice/test")
def voice_test(req: VoiceTestIn):
    out = DATA / "voice_tests" / f"test_{req.engine}_{req.language}_{req.voice or 'default'}.wav"
    try:
        voice.synthesize(req.text, req.language, str(out), req.engine, req.voice)
    except Exception as e:
        _bad(e, 502)
    return FileResponse(out, media_type="audio/wav")


# ---------------------------------------------------------------- web UI
app.mount("/", StaticFiles(directory=str(BASE_DIR / "web"), html=True), name="web")

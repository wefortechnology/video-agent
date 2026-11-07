"""Video pipeline. Two human-gated stages:
   1) create  -> script is written            (status: script_ready, you edit/approve the words)
   2) render  -> voice + footage + captions   (status: review, you watch it, then approve)
Nothing is ever posted automatically."""
import json
import logging
import shutil
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from app import db
from app.config import DATA, settings
from app.formats import get_format
from app.services import library, llm, motion, music, render, stock, voice

log = logging.getLogger("pipeline")
_pool = ThreadPoolExecutor(max_workers=1)  # CPU-bound (TTS + ffmpeg); one video at a time on a laptop


def video_dir(vid: int) -> Path:
    d = DATA / "videos" / str(vid)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _set(vid: int, **kw):
    db.update_video(vid, **kw)


def submit_script(vid: int):
    _pool.submit(_safe, vid, _script_job)


def submit_render(vid: int):
    _pool.submit(_safe, vid, _render_job)


def _safe(vid: int, fn):
    try:
        fn(vid)
    except Exception as e:  # surface the real reason in the UI
        log.error("Video %s failed: %s\n%s", vid, e, traceback.format_exc())
        msg = str(e)
        if "per day" in msg or "free_tier" in msg:
            msg = ("Gemini free-tier daily limit reached on all models. Finished chapters are saved: press Retry later "
                   "(limits reset daily) or enable billing on the key. Details: " + msg[:400])
        _set(vid, status="failed", error=msg[:800])


def _script_job(vid: int):
    v = db.get_video(vid)
    brand = db.get_brand(v["brand_id"])
    _set(vid, status="scripting", step="Writing the script...", progress=10, error="")
    def prog(step, pct):
        _set(vid, step=step, progress=pct)
    ckpt = video_dir(vid) / "script_partial.json"
    script = llm.generate_script(brand, v["brief"], v["idea"], v["format"], v["language"], v.get("style") or "motion",
                                 int(v.get("length_min") or 0), prog, ckpt, bool(v.get("use_ai")), v.get("structure") or "")
    ckpt.unlink(missing_ok=True)
    _set(vid, script_json=json.dumps(script, ensure_ascii=False), title=script.get("title") or v["title"],
         status="script_ready", step="Script ready: review and edit it, then render", progress=100)


def _render_job(vid: int):
    v = db.get_video(vid)
    brand = db.get_brand(v["brand_id"])
    script = v["script"]
    fmt = get_format(v["format"])
    lang = v["language"]
    engine = v["voice_engine"] or settings.VOICE_ENGINE
    work = video_dir(vid) / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    logo = brand["logo_path"] if brand["logo_path"] and Path(brand["logo_path"]).exists() else None
    scenes = script["scenes"]
    n = len(scenes)
    if (v.get("style") or "footage") == "motion":
        return _render_motion(vid, v, brand, script, fmt, lang, engine, work, logo)
    used: set = set()
    credits, segments = [], []

    for i, sc in enumerate(scenes):
        base = 5 + int(80 * i / n)
        _set(vid, status="rendering", step=f"Scene {i + 1}/{n}: voiceover", progress=base)
        wav = work / f"scene{i}.wav"
        secs = voice.synthesize(sc["narration"], lang, str(wav), engine, brand.get("voice", ""), speed=voice.speed_for(lang))

        _set(vid, step=f"Scene {i + 1}/{n}: footage", progress=base + int(80 / n * 0.35))
        queries = stock.split_queries(sc.get("stock_query") or "")
        n_shots = max(1, min(3, round((secs + 0.5) / 3.2)))  # a new shot about every 3 seconds keeps it lively
        shots = []
        lib = library.pick(brand["id"], " ".join(queries) + " " + (sc.get("title") or ""), used)  # 1) the brand's own footage first
        while lib and len(shots) < n_shots:
            lib["kind"] = "video"
            shots.append(lib)
            lib = library.pick(brand["id"], " ".join(queries), used) if len(shots) < n_shots else None
        if len(shots) < n_shots and stock.configured():  # 2) stock, chosen by tags then checked by eye (Gemini)
            shots += stock.find_shots(queries, fmt["orientation"], used, need=n_shots - len(shots), min_seconds=min(secs / n_shots, 4),
                                      must=stock.split_must(sc.get("must_match") or ""),
                                      scene_text=f"{sc.get('narration', '')} ({sc.get('caption', '')})",
                                      topic=stock.split_must(script.get("topic_keywords") or v["brief"]))
        credits += [x["credit"] for x in shots if x.get("credit")]

        _set(vid, step=f"Scene {i + 1}/{n}: assembling", progress=base + int(80 / n * 0.6))
        seg = work / f"seg{i}.mp4"
        render.render_scene(seg, work, i, fmt, lang, brand, sc.get("caption") or sc["narration"], str(wav), secs, shots, logo)
        segments.append(seg)

    _set(vid, step="End card and final cut", progress=92)
    end = work / "end.mp4"
    render.render_end_card(end, work, fmt, lang, brand, script.get("cta") or brand.get("cta") or "", logo)
    segments.append(end)
    final = video_dir(vid) / "final.mp4"
    render.concat(segments, final, work)
    _set(vid, step="Designing the thumbnail", progress=97)
    from app.services import design as dsg
    dz = dsg.normalise(script.get("design") or {}, f"{v['brief']} {script.get('title', '')}", brand)
    make_thumbnail(vid, v, brand, script, fmt, dz, {}, work)  # designed, like motion videos (falls back to a frame)
    embed_covers(vid)

    tags = " ".join("#" + t.lstrip("#") for t in script.get("hashtags", []))
    post = f"{script.get('post_caption', '')}{_series_line(v)}\n\n{tags}".strip()
    if credits:
        post += "\n\nFootage: " + ", ".join(sorted(set(credits)))
    (video_dir(vid) / "post.txt").write_text(post, encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    note = "" if (stock.configured() or db.list_footage(brand["id"])) else " (no footage available: branded background used)"
    _set(vid, status="review", step="Ready for your review" + note, progress=100)


FESTIVE_WORDS = ("diwali", "deepavali", "festival", "holi", "eid", "christmas", "navratri", "pongal", "onam", "raksha", "new year",
                 "दिवाली", "दीपावली", "त्योहार", "होली", "ईद")


def _is_festive(v, script) -> bool:
    text = f"{v['brief']} {script.get('topic_keywords', '')} {script.get('title', '')}".lower()
    return any(w in text for w in FESTIVE_WORDS)


def make_thumbnail(vid, v, brand, script, fmt, dz, photos, work):
    """Designed thumbnail: Gemini's thumbnail text + a striking photo, in the video's design. Never fails the video."""
    from app.services import thumbnail
    out = video_dir(vid) / "thumb.jpg"
    try:
        text = (script.get("thumbnail_text") or " ".join((script.get("title") or v["title"]).split()[:5])).strip()
        photo = None
        if script.get("thumbnail_photo"):
            topic = stock.split_must(script.get("topic_keywords") or "")
            # the photo's tags must mention the topic (a fancy query alone once returned a "WORK HARDER" neon sign)
            photo = (stock.find_photo([script["thumbnail_photo"]] + topic[:2], set(), topic, topic) if topic else None) \
                or stock.find_photo([script["thumbnail_photo"]], set(), [], topic)
        if not photo and photos:
            photo = next(iter(photos.values()))
        logo = brand.get("logo_path") if brand.get("logo_path") and Path(brand["logo_path"]).exists() else None
        thumbnail.make(out, work, fmt, dz, brand, text, script.get("thumbnail_highlight") or "", photo, script.get("thumbnail_tag") or "", logo)
    except Exception as e:
        log.warning("designed thumbnail failed (%s); using a frame", e)
        render.thumbnail(video_dir(vid) / "final.mp4", out, 2.0)


def embed_covers(vid):
    """The designed thumbnail becomes the cover picture of final.mp4 and voice_only.mp4. Never fails the video."""
    d = video_dir(vid)
    for name in ("final.mp4", "voice_only.mp4"):
        if (d / name).exists() and (d / "thumb.jpg").exists():
            try:
                render.embed_cover(d / name, d / "thumb.jpg")
            except Exception as e:
                log.warning("cover for %s failed: %s", name, e)


def _series_line(v) -> str:
    """'Part 2/5 · <playlist title>' for playlist episodes."""
    if not v.get("playlist_id"):
        return ""
    p = db.get_playlist(v["playlist_id"])
    if not p:
        return ""
    n = len(p["plan"].get("episodes") or [])
    return f"\n\n{'भाग' if v['language'] == 'hi' else 'Part'} {v['episode']}/{n} · {p['title']}"


def _ts(sec: float) -> str:
    sec = int(round(sec))
    h, m, x = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h}:{m:02d}:{x:02d}" if h else f"{m}:{x:02d}"


def _render_motion(vid, v, brand, script, fmt, lang, engine, work, logo):
    """2D motion graphics: every scene is an animated illustration timed to its voiceover (HyperFrames).
    Long YouTube videos get a chapter card before each chapter and chapter timestamps in the description."""
    from concurrent.futures import ThreadPoolExecutor
    if not motion.available():
        raise RuntimeError("Motion engine not installed (~/.video-studio/hyperframes). Choose the Footage style, or run video-studio setup.")
    scenes = script["scenes"]
    n = len(scenes)
    from app.services import design as dsg
    raw = script.get("design") or ({"theme": script["theme"]} if script.get("theme") else {"preset": "festive-night"} if _is_festive(v, script) else {})
    dz = dsg.normalise(raw, f"{v['brief']} {script.get('title', '')}", brand)
    festive = dz["preset"] == "festive-night"
    theme = ""
    chapters = script.get("chapters") or []
    long_form = v["format"] == "youtube" and len(chapters) >= 2
    fps = 24 if v["format"] == "youtube" else 30
    ch_label = "अध्याय" if lang == "hi" else "Chapter"

    # 1) voice every scene first (Kokoro is single-threaded), so we know each scene's length
    voiced = []
    for i, sc in enumerate(scenes):
        _set(vid, status="rendering", step=f"Voiceover {i + 1}/{n}", progress=2 + int(13 * i / n))
        wav = work / f"scene{i}.wav"
        voiced.append((wav, voice.synthesize(sc["narration"], lang, str(wav), engine, brand.get("voice", ""), speed=voice.speed_for(lang))))

    # 2) the render plan: chapter cards + scenes, with varied animations; real photos for 'photo' scenes
    arts = motion.assign_arts(scenes, festive, seed=f"{vid}:{script.get('title', '')}")
    used_photos: set = set()
    topic = stock.split_must(script.get("topic_keywords") or "")
    photos = {}
    for i, sc in enumerate(scenes):
        if arts[i] in motion.PHOTO_ARTS:
            _set(vid, step=f"Finding photos {i + 1}/{n}", progress=15)
            path = stock.find_photo(stock.split_queries(sc.get("stock_query") or ""), used_photos,
                                    stock.split_must(sc.get("must_match") or ""), topic)
            if path:
                photos[i] = path
            else:
                arts[i] = "orbit" if (i == 0 or arts[i - 1] != "orbit") else "quote"
    plan, prev_ch = [], None
    for i, sc in enumerate(scenes):
        ch = sc.get("chapter")
        if long_form and ch and ch != prev_ch and ch - 1 < len(chapters) and i > 0:  # the video opens on the hook, not a title card
            plan.append(("chapter", ch))
        prev_ch = ch
        plan.append(("scene", i))
    # optional AI hero clips: uploaded ones first, then the API; anything missing stays an animation
    from app.services import aivideo
    ai_sess = aivideo.Session()
    ai_paths = {}
    if v.get("use_ai"):
        clip_dir = video_dir(vid) / "clips"
        clip_dir.mkdir(exist_ok=True)
        wanted = [i for i, sc in enumerate(scenes) if sc.get("ai_clip")][: settings.AI_MAX_CLIPS]
        aspect = "16:9" if fmt["w"] > fmt["h"] else "9:16"
        for k, i in enumerate(wanted):
            _set(vid, step=f"AI clip {k + 1}/{len(wanted)}" + ("" if ai_sess.api_ok else " (using uploads only)"), progress=15)
            path, _src = aivideo.get_clip(ai_sess, scenes[i].get("ai_prompt") or "", clip_dir / f"scene_{i}.mp4",
                                          clip_dir / f"gen_{i}.mp4", aspect)
            if path:
                ai_paths[i] = path
    done = {"n": 0}
    total = len(plan)

    def job(k):
        kind, ref = plan[k]
        seg = work / f"seg{k:04d}.mp4"
        if kind == "chapter":
            dur = motion.render_motion_scene(seg, work, f"c{ref}", "chapter", fmt, brand, chapters[ref - 1]["title"], "", None, 0,
                                             seconds=3.0, festive=festive, data={"num": ref, "total": len(chapters), "label": ch_label},
                                             palette=ref, fps=fps, design=dz, logo=logo)
        elif ref in ai_paths:  # a real AI clip, with our captions, logo and voice on top
            sc, (wav, secs) = scenes[ref], voiced[ref]
            cap_brand = {**brand, "primary_color": "#111111"}
            dur = render.render_scene(seg, work, ref, fmt, lang, cap_brand, sc.get("caption") or sc["narration"], str(wav), secs,
                                      [{"path": ai_paths[ref], "kind": "video"}], logo, fps=fps)
        else:
            sc, (wav, secs) = scenes[ref], voiced[ref]
            data = {"points": sc.get("points") or [], "icons": sc.get("icons") or [], "number": sc.get("number") or "",
                    "values": sc.get("values") or [], "unit": sc.get("unit") or "", "photo_path": photos.get(ref)}
            kick = chapters[sc["chapter"] - 1]["title"] if long_form and sc.get("chapter") and sc["chapter"] - 1 < len(chapters) else ""
            dur = motion.render_motion_scene(seg, work, f"s{ref}", arts[ref], fmt, brand, sc.get("caption") or "", sc["narration"],
                                             str(wav), secs, festive=festive, data=data, palette=ref, kicker=kick, fps=fps, design=dz,
                                             mirror=(dz["layout"] == "left") or (dz["layout"] == "alternate" and ref % 2 == 1), logo=logo)
        done["n"] += 1
        _set(vid, step=f"Animating: {done['n']}/{total} parts done", progress=15 + int(77 * done["n"] / total))
        return seg, dur

    _set(vid, step=f"Animating: 0/{total} parts done", progress=15)
    with ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(job, range(total)))
    segments = [r[0] for r in results]
    cuts, t, stamps = [], 0.0, []
    if long_form and scenes[0].get("chapter") and scenes[0]["chapter"] - 1 < len(chapters):  # YouTube chapters must start at 0:00
        stamps.append(f"0:00 {chapters[scenes[0]['chapter'] - 1]['title']}")
    for (kind, ref), (_, dur) in zip(plan, results):
        if kind == "chapter":
            stamps.append(f"{_ts(t)} {chapters[ref - 1]['title']}")
        t += dur
        cuts.append(t)

    _set(vid, step="End card, music and final cut", progress=93)
    end = work / "end.mp4"
    motion.render_motion_scene(end, work, "end", "endcard", fmt, brand, "", "", None, 0, cta=script.get("cta") or brand.get("cta") or "",
                               logo=logo, seconds=2.0 if v["format"] in ("short", "reel") else 3.0, festive=festive, palette=total, fps=fps, design=dz)
    segments.append(end)
    final = video_dir(vid) / "final.mp4"
    render.concat(segments, final, work)
    shutil.copy(final, video_dir(vid) / "voice_only.mp4")  # for adding a licensed trending song in YouTube Shorts / Instagram
    if settings.MUSIC:
        funny = any(w in f"{v['brief']} {script.get('title', '')}".lower() for w in ("funny", "comedy", "meme", "hilarious", "joke", "मज़ेदार", "मजेदार"))
        music.add_to_video(final, "festive" if festive else "quirky" if funny else "uplift", cuts[:-1], t, work)
    _set(vid, step="Designing the thumbnail", progress=97)
    make_thumbnail(vid, v, brand, script, fmt, dz, photos, work)
    embed_covers(vid)
    tags = " ".join("#" + x.lstrip("#") for x in script.get("hashtags", []))
    chapters_txt = ("\n\n" + ("अध्याय" if lang == "hi" else "Chapters") + ":\n" + "\n".join(stamps)) if stamps else ""
    (video_dir(vid) / "post.txt").write_text(f"{script.get('post_caption', '')}{_series_line(v)}{chapters_txt}\n\n{tags}".strip(), encoding="utf-8")
    if script.get("pinned_comment"):
        (video_dir(vid) / "pinned_comment.txt").write_text(script["pinned_comment"].strip(), encoding="utf-8")
    shutil.rmtree(work, ignore_errors=True)
    _set(vid, status="review", step="Ready for your review" + (" · " + ai_sess.summary() if v.get("use_ai") else ""), progress=100)

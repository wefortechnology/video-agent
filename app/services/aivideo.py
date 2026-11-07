"""Optional AI video clips (Gemini omni-flash / Veo) for a few 'hero' scenes. Never fails a video.

Order per scene: 1) a clip you uploaded for that scene (e.g. made in the Gemini app with your Pro plan),
2) the Gemini API, if the key has video quota, 3) nothing: the scene falls back to motion graphics.
The first quota/permission error switches the API off for the rest of the video, so we do not waste time.
"""
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.config import settings

log = logging.getLogger("aivideo")


class Session:
    """One per video render: remembers whether the API is usable and why not."""

    def __init__(self):
        self.api_ok = bool(settings.GEMINI_API_KEY) and settings.AI_VIDEO_API
        self.reason = "" if self.api_ok else ("AI_VIDEO_API is off in .env" if settings.GEMINI_API_KEY else "no GEMINI_API_KEY")
        self.generated = 0
        self.uploaded = 0
        self.failed = 0

    def summary(self) -> str:
        parts = []
        if self.uploaded:
            parts.append(f"{self.uploaded} uploaded")
        if self.generated:
            parts.append(f"{self.generated} generated")
        if self.failed:
            parts.append(f"{self.failed} fell back to animation" + (f" ({self.reason})" if self.reason else ""))
        return "AI clips: " + (", ".join(parts) if parts else "none")


def _friendly(err: str) -> str:
    low = err.lower()
    if "limit: 0" in low or "free_tier" in low or "billing" in low:
        return "the API key has no video quota on the free tier; enable billing to use it"
    if "quota" in low or "429" in low:
        return "video quota used up for now"
    if "404" in low or "not found" in low:
        return "video model not available for this key"
    if "permission" in low or "403" in low:
        return "the key is not allowed to generate video"
    return err[:120]


def _save_inline(resp, dest: Path) -> bool:
    for cand in getattr(resp, "candidates", None) or []:
        for part in getattr(cand.content, "parts", None) or []:
            blob = getattr(part, "inline_data", None)
            if blob and (blob.mime_type or "").startswith("video") and blob.data:
                dest.write_bytes(blob.data)
                return True
    return False


def _try_omni(client, model: str, prompt: str, dest: Path) -> bool:
    from google.genai import types
    resp = client.models.generate_content(model=model, contents=prompt, config=types.GenerateContentConfig(response_modalities=["VIDEO"]))
    return _save_inline(resp, dest)


def _try_veo(client, model: str, prompt: str, aspect: str, dest: Path, timeout: int = 420) -> bool:
    from google.genai import types
    op = client.models.generate_videos(model=model, prompt=prompt,
                                       config=types.GenerateVideosConfig(aspect_ratio=aspect, number_of_videos=1))
    t0 = time.time()
    while not op.done:
        if time.time() - t0 > timeout:
            raise RuntimeError("video generation timed out")
        time.sleep(10)
        op = client.operations.get(op)
    vids = getattr(op.response, "generated_videos", None) or []
    if not vids:
        return False
    video = vids[0].video
    data = client.files.download(file=video)
    dest.write_bytes(data if isinstance(data, (bytes, bytearray)) else getattr(video, "video_bytes", b""))
    return dest.exists() and dest.stat().st_size > 0


def get_clip(sess: Session, prompt: str, uploaded: Optional[Path], dest: Path, aspect: str) -> Tuple[Optional[str], str]:
    """Return (path or None, source) where source is 'uploaded' | 'generated' | 'fallback'."""
    if uploaded and uploaded.exists() and uploaded.stat().st_size > 0:
        sess.uploaded += 1
        return str(uploaded), "uploaded"
    if not sess.api_ok or not prompt.strip():
        sess.failed += 1
        return None, "fallback"
    from app.services import llm
    client = llm._client()
    for model in [m.strip() for m in settings.AI_VIDEO_MODELS.split(",") if m.strip()]:
        try:
            ok = _try_veo(client, model, prompt, aspect, dest) if model.startswith("veo") else _try_omni(client, model, prompt, dest)
            if ok:
                sess.generated += 1
                log.info("AI clip generated with %s", model)
                return str(dest), "generated"
        except Exception as e:
            msg = str(e)
            log.warning("AI video with %s failed: %s", model, msg[:200])
            why = _friendly(msg)
            if "free tier" not in sess.reason:  # keep the most useful reason (no quota on the free tier) over a later 404
                sess.reason = why
    # every model refused: stop asking for the rest of this video
    sess.api_ok = False
    sess.failed += 1
    return None, "fallback"

"""Voiceover engines. Kokoro is the default: local, free, CPU-only. Gemini TTS is optional (uses your API quota)."""
import logging
import threading
import wave
from pathlib import Path
from typing import Dict

import numpy as np
import soundfile as sf

from app.config import settings

log = logging.getLogger("voice")

KOKORO_LANG = {"en": "en-us", "hi": "hi"}
KOKORO_DEFAULT_VOICE = {"en": "af_heart", "hi": "hf_alpha"}
KOKORO_VOICES = {
    "en": ["af_heart", "af_bella", "bf_emma", "am_michael", "bm_george"],
    "hi": ["hf_alpha", "hf_beta", "hm_omega", "hm_psi"],
}

_kokoro = None
_lock = threading.Lock()


def engines() -> Dict[str, dict]:
    models = Path(settings.KOKORO_MODELS_DIR)
    kok_ok = (models / "kokoro-v1.0.onnx").exists() and (models / "voices-v1.0.bin").exists()
    return {
        "kokoro": {"available": kok_ok, "cost": "free, local", "note": "" if kok_ok else f"Model files not found in {models}"},
        "gemini": {"available": bool(settings.GEMINI_API_KEY), "cost": "uses your Gemini API quota",
                   "note": "" if settings.GEMINI_API_KEY else "Add GEMINI_API_KEY to .env"},
        "chatterbox": {"available": False, "cost": "free, local (GPU recommended)", "note": "Planned: Hindi voice bake-off (not installed yet)"},
    }


def _get_kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        m = Path(settings.KOKORO_MODELS_DIR)
        _kokoro = Kokoro(str(m / "kokoro-v1.0.onnx"), str(m / "voices-v1.0.bin"))
    return _kokoro


def _kokoro_tts(text: str, language: str, voice: str, out: str, speed: float) -> None:
    voice = voice if voice in KOKORO_VOICES.get(language, []) else KOKORO_DEFAULT_VOICE[language]
    with _lock:  # one synthesis at a time; the ONNX session is not worth sharing across threads
        samples, sr = _get_kokoro().create(text, voice=voice, speed=speed, lang=KOKORO_LANG[language])
    sf.write(out, samples, sr)


def _gemini_tts(text: str, language: str, voice: str, out: str) -> None:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=settings.GEMINI_TTS_MODEL, contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice or settings.GEMINI_TTS_VOICE)))))
    pcm = resp.candidates[0].content.parts[0].inline_data.data
    with wave.open(out, "wb") as w:  # Gemini returns raw 16-bit mono PCM at 24 kHz
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)


def speed_for(language: str) -> float:
    return settings.VOICE_SPEED_HI if language == "hi" else settings.VOICE_SPEED_EN


def synthesize(text: str, language: str, out_path: str, engine: str = "", voice: str = "", speed: float = 1.0) -> float:
    """Write a WAV file and return its duration in seconds."""
    engine = engine or settings.VOICE_ENGINE
    text = text.strip()
    if not text:
        raise ValueError("Empty narration")
    if engine == "kokoro":
        if not engines()["kokoro"]["available"]:
            raise RuntimeError(engines()["kokoro"]["note"])
        _kokoro_tts(text, language, voice, out_path, speed)
    elif engine == "gemini":
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Gemini TTS needs GEMINI_API_KEY in .env")
        _gemini_tts(text, language, voice, out_path)
    else:
        raise RuntimeError(f"Voice engine '{engine}' is not available yet. Use 'kokoro' or 'gemini'.")
    info = sf.info(out_path)
    return info.frames / info.samplerate

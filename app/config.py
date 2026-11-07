"""Settings, loaded from environment or the project-level .env file."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # Gemini (script, ideas, optional TTS). Never commit the key; put it in .env
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.5-flash,gemini-3.8-flash,gemini-flash-lite-latest,gemini-3.5-flash-lite,gemini-3.1-flash-lite"
    # Seconds between Gemini calls (free tier allows ~5 per minute). Set 0 on a paid key.
    GEMINI_MIN_INTERVAL: float = 13.0
    GEMINI_TTS_MODEL: str = "gemini-2.5-flash-preview-tts"
    GEMINI_TTS_VOICE: str = "Kore"

    # Free stock footage (at least one recommended)
    # Let Gemini look at footage thumbnails and reject poor or off-topic shots (one extra Gemini call per scene)
    VISION_CHECK: bool = True
    # Optional AI video clips for a few hero scenes (needs a key with video quota; falls back to animation otherwise)
    AI_VIDEO_API: bool = True
    AI_VIDEO_MODELS: str = "gemini-omni-1.2-flash,gemini-omni-flash-preview,veo-3.1-fast-generate-preview"
    AI_MAX_CLIPS: int = 3
    # Procedural music bed (ducked under the voice) + whoosh on cuts, for motion videos
    MUSIC: bool = True

    PEXELS_API_KEY: str = ""
    PIXABAY_API_KEY: str = ""

    # Voice: kokoro (local, free) | gemini
    VOICE_ENGINE: str = "kokoro"
    # Kokoro speaking speed per language (measured: Hindi 1.0 = 178 words/min, English 1.0 = 219 words/min).
    # Top explainer channels speak at 165-205 words/min, so Hindi is nudged up and English down.
    VOICE_SPEED_HI: float = 1.15  # real script lines (commas, "!") average ~160 wpm at 1.05; 1.15 gives ~175
    VOICE_SPEED_EN: float = 0.9
    KOKORO_MODELS_DIR: str = str(Path.home() / ".video-studio" / "models")

    DATA_DIR: str = str(BASE_DIR / "data")
    HOST: str = "127.0.0.1"
    PORT: int = 8010

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), env_file_encoding="utf-8", extra="ignore")


settings = Settings()
settings.KOKORO_MODELS_DIR = str(Path(settings.KOKORO_MODELS_DIR).expanduser())  # allow ~ in .env
settings.DATA_DIR = str(Path(settings.DATA_DIR).expanduser())
DATA = Path(settings.DATA_DIR)
for sub in ("videos", "logos", "cache/stock", "voice_tests"):
    (DATA / sub).mkdir(parents=True, exist_ok=True)
FONTS_DIR = BASE_DIR / "assets" / "fonts"

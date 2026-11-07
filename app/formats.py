"""Platform presets. One place that knows what each destination needs."""
from typing import Dict, Any

FORMATS: Dict[str, Dict[str, Any]] = {
    "linkedin": {
        "label": "LinkedIn post video", "w": 1080, "h": 1080, "orientation": "square",
        "seconds": 40, "scene_seconds": 7, "caption_margin": 0.10,
        "tip": "Square, 30-45s, hook in the first 3 seconds, captions on (most people watch muted).",
    },
    "reel": {
        "label": "Instagram Reel", "w": 1080, "h": 1920, "orientation": "portrait",
        "seconds": 25, "scene_seconds": 5, "caption_margin": 0.20,
        "tip": "Vertical, 15-30s, fast cuts, big captions kept clear of the app buttons.",
    },
    "short": {
        "label": "YouTube Short", "w": 1080, "h": 1920, "orientation": "portrait",
        "seconds": 40, "scene_seconds": 5.5, "caption_margin": 0.20,
        "tip": "Vertical, 30-50s, one idea: a hook in the first line, fast spoken pace, and an ending that loops back to the start.",
    },
    "youtube": {
        "label": "YouTube video", "w": 1920, "h": 1080, "orientation": "landscape",
        "seconds": 150, "scene_seconds": 8, "caption_margin": 0.08,
        "tip": "Widescreen explainer in chapters. Length: Auto (the content decides, usually 6-12 min) or pick one. Rendering takes roughly 3-4x the video length on this laptop.",
    },
}

# Narration speed used to size the script (words per second)
WPS = {"en": 3.1, "hi": 2.9}


def get_format(key: str) -> Dict[str, Any]:
    if key not in FORMATS:
        raise KeyError(f"Unknown format '{key}'. Choose one of: {', '.join(FORMATS)}")
    return FORMATS[key]

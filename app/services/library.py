"""The brand's own footage library: clips the team uploads (office, events, product). Needs no API and no key."""
import re
import subprocess
from pathlib import Path
from typing import Optional, Set

from app import db

STOP = {"the", "a", "an", "and", "of", "in", "on", "for", "to", "with", "is", "are", "at", "our", "your"}


def _words(text: str) -> Set[str]:
    return {w for w in re.findall(r"[\w']+", (text or "").lower()) if len(w) > 2 and w not in STOP}


def probe_duration(path: str) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        raise ValueError("This file is not a readable video")


def pick(brand_id: int, query: str, used: Set[str]) -> Optional[dict]:
    """Best tag/filename match first; otherwise a clip not used yet in this video. Own footage is on-brand, so reuse beats a blank background."""
    allc = [c for c in db.list_footage(brand_id) if Path(c["path"]).exists()]
    if not allc:
        return None
    clips = [c for c in allc if f"lib_{c['id']}" not in used] or allc  # all used already: reuse own footage rather than a blank background
    q = _words(query)

    def score(c):
        return len(q & _words(c["tags"] + " " + Path(c["filename"]).stem.replace("_", " ").replace("-", " ")))

    best = max(clips, key=score)
    chosen = best if score(best) > 0 else clips[0]
    used.add(f"lib_{chosen['id']}")
    return {"path": chosen["path"], "credit": "", "page": "", "key": f"lib_{chosen['id']}"}

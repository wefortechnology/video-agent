"""Designed thumbnails (instead of a random frame): big 2-4 word title with one highlighted word, a real photo,
the video's design colours and fonts, and the channel name. Rendered with HyperFrames (1-second composition),
then the last frame is saved as JPG. Sizes: YouTube 1280x720, Shorts/Reels 1080x1920, LinkedIn 1080x1080.
"""
import html
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

from app.config import FONTS_DIR

HF_HOME = Path(os.environ.get("VEODRIVE_VIDEO_HOME", Path.home() / ".video-studio")) / "hyperframes"

PAGE = """<!doctype html><html><head><meta charset="UTF-8"><script src="gsap.min.js"></script><style>
{faces}
:root {{ {vars} }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body, #root {{ width: {W}px; height: {H}px; overflow: hidden; background: var(--bg2); }}
#bg {{ position: absolute; inset: 0; background: radial-gradient(ellipse 120% 100% at 30% 40%, var(--bg1), var(--bg2) 60%, var(--bg3)); }}
#blob {{ position: absolute; width: {blob}px; height: {blob}px; border-radius: 50%; right: {blobx}px; top: {bloby}px;
         background: var(--accent); opacity: .9; }}
#ring {{ position: absolute; width: {ring}px; height: {ring}px; border-radius: 50%; left: {ringx}px; bottom: {ringy}px; border: {ringw}px solid var(--accent2); opacity: .85; }}
#photo {{ position: absolute; {photo_pos} overflow: hidden; border-radius: 28px; border: 10px solid #fff; box-shadow: 0 30px 70px rgba(0,0,0,.35); rotate: {rot}deg; }}
#photo img {{ width: 100%; height: 100%; object-fit: cover; }}
#title {{ position: absolute; {title_pos} font-family: var(--font-head); font-weight: 900; text-transform: uppercase; line-height: .98;
          letter-spacing: -0.01em; color: var(--ink); font-size: {size}px; text-shadow: 0 6px 0 rgba(0,0,0,.08); }}
#title .hl {{ display: inline-block; padding: 0 .14em; margin: .04em 0; background: var(--accent); color: #fff; border-radius: 14px; rotate: -2deg;
              box-shadow: 0 10px 24px rgba(0,0,0,.2); }}
#brand {{ position: absolute; {brand_pos} display: flex; align-items: center; gap: 14px; font-family: var(--font-body); font-weight: 800; font-size: {bsize}px;
          letter-spacing: .12em; text-transform: uppercase; color: var(--ink); }}
#brand img {{ height: {logo_h}px; width: auto; }}
#brand i {{ width: {dot}px; height: {dot}px; border-radius: 50%; background: var(--accent2); display: inline-block; }}
#tag {{ position: absolute; {tag_pos} padding: 10px 22px; border-radius: 999px; background: var(--ink); color: var(--bg2); font-family: var(--font-body);
        font-weight: 800; font-size: {tsize}px; letter-spacing: .08em; text-transform: uppercase; }}
</style></head><body><div id="root" data-composition-id="thumb" data-start="0" data-duration="1" data-width="{W}" data-height="{H}" data-fps="10">
<div id="bg"></div><div id="blob"></div><div id="ring"></div>{photo}<div id="title">{title}</div>{tag}<div id="brand">{mark}{brand}</div></div>
<script>var tl = gsap.timeline({{paused: true}}); tl.set({{}}, {{}}, 1); window.__timelines = window.__timelines || {{}}; window.__timelines["thumb"] = tl;</script>
</body></html>"""


def _title_html(text: str, highlight: str) -> str:
    words = text.split()
    hl = highlight.strip().lower()
    out, done = [], False
    for w in words:
        if not done and hl and w.strip(".,!?:").lower() == hl:
            out.append(f'<span class="hl">{html.escape(w)}</span>')
            done = True
        else:
            out.append(html.escape(w))
    if not done and words:  # no usable highlight given: pick the strongest word (longest, not a filler word)
        small = {"vs", "and", "the", "of", "a", "an", "to", "in", "on", "for", "with", "how", "why", "what", "is", "are", "your", "my"}
        cands = [i for i, w in enumerate(words) if w.strip(".,!?:").lower() not in small] or list(range(len(words)))
        k = max(reversed(cands), key=lambda i: len(words[i].strip(".,!?:")))
        out[k] = f'<span class="hl">{html.escape(words[k])}</span>'
    return " ".join(out)


def make(out: Path, work: Path, fmt: Dict, design: Dict, brand: Dict, text: str, highlight: str = "",
         photo: Optional[str] = None, tag: str = "", logo: Optional[str] = None) -> Path:
    from app.services import design as dsg
    W, H = (1280, 720) if fmt["w"] > fmt["h"] else (fmt["w"], fmt["h"])
    land, square = W > H, W == H
    dz = dsg.normalise(design, text, brand)
    vars_css, _, fonts = dsg.css_vars(dz, 0)
    stage = work / "hf_thumb"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "fonts").mkdir(parents=True)
    for f in fonts:
        shutil.copy(FONTS_DIR / f, stage / "fonts" / f)
    shutil.copy(HF_HOME / "node_modules" / "gsap" / "dist" / "gsap.min.js", stage / "gsap.min.js")
    has_photo = bool(photo and Path(photo).exists())
    if has_photo:
        shutil.copy(photo, stage / "photo.jpg")
    has_logo = bool(logo and Path(logo).exists())
    if has_logo:
        shutil.copy(logo, stage / ("logo" + Path(logo).suffix))
    n = len(text)
    if land:
        size = 112 if n <= 18 else 96 if n <= 28 else 80
        geo = dict(blob=520, blobx=-120, bloby=-140, ring=300, ringx=560, ringy=-150, ringw=34,
                   photo_pos="right: 70px; top: 120px; width: 470px; height: 480px;", rot=3,
                   title_pos=f"left: 70px; top: 150px; width: {700 if has_photo else 1100}px;",
                   brand_pos="left: 74px; bottom: 54px;", bsize=26, dot=22, tag_pos="left: 70px; top: 64px;", tsize=26)
    elif square:
        size = 120 if n <= 18 else 100
        geo = dict(blob=520, blobx=-160, bloby=-160, ring=320, ringx=820, ringy=-140, ringw=36,
                   photo_pos="right: 70px; bottom: 150px; width: 520px; height: 440px;", rot=3,
                   title_pos="left: 70px; top: 120px; width: 940px;", brand_pos="left: 74px; bottom: 60px;", bsize=30, dot=24,
                   tag_pos="left: 70px; top: 50px;", tsize=28)
    else:
        size = 150 if n <= 18 else 124 if n <= 28 else 104
        geo = dict(blob=700, blobx=-220, bloby=-200, ring=420, ringx=800, ringy=-170, ringw=44,
                   photo_pos="left: 110px; top: 980px; width: 860px; height: 700px;", rot=-2,
                   title_pos="left: 80px; top: 300px; width: 920px;", brand_pos="left: 84px; bottom: 90px;", bsize=36, dot=28,
                   tag_pos="left: 80px; top: 180px;", tsize=34)
    page = PAGE.format(faces=dsg.font_faces(fonts), vars=vars_css, W=W, H=H, size=size,
                       photo=('<div id="photo"><img src="photo.jpg"/></div>' if has_photo else ""),
                       title=_title_html(text, highlight), brand=html.escape(brand.get("name", "")),
                       tag=(f'<div id="tag">{html.escape(tag)}</div>' if tag else ""),
                       mark=(f'<img src="logo{Path(logo).suffix}"/>' if has_logo else "<i></i>"), logo_h=int(geo["bsize"] * 2.2), **geo)
    (stage / "index.html").write_text(page, encoding="utf-8")
    clip = work / "thumb.mp4"
    env = {**os.environ, "HYPERFRAMES_SKIP_SKILLS": "1", "HYPERFRAMES_TELEMETRY_DISABLED": "1", "DO_NOT_TRACK": "1"}
    hf_pkg = json.loads((HF_HOME / "node_modules" / "hyperframes" / "package.json").read_text())
    rel = hf_pkg["bin"] if isinstance(hf_pkg["bin"], str) else hf_pkg["bin"]["hyperframes"]
    p = subprocess.run(["node", str(HF_HOME / "node_modules" / "hyperframes" / rel), "render", str(stage), "--fps", "10", "--quality", "delivery", "-o", str(clip)],
                       cwd=str(HF_HOME), env=env, capture_output=True, text=True)
    if p.returncode != 0 or not clip.exists():
        raise RuntimeError("thumbnail render failed: " + " | ".join((p.stderr or p.stdout).strip().splitlines()[-4:]))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-sseof", "-0.15", "-i", str(clip), "-frames:v", "1", "-q:v", "2", str(out)], check=True)
    return out

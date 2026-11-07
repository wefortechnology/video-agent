"""ffmpeg renderer: stock clip (or branded gradient) + voiceover + brand-coloured captions + logo + end card."""
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from app.config import FONTS_DIR

log = logging.getLogger("render")
FPS = 30


def run(cmd: List[str], cwd: Optional[Path] = None) -> None:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        tail = " | ".join((p.stderr or "").strip().splitlines()[-6:])
        raise RuntimeError(f"ffmpeg failed: {tail}")


def _hex(c: str) -> str:
    c = (c or "#1F4E79").strip().lstrip("#")
    return c if re.fullmatch(r"[0-9a-fA-F]{6}", c) else "1F4E79"


def _ass_color(hex6: str, alpha: int = 0) -> str:
    r, g, b = hex6[0:2], hex6[2:4], hex6[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _darker(hex6: str, k: float = 0.55) -> str:
    return "".join(f"{int(int(hex6[i:i + 2], 16) * k):02X}" for i in (0, 2, 4))


def _bg_source(W: int, H: int, primary: str, dur: float) -> str:
    """Calm vertical gradient in the brand colour (used when there is no stock clip)."""
    return (f"gradients=s={W}x{H}:c0=0x{primary}:c1=0x{_darker(primary)}:x0=0:y0=0:x1=0:y1={H}"
            f":nb_colors=2:speed=0.00001:rate={FPS}:duration={dur}")


def _lum(hex6: str) -> float:
    r, g, b = (int(hex6[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _font(language: str) -> str:
    return "Noto Sans Devanagari" if language == "hi" else "Inter"


def _chunks(text: str, per: int) -> List[str]:
    words = text.split()
    return [" ".join(words[i:i + per]) for i in range(0, len(words), per)] or [text]


def _ass(path: Path, W: int, H: int, language: str, primary: str, margin_v: int, size: int, events: List[tuple]) -> None:
    """events: (start_s, end_s, text, style)"""
    def t(s: float) -> str:
        h, rem = divmod(max(s, 0), 3600)
        m, sec = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{sec:05.2f}"
    text_col = "&H00000000" if _lum(primary) > 0.6 else "&H00FFFFFF"
    font = _font(language)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},{text_col},&H000000FF,{_ass_color(primary, 0x30)},{_ass_color(primary, 0x30)},-1,0,0,0,100,100,0,0,3,{int(size * 0.28)},0,2,{int(W * 0.07)},{int(W * 0.07)},{margin_v},1
Style: EndTitle,{font},{int(size * 1.5)},{text_col},&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,{int(W * 0.08)},{int(W * 0.08)},0,1
Style: EndCta,{font},{int(size * 1.0)},{text_col},&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,{int(W * 0.08)},{int(W * 0.08)},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = "".join(f"Dialogue: 0,{t(s)},{t(e)},{st},,0,0,0,,{tx.replace(chr(10), chr(92) + 'N')}\n" for s, e, tx, st in events)
    path.write_text(head + body, encoding="utf-8")


def _encode_args(fps: int = FPS) -> List[str]:
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(fps),
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-movflags", "+faststart"]


def _shot_filter(i: int, W: int, H: int, seconds: float, idx: int, fps: int = FPS) -> str:
    """One shot: cover-fit slightly oversized, drift across it slowly (alternating direction), light colour grade."""
    big_w, big_h = int(W * 1.14) // 2 * 2, int(H * 1.14) // 2 * 2
    prog = f"min(t/{seconds:.2f},1)"
    x = f"(iw-ow)*{prog}" if (idx + i) % 2 == 0 else f"(iw-ow)*(1-{prog})"
    return (f"[{i}:v]scale={big_w}:{big_h}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H}:x='{x}':y='(ih-oh)/2',setsar=1,fps={fps},"
            f"eq=contrast=1.06:saturation=1.15:brightness=-0.02,format=yuv420p[v{i}]")


def render_scene(out: Path, work: Path, idx: int, fmt: Dict, language: str, brand: Dict, caption: str, audio: str,
                 audio_seconds: float, shots: List[Dict], logo: Optional[str], fps: int = FPS) -> float:
    """shots: [{'path','kind'}]. Several shots per scene give fast cuts; none = branded gradient."""
    W, H = fmt["w"], fmt["h"]
    primary = _hex(brand["primary_color"])
    dur = round(audio_seconds + 0.5, 2)
    size = int(min(W, H) * 0.058)
    margin_v = int(H * fmt["caption_margin"])
    per = 4 if language == "hi" else 5
    parts = _chunks(caption, per)
    total_chars = sum(len(p) for p in parts) or 1
    pop = r"{\fad(120,80)\fscx88\fscy88\t(0,170,\fscx100\fscy100)}"
    events, t = [], 0.15
    span = max(audio_seconds - 0.1, 0.5)
    for p in parts:
        d = span * len(p) / total_chars
        events.append((t, t + d, pop + p, "Cap"))
        t += d
    ass_path = work / f"scene{idx}.ass"
    _ass(ass_path, W, H, language, primary, margin_v, size, events)

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    chain = ""
    if shots:
        sd = round(dur / len(shots), 2)
        for i, sh in enumerate(shots):
            if sh.get("kind") == "image":
                cmd += ["-loop", "1", "-framerate", str(fps), "-t", str(sd + 0.1), "-i", sh["path"]]
            else:
                cmd += ["-stream_loop", "-1", "-t", str(sd + 0.1), "-i", sh["path"]]
            chain += _shot_filter(i, W, H, sd, idx, fps) + ";"
        n = len(shots)
        chain += (f"{''.join(f'[v{i}]' for i in range(n))}concat=n={n}:v=1:a=0[bg]" if n > 1 else "[v0]null[bg]")
    else:  # nothing good enough to show: calm gradient in the brand colour
        cmd += ["-f", "lavfi", "-i", _bg_source(W, H, primary, dur)]
        chain = f"[0:v]setsar=1,format=yuv420p[bg]"
    audio_idx = len(shots) if shots else 1
    cmd += ["-i", audio]
    last = "bg"
    if logo:
        logo_idx = audio_idx + 1
        cmd += ["-i", logo]
        chain += f";[{logo_idx}:v]scale={int(W * 0.14)}:-1[lg];[bg][lg]overlay=W-w-{int(W * 0.04)}:{int(H * (0.07 if H > W else 0.04))}[wl]"
        last = "wl"
    chain += f";[{last}]ass='{ass_path.name}':fontsdir='{FONTS_DIR}'[v]"
    cmd += ["-filter_complex", chain, "-map", "[v]", "-map", f"{audio_idx}:a", "-af", "apad", "-t", str(dur)] + _encode_args(fps) + [str(out)]
    run(cmd, cwd=work)
    return dur


def render_end_card(out: Path, work: Path, fmt: Dict, language: str, brand: Dict, cta: str, logo: Optional[str], seconds: float = 3.0) -> float:
    W, H = fmt["w"], fmt["h"]
    primary, accent = _hex(brand["primary_color"]), _hex(brand["accent_color"])
    size = int(min(W, H) * 0.052)
    ass_path = work / "endcard.ass"
    y_title, y_cta = int(H * (0.62 if logo else 0.45)), int(H * (0.72 if logo else 0.56))
    events = [(0.0, seconds, f"{{\\pos({W // 2},{y_title})}}{brand['name']}", "EndTitle")]
    if cta:
        events.append((0.3, seconds, f"{{\\pos({W // 2},{y_cta})}}{cta}", "EndCta"))
    _ass(ass_path, W, H, language, primary, 0, size, events)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-f", "lavfi", "-i", _bg_source(W, H, primary, seconds),
           "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    chain = "[0:v]setsar=1[bg]"
    last = "bg"
    if logo:
        cmd += ["-i", logo]
        chain += f";[2:v]scale={int(min(W, H) * 0.30)}:-1[lg];[bg][lg]overlay=(W-w)/2:{int(H * 0.30)}[wl]"
        last = "wl"
    chain += f";[{last}]ass='{ass_path.name}':fontsdir='{FONTS_DIR}'[v]"
    cmd += ["-filter_complex", chain, "-map", "[v]", "-map", "1:a", "-t", str(seconds)] + _encode_args() + [str(out)]
    run(cmd, cwd=work)
    return seconds


def concat(segments: List[Path], out: Path, work: Path) -> None:
    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{s.resolve()}'\n" for s in segments))
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", "-movflags", "+faststart", str(out)], cwd=work)


def add_logo(video: Path, logo: str, until: float, work: Path) -> None:
    """Small brand logo in the top-right corner of `video` (in place), shown until `until` seconds (before the end card)."""
    W = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width",
                            "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout.strip() or 1080)
    size, pad = int(W * 0.085) // 2 * 2, int(W * 0.035)
    tmp = work / "with_logo.mp4"
    fc = (f"[1:v]scale={size}:{size}:force_original_aspect_ratio=decrease,format=rgba,colorchannelmixer=aa=0.92[lg];"
          f"[0:v][lg]overlay=W-w-{pad}:{pad}:enable='lt(t,{until:.2f})'[v]")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-loop", "1", "-i", str(logo),
         "-filter_complex", fc, "-map", "[v]", "-map", "0:a?", "-shortest", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(tmp)])
    tmp.replace(video)


def embed_cover(video: Path, cover: Path) -> None:
    """Put the designed thumbnail inside the MP4 as its cover picture (shown by file managers and players). In place, no re-encode."""
    tmp = video.with_suffix(".cover.mp4")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-i", str(cover),
         "-map", "0:v:0", "-map", "0:a?", "-map", "1:v", "-c", "copy", "-c:v:1", "mjpeg",
         "-disposition:v:1", "attached_pic", "-movflags", "+faststart", str(tmp)])
    tmp.replace(video)


def thumbnail(video: Path, out: Path, at: float = 1.0) -> None:
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(at), "-i", str(video), "-frames:v", "1", "-q:v", "3", str(out)])

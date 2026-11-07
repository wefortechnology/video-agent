"""Motion-graphics scenes (2D animation) rendered with HyperFrames: HTML + GSAP -> MP4, timed by the voiceover.

Same engine as the old video-studio (installed in ~/.video-studio/hyperframes). Each scene is an animated
illustration ("art") plus a kinetic headline, festive bokeh and burned-in captions. No stock footage needed.
"""
import html
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from app.config import FONTS_DIR

log = logging.getLogger("motion")
HERE = Path(__file__).resolve().parent.parent / "motion"
HF_HOME = Path(os.environ.get("VEODRIVE_VIDEO_HOME", Path.home() / ".video-studio")) / "hyperframes"
FPS = 30

# ------------------------------------------------------------------ shared SVG pieces
DEFS = """
<svg width="0" height="0" style="position:absolute"><defs>
  <linearGradient id="gBowl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e2672e"/><stop offset="1" stop-color="#7a2810"/></linearGradient>
  <radialGradient id="gFlame" cx=".5" cy=".72" r=".62"><stop offset="0" stop-color="#fffbe8"/><stop offset=".45" stop-color="#ffd24a"/><stop offset="1" stop-color="#ff6a12"/></radialGradient>
  <radialGradient id="gLaddu" cx=".38" cy=".35" r=".7"><stop offset="0" stop-color="#ffd27a"/><stop offset=".55" stop-color="#f39a1e"/><stop offset="1" stop-color="#b85d00"/></radialGradient>
  <linearGradient id="gPlate" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffe9a8"/><stop offset=".5" stop-color="#e0a52c"/><stop offset="1" stop-color="#8a5a06"/></linearGradient>
  <linearGradient id="gLantern" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff4f8b"/><stop offset=".5" stop-color="#ff9f1c"/><stop offset="1" stop-color="#c2185b"/></linearGradient>
</defs></svg>
"""


def _diya_svg(cls: str, width: int) -> str:
    return f"""<svg class="{cls}" width="{width}" viewBox="0 0 400 300" style="overflow:visible">
  <g class="flame"><path d="M200 18 C240 78 238 120 200 138 C162 120 160 78 200 18 Z" fill="url(#gFlame)"/>
     <path d="M200 72 C216 100 214 122 200 132 C186 122 184 100 200 72 Z" fill="#fff8d8"/></g>
  <rect x="196" y="128" width="8" height="22" rx="3" fill="#3a1d0b"/>
  <path d="M40 150 C64 284 336 284 360 150 Z" fill="url(#gBowl)"/>
  <ellipse cx="200" cy="150" rx="160" ry="28" fill="#ee8a43"/>
  <ellipse cx="200" cy="150" rx="126" ry="17" fill="#ffbf3c"/>
  <g fill="#ffd36b">{''.join(f'<circle cx="{x}" cy="{205 + abs(x - 200) * -0.12:.0f}" r="7"/>' for x in range(110, 300, 30))}</g>
  <path d="M78 186 C140 226 260 226 322 186" stroke="#ffd36b" stroke-width="5" fill="none" stroke-dasharray="2 12" stroke-linecap="round"/>
</svg>"""


def _toran(W: int) -> str:
    """Marigold garland across the top with mango leaves."""
    n = 15
    beads = []
    for i in range(n):
        x = 40 + i * (W - 80) / (n - 1)
        y = 40 + 90 * (1 - ((2 * i / (n - 1)) - 1) ** 2)
        col = "#ff8f00" if i % 2 else "#ffc107"
        beads.append(f'<g class="mg" transform="translate({x:.0f},{y:.0f})"><circle r="30" fill="{col}"/>'
                     f'<circle r="18" fill="{"#ffb300" if i % 2 else "#ff6f00"}" opacity=".7"/>'
                     f'<path d="M-10 26 Q0 90 10 26 Z" fill="#2e7d32"/></g>')
    return f'<svg id="toran" class="abs" style="left:0;top:0" width="{W}" height="240">{"".join(beads)}</svg>'


def _skyline(W: int, H: int, top: int) -> str:
    """Row of houses whose windows and string lights switch on: 'every home lit up'."""
    houses, wins, bulbs = [], [], []
    x, i = 0, 0
    widths = [150, 120, 180, 130, 160, 140, 170, 120, 150]
    heights = [260, 340, 220, 300, 380, 240, 320, 280, 230]
    while x < W:
        w, h = widths[i % len(widths)], heights[i % len(heights)]
        y = top + (400 - h)
        houses.append(f'<rect x="{x}" y="{y}" width="{w - 6}" height="{h + 400}" fill="#140b2b"/>'
                      f'<path d="M{x - 6} {y} L{x + w / 2 - 3} {y - 50} L{x + w} {y} Z" fill="#1c1038"/>')
        for r in range(2):
            for c in range(2):
                wx, wy = x + 22 + c * (w - 70), y + 40 + r * 90
                wins.append(f'<rect class="win" x="{wx:.0f}" y="{wy:.0f}" width="34" height="44" rx="4" fill="#ffcf5c"/>')
        x += w
        i += 1
    for k in range(32):
        bx = 20 + k * (W - 40) / 31
        by = top + 70 + 26 * (1 - ((2 * (k % 8) / 7) - 1) ** 2)
        col = ["#ffd54f", "#ff7043", "#4dd0e1", "#f06292"][k % 4]
        bulbs.append(f'<circle class="bulb" cx="{bx:.0f}" cy="{by:.0f}" r="9" fill="{col}"/>')
    return (f'<svg id="sky" class="abs" style="left:0;top:0" width="{W}" height="{H}">{"".join(houses)}'
            f'<path d="M0 {top + 70} ' + " ".join(f"Q{60 + j * (W / 4):.0f} {top + 110} {(j + 1) * W / 4:.0f} {top + 70}" for j in range(4)) +
            f'" stroke="#3a2a55" stroke-width="3" fill="none"/>{"".join(bulbs)}{"".join(wins)}</svg>')


# ------------------------------------------------------------------ scene arts
# Each art: style (CSS), content (HTML), script (JS: tl, D, W, H available). Positions are for 1080x1920 (9:16).
ARTS: Dict[str, Dict[str, str]] = {}

ARTS["diya"] = {
    "style": """
  #glow { left: 90px; top: 560px; width: 900px; height: 900px; border-radius: 50%;
          background: radial-gradient(circle, rgba(255,190,80,.55) 0%, rgba(255,140,40,.16) 38%, rgba(0,0,0,0) 66%); }
  #big { position: absolute; left: 190px; top: 820px; }
  #row { position: absolute; left: 0; top: 1330px; width: 1080px; text-align: center; font-size: 0; }
  #row svg { display: inline-block; margin: 0 6px; }""",
    "content": DEFS + '<div id="glow" class="abs"></div><div id="big">' + _diya_svg("bigd", 700) + '</div>'
               '<div id="row">' + "".join(_diya_svg("sd", 170) for _ in range(5)) + '</div>',
    "script": """
  gsap.set("#big", {opacity: 0, y: 80}); tl.to("#big", {opacity: 1, y: 0, duration: 1.0, ease: "power3.out"}, 0.2);
  gsap.set(".bigd .flame", {scale: 0, transformOrigin: "50% 100%"});
  tl.to(".bigd .flame", {scale: 1, duration: 0.7, ease: "back.out(2.4)"}, 0.9);
  tl.to(".bigd .flame", {scaleY: 1.12, scaleX: 0.92, duration: 0.17, yoyo: true, repeat: Math.floor(D / 0.34), ease: "sine.inOut"}, 1.6);
  gsap.set("#glow", {opacity: 0, scale: 0.5}); tl.to("#glow", {opacity: 1, scale: 1, duration: 1.2}, 0.9);
  tl.to("#glow", {scale: 1.1, duration: 0.9, yoyo: true, repeat: Math.max(1, Math.floor((D - 2) / 0.9)), ease: "sine.inOut"}, 2.1);
  gsap.set(".sd", {opacity: 0, y: 40}); tl.to(".sd", {opacity: 1, y: 0, duration: 0.5, stagger: 0.14}, 1.2);
  gsap.set(".sd .flame", {scale: 0, transformOrigin: "50% 100%"});
  tl.to(".sd .flame", {scale: 1, duration: 0.4, stagger: 0.22, ease: "back.out(3)"}, 1.9);
  tl.to(".sd .flame", {scaleY: 1.15, duration: 0.2, yoyo: true, repeat: Math.floor(D / 0.4), stagger: 0.05, ease: "sine.inOut"}, 3.0);
""",
}

_petals_outer = "".join(
    f'<g transform="rotate({i * 30})"><ellipse class="po" cx="0" cy="-165" rx="44" ry="105" fill="{"#e4007c" if i % 2 else "#ff8c00"}"/></g>'
    for i in range(12))
_petals_inner = "".join(
    f'<g transform="rotate({i * 30 + 15})"><ellipse class="pi" cx="0" cy="-95" rx="26" ry="62" fill="{"#ffd23f" if i % 2 else "#00b3a4"}"/></g>'
    for i in range(12))
_dots = "".join(f'<circle class="dt" cx="{__import__("math").sin(i * 3.14159 / 12) * 268:.1f}" cy="{-__import__("math").cos(i * 3.14159 / 12) * 268:.1f}" r="11" fill="{["#ffd23f", "#fff", "#00e5ff"][i % 3]}"/>' for i in range(24))
ARTS["rangoli"] = {
    "style": """
  #rgw { position: absolute; left: 70px; top: 640px; width: 940px; height: 940px; }
  #rglow { left: 40px; top: 610px; width: 1000px; height: 1000px; border-radius: 50%; background: radial-gradient(circle, rgba(255,80,160,.28), rgba(0,0,0,0) 62%); }""",
    "content": '<div id="rglow" class="abs"></div><svg id="rgw" viewBox="-320 -320 640 640"><g id="rg">'
               '<circle class="ring" r="300" fill="none" stroke="#ffd23f" stroke-width="6" stroke-dasharray="1885" stroke-dashoffset="1885"/>'
               '<circle class="ring" r="232" fill="none" stroke="#ff4fa3" stroke-width="5" stroke-dasharray="1458" stroke-dashoffset="1458"/>'
               + _dots + _petals_outer + _petals_inner +
               '<circle id="core1" r="62" fill="#7b2ff7"/><circle id="core2" r="40" fill="#ffd23f"/><circle id="core3" r="18" fill="#e4007c"/>'
               '</g></svg>',
    "script": """
  tl.to("#rg", {rotation: 45, svgOrigin: "0 0", duration: D, ease: "none"}, 0);
  tl.to(".ring", {strokeDashoffset: 0, duration: 1.4, stagger: 0.3, ease: "power2.inOut"}, 0.3);
  gsap.set([".po", ".pi"], {scale: 0, transformOrigin: "50% 100%"});
  tl.to(".po", {scale: 1, duration: 0.55, stagger: 0.07, ease: "back.out(1.8)"}, 0.8);
  tl.to(".pi", {scale: 1, duration: 0.45, stagger: 0.06, ease: "back.out(2)"}, 1.5);
  gsap.set([".dt", "#core1", "#core2", "#core3"], {scale: 0, transformOrigin: "50% 50%"});
  tl.to(["#core1", "#core2", "#core3"], {scale: 1, duration: 0.5, stagger: 0.12, ease: "back.out(2.5)"}, 0.5);
  tl.to(".dt", {scale: 1, duration: 0.3, stagger: 0.04, ease: "back.out(3)"}, 2.0);
  gsap.set("#rglow", {opacity: 0}); tl.to("#rglow", {opacity: 1, duration: 1.5}, 0.8);
""",
}

_laddu_pos = [(205, 500), (335, 500), (465, 500), (595, 500), (270, 400), (400, 400), (530, 400), (335, 300), (465, 300), (400, 205)]
_laddus = "".join(
    f'<g transform="translate({x},{y})"><g class="ld"><circle r="64" fill="url(#gLaddu)"/>'
    + "".join(f'<circle cx="{dx}" cy="{dy}" r="4" fill="#fff2c4" opacity=".75"/>' for dx, dy in [(-30, -10), (10, -30), (25, 15), (-10, 30), (35, -20), (-35, 20), (0, 0)])
    + '<ellipse cx="-22" cy="-26" rx="16" ry="10" fill="#fff" opacity=".35"/></g></g>' for x, y in _laddu_pos)
_stars = "".join(f'<path class="st" transform="translate({x},{y})" d="M0 -26 L6 -6 L26 0 L6 6 L0 26 L-6 6 L-26 0 L-6 -6 Z" fill="#fff6c8"/>'
                 for x, y in [(90, 140), (720, 110), (60, 420), (760, 380), (400, 70)])
ARTS["sweets"] = {
    "style": """
  #plate { position: absolute; left: 90px; top: 760px; }
  #sglow { left: 40px; top: 700px; width: 1000px; height: 900px; border-radius: 50%; background: radial-gradient(circle, rgba(255,170,60,.35), rgba(0,0,0,0) 62%); }""",
    "content": DEFS + '<div id="sglow" class="abs"></div><svg id="plate" width="900" viewBox="0 0 800 700" style="overflow:visible">'
               '<ellipse cx="400" cy="575" rx="380" ry="92" fill="url(#gPlate)"/><ellipse cx="400" cy="565" rx="330" ry="68" fill="#c78a1c"/>'
               '<ellipse cx="400" cy="560" rx="300" ry="56" fill="#e7b443"/>' + _laddus + _stars + '</svg>',
    "script": """
  gsap.set("#plate", {opacity: 0, y: 60}); tl.to("#plate", {opacity: 1, y: 0, duration: 0.8, ease: "power3.out"}, 0.2);
  gsap.set(".ld", {y: -700, opacity: 0});
  tl.to(".ld", {y: 0, opacity: 1, duration: 0.75, stagger: 0.16, ease: "bounce.out"}, 0.7);
  gsap.set(".st", {scale: 0, opacity: 0, transformOrigin: "50% 50%"});
  tl.to(".st", {scale: 1, opacity: 1, rotation: 45, duration: 0.5, stagger: 0.25, ease: "back.out(3)"}, 2.0);
  tl.to(".st", {scale: 0.5, opacity: 0.4, duration: 0.5, yoyo: true, repeat: Math.max(1, Math.floor((D - 2.6) / 0.5)), stagger: 0.1}, 2.6);
  gsap.set("#sglow", {opacity: 0}); tl.to("#sglow", {opacity: 1, duration: 1.2}, 0.6);
""",
}

ARTS["fireworks"] = {
    "style": "#fw { left: 0; top: 0; }",
    "content": '<svg id="fw" class="abs" width="{{W}}" height="{{H}}"></svg>' + _skyline(1080, 1920, 1380),
    "script": """
  var NS = "http://www.w3.org/2000/svg", fw = document.getElementById("fw");
  var cols = ["#ffd54f", "#ff4f8b", "#4dd0e1", "#ff9100", "#ffffff", "#b388ff"];
  function burst(cx, cy, col, t, len) {
    var rocket = document.createElementNS(NS, "line");
    rocket.setAttribute("x1", cx); rocket.setAttribute("x2", cx); rocket.setAttribute("y1", H); rocket.setAttribute("y2", H + 60);
    rocket.setAttribute("stroke", "#ffe9a8"); rocket.setAttribute("stroke-width", 5); rocket.setAttribute("stroke-linecap", "round");
    fw.appendChild(rocket); gsap.set(rocket, {opacity: 0});
    tl.set(rocket, {opacity: 1}, t - 0.6);
    tl.fromTo(rocket, {attr: {y1: H * 0.95, y2: H * 0.95 + 70}}, {attr: {y1: cy, y2: cy + 70}, duration: 0.6, ease: "power2.out"}, t - 0.6);
    tl.set(rocket, {opacity: 0}, t);
    var g = document.createElementNS(NS, "g"); g.setAttribute("transform", "translate(" + cx + "," + cy + ")"); fw.appendChild(g);
    var inner = document.createElementNS(NS, "g"); g.appendChild(inner);
    for (var k = 0; k < 24; k++) {
      var a = k / 24 * Math.PI * 2, l = document.createElementNS(NS, "line");
      l.setAttribute("x1", Math.cos(a) * 18); l.setAttribute("y1", Math.sin(a) * 18);
      l.setAttribute("x2", Math.cos(a) * len); l.setAttribute("y2", Math.sin(a) * len);
      l.setAttribute("stroke", col); l.setAttribute("stroke-width", 6); l.setAttribute("stroke-linecap", "round");
      inner.appendChild(l);
      var c = document.createElementNS(NS, "circle");
      c.setAttribute("cx", Math.cos(a) * (len + 16)); c.setAttribute("cy", Math.sin(a) * (len + 16)); c.setAttribute("r", 7); c.setAttribute("fill", "#fff");
      inner.appendChild(c);
    }
    gsap.set(inner, {scale: 0.1, opacity: 0, svgOrigin: "0 0"});
    tl.to(inner, {scale: 1, opacity: 1, duration: 0.5, ease: "expo.out", svgOrigin: "0 0"}, t);
    tl.to(inner, {opacity: 0, scale: 1.15, y: 40, duration: 1.1, ease: "power1.in", svgOrigin: "0 0"}, t + 0.5);
  }
  var t = 0.9, i = 0;
  while (t < D - 1.0) {
    burst(160 + EZ.rand() * (W - 320), 720 + EZ.rand() * 460, cols[i % cols.length], t, 120 + EZ.rand() * 110);
    t += 0.55 + EZ.rand() * 0.45; i++;
  }
  gsap.set(".win", {opacity: 0.08}); gsap.set(".bulb", {opacity: 0.1});
  tl.to(".win", {opacity: 1, duration: 0.25, stagger: {each: 0.05, from: "random"}}, 0.5);
  tl.to(".bulb", {opacity: 1, duration: 0.2, stagger: 0.04}, 0.8);
  tl.to(".bulb", {opacity: 0.35, duration: 0.35, yoyo: true, repeat: Math.floor(D / 0.7), stagger: {each: 0.03, from: "edges"}}, 2.2);
""",
}

ARTS["greeting"] = {
    "style": """
  .lan { position: absolute; top: 150px; }
  #lanL { left: 60px; } #lanR { right: 60px; }
  #bname { position: absolute; left: 0; width: 1080px; top: 1250px; text-align: center; font-size: 60px; font-weight: 800; letter-spacing: .04em; color: #ffe6a8; }
  #bline { position: absolute; left: 340px; top: 1340px; width: 400px; height: 6px; border-radius: 3px; background: linear-gradient(90deg, rgba(255,200,80,0), #ffc94d, rgba(255,200,80,0)); }
  #grow { position: absolute; left: 0; top: 1410px; width: 1080px; text-align: center; font-size: 0; }
  #grow svg { display: inline-block; margin: 0 4px; }""",
    "content": DEFS + _toran(1080) + "".join(
        f'<svg id="{i}" class="lan" width="170" height="560" viewBox="0 0 170 560"><line x1="85" y1="0" x2="85" y2="170" stroke="#ffcf6e" stroke-width="4"/>'
        f'<polygon points="85,170 160,280 85,420 10,280" fill="url(#gLantern)"/><polygon points="85,200 135,280 85,390 35,280" fill="#ffd54f" opacity=".55"/>'
        f'<rect x="60" y="160" width="50" height="16" rx="4" fill="#ffcf6e"/>'
        + "".join(f'<line x1="{x}" y1="420" x2="{x}" y2="520" stroke="#ffcf6e" stroke-width="4"/>' for x in (70, 85, 100)) + '</svg>'
        for i in ("lanL", "lanR")) + '<div id="bname">{{BRAND}}</div><div id="bline"></div><div id="grow">'
        + "".join(_diya_svg("gd", 150) for _ in range(5)) + '</div>',
    "script": """
  gsap.set(".mg", {scale: 0, transformOrigin: "50% 50%"});
  tl.to(".mg", {scale: 1, duration: 0.35, stagger: 0.05, ease: "back.out(2.5)"}, 0.1);
  gsap.set(".lan", {y: -600}); tl.to(".lan", {y: 0, duration: 1.1, stagger: 0.2, ease: "bounce.out"}, 0.3);
  tl.to("#lanL", {rotation: 6, transformOrigin: "50% 0%", duration: 1.1, yoyo: true, repeat: Math.floor(D / 1.1), ease: "sine.inOut"}, 1.4);
  tl.to("#lanR", {rotation: -6, transformOrigin: "50% 0%", duration: 1.2, yoyo: true, repeat: Math.floor(D / 1.2), ease: "sine.inOut"}, 1.5);
  gsap.set(["#bname", "#bline"], {opacity: 0, y: 30});
  tl.to(["#bname", "#bline"], {opacity: 1, y: 0, duration: 0.7, stagger: 0.15}, 1.4);
  gsap.set(".gd", {opacity: 0, y: 30}); tl.to(".gd", {opacity: 1, y: 0, duration: 0.4, stagger: 0.12}, 1.8);
  gsap.set(".gd .flame", {scale: 0, transformOrigin: "50% 100%"});
  tl.to(".gd .flame", {scale: 1, duration: 0.35, stagger: 0.15, ease: "back.out(3)"}, 2.3);
  tl.to(".gd .flame", {scaleY: 1.15, duration: 0.2, yoyo: true, repeat: Math.floor(D / 0.4), stagger: 0.05}, 3.2);
  tl.fromTo("#head .w", {backgroundPosition: "0% 0%"}, {backgroundPosition: "0% 100%", duration: 1.2, yoyo: true, repeat: Math.floor(D / 1.2)}, 1.0);
""",
}

# ------------------------------------------------------------------ line icons (24x24, Feather-style)
ICONS = {  # line icons (24x24, Feather-style)
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "briefcase": '<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "heart": '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78z"/>',
    "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "pin": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    "trending": '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
    "gift": '<polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
}
_esc = html.escape


# ================================================================== theme-aware templates (any topic)
ARTS["endcard"] = {
    "style": """
  #logo { position: absolute; left: 340px; top: 640px; width: 400px; height: 400px; object-fit: contain; }
  #ename { position: absolute; left: 0; width: 1080px; top: 1080px; text-align: center; font-size: 84px; font-family: var(--font-head); font-weight: var(--head-weight); text-transform: var(--head-case); color: var(--ink); }
  #ecta { position: absolute; left: 50%; top: 1230px; transform: translateX(-50%); padding: 22px 48px; border-radius: 60px; white-space: nowrap;
          background: linear-gradient(90deg, var(--accent), var(--accent2)); font-family: var(--font-body); font-size: 48px; font-weight: 700; color: #fff; }
  #ediya { position: absolute; left: 390px; top: 720px; }""",
    "content": DEFS + _toran(1080) + '{{LOGO}}<div id="ename">{{BRAND}}</div><div id="ecta">{{CTA}}</div>',
    "script": """
  gsap.set(".mg", {scale: 0, transformOrigin: "50% 50%"});
  tl.to(".mg", {scale: 1, duration: 0.3, stagger: 0.04, ease: "back.out(2.5)"}, 0.05);
  gsap.set(["#logo", "#ediya"], {opacity: 0, scale: 0.6, transformOrigin: "50% 50%"});
  tl.to(["#logo", "#ediya"], {opacity: 1, scale: 1, duration: 0.7, ease: "back.out(2)"}, 0.2);
  gsap.set("#ename", {opacity: 0, y: 30}); tl.to("#ename", {opacity: 1, y: 0, duration: 0.6}, 0.5);
  gsap.set("#ecta", {opacity: 0, scale: 0.7}); tl.to("#ecta", {opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2.2)"}, 0.9);
  tl.to("#ecta", {scale: 1.06, duration: 0.4, yoyo: true, repeat: 3, ease: "sine.inOut"}, 1.6);
""",
}

_rays = "".join(f'<g transform="rotate({i * 22.5})"><path d="M-14 0 L14 0 L5 -760 L-5 -760 Z" fill="url(#gRay)"/></g>' for i in range(16))
_confetti = "".join(
    f'<rect class="cf" x="{x}" y="{y}" width="{s}" height="{s * (0.45 if i % 2 else 1):.0f}" rx="{4 if i % 3 else s // 2}" style="fill:var({c})"/>'
    for i, (x, y, s, c) in enumerate([(120, 520, 34, "--accent"), (900, 600, 28, "--accent2"), (200, 1180, 30, "--accent3"),
                                      (860, 1240, 36, "--accent2"), (520, 470, 22, "--accent"), (70, 880, 26, "--accent2"),
                                      (980, 930, 24, "--accent"), (640, 1330, 28, "--accent3")]))
ARTS["spotlight"] = {  # glowing rings, slow rays, confetti: an opening hook or a big statement
    "style": "#spot { position: absolute; left: 0; top: 0; }",
    "content": '<svg id="spot" width="1080" height="1920" viewBox="0 0 1080 1920"><defs>'
               '<linearGradient id="gRay" x1="0" y1="1" x2="0" y2="0"><stop offset="0" style="stop-color:var(--accent);stop-opacity:.3"/>'
               '<stop offset="1" style="stop-color:var(--accent);stop-opacity:0"/></linearGradient></defs>'
               '<g id="rays" transform="translate(540,900)">' + _rays + '</g>'
               '<g transform="translate(540,900)"><circle class="sr" r="230" fill="none" style="stroke:var(--accent)" stroke-width="5"/>'
               '<circle class="sr" r="330" fill="none" style="stroke:var(--accent2)" stroke-width="3"/>'
               '<circle class="sr" r="430" fill="none" style="stroke:var(--accent3)" stroke-width="2"/></g>' + _confetti + '</svg>',
    "script": """
  gsap.set("#rays", {opacity: 0}); tl.to("#rays", {opacity: 1, duration: 1}, 0.2);
  tl.to("#rays", {rotation: 30, svgOrigin: "540 900", duration: D, ease: "none"}, 0);
  gsap.set(".sr", {scale: 0, opacity: 0, transformOrigin: "50% 50%"});
  tl.to(".sr", {scale: 1, opacity: 0.9, duration: 0.9, stagger: 0.2, ease: "expo.out"}, 0.3);
  tl.to(".sr", {scale: 1.06, duration: 1.0, yoyo: true, repeat: Math.max(1, Math.floor((D - 1.5) / 1.0)), stagger: 0.15, ease: "sine.inOut"}, 1.3);
  gsap.set(".cf", {opacity: 0, scale: 0, transformOrigin: "50% 50%"});
  tl.to(".cf", {opacity: 1, scale: 1, rotation: 120, duration: 0.7, stagger: 0.1, ease: "back.out(2)"}, 0.6);
  tl.to(".cf", {y: -40, rotation: "+=90", duration: 1.6, yoyo: true, repeat: Math.max(1, Math.floor(D / 1.6)), stagger: 0.1, ease: "sine.inOut"}, 1.4);
""",
}

ARTS["orbit"] = {  # calm, topic-neutral: dashed rings turning, dots orbiting
    "style": "#orb { position: absolute; left: 0; top: 0; }",
    "content": '<svg id="orb" width="1080" height="1920" viewBox="0 0 1080 1920"><g transform="translate(540,1000)">'
               '<circle r="400" fill="none" style="stroke:var(--cardline)" stroke-width="3"/>'
               '<g id="o1"><circle r="300" fill="none" style="stroke:var(--accent)" stroke-width="6" stroke-dasharray="30 26" stroke-linecap="round"/>'
               '<circle cx="0" cy="-300" r="20" style="fill:var(--accent)"/></g>'
               '<g id="o2"><circle r="200" fill="none" style="stroke:var(--accent2)" stroke-width="5" stroke-dasharray="4 18" stroke-linecap="round"/>'
               '<circle cx="200" cy="0" r="16" style="fill:var(--accent2)"/></g>'
               '<circle id="ocore" r="90" style="fill:var(--card);stroke:var(--accent3)" stroke-width="6"/>'
               '<circle id="ocore2" r="34" style="fill:var(--accent3)"/></g></svg>',
    "script": """
  gsap.set(["#o1", "#o2", "#ocore", "#ocore2"], {scale: 0.01, opacity: 0, svgOrigin: "0 0"});
  tl.to(["#ocore", "#ocore2"], {scale: 1, opacity: 1, duration: 0.6, stagger: 0.1, ease: "back.out(2.4)", svgOrigin: "0 0"}, 0.3);
  tl.to(["#o2", "#o1"], {scale: 1, opacity: 1, duration: 0.8, stagger: 0.15, ease: "expo.out", svgOrigin: "0 0"}, 0.5);
  tl.to("#o1", {rotation: 120, svgOrigin: "0 0", duration: D, ease: "none"}, 0);
  tl.to("#o2", {rotation: -200, svgOrigin: "0 0", duration: D, ease: "none"}, 0);
""",
}


def _build_checklist(d):
    rows = []
    for i, p in enumerate((d.get("points") or [])[:4]):
        rows.append(f'<div class="crow" style="top:{700 + i * 200}px"><svg class="ck" width="104" height="104" viewBox="0 0 112 112">'
                    f'<circle class="ckc" cx="56" cy="56" r="46" fill="none" style="stroke:var(--accent)" stroke-width="8" stroke-dasharray="290" stroke-dashoffset="290"/>'
                    f'<path class="ckm" d="M33 58 L50 75 L81 40" fill="none" style="stroke:var(--ok)" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="80" stroke-dashoffset="80"/></svg>'
                    f'<div class="ctext">{_esc(p)}</div></div>')
    return "".join(rows)


def _build_counter(d):
    import re as _re
    m = _re.match(r"^(\D*?)([\d][\d,]*(?:\.\d+)?)(.*)$", (d.get("number") or "").strip())
    pre, num, post = (m.group(1), m.group(2), m.group(3)) if m else ("", "0", "")
    return (f'<svg id="cring" class="abs" width="760" height="760" viewBox="-380 -380 760 760" style="left:160px;top:620px">'
            f'<circle r="330" fill="none" style="stroke:var(--cardline)" stroke-width="18"/>'
            f'<circle id="carc" r="330" fill="none" style="stroke:var(--accent)" stroke-width="18" stroke-linecap="round" stroke-dasharray="2073" stroke-dashoffset="2073" transform="rotate(-90)"/>'
            f'<circle id="cdot" r="16" cx="0" cy="-330" style="fill:var(--accent2)"/></svg>'
            f'<div id="cnum"><span class="cpre">{_esc(pre)}</span><span id="cval" data-to="{_esc(num.replace(",", ""))}">0</span><span class="cpost">{_esc(post)}</span></div>')


def _build_quote(d):
    return (f'<div id="qmark" class="serif">&#8220;</div><div id="qtext" class="serif">{_esc(d.get("headline", ""))}</div><div id="qbar"></div>'
            f'<div id="qby">{_esc(d.get("brand", ""))}</div>')


def _build_card(d):
    pills = "".join(f'<span class="pill">{_esc(p)}</span>' for p in (d.get("points") or [])[:4])
    return (f'<div id="card"><div id="shine"></div><div id="ckick">{_esc(d.get("kicker", ""))}</div>'
            f'<div id="ctitle" class="serif">{_esc(d.get("headline", ""))}</div><div id="cdiv"></div><div id="cpills">{pills}</div></div>')


def _icon_svg(name: str, size: int, color: str = "var(--accent)") -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" style="stroke:{color}" stroke-width="1.6" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS.get(name, ICONS["star"])}</svg>')


def _build_icons(d):
    pts = (d.get("points") or [])[:3]
    icons = d.get("icons") or []
    n = len(pts) or 1
    xs = {1: [540], 2: [330, 750], 3: [190, 540, 890]}[n]
    items = []
    for i, p in enumerate(pts):
        name = icons[i] if i < len(icons) and icons[i] in ICONS else ["star", "heart", "zap"][i % 3]
        items.append(f'<div class="ic" style="left:{xs[i] - 150}px"><div class="icc">{_icon_svg(name, 130)}</div><div class="icl">{_esc(p)}</div></div>')
    line = (f'<svg id="icline" class="abs" width="1080" height="40" style="left:0;top:860px"><line x1="{xs[0]}" y1="20" x2="{xs[-1]}" y2="20" '
            f'style="stroke:var(--accent)" stroke-width="4" stroke-dasharray="10 14" opacity=".6"/></svg>') if n > 1 else ""
    return line + "".join(items)


def _build_flow(d):
    pts = (d.get("points") or [])[:4]
    n = len(pts)
    gap = 230 if n <= 3 else 200
    top0 = 1000 - (n - 1) * gap / 2 - 80
    out = []
    for i, p in enumerate(pts):
        y = top0 + i * gap
        out.append(f'<div class="fbox" style="top:{y:.0f}px"><div class="fnum">{i + 1}</div><div class="ftext">{_esc(p)}</div></div>')
        if i < n - 1:
            out.append(f'<svg class="farr" width="60" height="70" viewBox="0 0 60 70" style="left:510px;top:{y + 160:.0f}px">'
                       f'<path d="M30 4 L30 56 M14 42 L30 60 L46 42" fill="none" style="stroke:var(--accent2)" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>')
    return "".join(out)


def _build_compare(d):
    pts = (d.get("points") or ["", ""])
    icons = d.get("icons") or []
    def side(i, x):
        name = icons[i] if i < len(icons) and icons[i] in ICONS else ["zap", "check"][i % 2]
        return (f'<div class="cmp" id="cmp{i}" style="left:{x}px"><div class="cmpi">{_icon_svg(name, 120, "var(--accent)" if i == 0 else "var(--accent2)")}</div>'
                f'<div class="cmpt">{_esc(pts[i] if i < len(pts) else "")}</div></div>')
    return side(0, 70) + side(1, 570) + '<div id="vs" class="serif">vs</div>'


def _build_chapter(d):
    n, tot = int(d.get("num") or 1), int(d.get("total") or 1)
    dots = "".join(f'<span class="chd{" on" if i < n else ""}"></span>' for i in range(tot))
    title = d.get("headline", "")
    size = 118 if len(title) <= 22 else (96 if len(title) <= 40 else 80)
    return (f'<div id="chwrap"><div id="chk">{_esc(d.get("label") or "Chapter")} {n}</div>'
            f'<div id="cht" class="serif" style="font-size:{size}px">{_esc(title)}</div>'
            f'<div id="chl"></div><div id="chdots">{dots}</div></div>')


_NET_NODES = [(540, 720), (240, 960), (840, 960), (540, 1180), (200, 1360), (880, 1360)]
_NET_EDGES = [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (3, 5), (1, 4), (2, 5)]


def _build_network(d):
    lab = (d.get("points") or [])[:3]
    icons = (d.get("icons") or []) + ["globe", "zap", "home"]
    edges = "".join(f'<line class="ne" x1="{_NET_NODES[a][0]}" y1="{_NET_NODES[a][1]}" x2="{_NET_NODES[b][0]}" y2="{_NET_NODES[b][1]}" '
                    f'style="stroke:var(--cardline)" stroke-width="5" stroke-dasharray="600" stroke-dashoffset="600"/>' for a, b in _NET_EDGES)
    nodes = "".join(f'<circle class="nn" cx="{x}" cy="{y}" r="{60 if i in (0, 3) else 42}" style="fill:var(--card);stroke:var(--accent)" stroke-width="6"/>'
                    for i, (x, y) in enumerate(_NET_NODES))
    packets = "".join(f'<rect class="pk" x="-14" y="-10" width="28" height="20" rx="4" style="fill:var({c})"/>' for c in ("--accent2", "--accent3", "--accent"))
    labels = "".join(f'<div class="nl" style="left:{_NET_NODES[k][0] - 160}px;top:{_NET_NODES[k][1] + (70 if k else -130)}px">{_esc(t)}</div>'
                     for k, t in zip((0, 3, 5), lab))
    icn = "".join(f'<div class="ni" style="left:{_NET_NODES[k][0] - 34}px;top:{_NET_NODES[k][1] - 34}px">{_icon_svg(icons[j] if icons[j] in ICONS else "globe", 68)}</div>'
                  for j, k in enumerate((0, 3)))
    return f'<svg id="net" class="abs" width="1080" height="1920" style="left:0;top:0">{edges}{nodes}{packets}</svg>{icn}{labels}'


def _build_globe(d):
    meridians = "".join(f'<ellipse class="gm" cx="0" cy="0" rx="{r}" ry="330" fill="none" style="stroke:var(--accent)" stroke-width="3" opacity=".55"/>'
                        for r in (330, 250, 160, 60))
    lats = "".join(f'<ellipse cx="0" cy="{y}" rx="{(330 ** 2 - y ** 2) ** 0.5:.0f}" ry="{abs(18 + (330 - abs(y)) * 0.06):.0f}" fill="none" style="stroke:var(--accent)" stroke-width="2.5" opacity=".4"/>'
                   for y in (-220, -110, 0, 110, 220))
    pts = [(-200, -120), (150, -200), (230, 90), (-120, 180), (40, 30)]
    arcs = "".join(f'<path class="ga" d="M{pts[a][0]} {pts[a][1]} Q{(pts[a][0] + pts[b][0]) / 2:.0f} {min(pts[a][1], pts[b][1]) - 160} {pts[b][0]} {pts[b][1]}" '
                   f'fill="none" style="stroke:var(--accent2)" stroke-width="5" stroke-linecap="round" stroke-dasharray="700" stroke-dashoffset="700"/>'
                   for a, b in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 0)))
    dots = "".join(f'<circle class="gd2" cx="{x}" cy="{y}" r="14" style="fill:var(--accent3)"/>' for x, y in pts)
    return (f'<svg id="globe" class="abs" width="900" height="900" viewBox="-450 -450 900 900" style="left:90px;top:550px">'
            f'<circle r="330" style="fill:var(--card);stroke:var(--accent)" stroke-width="5"/><g id="gmer">{meridians}</g>{lats}{arcs}{dots}</svg>')


def _build_server(d):
    racks = []
    for r, x in enumerate((150, 420, 690)):
        slots = "".join(f'<rect x="{x + 20}" y="{760 + s * 100}" width="200" height="70" rx="10" style="fill:var(--bg2);stroke:var(--cardline)" stroke-width="3"/>'
                        f'<circle class="led" cx="{x + 52}" cy="{795 + s * 100}" r="10" style="fill:var({["--ok", "--accent", "--accent2"][(r + s) % 3]})"/>'
                        f'<rect x="{x + 80}" y="{789 + s * 100}" width="110" height="10" rx="5" style="fill:var(--cardline)"/>' for s in range(6))
        racks.append(f'<g class="rack"><rect x="{x}" y="730" width="240" height="640" rx="22" style="fill:var(--card);stroke:var(--accent)" stroke-width="5"/>{slots}</g>')
    return f'<svg id="srv" class="abs" width="1080" height="1920" style="left:0;top:0">{"".join(racks)}</svg>'


def _build_lock(d):
    return ('<svg id="lock" class="abs" width="1080" height="1920" style="left:0;top:0"><g transform="translate(540,1010)">'
            '<circle id="lring" r="360" fill="none" style="stroke:var(--accent2)" stroke-width="5" stroke-dasharray="2262" stroke-dashoffset="2262" transform="rotate(-90)"/>'
            '<path id="lshack" d="M-120 -60 L-120 -170 A120 120 0 0 1 120 -170 L120 -60" fill="none" style="stroke:var(--accent)" stroke-width="40" stroke-linecap="round"/>'
            '<rect x="-200" y="-70" width="400" height="320" rx="44" style="fill:var(--card);stroke:var(--accent)" stroke-width="10"/>'
            '<circle cx="0" cy="60" r="38" style="fill:var(--accent)"/><rect x="-14" y="70" width="28" height="90" rx="12" style="fill:var(--accent)"/>'
            '<g id="lstars">' + "".join(f'<circle class="ls" cx="{x}" cy="330" r="16" style="fill:var(--accent3)"/>' for x in (-120, -60, 0, 60, 120)) + '</g></g></svg>')


ARTS["checklist"] = {
    "needs": "points",
    "style": """
  .crow { position: absolute; left: 90px; width: 900px; height: 164px; border-radius: var(--radius); display: flex; align-items: center; gap: 26px; padding: 0 34px;
          background: var(--card); border: 2px solid var(--cardline); box-shadow: var(--shadow); }
  .ctext { font-family: var(--font-body); font-weight: 700; font-size: 50px; line-height: 1.2; color: var(--ink); }""",
    "build": _build_checklist,
    "script": """
  var rows = EZ.$$(".crow"), n = rows.length || 1, gap = Math.max(0.45, Math.min(1.2, (D - 2.0) / n));
  rows.forEach(function (r, i) {
    var t = 0.7 + i * gap;
    gsap.set(r, {opacity: 0, x: -140});
    tl.to(r, {opacity: 1, x: 0, duration: 0.6, ease: "power3.out"}, t);
    tl.to(r.querySelector(".ckc"), {strokeDashoffset: 0, duration: 0.45, ease: "power2.inOut"}, t + 0.25);
    tl.to(r.querySelector(".ckm"), {strokeDashoffset: 0, duration: 0.3, ease: "power2.out"}, t + 0.6);
  });
""",
}

ARTS["counter"] = {
    "needs": "number",
    "style": """
  #cnum { position: absolute; left: 0; width: 1080px; top: 860px; text-align: center; font-family: var(--font-head); font-weight: 800; font-size: 230px;
          line-height: 1; background: linear-gradient(180deg, var(--headA), var(--headB) 50%, var(--accent)); -webkit-background-clip: text; background-clip: text;
          color: transparent; filter: drop-shadow(var(--glow)); white-space: nowrap; }
  #cnum .cpre, #cnum .cpost { font-size: 120px; }""",
    "build": _build_counter,
    "script": """
  var el = EZ.$("#cval"), to = parseFloat(el.getAttribute("data-to")) || 0, dec = (el.getAttribute("data-to").split(".")[1] || "").length;
  var T = Math.min(2.2, D - 1.2);
  gsap.set("#cnum", {opacity: 0, scale: 0.7, transformOrigin: "50% 50%"});
  tl.to("#cnum", {opacity: 1, scale: 1, duration: 0.6, ease: "back.out(2)"}, 0.5);
  EZ.count(tl, el, 0, to, 0.6, T, function (v) { return v.toLocaleString("en-IN", {minimumFractionDigits: dec, maximumFractionDigits: dec}); });
  tl.to("#carc", {strokeDashoffset: 0, duration: T, ease: "power2.out"}, 0.6);
  tl.to("#cdot", {rotation: 360, svgOrigin: "0 0", duration: T, ease: "power2.out"}, 0.6);
""",
}

ARTS["quote"] = {
    "own_head": True,
    "style": """
  #qmark { position: absolute; left: 90px; top: 500px; font-size: 380px; line-height: 1; color: var(--accent); }
  #qtext { position: absolute; left: 110px; width: 860px; top: 800px; font-size: 88px; line-height: 1.28; color: var(--ink); }
  #qbar { position: absolute; left: 110px; top: 1340px; width: 300px; height: 8px; border-radius: 4px; background: linear-gradient(90deg, var(--accent), var(--accent2)); transform-origin: 0 50%; }
  #qby { position: absolute; left: 110px; top: 1380px; font-size: 40px; font-weight: 700; letter-spacing: .08em; color: var(--muted); }""",
    "build": _build_quote,
    "script": """
  gsap.set("#qmark", {opacity: 0, scale: 0.4, rotation: -20, transformOrigin: "30% 60%"});
  tl.to("#qmark", {opacity: 1, scale: 1, rotation: 0, duration: 0.7, ease: "back.out(2)"}, 0.2);
  var TT = Math.min(D * 0.5, 2.4);
  EZ.type(tl, "#qtext", 0.6, TT);
  gsap.set("#qbar", {scaleX: 0}); tl.to("#qbar", {scaleX: 1, duration: 0.6, ease: "power2.out"}, TT + 0.6);
  gsap.set("#qby", {opacity: 0, y: 20}); tl.to("#qby", {opacity: 1, y: 0, duration: 0.5}, TT + 0.8);
""",
}

ARTS["card"] = {
    "own_head": True,
    "needs": "points",
    "style": """
  #card { position: absolute; left: 80px; top: 620px; width: 920px; border-radius: calc(var(--radius) + 10px); overflow: hidden; padding: 70px 64px 76px;
          background: var(--card); border: 2px solid var(--cardline); box-shadow: var(--shadow); }
  #shine { position: absolute; top: -200px; left: -400px; width: 220px; height: 1400px; background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.28), rgba(255,255,255,0)); }
  #ckick { font-size: 34px; font-weight: 800; letter-spacing: .2em; text-transform: uppercase; color: var(--accent); }
  #ctitle { margin-top: 26px; font-size: 100px; line-height: 1.15; color: var(--ink); }
  #cdiv { margin: 40px 0 36px; width: 260px; height: 8px; border-radius: 4px; background: linear-gradient(90deg, var(--accent), var(--accent2)); transform-origin: 0 50%; }
  #cpills { display: flex; flex-wrap: wrap; gap: 20px; }
  #cpills .pill { padding: 18px 34px; border-radius: 60px; border: 2px solid var(--accent); font-family: var(--font-body); font-size: 42px; font-weight: 700; color: var(--ink); }""",
    "build": _build_card,
    "script": """
  gsap.set("#card", {opacity: 0, y: 140, scale: 0.92, transformOrigin: "50% 50%"});
  tl.to("#card", {opacity: 1, y: 0, scale: 1, duration: 0.9, ease: "power3.out"}, 0.2);
  gsap.set(["#ckick", "#ctitle"], {opacity: 0, y: 30});
  tl.to(["#ckick", "#ctitle"], {opacity: 1, y: 0, duration: 0.6, stagger: 0.15}, 0.6);
  gsap.set("#cdiv", {scaleX: 0}); tl.to("#cdiv", {scaleX: 1, duration: 0.5}, 1.1);
  gsap.set("#cpills .pill", {opacity: 0, scale: 0.6, transformOrigin: "50% 50%"});
  tl.to("#cpills .pill", {opacity: 1, scale: 1, duration: 0.45, stagger: 0.18, ease: "back.out(2.2)"}, 1.3);
  tl.to("#shine", {x: 1700, duration: 1.4, ease: "power2.inOut"}, 1.0);
""",
}

ARTS["icons"] = {
    "needs": "points",
    "style": """
  .ic { position: absolute; top: 720px; width: 300px; text-align: center; }
  .icc { width: 280px; height: 280px; margin: 0 auto; border-radius: 50%; display: flex; align-items: center; justify-content: center;
         background: var(--card); border: 3px solid var(--cardline); box-shadow: var(--shadow); }
  .icl { margin-top: 30px; font-family: var(--font-body); font-size: 46px; font-weight: 700; line-height: 1.25; color: var(--ink); }""",
    "build": _build_icons,
    "script": """
  var items = EZ.$$(".ic"), n = items.length || 1, gap = Math.max(0.35, Math.min(0.9, (D - 2.0) / n));
  if (EZ.$("#icline")) { gsap.set("#icline", {opacity: 0}); tl.to("#icline", {opacity: 1, duration: 0.8}, 0.5); }
  items.forEach(function (it, i) {
    var t = 0.6 + i * gap;
    gsap.set(it.querySelector(".icc"), {scale: 0, transformOrigin: "50% 50%"});
    tl.to(it.querySelector(".icc"), {scale: 1, duration: 0.6, ease: "back.out(2.2)"}, t);
    var paths = it.querySelectorAll("svg *");
    gsap.set(paths, {strokeDasharray: 80, strokeDashoffset: 80});
    tl.to(paths, {strokeDashoffset: 0, duration: 0.7, ease: "power2.out"}, t + 0.3);
    gsap.set(it.querySelector(".icl"), {opacity: 0, y: 30});
    tl.to(it.querySelector(".icl"), {opacity: 1, y: 0, duration: 0.5}, t + 0.45);
  });
""",
}

ARTS["flow"] = {  # a process: step 1 -> 2 -> 3
    "needs": "points2",
    "style": """
  .fbox { position: absolute; left: 140px; width: 800px; height: 160px; border-radius: var(--radius); display: flex; align-items: center; gap: 30px; padding: 0 36px;
          background: var(--card); border: 2px solid var(--cardline); box-shadow: var(--shadow); }
  .fnum { flex: 0 0 96px; height: 96px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 52px; font-weight: 800;
          color: #fff; background: linear-gradient(135deg, var(--accent), var(--accent2)); }
  .ftext { font-family: var(--font-body); font-size: 48px; font-weight: 700; line-height: 1.2; color: var(--ink); }
  .farr { position: absolute; }""",
    "build": _build_flow,
    "script": """
  var boxes = EZ.$$(".fbox"), arr = EZ.$$(".farr"), n = boxes.length || 1, gap = Math.max(0.5, Math.min(1.1, (D - 2.0) / n));
  boxes.forEach(function (b, i) {
    var t = 0.6 + i * gap;
    gsap.set(b, {opacity: 0, y: 50, scale: 0.94, transformOrigin: "50% 50%"});
    tl.to(b, {opacity: 1, y: 0, scale: 1, duration: 0.55, ease: "back.out(1.7)"}, t);
    if (arr[i]) { gsap.set(arr[i], {opacity: 0, y: -20}); tl.to(arr[i], {opacity: 1, y: 0, duration: 0.35}, t + gap * 0.6); }
  });
""",
}

ARTS["compare"] = {  # two sides of an idea
    "own_head": False,
    "needs": "points2",
    "style": """
  .cmp { position: absolute; top: 720px; width: 440px; height: 600px; border-radius: var(--radius); display: flex; flex-direction: column; align-items: center;
         justify-content: center; gap: 40px; padding: 40px; background: var(--card); border: 2px solid var(--cardline); box-shadow: var(--shadow); text-align: center; }
  .cmpt { font-family: var(--font-body); font-size: 50px; font-weight: 800; line-height: 1.2; color: var(--ink); }
  #vs { position: absolute; left: 470px; top: 960px; width: 140px; height: 140px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-size: 60px; font-style: italic; color: #fff; background: linear-gradient(135deg, var(--accent), var(--accent2)); box-shadow: var(--shadow); }""",
    "build": _build_compare,
    "script": """
  gsap.set("#cmp0", {opacity: 0, x: -160}); gsap.set("#cmp1", {opacity: 0, x: 160});
  tl.to("#cmp0", {opacity: 1, x: 0, duration: 0.7, ease: "power3.out"}, 0.5);
  tl.to("#cmp1", {opacity: 1, x: 0, duration: 0.7, ease: "power3.out"}, 0.5 + Math.min(1.2, D * 0.25));
  gsap.set("#vs", {opacity: 0, scale: 0, transformOrigin: "50% 50%"});
  tl.to("#vs", {opacity: 1, scale: 1, duration: 0.5, ease: "back.out(3)"}, 0.9 + Math.min(1.2, D * 0.25));
""",
}

ARTS["chapter"] = {  # YouTube chapter title card
    "own_head": True,
    "style": """
  #chwrap { position: absolute; left: 110px; width: 860px; top: 560px; height: 900px; display: flex; flex-direction: column; justify-content: center; }
  #chk { font-family: var(--font-body); font-size: 40px; font-weight: 800; letter-spacing: .24em; text-transform: uppercase; color: var(--accent); margin-bottom: 26px; }
  #cht { line-height: 1.12; color: var(--ink); }
  #chl { margin-top: 44px; width: 420px; height: 10px; border-radius: 5px; background: linear-gradient(90deg, var(--accent), var(--accent2)); transform-origin: 0 50%; }
  #chdots { margin-top: 30px; display: flex; gap: 14px; }
  .chd { width: 22px; height: 22px; border-radius: 50%; background: var(--cardline); }
  .chd.on { background: var(--accent2); }""",
    "build": _build_chapter,
    "script": """
  gsap.set("#chk", {opacity: 0, x: -40}); tl.to("#chk", {opacity: 1, x: 0, duration: 0.5}, 0.2);
  gsap.set("#cht", {opacity: 0, y: 50}); tl.to("#cht", {opacity: 1, y: 0, duration: 0.8, ease: "power3.out"}, 0.4);
  gsap.set("#chl", {scaleX: 0}); tl.to("#chl", {scaleX: 1, duration: 0.8, ease: "power2.inOut"}, 0.9);
  gsap.set(".chd", {opacity: 0, scale: 0, transformOrigin: "50% 50%"}); tl.to(".chd", {opacity: 1, scale: 1, duration: 0.3, stagger: 0.06}, 1.1);
""",
}

ARTS["network"] = {  # devices linked; packets travel along the lines (internet, data, connections)
    "build": _build_network,
    "style": """
  .ni { position: absolute; width: 68px; height: 68px; }
  .nl { position: absolute; width: 320px; text-align: center; font-family: var(--font-body); font-size: 40px; font-weight: 700; color: var(--ink); }""",
    "script": """
  var nodes = [[540,720],[240,960],[840,960],[540,1180],[200,1360],[880,1360]];
  tl.to(".ne", {strokeDashoffset: 0, duration: 0.8, stagger: 0.12, ease: "power2.inOut"}, 0.4);
  gsap.set([".nn", ".ni"], {scale: 0, transformOrigin: "50% 50%"});
  tl.to(".nn", {scale: 1, duration: 0.45, stagger: 0.1, ease: "back.out(2.5)"}, 0.3);
  tl.to(".ni", {scale: 1, duration: 0.45, stagger: 0.1, ease: "back.out(2.5)"}, 0.6);
  gsap.set(".nl", {opacity: 0, y: 20}); tl.to(".nl", {opacity: 1, y: 0, duration: 0.5, stagger: 0.2}, 1.0);
  var paths = [[0,1,3,4],[0,2,3,5],[4,3,1,0]];
  EZ.$$(".pk").forEach(function (p, k) {
    var route = paths[k % paths.length], t = 1.0 + k * 0.45;
    gsap.set(p, {opacity: 0, x: nodes[route[0]][0], y: nodes[route[0]][1]});
    while (t < D - 0.8) {
      tl.set(p, {opacity: 1, x: nodes[route[0]][0], y: nodes[route[0]][1]}, t);
      for (var s = 1; s < route.length; s++) {
        tl.to(p, {x: nodes[route[s]][0], y: nodes[route[s]][1], duration: 0.45, ease: "power1.inOut"}, t + (s - 1) * 0.45);
      }
      t += route.length * 0.45 + 0.3;
      tl.set(p, {opacity: 0}, t - 0.3);
    }
  });
""",
}

ARTS["globe"] = {  # the world connected (internet, global reach, travel, partners everywhere)
    "build": _build_globe,
    "style": "",
    "script": """
  gsap.set("#globe", {opacity: 0, scale: 0.8, transformOrigin: "50% 50%"});
  tl.to("#globe", {opacity: 1, scale: 1, duration: 0.8, ease: "power3.out"}, 0.2);
  EZ.$$(".gm").forEach(function (m, i) {
    var r = parseFloat(m.getAttribute("rx"));
    tl.fromTo(m, {attr: {rx: r}}, {attr: {rx: Math.max(10, 330 - r)}, duration: 2.2, yoyo: true, repeat: Math.max(1, Math.floor(D / 2.2)), ease: "sine.inOut"}, 0);
  });
  tl.to(".ga", {strokeDashoffset: 0, duration: 0.9, stagger: 0.35, ease: "power2.inOut"}, 0.8);
  gsap.set(".gd2", {scale: 0, transformOrigin: "50% 50%"}); tl.to(".gd2", {scale: 1, duration: 0.35, stagger: 0.15, ease: "back.out(3)"}, 0.7);
""",
}

ARTS["server"] = {  # data centres, cloud, storage, computing
    "build": _build_server,
    "style": "",
    "script": """
  gsap.set(".rack", {opacity: 0, y: 80}); tl.to(".rack", {opacity: 1, y: 0, duration: 0.7, stagger: 0.18, ease: "power3.out"}, 0.3);
  EZ.$$(".led").forEach(function (l, i) {
    gsap.set(l, {opacity: 0.25});
    tl.to(l, {opacity: 1, duration: 0.12, yoyo: true, repeat: Math.max(1, Math.floor((D - 1) / (0.3 + EZ.rand() * 0.4))), ease: "none"}, 1.0 + EZ.rand() * 0.8);
  });
""",
}

ARTS["lock"] = {  # security, privacy, passwords, trust
    "build": _build_lock,
    "style": "",
    "script": """
  gsap.set("#lock", {opacity: 0, scale: 0.85, transformOrigin: "50% 52%"}); tl.to("#lock", {opacity: 1, scale: 1, duration: 0.7, ease: "back.out(1.8)"}, 0.2);
  gsap.set("#lshack", {y: -70}); tl.to("#lshack", {y: 0, duration: 0.45, ease: "bounce.out"}, 1.0);
  tl.to("#lring", {strokeDashoffset: 0, duration: 1.2, ease: "power2.inOut"}, 1.2);
  gsap.set(".ls", {scale: 0, transformOrigin: "50% 50%"}); tl.to(".ls", {scale: 1, duration: 0.3, stagger: 0.12, ease: "back.out(3)"}, 1.6);
""",
}

def _build_photo(d):
    label = (d.get("points") or [""])[0]
    return ('<div id="pdeco"></div><div id="pframe"><img id="pimg" src="photo.jpg"/><div id="pshade"></div></div>'
            + (f'<div id="plabel">{_esc(label)}</div>' if label else ""))


ARTS["photo"] = {  # a real photograph in a designed frame, slow Ken Burns zoom (people, places, objects)
    "needs": "photo",
    "build": _build_photo,
    "style": """
  #pframe { position: absolute; left: 80px; top: 600px; width: 920px; height: 860px; border-radius: calc(var(--radius) + 8px); overflow: hidden;
            box-shadow: var(--shadow); border: 3px solid var(--cardline); background: var(--surface); }
  #pimg { position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: cover; }
  #pshade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,0) 55%, rgba(0,0,0,.35) 100%); }
  #plabel { position: absolute; left: 130px; top: 1360px; padding: 16px 30px; border-radius: 999px; background: var(--accent); color: #fff;
            font-family: var(--font-body); font-size: 40px; font-weight: 800; box-shadow: var(--shadow); }
  #pdeco { position: absolute; left: 30px; top: 1290px; width: 230px; height: 230px; border-radius: 50%; background: var(--accent2); opacity: .8; }""",
    "script": """
  gsap.set("#pframe", {opacity: 0, y: 70, scale: 0.94, transformOrigin: "50% 50%"});
  tl.to("#pframe", {opacity: 1, y: 0, scale: 1, duration: 0.8, ease: "power3.out"}, 0.2);
  tl.fromTo("#pimg", {scale: 1.16, xPercent: -2}, {scale: 1.0, xPercent: 2, duration: D, ease: "none", transformOrigin: "50% 50%"}, 0);
  if (EZ.$("#plabel")) { gsap.set("#plabel", {opacity: 0, x: -40}); tl.to("#plabel", {opacity: 1, x: 0, duration: 0.5, ease: "back.out(2)"}, 0.9); }
  gsap.set("#pdeco", {scale: 0, opacity: 0, transformOrigin: "50% 50%"}); tl.to("#pdeco", {scale: 1, opacity: 0.8, duration: 0.6, ease: "back.out(2)"}, 0.5);
""",
}


# What the script writer may choose from (motion style)
ART_CHOICES = {
    "diya": "lit clay lamps with flickering flames (Diwali, light, hope)",
    "rangoli": "colourful rangoli blooming and turning (Diwali, festivals, welcome)",
    "sweets": "plate of laddoos dropping into place (sweets, sharing, festivals)",
    "fireworks": "fireworks over houses whose lights switch on (celebration, every home lit up)",
    "greeting": "marigold garland, swinging lanterns, the brand name (festive closing wish)",
    "spotlight": "glowing rings and rays around the headline (opening hook, big announcement)",
    "orbit": "calm turning rings around the headline (a key idea, a transition, a definition)",
    "quote": "a sentence typed out large (a belief, a key takeaway, a short message)",
    "checklist": "2-4 short points ticked off (needs points: tips, requirements, benefits)",
    "flow": "2-4 numbered steps with arrows (needs points: a process, how something happens in order)",
    "compare": "two sides with 'vs' (needs points: exactly two short labels, e.g. 'Old way', 'New way')",
    "icons": "three icons with labels (needs points and icons: three parts, values or services)",
    "card": "a card with the headline and 2-4 pills (needs points: a role, product, event and its details)",
    "counter": "a big number counting up (needs number: ONLY a number given in the request)",
    "network": "devices linked by lines with data packets travelling (internet, networks, data moving; points = up to 3 node labels)",
    "globe": "a turning wireframe globe with arcs between places (worldwide, global, connecting countries)",
    "server": "data-centre racks with blinking lights (servers, cloud, storage, computing)",
    "lock": "a padlock closing inside a shield ring (security, privacy, passwords, safety online)",
    "photo": "a REAL photograph of the subject in a designed frame (people at work, a place, an object, a moment); fill must_match and stock_query with what the photo should show",
}
from app.services import diagrams as _dg  # noqa: E402  (more diagrams + alternative layouts)
_dg.register(ARTS, ART_CHOICES)
FAMILIES = _dg.FAMILIES
FAMILY_OF = {member: root for root, members in FAMILIES.items() for member in members}
PHOTO_ARTS = tuple(FAMILIES["photo"])
THEME_CHOICES = {}  # replaced by app/services/design.py presets
THEMES = {}
FESTIVE_ARTS = ("diya", "rangoli", "sweets", "fireworks", "greeting")
NEUTRAL_POOL = ("orbit", "quote", "spotlight")

KEYWORDS = [
    ("diya", ["diya", "lamp", "diyas", "candle", "deepak"]),
    ("rangoli", ["rangoli", "kolam", "floor art", "mandala"]),
    ("sweets", ["sweet", "mithai", "laddu", "laddoo", "dessert", "gulab"]),
    ("fireworks", ["firework", "cracker", "sparkler", "pataka", "night sky"]),
    ("network", ["network", "packet", "router", "internet", "wifi", "data travel"]),
    ("globe", ["globe", "world", "global", "worldwide", "country", "countries"]),
    ("server", ["server", "data centre", "data center", "cloud", "storage"]),
    ("lock", ["secure", "security", "password", "privacy", "safe online", "hacker"]),
]


def _has_data(art: str, scene: Dict) -> bool:
    need = ARTS[art].get("needs")
    pts = [p for p in (scene.get("points") or []) if str(p).strip()]
    if need == "points":
        return bool(pts)
    if need == "points2":
        return len(pts) >= 2
    if need == "points3":
        return len(pts) >= 3
    if need == "values":
        vals = [v for v in (scene.get("values") or []) if str(v).strip()]
        return bool(pts) and len(vals) >= len(pts)
    if need == "number":
        return any(ch.isdigit() for ch in str(scene.get("number") or ""))
    if need == "photo":
        return True  # the pipeline swaps in a neutral scene if no photo could be found
    return True


def pick_art(scene: Dict, is_last: bool, festive: bool = True) -> str:
    """The script's choice wins (if it has the data it needs); otherwise guess from keywords. The last scene closes with the brand."""
    chosen = (scene.get("art") or "").strip().lower()
    if chosen in ARTS and chosen not in ("endcard", "chapter"):
        if chosen in FESTIVE_ARTS and not festive:
            chosen = ""
        elif _has_data(chosen, scene):
            return chosen
        else:
            chosen = ""
    if is_last:
        return "greeting" if festive else "spotlight"
    text = " ".join(str(scene.get(k, "")) for k in ("must_match", "stock_query", "title", "caption")).lower()
    for art, words in KEYWORDS:
        if art in FESTIVE_ARTS and not festive:
            continue
        if any(w in text for w in words):
            return art
    return "orbit"


GENERIC_LISTS = ("flow", "checklist", "icons", "steps", "mindmap")  # same data, freely interchangeable
NEUTRALS = ("orbit", "quote", "spotlight")                         # headline-only scenes


def assign_arts(scenes: List[Dict], festive: bool, seed: str = "") -> List[str]:
    """Pick the animation for every scene so the video never repeats a picture:
    1) the script's choice (if it has its data), 2) no family twice in a row and no family over-used (generic lists and
    headline scenes rotate to their least-used sibling), 3) every repeat of a family uses its next layout variant
    (a second 'flow' becomes chevrons, a third a winding path...). The starting variant depends on the video (seed)."""
    import zlib
    n = len(scenes)
    roots = [FAMILY_OF.get(a, a) for a in (pick_art(sc, i == n - 1, festive) for i, sc in enumerate(scenes))]
    count: Dict[str, int] = {}
    cap_list = max(2, round(n * 0.12))
    cap_neutral = max(2, round(n * 0.10))
    for i in range(n):
        r = roots[i]
        prev = roots[i - 1] if i else None
        pool = GENERIC_LISTS if r in GENERIC_LISTS else NEUTRALS if r in NEUTRALS else None
        if pool and i not in (0, n - 1):
            over = count.get(r, 0) >= (cap_list if pool is GENERIC_LISTS else cap_neutral)
            if r == prev or over:
                alts = [x for x in pool if x != prev and _has_data(x, scenes[i])]
                if alts:
                    r = min(alts, key=lambda x: (count.get(x, 0), pool.index(x)))
        elif r == prev and i != n - 1 and r not in FAMILIES:  # e.g. two server scenes in a row
            alts = [x for x in NEUTRALS if x != prev]
            r = min(alts, key=lambda x: count.get(x, 0))
        roots[i] = r
        count[r] = count.get(r, 0) + 1
    # a diagram (with no layout variants) seen in the last 6 scenes gives way to a similar one
    similar = _dg.SIMILAR
    for i in range(n):
        r = roots[i]
        if r in similar and r not in FAMILIES and r in roots[max(0, i - 6):i] and i != n - 1:
            for alt in similar[r]:
                alt_root = FAMILY_OF.get(alt, alt)
                if alt_root not in roots[max(0, i - 3):i] and _has_data(alt, scenes[i]):
                    roots[i] = alt_root
                    break
    # layout variants: rotate inside each family, but only to a layout that can show all of this scene's data
    single_value = ("gauge", "waffle")

    def fits(art: str, sc: Dict) -> bool:
        npts = len([p for p in (sc.get("points") or []) if str(p).strip()])
        if art in single_value and npts > 1:
            return False
        return _has_data(art, sc)

    seen: Dict[str, int] = {}
    out = []
    for i, r in enumerate(roots):
        members = FAMILIES.get(r, [r])
        off = zlib.crc32(f"{seed}:{r}".encode()) % len(members)
        k = seen.get(r, 0)
        seen[r] = k + 1
        order = [members[(off + k + j) % len(members)] for j in range(len(members))]
        out.append(next((m for m in order if fits(m, scenes[i])), r))
    return out


# ------------------------------------------------------------------ render
def _hf_bin() -> Path:
    pkg = json.loads((HF_HOME / "node_modules" / "hyperframes" / "package.json").read_text())
    rel = pkg["bin"] if isinstance(pkg["bin"], str) else pkg["bin"]["hyperframes"]
    return HF_HOME / "node_modules" / "hyperframes" / rel


def available() -> bool:
    return (HF_HOME / "node_modules" / "hyperframes" / "package.json").exists() and bool(shutil.which("node"))


def min_seconds(art: str, data: Optional[Dict]) -> float:
    """Long enough for the animation to finish and be read, even if the voice line is short."""
    n = len((data or {}).get("points") or []) or 1
    if art in _dg.NEW:
        return _dg.min_seconds(art, n)
    return {"checklist": 1.8 + 0.85 * n, "icons": 1.8 + 0.75 * n, "flow": 1.8 + 0.8 * n, "counter": 4.0, "quote": 4.2,
            "card": 4.0, "compare": 4.0, "network": 4.5, "globe": 4.0, "chapter": 3.0}.get(art, 3.0)


def _chunks(text: str, per: int) -> List[str]:
    w = text.split()
    return [" ".join(w[i:i + per]) for i in range(0, len(w), per)] or [text]


def _layout(art: str, RW: int, RH: int, own_head: bool, mirror: bool = False, top_right: int = 0) -> Dict:
    """Where the 1080x1920 design goes in the output frame, and where the headline sits.
    portrait: full design; square: design scaled to fit; landscape (YouTube): headline on one side, visual on the other
    (mirror=True swaps the sides, so consecutive scenes do not all look the same)."""
    if RH > RW:
        s = RW / 1080
        return {"mode": "portrait", "scale": s, "ox": 0, "oy": (RH - 1920 * s) / 2}
    if RW == RH:
        s = RH / 1920
        return {"mode": "square", "scale": s, "ox": (RW - 1080 * s) / 2, "oy": 0}
    top, bottom = (420, 1480) if own_head else (540, 1520)  # the part of the design that holds the visual
    s = (RH - 120) / (bottom - top)
    w = 1080 * s
    if own_head:
        return {"mode": "landscape", "scale": s, "ox": (RW - w) / 2, "oy": 40 - top * s, "hl_x": 120, "hl_w": 600}
    if mirror:
        ox = 80
        return {"mode": "landscape", "scale": s, "ox": ox, "oy": 40 - top * s, "hl_x": ox + w + 90, "hl_w": max(520, RW - (ox + w + 90) - 120)}
    # visual on the right: keep it below the logo lockup in the top-right corner (top_right = the lockup's height)
    s = (RH - 120 - top_right) / (bottom - top)
    w = 1080 * s
    ox = RW - w - 80
    return {"mode": "landscape", "scale": s, "ox": ox, "oy": 40 + top_right - top * s, "hl_x": 120, "hl_w": max(520, ox - 170)}


def render_motion_scene(out: Path, work: Path, sid: str, art: str, fmt: Dict, brand: Dict, headline: str,
                        narration: str, audio: Optional[str], audio_seconds: float, cta: str = "", logo: Optional[str] = None,
                        seconds: Optional[float] = None, festive: bool = True, data: Optional[Dict] = None, palette: int = 0,
                        theme: str = "", kicker: str = "", fps: int = FPS, design: Optional[Dict] = None, mirror: bool = False) -> float:
    """Stage one HTML composition, render it with HyperFrames, then lay the voiceover on it.
    design: the video's design system (app/services/design.py); palette: per-scene background variant; mirror: swap sides (16:9)."""
    from app.services import design as dsg
    dz = dsg.normalise(design or {"theme": theme or ("festive" if festive else "clean")}, headline, brand)
    festive_look = dz["preset"] == "festive-night"
    RW, RH = fmt["w"], fmt["h"]
    dur = round(seconds if seconds else max(audio_seconds + 0.4, min_seconds(art, data)), 2)
    stage = work / f"hf_{sid}"
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "fonts").mkdir(parents=True)
    vars_css, particles, font_files = dsg.css_vars(dz, palette)
    for f in font_files:
        shutil.copy(FONTS_DIR / f, stage / "fonts" / f)
    shutil.copy(HERE / "kit.js", stage / "kit.js")
    shutil.copy(HF_HOME / "node_modules" / "gsap" / "dist" / "gsap.min.js", stage / "gsap.min.js")
    if data and data.get("photo_path") and Path(data["photo_path"]).exists():
        shutil.copy(data["photo_path"], stage / "photo.jpg")

    # captions = the narration in short chunks, timed across the voiceover
    caps, t0 = [], 0.25
    if narration:
        parts = _chunks(narration, 5 if RW > RH else 4)
        total = sum(len(p) for p in parts) or 1
        span = max(audio_seconds - 0.1, 0.5)
        for p in parts:
            d = span * len(p) / total
            ws, wt = p.split(), t0
            wtot = sum(len(w) + 1 for w in ws) or 1
            words = []
            for w in ws:  # each word lights up while it is spoken (time shared by word length)
                wd = d * (len(w) + 1) / wtot
                words.append({"w": w, "s": round(wt, 3), "e": round(wt + wd, 3)})
                wt += wd
            caps.append({"text": p, "start": round(t0, 3), "end": round(t0 + d, 3), "words": words})
            t0 += d
    act = dz["accent"]
    cap_dark_bg = "#000000" if dz["dark"] else dz["ink"]
    if dsg.contrast(act, cap_dark_bg) < 3:  # active-word pill must stand out from the caption box
        act = dz["accent2"] if dsg.contrast(dz["accent2"], cap_dark_bg) >= 3 else "#FFD54A"
    act_fg = "#111111" if dsg.contrast("#111111", act) >= dsg.contrast("#ffffff", act) else "#ffffff"
    cues = {"scene": sid, "duration": dur, "series": "", "captions": bool(caps),
            "capact": act, "capactfg": act_fg, "capfg": "#ffffff" if dz["dark"] else dz["bg"],
            "beats": [{"start": 0.25, "end": round(max(audio_seconds, 0.5) + 0.25, 3), "captions": caps}]}
    (stage / "cues.js").write_text("window.CUES = " + json.dumps(cues, ensure_ascii=False) + ";\n", encoding="utf-8")

    logo_html = ""
    if logo and Path(logo).exists():
        ext = Path(logo).suffix
        shutil.copy(logo, stage / f"logo{ext}")
        logo_html = f'<img id="logo" src="logo{ext}" />'
    elif art == "endcard" and festive_look:
        logo_html = '<div id="ediya">' + _diya_svg("ed", 300) + "</div>"
    elif art == "endcard":
        logo_html = ('<svg id="ediya" width="300" height="300" viewBox="-150 -150 300 300"><circle r="120" fill="none" style="stroke:var(--accent)" stroke-width="8"/>'
                     '<circle r="80" fill="none" style="stroke:var(--accent2)" stroke-width="5"/><circle r="36" style="fill:var(--accent3)"/></svg>')

    a = dict(ARTS[art])
    if "build" in a:
        a["content"] = a["build"]({**(data or {}), "headline": headline, "brand": brand.get("name", ""),
                                   "kicker": (data or {}).get("kicker") or brand.get("name", "")})
    if art == "endcard" and not festive_look:
        a["content"] = a["content"].replace(_toran(1080), "")
    has_toran = 'id="toran"' in a["content"]
    has_lockup = bool(logo and Path(logo).exists()) and art != "endcard"
    lw, pad = int(min(RW, RH) * 0.085), int(min(RW, RH) * 0.035)
    nsize = max(16, int(RW * 0.0165)) if RH > RW else max(13, int(min(RW, RH) * 0.0135))
    lay = _layout(art, RW, RH, bool(a.get("own_head")) or art == "endcard", mirror,
                  top_right=(pad + lw + 2 * nsize) if has_lockup else 0)
    head_text = "" if a.get("own_head") else headline
    words = "".join(f'<span class="w">{html.escape(w)}</span>' for w in head_text.split()) if head_text else ""
    tclass = "t-" + dz["title_style"]
    if dz["fonts"] in ("news", "condensed"):
        size_k = 1.15  # condensed display faces read small
    else:
        size_k = 1.0

    if lay["mode"] == "landscape":
        size = int((92 if len(head_text) <= 22 else (78 if len(head_text) <= 40 else 66)) * size_k)
        head_in = ""
        head_out = (f'<div id="headL">' + (f'<div class="kick">{html.escape(kicker)}</div>' if kicker else "") +
                    f'<div id="head" class="out {tclass}">{words}</div><div class="bar"></div></div>') if words else ""
        bt = {"x": 120, "y": 46, "w": 900, "align": "left", "size": 22}
    else:
        head_top = {"greeting": 820, "spotlight": 780, "orbit": 780}.get(art, 330)
        size = int(((150 if len(head_text) <= 14 else 110) if art in ("greeting", "spotlight", "orbit") else 104) * size_k)
        if art in ("greeting", "spotlight", "orbit") and len(head_text) > 14:
            head_top = 720
        head_in = f'<div id="head" class="in {tclass}">{words}</div>' if words else ""
        head_out = ""
        s = lay["scale"]
        bt = {"x": lay["ox"], "y": lay["oy"] + 70 * s, "w": 1080 * s, "align": "center", "size": max(14, int(30 * s))}
    if has_toran:
        bt["size"] = 0
    lockup_css, brand_html = "", html.escape(brand.get("name", ""))
    if art == "endcard" and logo and Path(logo).exists():
        lockup_css = "\n  #brandtag { display: none; }"  # the end card already shows the big logo and name
    if has_lockup and not has_toran:
        lockup_css = (f"\n  #brandtag {{ left: auto; right: {pad}px; top: {pad}px; width: auto; display: flex; flex-direction: column;"
                      f" align-items: center; gap: {int(nsize * 0.6)}px; font-size: {nsize}px; letter-spacing: .18em; }}"
                      f"\n  #brandtag img {{ width: {lw}px; height: {lw}px; object-fit: contain; }}")
        brand_html = f'<img src="logo{Path(logo).suffix}" /><span>{brand_html}</span>'
    bg_html, bg_css, bg_js = dsg.bg_layer(dz["background"], RW, RH)
    page = (HERE / "base.html").read_text(encoding="utf-8")
    rep = {
        "{{STYLE}}": a.get("style", "") + ("\n  #brandtag { display: none; }" if has_toran else "") + lockup_css,
        "{{CONTENT}}": a["content"], "{{SCRIPT}}": a["script"], "{{HEADIN}}": head_in, "{{HEADOUT}}": head_out, "{{LOGO}}": logo_html,
        "{{BRANDTAG}}": brand_html, "{{BRAND}}": html.escape(brand.get("name", "")), "{{CTA}}": html.escape(cta or brand.get("cta") or ""),
        "{{ID}}": sid, "{{DURATION}}": f"{dur:.3f}", "{{W}}": "1080", "{{H}}": "1920", "{{RW}}": str(RW), "{{RH}}": str(RH),
        "{{SCALE}}": f"{lay['scale']:.4f}", "{{OX}}": f"{lay['ox']:.1f}", "{{OY}}": f"{lay['oy']:.1f}",
        "{{HLX}}": f"{lay.get('hl_x', 0):.0f}", "{{HLW}}": f"{lay.get('hl_w', 0):.0f}",
        "{{HEADTOP}}": str(head_top) if lay["mode"] != "landscape" else "0", "{{HEADSIZE}}": str(size),
        "{{BTX}}": f"{bt['x']:.0f}", "{{BTY}}": f"{bt['y']:.0f}", "{{BTW}}": f"{bt['w']:.0f}", "{{BTALIGN}}": bt["align"], "{{BTSIZE}}": str(bt["size"]),
        "{{CAPBOTTOM}}": str(int(RH * (0.11 if RH > RW else 0.045))), "{{CAPW}}": str(int(RW * (0.86 if RH >= RW else 0.7))),
        "{{CAPSIZE}}": str(int(min(RW, RH) * (0.05 if RH > RW else 0.04))),
        "{{THEMEVARS}}": vars_css, "{{PARTICLES}}": particles, "{{FPS}}": str(fps), "{{FONTFACES}}": dsg.font_faces(font_files),
        "{{BGKIND}}": dz["background"], "{{BGLAYER}}": bg_html, "{{BGSTYLE}}": bg_css, "{{BGSCRIPT}}": bg_js, "{{TRANSITION}}": dz["transition"],
    }
    for _ in range(2):  # content contains {{BRAND}}/{{LOGO}} too
        for k, v in rep.items():
            page = page.replace(k, v)
    (stage / "index.html").write_text(page, encoding="utf-8")

    silent = work / f"{sid}_silent.mp4"
    env = {**os.environ, "HYPERFRAMES_SKIP_SKILLS": "1", "HYPERFRAMES_TELEMETRY_DISABLED": "1", "DO_NOT_TRACK": "1"}
    extra = ["--workers", os.environ["HF_WORKERS"]] if os.environ.get("HF_WORKERS") else []
    p = subprocess.run(["node", str(_hf_bin()), "render", str(stage), "--fps", str(fps), "--quality", "delivery", "-o", str(silent), *extra],
                       cwd=str(HF_HOME), env=env, capture_output=True, text=True)
    if p.returncode != 0 or not silent.exists():
        raise RuntimeError("HyperFrames render failed: " + " | ".join((p.stderr or p.stdout).strip().splitlines()[-6:]))

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(silent)]
    cmd += ["-i", audio] if audio else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    cmd += ["-map", "0:v", "-map", "1:a", "-af", "apad", "-t", str(dur), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-ar", "44100", "-ac", "2", "-movflags", "+faststart", str(out)]
    q = subprocess.run(cmd, capture_output=True, text=True)
    if q.returncode != 0:
        raise RuntimeError("ffmpeg mux failed: " + q.stderr[-400:])
    silent.unlink(missing_ok=True)
    if not os.environ.get("HF_KEEP_STAGE"):
        shutil.rmtree(stage, ignore_errors=True)
    return dur

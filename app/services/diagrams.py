"""More diagram types and alternative layouts, so a video never shows the same picture twice.

Two ideas:
  1. New diagrams whose SHAPE carries meaning: timeline, cycle, pyramid, hierarchy, matrix, funnel, venn, bars, steps, mindmap, target.
  2. Alternative layouts (variants) of the common ones: a "flow" can be stacked boxes, chevrons or a winding path; a "compare"
     can be two cards, a balance or before/after; and so on. motion.assign_arts rotates through them.
All coordinates are in the 1080x1920 design space; visuals stay inside y 600-1460 so the 16:9 crop keeps them. Colours,
fonts and corners come from the design system's CSS variables.
"""
import html
import math
from typing import Dict, List

_esc = html.escape


def _pts(d: Dict, lo: int = 2, hi: int = 5) -> List[str]:
    p = [str(x).strip() for x in (d.get("points") or []) if str(x).strip()]
    return p[:hi]


def _icon(name: str, size: int, color: str = "var(--accent)") -> str:
    from app.services.motion import _icon_svg
    return _icon_svg(name, size, color)


LABEL = "font-family: var(--font-body); font-weight: 700; color: var(--ink); line-height: 1.2;"
BOX = "background: var(--card); border: 2px solid var(--cardline); box-shadow: var(--shadow); border-radius: var(--radius);"
NEW: Dict[str, Dict] = {}

# ------------------------------------------------------------------ timeline (a sequence in time)
def _timeline(d, zig=False):
    p = _pts(d)
    n = max(len(p), 1)
    gap = min(230, 820 / max(n - 1, 1))
    y0 = 1040 - (n - 1) * gap / 2
    out = [f'<div class="tl-line" style="left:{538 if zig else 178}px;top:{y0 - 40:.0f}px;height:{(n - 1) * gap + 80:.0f}px"></div>']
    for i, t in enumerate(p):
        date, _, text = t.partition(": ") if ": " in t else ("", "", t)  # "12:00 PM: lunch" keeps the time whole
        y = y0 + i * gap
        x = 540 if zig else 180
        out.append(f'<div class="tl-dot" style="left:{x - 26}px;top:{y - 26:.0f}px"></div>')
        side = (i % 2 == 0) if zig else True
        left = (610 if side else 80) if zig else 250
        align = "left" if side else "right"
        out.append(f'<div class="tl-item" style="left:{left}px;top:{y - 70:.0f}px;text-align:{align}">'
                   + (f'<div class="tl-date">{_esc(date.strip())}</div>' if date else "") + f'<div class="tl-text">{_esc(text.strip())}</div></div>')
    return "".join(out)


_TL_STYLE = f"""
  .tl-line {{ position: absolute; width: 8px; border-radius: 4px; background: linear-gradient(var(--accent), var(--accent2)); transform-origin: 50% 0; }}
  .tl-dot {{ position: absolute; width: 52px; height: 52px; border-radius: 50%; background: var(--surface); border: 8px solid var(--accent); }}
  .tl-item {{ position: absolute; width: 390px; }}
  .tl-item .tl-date {{ font-family: var(--font-head); font-size: 40px; color: var(--accent); margin-bottom: 6px; }}
  .tl-item .tl-text {{ {LABEL} font-size: 44px; }}"""
_TL_STYLE_WIDE = _TL_STYLE.replace("width: 390px", "width: 760px")
_TL_SCRIPT = """
  gsap.set(".tl-line", {scaleY: 0}); tl.to(".tl-line", {scaleY: 1, duration: 1.0, ease: "power2.inOut"}, 0.3);
  var dots = EZ.$$(".tl-dot"), items = EZ.$$(".tl-item"), g = Math.max(0.35, Math.min(0.9, (D - 2) / (dots.length || 1)));
  dots.forEach(function (o, i) { gsap.set(o, {scale: 0, transformOrigin: "50% 50%"}); tl.to(o, {scale: 1, duration: 0.4, ease: "back.out(3)"}, 0.6 + i * g); });
  items.forEach(function (o, i) { gsap.set(o, {opacity: 0, y: 24}); tl.to(o, {opacity: 1, y: 0, duration: 0.5}, 0.75 + i * g); });
"""
NEW["timeline"] = {"needs": "points2", "build": lambda d: _timeline(d), "style": _TL_STYLE_WIDE, "script": _TL_SCRIPT}
NEW["timeline_zig"] = {"needs": "points2", "build": lambda d: _timeline(d, True), "style": _TL_STYLE, "script": _TL_SCRIPT}

# ------------------------------------------------------------------ cycle (a loop that repeats)
def _cycle(d):
    p = _pts(d, 3, 5) or ["", "", ""]
    n = len(p)
    cx, cy, r = 540, 1010, 330
    out = ['<svg class="abs" width="1080" height="1920" style="left:0;top:0"><defs><marker id="cyar" markerWidth="10" markerHeight="10" refX="6" refY="5" orient="auto">'
           '<path d="M0 0 L10 5 L0 10 Z" style="fill:var(--accent2)"/></marker></defs>']
    for k in range(n):
        a0 = math.radians(-90 + k * 360 / n + 24)
        a1 = math.radians(-90 + (k + 1) * 360 / n - 24)
        x0, y0, x1, y1 = cx + r * math.cos(a0), cy + r * math.sin(a0), cx + r * math.cos(a1), cy + r * math.sin(a1)
        out.append(f'<path class="cy-arc" d="M{x0:.0f} {y0:.0f} A{r} {r} 0 0 1 {x1:.0f} {y1:.0f}" fill="none" style="stroke:var(--accent2)" '
                   f'stroke-width="9" stroke-linecap="round" marker-end="url(#cyar)" stroke-dasharray="900" stroke-dashoffset="900"/>')
    out.append(f'<g id="cy-core"><circle cx="{cx}" cy="{cy}" r="120" fill="none" style="stroke:var(--cardline)" stroke-width="6" stroke-dasharray="18 16"/></g></svg>')
    for k, t in enumerate(p):
        a = math.radians(-90 + k * 360 / n)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        out.append(f'<div class="cy-node" style="left:{x - 125:.0f}px;top:{y - 125:.0f}px"><span>{_esc(t)}</span></div>')
    return "".join(out)


NEW["cycle"] = {"needs": "points3", "build": _cycle, "style": f"""
  .cy-node {{ position: absolute; width: 250px; height: 250px; border-radius: 50%; display: flex; align-items: center; justify-content: center; padding: 26px;
             text-align: center; background: var(--surface); border: 6px solid var(--accent); box-shadow: var(--shadow); }}
  .cy-node span {{ {LABEL} font-size: 38px; }}""", "script": """
  var nodes = EZ.$$(".cy-node"), g = Math.max(0.35, Math.min(0.8, (D - 2) / (nodes.length || 1)));
  nodes.forEach(function (o, i) { gsap.set(o, {scale: 0, transformOrigin: "50% 50%"}); tl.to(o, {scale: 1, duration: 0.5, ease: "back.out(2.2)"}, 0.4 + i * g); });
  EZ.$$(".cy-arc").forEach(function (o, i) { tl.to(o, {strokeDashoffset: 0, duration: 0.5, ease: "power2.inOut"}, 0.7 + i * g); });
  tl.to("#cy-core", {rotation: 90, svgOrigin: "540 1010", duration: D, ease: "none"}, 0);
"""}

# ------------------------------------------------------------------ pyramid (levels / priorities, top = most important)
def _pyramid(d):
    p = _pts(d, 2, 5) or ["", ""]
    n = len(p)
    top, bottom, gap = 640, 1440, 14
    h = (bottom - top - gap * (n - 1)) / n
    out = ['<svg class="abs" width="1080" height="1920" style="left:0;top:0">']
    labels = []
    for i, t in enumerate(p):
        y0 = top + i * (h + gap)
        y1 = y0 + h
        w0 = 220 + (y0 - top) / (bottom - top) * 760
        w1 = 220 + (y1 - top) / (bottom - top) * 760
        fill = "color-mix(in srgb, var(--accent) 30%, var(--surface))" if i == 0 else "var(--surface)"
        out.append(f'<polygon class="py-l" points="{540 - w0 / 2:.0f},{y0:.0f} {540 + w0 / 2:.0f},{y0:.0f} {540 + w1 / 2:.0f},{y1:.0f} {540 - w1 / 2:.0f},{y1:.0f}" '
                   f'style="fill:{fill};stroke:var(--accent)" stroke-width="5" stroke-linejoin="round"/>')
        labels.append(f'<div class="py-t" style="top:{y0 + h / 2 - 30:.0f}px">{_esc(t)}</div>')
    out.append("</svg>")
    return "".join(out) + "".join(labels)


NEW["pyramid"] = {"needs": "points2", "build": _pyramid, "style": f"""
  .py-t {{ position: absolute; left: 140px; width: 800px; text-align: center; {LABEL} font-size: 42px; }}""", "script": """
  var L = EZ.$$(".py-l"), T = EZ.$$(".py-t"), n = L.length || 1, g = Math.max(0.3, Math.min(0.8, (D - 2) / n));
  for (var i = n - 1; i >= 0; i--) { var t = 0.4 + (n - 1 - i) * g;
    gsap.set(L[i], {opacity: 0, y: 40}); tl.to(L[i], {opacity: 1, y: 0, duration: 0.5, ease: "power3.out"}, t);
    gsap.set(T[i], {opacity: 0}); tl.to(T[i], {opacity: 1, duration: 0.4}, t + 0.2); }
"""}

# ------------------------------------------------------------------ hierarchy (a team, roles, delegation)
def _hierarchy(d):
    p = _pts(d, 2, 4) or ["", ""]
    root, kids = p[0], p[1:] or [""]
    n = len(kids)
    xs = {1: [540], 2: [300, 780], 3: [190, 540, 890]}[min(n, 3)]
    out = ['<svg class="abs" width="1080" height="1920" style="left:0;top:0">']
    for x in xs[:n]:
        out.append(f'<path class="hi-ln" d="M540 860 L540 960 L{x} 960 L{x} 1080" fill="none" style="stroke:var(--accent)" stroke-width="6" '
                   f'stroke-linejoin="round" stroke-dasharray="700" stroke-dashoffset="700"/>')
    out.append("</svg>")
    out.append(f'<div class="hi-box hi-root" style="left:300px;top:660px;width:480px">{_icon("users", 64)}<span>{_esc(root)}</span></div>')
    for x, t in zip(xs, kids):
        out.append(f'<div class="hi-box hi-kid" style="left:{x - 150}px;top:1080px;width:300px">{_icon("check", 48, "var(--accent2)")}<span>{_esc(t)}</span></div>')
    return "".join(out)


NEW["hierarchy"] = {"needs": "points2", "build": _hierarchy, "style": f"""
  .hi-box {{ position: absolute; min-height: 190px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px;
            padding: 22px; text-align: center; {BOX} }}
  .hi-root {{ border-color: var(--accent); border-width: 4px; }}
  .hi-box span {{ {LABEL} font-size: 40px; }}""", "script": """
  gsap.set(".hi-root", {opacity: 0, y: -40}); tl.to(".hi-root", {opacity: 1, y: 0, duration: 0.6, ease: "back.out(1.8)"}, 0.3);
  tl.to(".hi-ln", {strokeDashoffset: 0, duration: 0.7, stagger: 0.15, ease: "power2.inOut"}, 0.9);
  gsap.set(".hi-kid", {opacity: 0, y: 40}); tl.to(".hi-kid", {opacity: 1, y: 0, duration: 0.5, stagger: 0.2, ease: "back.out(1.8)"}, 1.3);
"""}

# ------------------------------------------------------------------ matrix (two factors, four options)
def _matrix(d):
    p = (_pts(d, 2, 4) + ["", "", "", ""])[:4]
    cells = [(100, 640), (560, 640), (100, 1060), (560, 1060)]
    out = ['<div class="mx-ax mx-y"></div><div class="mx-ax mx-x"></div>']
    for i, ((x, y), t) in enumerate(zip(cells, p)):
        out.append(f'<div class="mx-c{" mx-hi" if i == 1 else ""}" style="left:{x}px;top:{y}px"><span>{_esc(t)}</span></div>')
    return "".join(out)


NEW["matrix"] = {"needs": "points2", "build": _matrix, "style": f"""
  .mx-c {{ position: absolute; width: 420px; height: 390px; display: flex; align-items: center; justify-content: center; padding: 30px; text-align: center; {BOX} }}
  .mx-c span {{ {LABEL} font-size: 42px; }}
  .mx-hi {{ background: color-mix(in srgb, var(--accent) 26%, var(--surface)); border-color: var(--accent); border-width: 4px; }}
  .mx-ax {{ position: absolute; background: var(--accent2); border-radius: 4px; }}
  .mx-y {{ left: 70px; top: 610px; width: 8px; height: 860px; transform-origin: 50% 100%; }}
  .mx-x {{ left: 70px; top: 1462px; width: 940px; height: 8px; transform-origin: 0 50%; }}""", "script": """
  gsap.set(".mx-y", {scaleY: 0}); gsap.set(".mx-x", {scaleX: 0});
  tl.to(".mx-y", {scaleY: 1, duration: 0.6}, 0.3); tl.to(".mx-x", {scaleX: 1, duration: 0.6}, 0.5);
  gsap.set(".mx-c", {opacity: 0, scale: 0.85, transformOrigin: "50% 50%"});
  tl.to(".mx-c", {opacity: 1, scale: 1, duration: 0.45, stagger: 0.22, ease: "back.out(1.8)"}, 0.8);
  tl.to(".mx-hi", {scale: 1.05, duration: 0.4, yoyo: true, repeat: 1, ease: "sine.inOut"}, 2.0);
"""}

# ------------------------------------------------------------------ funnel (filtering many into few)
def _funnel(d):
    p = _pts(d, 2, 4) or ["", ""]
    n = len(p)
    top, bottom = 660, 1400
    h = (bottom - top) / n
    out = ['<svg class="abs" width="1080" height="1920" style="left:0;top:0">']
    for i in range(n):
        y0, y1 = top + i * h + 6, top + (i + 1) * h - 6
        w0 = 960 - (i / n) * 640
        w1 = 960 - ((i + 1) / n) * 640
        out.append(f'<polygon class="fn-l" points="{540 - w0 / 2:.0f},{y0:.0f} {540 + w0 / 2:.0f},{y0:.0f} {540 + w1 / 2:.0f},{y1:.0f} {540 - w1 / 2:.0f},{y1:.0f}" '
                   f'style="fill:color-mix(in srgb, var({["--accent", "--accent2", "--accent3", "--accent"][i]}) {38 - i * 6}%, var(--surface));stroke:var(--cardline)" stroke-width="3"/>')
    out += [f'<circle class="fn-d" cx="{300 + k * 120}" cy="600" r="14" style="fill:var(--accent)"/>' for k in range(5)]
    out.append("</svg>")
    out += [f'<div class="fn-t" style="top:{top + i * h + h / 2 - 28:.0f}px">{_esc(t)}</div>' for i, t in enumerate(p)]
    return "".join(out)


NEW["funnel"] = {"needs": "points2", "build": _funnel, "style": f"""
  .fn-t {{ position: absolute; left: 190px; width: 700px; text-align: center; {LABEL} font-size: 42px; }}""", "script": """
  var L = EZ.$$(".fn-l"), T = EZ.$$(".fn-t"), g = Math.max(0.3, Math.min(0.7, (D - 2) / (L.length || 1)));
  L.forEach(function (o, i) { gsap.set(o, {opacity: 0, scaleX: 0.6, transformOrigin: "50% 50%"}); tl.to(o, {opacity: 1, scaleX: 1, duration: 0.5, ease: "power3.out"}, 0.3 + i * g); });
  T.forEach(function (o, i) { gsap.set(o, {opacity: 0}); tl.to(o, {opacity: 1, duration: 0.4}, 0.5 + i * g); });
  EZ.$$(".fn-d").forEach(function (o, k) { gsap.set(o, {opacity: 0}); tl.set(o, {opacity: 1}, 1.2 + k * 0.25);
    tl.to(o, {attr: {cx: 540, cy: 1420}, duration: 1.4, ease: "power1.in"}, 1.2 + k * 0.25); tl.to(o, {opacity: 0, duration: 0.2}, 2.5 + k * 0.25); });
"""}

# ------------------------------------------------------------------ venn (two or three ideas overlapping)
def _venn(d):
    p = _pts(d, 2, 3) or ["", ""]
    n = len(p)
    pos = {2: [(390, 1020), (690, 1020)], 3: [(540, 880), (400, 1130), (680, 1130)]}[n]
    lab = {2: [(160, 980), (660, 980)], 3: [(390, 700), (100, 1250), (690, 1250)]}[n]
    cols = ["--accent", "--accent2", "--accent3"]
    out = ['<svg class="abs" width="1080" height="1920" style="left:0;top:0">']
    out += [f'<circle class="vn-c" cx="{x}" cy="{y}" r="270" style="fill:color-mix(in srgb, var({cols[i]}) 30%, transparent);stroke:var({cols[i]})" stroke-width="5"/>'
            for i, (x, y) in enumerate(pos)]
    out.append("</svg>")
    out += [f'<div class="vn-t" style="left:{x}px;top:{y}px">{_esc(t)}</div>' for (x, y), t in zip(lab, p)]
    out.append(f'<div class="vn-star" style="left:{sum(x for x, _ in pos) / n - 50:.0f}px;top:{sum(y for _, y in pos) / n - 50:.0f}px">{_icon("star", 70, "var(--ink)")}</div>')
    return "".join(out)


NEW["venn"] = {"needs": "points2", "build": _venn, "style": f"""
  .vn-t {{ position: absolute; width: 300px; text-align: center; {LABEL} font-size: 40px; }}
  .vn-star {{ position: absolute; width: 100px; height: 100px; display: flex; align-items: center; justify-content: center; }}""", "script": """
  var C = EZ.$$(".vn-c");
  C.forEach(function (o, i) { gsap.set(o, {opacity: 0, x: (i - (C.length - 1) / 2) * 160}); tl.to(o, {opacity: 1, x: 0, duration: 0.9, ease: "power3.out"}, 0.3 + i * 0.25); });
  gsap.set(".vn-t", {opacity: 0, y: 20}); tl.to(".vn-t", {opacity: 1, y: 0, duration: 0.5, stagger: 0.2}, 1.0);
  gsap.set(".vn-star", {scale: 0, rotation: -90, transformOrigin: "50% 50%"}); tl.to(".vn-star", {scale: 1, rotation: 0, duration: 0.6, ease: "back.out(2.5)"}, 1.6);
"""}

# ------------------------------------------------------------------ bars (growth, more of something; no numbers invented)
def _bars(d):
    p = _pts(d, 2, 5) or ["", "", ""]
    n = len(p)
    w = min(170, 840 / n - 40)
    x0 = 540 - (n * (w + 30) - 30) / 2
    from app.services.charts import _vals, _fmt
    vals, ill = _vals(d, n, [1])
    hi = max(vals) or 1
    unit = d.get("unit") or ""
    out = ['<div class="br-base"></div>']
    if ill:
        out.append('<div class="ill">Illustrative</div>')
    for i, t in enumerate(p):
        h = 260 + (i / max(n - 1, 1)) * 460 if ill else max(40, 720 * vals[i] / hi)
        x = x0 + i * (w + 30)
        if not ill:
            out.append(f'<div class="br-v" style="left:{x - 20:.0f}px;width:{w + 40:.0f}px;top:{1380 - h - 70:.0f}px">{_esc(_fmt(vals[i], unit))}</div>')
        out.append(f'<div class="br-b" style="left:{x:.0f}px;top:{1380 - h:.0f}px;width:{w:.0f}px;height:{h:.0f}px;'
                   f'background:linear-gradient(180deg, var({"--accent" if i == n - 1 else "--accent2"}), color-mix(in srgb, var({"--accent" if i == n - 1 else "--accent2"}) 55%, var(--surface)))"></div>'
                   f'<div class="br-t" style="left:{x - 8:.0f}px;width:{w + 16:.0f}px">{_esc(t)}</div>')
    if ill:  # the dashed trend line only makes sense for the illustrative rising bars
        out.append('<svg class="abs" width="1080" height="1920" style="left:0;top:0"><path id="br-tr" d="M150 1180 C 400 1100, 600 900, 960 620" fill="none" '
                   'style="stroke:var(--ink)" stroke-width="6" stroke-linecap="round" stroke-dasharray="14 14" opacity=".55"/></svg>')
    return "".join(out)


NEW["bars"] = {"needs": "points2", "build": _bars, "style": f"""
  .br-base {{ position: absolute; left: 90px; top: 1384px; width: 900px; height: 6px; border-radius: 3px; background: var(--cardline); }}
  .br-b {{ position: absolute; border-radius: min(var(--radius), 20px) min(var(--radius), 20px) 6px 6px; transform-origin: 50% 100%; }}
  .br-t {{ position: absolute; top: 1404px; text-align: center; {LABEL} font-size: 28px; line-height: 1.15; }}
  .br-v {{ position: absolute; text-align: center; font-family: var(--font-head); font-size: 44px; color: var(--ink); }}
  .ill {{ position: absolute; right: 70px; top: 610px; padding: 8px 18px; border-radius: 999px; border: 2px solid var(--cardline);
         font-family: var(--font-body); font-size: 24px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }}""", "script": """
  var B = EZ.$$(".br-b"), g = Math.max(0.2, Math.min(0.5, (D - 2) / (B.length || 1)));
  B.forEach(function (o, i) { gsap.set(o, {scaleY: 0}); tl.to(o, {scaleY: 1, duration: 0.6, ease: "back.out(1.4)"}, 0.4 + i * g); });
  gsap.set(".br-t", {opacity: 0}); tl.to(".br-t", {opacity: 1, duration: 0.4, stagger: g}, 0.6);
  if (EZ.$("#br-tr")) { gsap.set("#br-tr", {opacity: 0}); tl.to("#br-tr", {opacity: 0.55, duration: 0.6}, 0.6 + B.length * g); }
  gsap.set(".br-v", {opacity: 0, y: 10}); tl.to(".br-v", {opacity: 1, y: 0, duration: 0.35, stagger: g}, 0.8);
"""}

# ------------------------------------------------------------------ steps (a staircase of progress)
def _steps(d):
    p = _pts(d, 2, 5) or ["", ""]
    n = len(p)
    w = 900 / n
    out = []
    for i, t in enumerate(p):
        h = 180 + i * (560 / max(n - 1, 1))
        x = 90 + i * w
        out.append(f'<div class="st-b" style="left:{x:.0f}px;top:{1430 - h:.0f}px;width:{w - 12:.0f}px;height:{h:.0f}px"><div class="st-n">{i + 1}</div></div>'
                   f'<div class="st-t" style="left:{x - 10:.0f}px;top:{1430 - h - 120:.0f}px;width:{w + 8:.0f}px">{_esc(t)}</div>')
    out.append(f'<div id="st-flag" style="left:{90 + (n - 1) * w + w / 2 - 40:.0f}px;top:{1430 - 740 - 270:.0f}px">{_icon("star", 80)}</div>')
    return "".join(out)


NEW["steps"] = {"needs": "points2", "build": _steps, "style": f"""
  .st-b {{ position: absolute; border-radius: min(var(--radius), 18px) min(var(--radius), 18px) 0 0; transform-origin: 50% 100%;
          background: linear-gradient(180deg, color-mix(in srgb, var(--accent) 70%, var(--surface)), color-mix(in srgb, var(--accent) 25%, var(--surface)));
          border: 2px solid var(--cardline); }}
  .st-n {{ margin: 18px auto 0; width: 70px; height: 70px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
          background: var(--surface); color: var(--ink); font-family: var(--font-head); font-size: 40px; }}
  .st-t {{ position: absolute; text-align: center; {LABEL} font-size: 34px; }}
  #st-flag {{ position: absolute; width: 80px; height: 80px; }}""", "script": """
  var B = EZ.$$(".st-b"), T = EZ.$$(".st-t"), g = Math.max(0.3, Math.min(0.7, (D - 2) / (B.length || 1)));
  B.forEach(function (o, i) { gsap.set(o, {scaleY: 0}); tl.to(o, {scaleY: 1, duration: 0.5, ease: "power3.out"}, 0.4 + i * g); });
  T.forEach(function (o, i) { gsap.set(o, {opacity: 0, y: 20}); tl.to(o, {opacity: 1, y: 0, duration: 0.4}, 0.6 + i * g); });
  gsap.set("#st-flag", {opacity: 0, y: -60}); tl.to("#st-flag", {opacity: 1, y: 0, duration: 0.6, ease: "bounce.out"}, 0.6 + B.length * g);
"""}

# ------------------------------------------------------------------ mindmap (ideas around one core)
def _mindmap(d):
    p = _pts(d, 3, 6) or ["", "", ""]
    n = len(p)
    cx, cy = 540, 1030
    out = ['<svg class="abs" width="1080" height="1920" style="left:0;top:0">']
    nodes = []
    for k, t in enumerate(p):
        a = math.radians(-90 + k * 360 / n + (15 if n % 2 == 0 else 0))
        x, y = cx + 360 * math.cos(a), cy + 330 * math.sin(a)
        mx, my = cx + 180 * math.cos(a + 0.35), cy + 165 * math.sin(a + 0.35)
        out.append(f'<path class="mm-ln" d="M{cx} {cy} Q{mx:.0f} {my:.0f} {x:.0f} {y:.0f}" fill="none" style="stroke:var(--accent2)" stroke-width="6" '
                   f'stroke-linecap="round" stroke-dasharray="600" stroke-dashoffset="600"/>')
        nodes.append(f'<div class="mm-n" style="left:{x - 150:.0f}px;top:{y - 55:.0f}px">{_esc(t)}</div>')
    out.append("</svg>")
    return "".join(out) + f'<div id="mm-core">{_icon("zap", 90, "#fff")}</div>' + "".join(nodes)


NEW["mindmap"] = {"needs": "points3", "build": _mindmap, "style": f"""
  #mm-core {{ position: absolute; left: 430px; top: 920px; width: 220px; height: 220px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
             background: linear-gradient(135deg, var(--accent), var(--accent2)); box-shadow: var(--shadow); }}
  .mm-n {{ position: absolute; width: 300px; min-height: 110px; padding: 18px 22px; display: flex; align-items: center; justify-content: center; text-align: center;
          {BOX} {LABEL} font-size: 36px; }}""", "script": """
  gsap.set("#mm-core", {scale: 0, transformOrigin: "50% 50%"}); tl.to("#mm-core", {scale: 1, duration: 0.6, ease: "back.out(2.2)"}, 0.3);
  var L = EZ.$$(".mm-ln"), N = EZ.$$(".mm-n"), g = Math.max(0.25, Math.min(0.6, (D - 2) / (N.length || 1)));
  L.forEach(function (o, i) { tl.to(o, {strokeDashoffset: 0, duration: 0.5, ease: "power2.out"}, 0.8 + i * g); });
  N.forEach(function (o, i) { gsap.set(o, {opacity: 0, scale: 0.7, transformOrigin: "50% 50%"}); tl.to(o, {opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2)"}, 1.0 + i * g); });
"""}

# ------------------------------------------------------------------ target (a goal, focus, aim)
def _target(d):
    p = _pts(d, 0, 3)
    rings = "".join(f'<circle class="tg-r" cx="470" cy="1030" r="{r}" style="fill:{f}"/>' for r, f in
                    ((340, "var(--surface)"), (260, "color-mix(in srgb, var(--accent) 30%, var(--surface))"), (180, "var(--surface)"),
                     (100, "color-mix(in srgb, var(--accent) 65%, var(--surface))"), (36, "var(--accent2)")))
    arrow = ('<g id="tg-ar"><line x1="470" y1="1030" x2="760" y2="760" style="stroke:var(--ink)" stroke-width="10" stroke-linecap="round"/>'
             '<path d="M760 760 L800 700 M760 760 L820 750" style="stroke:var(--accent)" stroke-width="10" stroke-linecap="round"/></g>')
    chips = "".join(f'<div class="tg-c" style="top:{1240 + i * 0}px;left:{90 + i * 300}px">{_esc(t)}</div>' for i, t in enumerate(p))
    return f'<svg class="abs" width="1080" height="1920" style="left:0;top:0">{rings}{arrow}</svg>' + (f'<div id="tg-cs">{chips}</div>' if p else "")


NEW["target"] = {"build": _target, "style": f"""
  .tg-r {{ stroke: var(--cardline); stroke-width: 3; }}
  #tg-cs {{ position: absolute; left: 90px; top: 1400px; width: 900px; display: flex; gap: 18px; justify-content: center; flex-wrap: wrap; }}
  .tg-c {{ position: static; padding: 14px 26px; border-radius: 999px; border: 3px solid var(--accent); {LABEL} font-size: 34px; }}""", "script": """
  gsap.set(".tg-r", {scale: 0, transformOrigin: "50% 50%"}); tl.to(".tg-r", {scale: 1, duration: 0.5, stagger: 0.12, ease: "back.out(2)"}, 0.3);
  gsap.set("#tg-ar", {x: 420, y: -420, opacity: 0}); tl.to("#tg-ar", {x: 0, y: 0, opacity: 1, duration: 0.45, ease: "power4.in"}, 1.1);
  tl.to("#tg-ar", {rotation: 3, svgOrigin: "470 1030", duration: 0.08, yoyo: true, repeat: 5}, 1.55);
  if (EZ.$("#tg-cs")) { gsap.set(".tg-c", {opacity: 0, y: 20}); tl.to(".tg-c", {opacity: 1, y: 0, duration: 0.4, stagger: 0.15}, 1.8); }
"""}

# ================================================================== alternative layouts of the common animations
# flow -> chevrons (left to right arrows)
def _chevrons(d):
    p = _pts(d, 2, 4) or ["", ""]
    n = len(p)
    h = min(240, 760 / n)
    out = []
    for i, t in enumerate(p):
        y = 1030 - n * h / 2 + i * h
        out.append(f'<div class="cv" style="top:{y:.0f}px;height:{h - 18:.0f}px;left:{90 + i * 40}px;width:{900 - i * 80}px">'
                   f'<b>{i + 1}</b><span>{_esc(t)}</span></div>')
    return "".join(out)


NEW["chevrons"] = {"needs": "points2", "build": _chevrons, "style": f"""
  .cv {{ position: absolute; display: flex; align-items: center; gap: 28px; padding: 0 90px 0 50px;
        clip-path: polygon(0 0, calc(100% - 60px) 0, 100% 50%, calc(100% - 60px) 100%, 0 100%, 40px 50%);
        background: color-mix(in srgb, var(--accent) 22%, var(--surface)); }}
  .cv:nth-child(even) {{ background: color-mix(in srgb, var(--accent2) 22%, var(--surface)); }}
  .cv b {{ font-family: var(--font-head); font-size: 64px; color: var(--accent); min-width: 60px; text-align: center; }}
  .cv span {{ {LABEL} font-size: 44px; }}""", "script": """
  var C = EZ.$$(".cv"), g = Math.max(0.35, Math.min(0.9, (D - 2) / (C.length || 1)));
  C.forEach(function (o, i) { gsap.set(o, {opacity: 0, x: -200}); tl.to(o, {opacity: 1, x: 0, duration: 0.55, ease: "power3.out"}, 0.4 + i * g); });
"""}


# flow -> numbered stops on a winding path
def _pathsteps(d):
    p = _pts(d, 2, 4) or ["", ""]
    n = len(p)
    pts = [(240, 700), (800, 900), (260, 1130), (790, 1350)][:n]
    path = "M" + " ".join(f"{x} {y}" if i == 0 else f"C {pts[i - 1][0]} {pts[i - 1][1] + 160}, {x} {y - 160}, {x} {y}" for i, (x, y) in enumerate(pts))
    out = [f'<svg class="abs" width="1080" height="1920" style="left:0;top:0"><path id="ps-path" d="{path}" fill="none" style="stroke:var(--accent2)" '
           f'stroke-width="10" stroke-linecap="round" stroke-dasharray="3000" stroke-dashoffset="3000"/></svg>']
    for i, ((x, y), t) in enumerate(zip(pts, p)):
        lx = x + 90 if x < 540 else x - 470
        out.append(f'<div class="ps-n" style="left:{x - 60}px;top:{y - 60}px">{i + 1}</div><div class="ps-t" style="left:{lx}px;top:{y - 40}px">{_esc(t)}</div>')
    return "".join(out)


NEW["pathsteps"] = {"needs": "points2", "build": _pathsteps, "style": f"""
  .ps-n {{ position: absolute; width: 120px; height: 120px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #fff;
          font-family: var(--font-head); font-size: 56px; background: linear-gradient(135deg, var(--accent), var(--accent2)); box-shadow: var(--shadow); }}
  .ps-t {{ position: absolute; width: 380px; {LABEL} font-size: 42px; }}""", "script": """
  tl.to("#ps-path", {strokeDashoffset: 0, duration: Math.min(2.4, D - 1.2), ease: "power1.inOut"}, 0.3);
  var N = EZ.$$(".ps-n"), T = EZ.$$(".ps-t"), g = Math.min(2.4, D - 1.2) / (N.length || 1);
  N.forEach(function (o, i) { gsap.set(o, {scale: 0, transformOrigin: "50% 50%"}); tl.to(o, {scale: 1, duration: 0.4, ease: "back.out(3)"}, 0.3 + i * g); });
  T.forEach(function (o, i) { gsap.set(o, {opacity: 0}); tl.to(o, {opacity: 1, duration: 0.4}, 0.45 + i * g); });
"""}


# checklist -> sticky notes grid
def _notes(d):
    p = _pts(d, 1, 4)
    n = len(p)
    cells = [(100, 650), (560, 700), (120, 1080), (570, 1120)][:n]
    rot = [-3, 2.5, 2, -2.5]
    return "".join(f'<div class="nt" style="left:{x}px;top:{y}px;--r:{rot[i]}deg"><div class="nt-pin"></div>{_icon("check", 56, "var(--accent2)")}<span>{_esc(t)}</span></div>'
                   for i, ((x, y), t) in enumerate(zip(cells, p)))


NEW["notes"] = {"needs": "points", "build": _notes, "style": f"""
  .nt {{ position: absolute; width: 400px; height: 340px; padding: 50px 34px 30px; display: flex; flex-direction: column; gap: 18px;
        background: color-mix(in srgb, var(--accent3) 28%, var(--surface)); box-shadow: 0 18px 40px rgba(0,0,0,.18); border-radius: 6px; rotate: var(--r); }}
  .nt span {{ {LABEL} font-size: 42px; }}
  .nt-pin {{ position: absolute; left: 175px; top: -18px; width: 50px; height: 50px; border-radius: 50%; background: var(--accent); box-shadow: 0 4px 10px rgba(0,0,0,.3); }}""",
                "script": """
  var N = EZ.$$(".nt"), g = Math.max(0.35, Math.min(0.9, (D - 2) / (N.length || 1)));
  N.forEach(function (o, i) { gsap.set(o, {opacity: 0, y: -80, scale: 0.9}); tl.to(o, {opacity: 1, y: 0, scale: 1, duration: 0.5, ease: "back.out(2)"}, 0.4 + i * g); });
"""}


# checklist -> big numbered tiles with a progress bar
def _tiles(d):
    p = _pts(d, 1, 4)
    n = len(p)
    h = min(220, 780 / max(n, 1))
    y0 = 1030 - n * h / 2
    tiles = "".join(f'<div class="tt" style="top:{y0 + i * h:.0f}px;height:{h - 20:.0f}px"><div class="tt-n">{i + 1:02d}</div><span>{_esc(t)}</span></div>'
                    for i, t in enumerate(p))
    return tiles + f'<div class="tt-bar" style="top:{y0 - 40:.0f}px"><div id="tt-fill"></div></div>'


NEW["tiles"] = {"needs": "points", "build": _tiles, "style": f"""
  .tt {{ position: absolute; left: 90px; width: 900px; display: flex; align-items: center; gap: 34px; padding: 0 40px; {BOX} }}
  .tt-n {{ font-family: var(--font-head); font-size: 76px; color: var(--accent); min-width: 120px; }}
  .tt span {{ {LABEL} font-size: 44px; }}
  .tt-bar {{ position: absolute; left: 90px; width: 900px; height: 14px; border-radius: 7px; background: var(--cardline); overflow: hidden; }}
  #tt-fill {{ width: 100%; height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); transform-origin: 0 50%; }}""", "script": """
  var T = EZ.$$(".tt"), g = Math.max(0.35, Math.min(0.9, (D - 2) / (T.length || 1)));
  gsap.set("#tt-fill", {scaleX: 0}); tl.to("#tt-fill", {scaleX: 1, duration: g * T.length, ease: "none"}, 0.4);
  T.forEach(function (o, i) { gsap.set(o, {opacity: 0, x: 120}); tl.to(o, {opacity: 1, x: 0, duration: 0.5, ease: "power3.out"}, 0.4 + i * g); });
"""}


# compare -> a balance that tips
def _balance(d):
    p = (_pts(d, 2, 2) + ["", ""])[:2]
    return ('<svg class="abs" width="1080" height="1920" style="left:0;top:0"><polygon points="540,1010 470,1420 610,1420" style="fill:var(--accent2)"/>'
            '<rect x="400" y="1410" width="280" height="24" rx="12" style="fill:var(--accent2)"/>'
            '<g id="bl-beam"><rect x="140" y="990" width="800" height="22" rx="11" style="fill:var(--ink)"/>'
            '<line x1="200" y1="1000" x2="200" y2="1120" style="stroke:var(--ink)" stroke-width="5"/><line x1="880" y1="1000" x2="880" y2="1120" style="stroke:var(--ink)" stroke-width="5"/>'
            '<path d="M80 1120 L320 1120 Q200 1200 80 1120 Z" style="fill:var(--accent)"/><path d="M760 1120 L1000 1120 Q880 1200 760 1120 Z" style="fill:var(--accent)"/></g>'
            '<circle cx="540" cy="1000" r="26" style="fill:var(--accent)"/></svg>'
            f'<div class="bl-t" id="bl0" style="left:50px;top:760px">{_esc(p[0])}</div><div class="bl-t" id="bl1" style="left:730px;top:760px">{_esc(p[1])}</div>')


NEW["balance"] = {"needs": "points2", "build": _balance, "style": f"""
  .bl-t {{ position: absolute; width: 300px; min-height: 160px; padding: 22px; display: flex; align-items: center; justify-content: center; text-align: center;
          {BOX} {LABEL} font-size: 40px; }}""", "script": """
  gsap.set(["#bl0", "#bl1"], {opacity: 0, y: -40});
  tl.to("#bl0", {opacity: 1, y: 0, duration: 0.5}, 0.4); tl.to("#bl1", {opacity: 1, y: 0, duration: 0.5}, 0.8);
  tl.fromTo("#bl-beam", {rotation: -7}, {rotation: 7, svgOrigin: "540 1000", duration: 1.0, ease: "sine.inOut", yoyo: true, repeat: Math.max(1, Math.floor((D - 1.2) / 1.0))}, 0.5);
  tl.fromTo("#bl0", {y: 0}, {y: 40, duration: 1.0, ease: "sine.inOut", yoyo: true, repeat: Math.max(1, Math.floor((D - 1.2) / 1.0))}, 0.9);
"""}


# compare -> before / after
def _beforeafter(d):
    p = (_pts(d, 2, 2) + ["", ""])[:2]
    return (f'<div class="ba ba-old"><div class="ba-k">BEFORE</div><span>{_esc(p[0])}</span></div>'
            f'<div id="ba-ar">{_icon("trending", 110, "var(--accent2)")}</div>'
            f'<div class="ba ba-new"><div class="ba-k">AFTER</div><span>{_esc(p[1])}</span></div>')


NEW["beforeafter"] = {"needs": "points2", "build": _beforeafter, "style": f"""
  .ba {{ position: absolute; left: 140px; width: 800px; height: 300px; padding: 36px 44px; display: flex; flex-direction: column; justify-content: center; gap: 16px; {BOX} }}
  .ba-old {{ top: 640px; opacity: .65; filter: grayscale(.6); }}
  .ba-new {{ top: 1130px; border-color: var(--accent); border-width: 4px; }}
  .ba-k {{ font-family: var(--font-body); font-size: 28px; font-weight: 800; letter-spacing: .2em; color: var(--accent); }}
  .ba span {{ {LABEL} font-size: 50px; }}
  #ba-ar {{ position: absolute; left: 485px; top: 965px; width: 110px; height: 110px; rotate: 45deg; }}""", "script": """
  gsap.set(".ba-old", {opacity: 0, x: -100}); tl.to(".ba-old", {opacity: 0.65, x: 0, duration: 0.6}, 0.3);
  gsap.set("#ba-ar", {opacity: 0, y: -30}); tl.to("#ba-ar", {opacity: 1, y: 0, duration: 0.4}, 1.0);
  gsap.set(".ba-new", {opacity: 0, x: 100, scale: 0.95}); tl.to(".ba-new", {opacity: 1, x: 0, scale: 1, duration: 0.6, ease: "back.out(1.6)"}, 1.3);
"""}


# icons -> vertical list with square icon tiles
def _iconlist(d):
    p = _pts(d, 1, 4)
    icons = d.get("icons") or []
    n = len(p)
    h = min(240, 800 / max(n, 1))
    y0 = 1030 - n * h / 2
    from app.services.motion import ICONS
    return "".join(f'<div class="il" style="top:{y0 + i * h:.0f}px"><div class="il-i">{_icon(icons[i] if i < len(icons) and icons[i] in ICONS else ["star", "heart", "zap", "check"][i % 4], 80, "#fff")}</div>'
                   f'<span>{_esc(t)}</span></div>' for i, t in enumerate(p))


NEW["iconlist"] = {"needs": "points", "build": _iconlist, "style": f"""
  .il {{ position: absolute; left: 110px; width: 860px; display: flex; align-items: center; gap: 36px; }}
  .il-i {{ width: 150px; height: 150px; flex: 0 0 150px; border-radius: var(--radius); display: flex; align-items: center; justify-content: center;
          background: linear-gradient(135deg, var(--accent), var(--accent2)); box-shadow: var(--shadow); }}
  .il span {{ {LABEL} font-size: 46px; }}""", "script": """
  var I = EZ.$$(".il"), g = Math.max(0.35, Math.min(0.8, (D - 2) / (I.length || 1)));
  I.forEach(function (o, i) { var ic = o.querySelector(".il-i"); gsap.set(ic, {scale: 0, rotation: -30, transformOrigin: "50% 50%"}); gsap.set(o.querySelector("span"), {opacity: 0, x: 40});
    tl.to(ic, {scale: 1, rotation: 0, duration: 0.5, ease: "back.out(2.4)"}, 0.4 + i * g); tl.to(o.querySelector("span"), {opacity: 1, x: 0, duration: 0.45}, 0.55 + i * g); });
"""}


# icons -> triangle of three connected badges
def _triad(d):
    p = (_pts(d, 1, 3) + ["", "", ""])[:3]
    icons = d.get("icons") or []
    from app.services.motion import ICONS
    pos = [(540, 720), (250, 1240), (830, 1240)]
    lines = "".join(f'<line class="tr-l" x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" style="stroke:var(--cardline)" stroke-width="6" stroke-dasharray="700" stroke-dashoffset="700"/>'
                    for a, b in ((pos[0], pos[1]), (pos[1], pos[2]), (pos[2], pos[0])))
    nodes = "".join(f'<div class="tr-n" style="left:{x - 120}px;top:{y - 120}px">{_icon(icons[i] if i < len(icons) and icons[i] in ICONS else ["star", "heart", "zap"][i], 96)}</div>'
                    f'<div class="tr-t" style="left:{x - 170}px;top:{y + 130}px">{_esc(t)}</div>' for i, ((x, y), t) in enumerate(zip(pos, p)))
    return f'<svg class="abs" width="1080" height="1920" style="left:0;top:0">{lines}</svg>{nodes}'


NEW["triad"] = {"needs": "points", "build": _triad, "style": f"""
  .tr-n {{ position: absolute; width: 240px; height: 240px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
          background: var(--surface); border: 6px solid var(--accent); box-shadow: var(--shadow); }}
  .tr-t {{ position: absolute; width: 340px; text-align: center; {LABEL} font-size: 40px; }}""", "script": """
  tl.to(".tr-l", {strokeDashoffset: 0, duration: 0.8, stagger: 0.2, ease: "power2.inOut"}, 0.3);
  gsap.set(".tr-n", {scale: 0, transformOrigin: "50% 50%"}); tl.to(".tr-n", {scale: 1, duration: 0.5, stagger: 0.25, ease: "back.out(2.2)"}, 0.5);
  gsap.set(".tr-t", {opacity: 0}); tl.to(".tr-t", {opacity: 1, duration: 0.4, stagger: 0.25}, 0.8);
"""}


# network -> hub and spokes
def _hub(d):
    p = _pts(d, 0, 6)
    n = max(len(p), 6)
    cx, cy = 540, 1030
    spokes, nodes = [], []
    for k in range(n):
        a = math.radians(-90 + k * 360 / n)
        x, y = cx + 360 * math.cos(a), cy + 340 * math.sin(a)
        spokes.append(f'<line class="hb-s" x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" style="stroke:var(--accent)" stroke-width="5" stroke-dasharray="400" stroke-dashoffset="400"/>')
        spokes.append(f'<circle class="hb-p" cx="{cx}" cy="{cy}" r="10" style="fill:var(--accent2)" data-x="{x:.0f}" data-y="{y:.0f}"/>')
        label = _esc(p[k]) if k < len(p) else ""
        nodes.append(f'<div class="hb-n" style="left:{x - 70:.0f}px;top:{y - 70:.0f}px"></div>'
                     + (f'<div class="hb-t" style="left:{x - 140:.0f}px;top:{y + (80 if y > cy else -130):.0f}px">{label}</div>' if label else ""))
    return (f'<svg class="abs" width="1080" height="1920" style="left:0;top:0">{"".join(spokes)}</svg>'
            f'<div id="hb-core">{_icon("globe", 110, "#fff")}</div>' + "".join(nodes))


NEW["hub"] = {"build": _hub, "style": f"""
  #hb-core {{ position: absolute; left: 420px; top: 910px; width: 240px; height: 240px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
             background: linear-gradient(135deg, var(--accent), var(--accent2)); box-shadow: var(--shadow); }}
  .hb-n {{ position: absolute; width: 140px; height: 140px; border-radius: 50%; background: var(--surface); border: 6px solid var(--accent2); box-shadow: var(--shadow); }}
  .hb-t {{ position: absolute; width: 280px; text-align: center; {LABEL} font-size: 34px; }}""", "script": """
  gsap.set("#hb-core", {scale: 0, transformOrigin: "50% 50%"}); tl.to("#hb-core", {scale: 1, duration: 0.6, ease: "back.out(2)"}, 0.3);
  tl.to(".hb-s", {strokeDashoffset: 0, duration: 0.5, stagger: 0.08}, 0.7);
  gsap.set(".hb-n", {scale: 0, transformOrigin: "50% 50%"}); tl.to(".hb-n", {scale: 1, duration: 0.4, stagger: 0.08, ease: "back.out(2.5)"}, 0.9);
  gsap.set(".hb-t", {opacity: 0}); tl.to(".hb-t", {opacity: 1, duration: 0.4, stagger: 0.1}, 1.2);
  EZ.$$(".hb-p").forEach(function (c, i) { gsap.set(c, {opacity: 0}); var t = 1.4 + i * 0.2;
    while (t < D - 0.8) { tl.set(c, {opacity: 1, attr: {cx: 540, cy: 1030}}, t); tl.to(c, {attr: {cx: +c.dataset.x, cy: +c.dataset.y}, duration: 0.7, ease: "power1.inOut"}, t); tl.set(c, {opacity: 0}, t + 0.7); t += 1.6; } });
"""}


# network -> a chain of linked steps along a line
def _chain(d):
    p = _pts(d, 0, 5)
    n = max(len(p), 4)
    xs = [140 + k * (800 / (n - 1)) for k in range(n)]
    ys = [1030 + (90 if k % 2 else -90) for k in range(n)]
    links = "".join(f'<line class="ch-l" x1="{xs[k]:.0f}" y1="{ys[k]}" x2="{xs[k + 1]:.0f}" y2="{ys[k + 1]}" style="stroke:var(--accent)" stroke-width="10" '
                    f'stroke-linecap="round" stroke-dasharray="400" stroke-dashoffset="400"/>' for k in range(n - 1))
    pk = '<rect id="ch-pk" x="-18" y="-12" width="36" height="24" rx="6" style="fill:var(--accent2)"/>'
    nodes = "".join(f'<div class="ch-n" style="left:{xs[k] - 60:.0f}px;top:{ys[k] - 60}px"></div>'
                    + (f'<div class="ch-t" style="left:{xs[k] - 120:.0f}px;top:{ys[k] + (80 if k % 2 else -150)}px">{_esc(p[k])}</div>' if k < len(p) else "")
                    for k in range(n))
    return f'<svg class="abs" width="1080" height="1920" style="left:0;top:0">{links}{pk}</svg>{nodes}<script>window.CHAIN={[[round(x), y] for x, y in zip(xs, ys)]};</script>'


NEW["chain"] = {"build": _chain, "style": f"""
  .ch-n {{ position: absolute; width: 120px; height: 120px; border-radius: min(var(--radius), 30px); background: var(--surface); border: 8px solid var(--accent); box-shadow: var(--shadow); }}
  .ch-t {{ position: absolute; width: 240px; text-align: center; {LABEL} font-size: 34px; }}""", "script": """
  gsap.set(".ch-n", {scale: 0, transformOrigin: "50% 50%"}); tl.to(".ch-n", {scale: 1, duration: 0.4, stagger: 0.18, ease: "back.out(2.5)"}, 0.3);
  tl.to(".ch-l", {strokeDashoffset: 0, duration: 0.4, stagger: 0.18}, 0.5);
  gsap.set(".ch-t", {opacity: 0}); tl.to(".ch-t", {opacity: 1, duration: 0.4, stagger: 0.18}, 0.7);
  var P = window.CHAIN || [], t = 1.4; gsap.set("#ch-pk", {opacity: 0});
  while (t < D - 1 && P.length) { tl.set("#ch-pk", {opacity: 1, x: P[0][0], y: P[0][1]}, t);
    for (var k = 1; k < P.length; k++) tl.to("#ch-pk", {x: P[k][0], y: P[k][1], duration: 0.35, ease: "power1.inOut"}, t + (k - 1) * 0.35);
    t += P.length * 0.35 + 0.3; tl.set("#ch-pk", {opacity: 0}, t - 0.3); }
"""}


# orbit -> ripples (pulses spreading out)
NEW["ripples"] = {"build": lambda d: ('<svg class="abs" width="1080" height="1920" style="left:0;top:0">'
                                      + "".join(f'<circle class="rp" cx="540" cy="1000" r="80" fill="none" style="stroke:var({c})" stroke-width="6"/>'
                                                for c in ("--accent", "--accent2", "--accent3", "--accent"))
                                      + '<circle id="rp-c" cx="540" cy="1000" r="70" style="fill:var(--accent)"/></svg>'),
                  "style": "", "script": """
  gsap.set("#rp-c", {scale: 0, transformOrigin: "50% 50%"}); tl.to("#rp-c", {scale: 1, duration: 0.5, ease: "back.out(2.5)"}, 0.2);
  EZ.$$(".rp").forEach(function (c, i) { var t = 0.4 + i * 0.5;
    while (t < D - 0.5) { tl.fromTo(c, {attr: {r: 80}, opacity: 0.9}, {attr: {r: 460}, opacity: 0, duration: 2.0, ease: "power1.out"}, t); t += 2.0; } });
"""}

# orbit -> geometric (rotating outlined shapes)
NEW["geo"] = {"build": lambda d: ('<svg class="abs" width="1080" height="1920" style="left:0;top:0">'
                                  '<rect id="g1" x="290" y="750" width="500" height="500" rx="30" fill="none" style="stroke:var(--accent)" stroke-width="8"/>'
                                  '<polygon id="g2" points="540,770 760,1150 320,1150" fill="none" style="stroke:var(--accent2)" stroke-width="8" stroke-linejoin="round"/>'
                                  '<circle id="g3" cx="540" cy="1000" r="120" style="fill:color-mix(in srgb, var(--accent3) 40%, transparent)"/>'
                                  '<circle cx="540" cy="1000" r="16" style="fill:var(--ink)"/></svg>'),
              "style": "", "script": """
  gsap.set(["#g1", "#g2", "#g3"], {scale: 0.01, opacity: 0, svgOrigin: "540 1000"});
  tl.to(["#g3", "#g1", "#g2"], {scale: 1, opacity: 1, duration: 0.7, stagger: 0.15, ease: "back.out(1.8)", svgOrigin: "540 1000"}, 0.2);
  tl.to("#g1", {rotation: 45, svgOrigin: "540 1000", duration: D, ease: "none"}, 0);
  tl.to("#g2", {rotation: -60, svgOrigin: "540 1000", duration: D, ease: "none"}, 0);
  tl.to("#g3", {scale: 1.25, svgOrigin: "540 1000", duration: 1.2, yoyo: true, repeat: Math.max(1, Math.floor((D - 1) / 1.2)), ease: "sine.inOut"}, 1.0);
"""}


# quote -> centred between rules
def _quotecenter(d):
    return (f'<div class="qc-rule" id="qc1"></div><div id="qc-text" class="serif">{_esc(d.get("headline", ""))}</div>'
            f'<div class="qc-rule" id="qc2"></div><div id="qc-by">{_esc(d.get("brand", ""))}</div>')


NEW["quotecenter"] = {"own_head": True, "build": _quotecenter, "style": """
  .qc-rule { position: absolute; left: 340px; width: 400px; height: 6px; border-radius: 3px; background: var(--accent); transform-origin: 50% 50%; }
  #qc1 { top: 720px; } #qc2 { top: 1300px; }
  #qc-text { position: absolute; left: 90px; width: 900px; top: 780px; height: 490px; display: flex; align-items: center; justify-content: center;
             text-align: center; font-size: 84px; line-height: 1.25; color: var(--ink); }
  #qc-by { position: absolute; left: 0; width: 1080px; top: 1340px; text-align: center; font-size: 36px; font-weight: 700; letter-spacing: .14em; color: var(--muted); }""",
                      "script": """
  gsap.set(".qc-rule", {scaleX: 0}); tl.to(".qc-rule", {scaleX: 1, duration: 0.6, stagger: 0.1}, 0.2);
  gsap.set("#qc-text", {opacity: 0, scale: 0.94, transformOrigin: "50% 50%"}); tl.to("#qc-text", {opacity: 1, scale: 1, duration: 0.9, ease: "power3.out"}, 0.5);
  gsap.set("#qc-by", {opacity: 0}); tl.to("#qc-by", {opacity: 1, duration: 0.5}, 1.3);
"""}


# quote -> speech bubble
def _bubble(d):
    return (f'<div id="sb"><div id="sb-text" class="serif">{_esc(d.get("headline", ""))}</div></div><div id="sb-tail"></div>'
            f'<div id="sb-av">{_icon("message", 90, "#fff")}</div>')


NEW["bubble"] = {"own_head": True, "build": _bubble, "style": """
  #sb { position: absolute; left: 90px; top: 640px; width: 900px; min-height: 520px; padding: 70px 64px; display: flex; align-items: center;
        background: var(--surface); border: 4px solid var(--accent); border-radius: calc(var(--radius) + 20px); box-shadow: var(--shadow); }
  #sb-text { font-size: 80px; line-height: 1.25; color: var(--ink); }
  #sb-tail { position: absolute; left: 230px; top: 1150px; width: 90px; height: 90px; background: var(--surface); border-right: 4px solid var(--accent);
             border-bottom: 4px solid var(--accent); rotate: 45deg; }
  #sb-av { position: absolute; left: 150px; top: 1270px; width: 160px; height: 160px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
           background: linear-gradient(135deg, var(--accent), var(--accent2)); }""", "script": """
  gsap.set(["#sb", "#sb-tail"], {opacity: 0, scale: 0.85, transformOrigin: "20% 100%"}); tl.to(["#sb", "#sb-tail"], {opacity: 1, scale: 1, duration: 0.6, ease: "back.out(1.8)"}, 0.3);
  EZ.type(tl, "#sb-text", 0.7, Math.min(D * 0.5, 2.4));
  gsap.set("#sb-av", {scale: 0, transformOrigin: "50% 50%"}); tl.to("#sb-av", {scale: 1, duration: 0.4, ease: "back.out(2.5)"}, 0.2);
"""}


# photo -> polaroid (tilted print with tape)
def _polaroid(d):
    label = (d.get("points") or [""])[0]
    return (f'<div id="pl"><div id="pl-img"><img src="photo.jpg"/></div><div id="pl-cap">{_esc(label)}</div><div id="pl-tape"></div></div>')


NEW["polaroid"] = {"needs": "photo", "build": _polaroid, "style": f"""
  #pl {{ position: absolute; left: 130px; top: 600px; width: 820px; height: 900px; padding: 36px 36px 0; background: #fbfaf7; box-shadow: 0 30px 70px rgba(0,0,0,.3); rotate: -3deg; }}
  #pl-img {{ width: 748px; height: 700px; overflow: hidden; background: #ddd; }}
  #pl-img img {{ width: 100%; height: 100%; object-fit: cover; }}
  #pl-cap {{ margin-top: 30px; text-align: center; font-family: "Caveat", var(--font-body); font-size: 64px; color: #222; }}
  #pl-tape {{ position: absolute; left: 300px; top: -30px; width: 220px; height: 64px; background: color-mix(in srgb, var(--accent3) 55%, rgba(255,255,255,.4)); rotate: 4deg; }}""",
                   "script": """
  gsap.set("#pl", {opacity: 0, y: -120, rotation: -12}); tl.to("#pl", {opacity: 1, y: 0, rotation: 0, duration: 0.9, ease: "back.out(1.4)"}, 0.2);
  tl.fromTo("#pl-img img", {scale: 1.12}, {scale: 1, duration: D, ease: "none", transformOrigin: "50% 50%"}, 0);
"""}


# photo -> circle crop with a ring
def _photocircle(d):
    label = (d.get("points") or [""])[0]
    return (f'<svg class="abs" width="1080" height="1920" style="left:0;top:0"><circle id="pc-ring" cx="540" cy="1010" r="420" fill="none" style="stroke:var(--accent)" '
            f'stroke-width="12" stroke-dasharray="2640" stroke-dashoffset="2640" transform="rotate(-90 540 1010)"/></svg>'
            f'<div id="pc"><img src="photo.jpg"/></div>' + (f'<div id="pc-l">{_esc(label)}</div>' if label else ""))


NEW["photocircle"] = {"needs": "photo", "build": _photocircle, "style": f"""
  #pc {{ position: absolute; left: 150px; top: 620px; width: 780px; height: 780px; border-radius: 50%; overflow: hidden; box-shadow: var(--shadow); }}
  #pc img {{ width: 100%; height: 100%; object-fit: cover; }}
  #pc-l {{ position: absolute; left: 0; width: 1080px; top: 1445px; text-align: center; }}
  #pc-l {{ font-family: var(--font-body); font-size: 42px; font-weight: 800; color: var(--ink); }}""", "script": """
  gsap.set("#pc", {scale: 0.6, opacity: 0, transformOrigin: "50% 50%"}); tl.to("#pc", {scale: 1, opacity: 1, duration: 0.8, ease: "back.out(1.6)"}, 0.2);
  tl.fromTo("#pc img", {scale: 1.15}, {scale: 1, duration: D, ease: "none", transformOrigin: "50% 50%"}, 0);
  tl.to("#pc-ring", {strokeDashoffset: 0, duration: 1.2, ease: "power2.inOut"}, 0.5);
  if (EZ.$("#pc-l")) { gsap.set("#pc-l", {opacity: 0, y: 20}); tl.to("#pc-l", {opacity: 1, y: 0, duration: 0.5}, 1.0); }
"""}



# target -> summit (a flag on a mountain top, a path climbing to it)
def _summit(d):
    p = _pts(d, 0, 3)
    chips = "".join(f'<div class="sm-c">{_esc(t)}</div>' for t in p)
    return ('<svg class="abs" width="1080" height="1920" style="left:0;top:0">'
            '<polygon points="90,1420 470,700 640,980 760,860 1000,1420" style="fill:color-mix(in srgb, var(--accent2) 30%, var(--surface));stroke:var(--accent2)" stroke-width="5" stroke-linejoin="round"/>'
            '<polygon points="420,795 470,700 520,795 495,780 470,800 445,780" style="fill:var(--surface)"/>'
            '<path id="sm-path" d="M180 1400 C 300 1300, 260 1200, 360 1120 S 430 900, 470 720" fill="none" style="stroke:var(--accent)" stroke-width="8" '
            'stroke-dasharray="20 16" stroke-linecap="round"/>'
            '<g id="sm-flag"><line x1="470" y1="700" x2="470" y2="560" style="stroke:var(--ink)" stroke-width="8" stroke-linecap="round"/>'
            '<path d="M470 560 L590 595 L470 630 Z" style="fill:var(--accent)"/></g></svg>' + (f'<div id="sm-cs">{chips}</div>' if p else ""))


NEW["summit"] = {"build": _summit, "style": f"""
  #sm-cs {{ position: absolute; left: 600px; top: 640px; width: 420px; display: flex; flex-direction: column; gap: 16px; }}
  .sm-c {{ padding: 14px 24px; border-radius: 999px; border: 3px solid var(--accent); background: var(--surface); {LABEL} font-size: 34px; }}""", "script": """
  var T = Math.min(2.2, D - 1.4);
  tl.fromTo("#sm-path", {strokeDashoffset: 900}, {strokeDashoffset: 0, duration: T, ease: "power1.inOut"}, 0.4);
  gsap.set("#sm-flag", {scaleY: 0.01, svgOrigin: "470 700"}); tl.to("#sm-flag", {scaleY: 1, svgOrigin: "470 700", duration: 0.5, ease: "back.out(2.5)"}, 0.4 + T);
  if (EZ.$("#sm-cs")) { gsap.set(".sm-c", {opacity: 0, x: 40}); tl.to(".sm-c", {opacity: 1, x: 0, duration: 0.4, stagger: 0.2}, 0.8); }
"""}


# cycle -> a loop track with stations and a runner going round
def _looptrack(d):
    p = _pts(d, 3, 5) or ["", "", ""]
    n = len(p)
    cx, cy, rx, ry = 540, 1020, 380, 280
    st = []
    for k, t in enumerate(p):
        a = math.radians(-90 + k * 360 / n)
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        st.append(f'<div class="lt-s" style="left:{x - 130:.0f}px;top:{y - 48:.0f}px">{_esc(t)}</div>')
    return (f'<svg class="abs" width="1080" height="1920" style="left:0;top:0"><ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" '
            f'style="stroke:var(--cardline)" stroke-width="34"/><ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" style="stroke:var(--accent)" '
            f'stroke-width="6" stroke-dasharray="26 22"/><circle id="lt-run" cx="{cx}" cy="{cy - ry}" r="26" style="fill:var(--accent2)"/></svg>' + "".join(st))


NEW["looptrack"] = {"needs": "points3", "build": _looptrack, "style": f"""
  .lt-s {{ position: absolute; width: 260px; min-height: 96px; padding: 14px 20px; display: flex; align-items: center; justify-content: center; text-align: center;
          {BOX} {LABEL} font-size: 36px; }}""", "script": """
  var S = EZ.$$(".lt-s"), g = Math.max(0.3, Math.min(0.7, (D - 2) / (S.length || 1)));
  S.forEach(function (o, i) { gsap.set(o, {opacity: 0, scale: 0.7, transformOrigin: "50% 50%"}); tl.to(o, {opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2)"}, 0.4 + i * g); });
  var run = EZ.$("#lt-run"), o = {a: -Math.PI / 2};
  tl.to(o, {a: -Math.PI / 2 + Math.PI * 2 * Math.max(1, Math.floor(D / 2.6)), duration: D - 0.6, ease: "none",
            onUpdate: function () { run.setAttribute("cx", 540 + 380 * Math.cos(o.a)); run.setAttribute("cy", 1020 + 280 * Math.sin(o.a)); }}, 0.4);
"""}

# diagrams without layout variants: what to use instead if the same one was shown a moment ago
SIMILAR = {
    "steps": ["chevrons", "pathsteps", "bars"], "pyramid": ["funnel", "steps"], "funnel": ["pyramid", "chevrons"],
    "venn": ["compare", "triad"], "matrix": ["notes", "compare"], "hierarchy": ["hub", "mindmap"], "mindmap": ["hub", "triad"],
    "spotlight": ["ripples", "geo"], "counter": ["orbit", "target"], "card": ["notes", "tiles"], "globe": ["hub", "network"],
    "server": ["chain", "network"], "lock": ["target", "checklist"],
}

# ------------------------------------------------------------------ registry
# family -> interchangeable layouts (same data, different picture); motion.assign_arts rotates through them
FAMILIES = {
    "flow": ["flow", "chevrons", "pathsteps"],
    "checklist": ["checklist", "notes", "tiles"],
    "compare": ["compare", "balance", "beforeafter"],
    "icons": ["icons", "iconlist", "triad"],
    "network": ["network", "hub", "chain"],
    "orbit": ["orbit", "ripples", "geo"],
    "quote": ["quote", "quotecenter", "bubble"],
    "photo": ["photo", "polaroid", "photocircle"],
    "timeline": ["timeline", "timeline_zig"],
    "target": ["target", "summit"],
    "cycle": ["cycle", "looptrack"],
}
# shape-meaning diagrams the script writer can choose directly
CHOICES = {
    "timeline": "events in time order (needs points; 'Year: event' shows a date)",
    "cycle": "a loop that repeats, feedback, habits (needs 3-5 points)",
    "pyramid": "levels or priorities, the top matters most (needs 2-5 points, top first)",
    "hierarchy": "a team, roles, delegation, one leads several (needs points: leader first, then 1-3 roles)",
    "matrix": "two factors giving four options, e.g. urgent/important (needs up to 4 points)",
    "funnel": "narrowing many options down to the best (needs 2-4 points, widest first)",
    "venn": "two or three ideas that overlap (needs 2-3 points)",
    "bars": "growth or more of something, rising bars without numbers (needs 2-5 labels)",
    "steps": "a staircase of progress, each step higher (needs 2-5 points)",
    "mindmap": "several ideas around one core idea (needs 3-6 points)",
    "target": "a goal, focus, aiming at one thing (points optional)",
}
_MIN = {"timeline": 2.0, "cycle": 2.2, "pyramid": 2.0, "hierarchy": 3.6, "matrix": 4.0, "funnel": 4.0, "venn": 3.6, "bars": 2.0, "steps": 2.2,
        "mindmap": 2.4, "target": 3.6, "balance": 4.0, "beforeafter": 4.0, "hub": 4.0, "chain": 4.0, "ripples": 3.0, "geo": 3.0,
        "quotecenter": 4.0, "bubble": 4.2, "polaroid": 4.0, "photocircle": 4.0, "chevrons": 2.0, "pathsteps": 2.4, "notes": 2.0, "tiles": 2.0,
        "iconlist": 2.0, "triad": 3.6, "timeline_zig": 2.0, "summit": 3.8, "looptrack": 3.0}
_PER_POINT = {"timeline": 0.8, "timeline_zig": 0.8, "cycle": 0.7, "pyramid": 0.7, "bars": 0.5, "steps": 0.7, "mindmap": 0.55, "chevrons": 0.85,
              "pathsteps": 0.8, "notes": 0.85, "tiles": 0.85, "iconlist": 0.8}


def min_seconds(art: str, n_points: int) -> float:
    return _MIN.get(art, 3.0) + _PER_POINT.get(art, 0) * max(n_points, 1)


def register(arts: Dict, choices: Dict) -> None:
    from app.services import charts
    NEW.update(charts.NEW)
    CHOICES.update(charts.CHOICES)
    _MIN.update(charts.MIN)
    SIMILAR.update(charts.SIMILAR)
    FAMILIES.update(charts.FAMILIES)
    for root, extra in charts.EXTEND.items():
        FAMILIES[root] = list(dict.fromkeys(FAMILIES.get(root, [root]) + extra))
    arts.update(NEW)
    choices.update(CHOICES)

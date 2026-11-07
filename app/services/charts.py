"""Data charts and more explainer diagrams (registered into the motion engine by diagrams.register).

Charts: pie, donut, stackbar (shares), line, area (trend), hbars (ranking), gauge, rings (one score), waffle (n of 100),
kpis (headline numbers), radar (several attributes).
Diagrams: iceberg, layers, puzzle, proscons, gap, decision, hexagons, roadmap.

Numbers: a chart shows numbers only from scene["values"] (which the script writer may fill ONLY with numbers stated in the
request or brand facts). Without values it draws an illustrative shape, prints no numbers and shows an "Illustrative" tag.
"""
import html
import math
import re
from typing import Dict, List, Tuple

_esc = html.escape
LABEL = "font-family: var(--font-body); font-weight: 700; color: var(--ink); line-height: 1.2;"
BOX = "background: var(--card); border: 2px solid var(--cardline); box-shadow: var(--shadow); border-radius: var(--radius);"
COLS = ["var(--accent)", "var(--accent2)", "var(--accent3)", "color-mix(in srgb, var(--accent) 55%, var(--surface))",
        "color-mix(in srgb, var(--accent2) 55%, var(--surface))", "color-mix(in srgb, var(--ink) 35%, var(--surface))"]
TAG_STYLE = """
  .ill { position: absolute; right: 70px; top: 610px; padding: 8px 18px; border-radius: 999px; border: 2px solid var(--cardline);
         font-family: var(--font-body); font-size: 24px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }"""
NEW: Dict[str, Dict] = {}


def _pts(d, hi=6):
    return [str(x).strip() for x in (d.get("points") or []) if str(x).strip()][:hi]


def _vals(d, n: int, default: List[float]) -> Tuple[List[float], bool]:
    """Real values (from the brief) or an illustrative default. Returns (values, illustrative)."""
    raw = d.get("values") or []
    vals = []
    for x in raw[:n]:
        try:
            vals.append(float(str(x).replace(",", "").replace("%", "")))
        except ValueError:
            pass
    if len(vals) == n and any(v > 0 for v in vals):
        return vals, False
    if n == 1:  # e.g. headline "74% of the World": use the number the scene itself states, never a made-up default
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(d.get("headline", "")))
        if m:
            return [float(m.group(1))], False
    return (default * ((n // len(default)) + 1))[:n], True


def _fmt(v: float, unit: str) -> str:
    s = f"{v:,.0f}" if abs(v - round(v)) < 1e-9 else f"{v:,.1f}"
    return (unit + s) if unit in ("₹", "$", "€", "£") else (s + unit)


def _tag(ill: bool) -> str:
    return '<div class="ill">Illustrative</div>' if ill else ""


def _legend(labels: List[str], vals: List[float], ill: bool, unit: str, top: int, pct: bool = False) -> str:
    tot = sum(vals) or 1
    items = []
    for i, t in enumerate(labels):
        num = "" if ill else f' <b>{_esc(_fmt(vals[i] / tot * 100, "%") if pct else _fmt(vals[i], unit))}</b>'
        items.append(f'<div class="lg-i"><span class="lg-d" style="background:{COLS[i % len(COLS)]}"></span>{_esc(t)}{num}</div>')
    return f'<div class="lg" style="top:{top}px">{"".join(items)}</div>'


LEGEND_STYLE = f"""
  .lg {{ position: absolute; left: 90px; width: 900px; display: flex; flex-wrap: wrap; justify-content: center; gap: 14px 34px; }}
  .lg-i {{ display: flex; align-items: center; gap: 12px; {LABEL} font-size: 34px; }}
  .lg-i b {{ color: var(--accent); }}
  .lg-d {{ width: 26px; height: 26px; border-radius: 50%; flex: 0 0 26px; }}"""


# ------------------------------------------------------------------ pie / donut / stacked bar (parts of a whole)
def _pie(d, donut=False):
    labels = _pts(d) or ["", "", ""]
    n = len(labels)
    vals, ill = _vals(d, n, [40, 25, 20, 15, 10, 8])
    unit = d.get("unit") or ""
    tot = sum(vals) or 1
    cx, cy, r = 540, 940, 300
    out = ['<svg class="abs" width="1080" height="1920" style="left:0;top:0">']
    if donut:
        circ = 2 * math.pi * 230
        acc = 0.0
        for i, v in enumerate(vals):
            seg = circ * v / tot
            out.append(f'<circle class="dn-s" cx="{cx}" cy="{cy}" r="230" fill="none" style="stroke:{COLS[i % len(COLS)]}" stroke-width="120" '
                       f'stroke-dasharray="{seg:.1f} {circ:.1f}" stroke-dashoffset="{-acc:.1f}" transform="rotate(-90 {cx} {cy})" data-len="{seg:.1f}"/>')
            acc += seg
        out.append("</svg>")
        big = labels[max(range(n), key=lambda i: vals[i])]
        share = vals[max(range(n), key=lambda i: vals[i])] / tot * 100
        centre = f'<div id="dn-c"><b>{_esc(_fmt(share, "%")) if not ill else ""}</b><span>{_esc(big)}</span></div>'
        return "".join(out) + centre + _legend(labels, vals, ill, unit, 1330, pct=True) + _tag(ill)
    a0 = -90.0
    for i, v in enumerate(vals):
        a1 = a0 + 360 * v / tot
        large = 1 if a1 - a0 > 180 else 0
        x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
        x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
        mid = math.radians((a0 + a1) / 2)
        out.append(f'<path class="pi-s" d="M{cx} {cy} L{x0:.1f} {y0:.1f} A{r} {r} 0 {large} 1 {x1:.1f} {y1:.1f} Z" style="fill:{COLS[i % len(COLS)]};stroke:var(--bg2)" '
                   f'stroke-width="6" data-dx="{math.cos(mid) * 22:.1f}" data-dy="{math.sin(mid) * 22:.1f}"/>')
        a0 = a1
    out.append("</svg>")
    return "".join(out) + _legend(labels, vals, ill, unit, 1330, pct=True) + _tag(ill)


NEW["pie"] = {"needs": "points2", "build": lambda d: _pie(d), "style": LEGEND_STYLE + TAG_STYLE, "script": """
  var S = EZ.$$(".pi-s"), g = Math.max(0.2, Math.min(0.5, (D - 2) / (S.length || 1)));
  S.forEach(function (o, i) { gsap.set(o, {scale: 0, opacity: 0, svgOrigin: "540 940"});
    tl.to(o, {scale: 1, opacity: 1, duration: 0.5, ease: "back.out(1.6)", svgOrigin: "540 940"}, 0.4 + i * g);
    if (i === 0) tl.to(o, {x: +o.dataset.dx, y: +o.dataset.dy, duration: 0.4, ease: "power2.out"}, 0.6 + S.length * g); });
  gsap.set(".lg-i", {opacity: 0, y: 16}); tl.to(".lg-i", {opacity: 1, y: 0, duration: 0.35, stagger: g}, 0.6);
"""}
NEW["donut"] = {"needs": "points2", "build": lambda d: _pie(d, True), "style": LEGEND_STYLE + TAG_STYLE + f"""
  #dn-c {{ position: absolute; left: 390px; top: 790px; width: 300px; height: 300px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }}
  #dn-c b {{ font-family: var(--font-head); font-size: 92px; color: var(--ink); line-height: 1; }}
  #dn-c span {{ {LABEL} font-size: 32px; margin-top: 8px; }}""", "script": """
  var S = EZ.$$(".dn-s"), g = Math.max(0.25, Math.min(0.55, (D - 2) / (S.length || 1)));
  S.forEach(function (o, i) { var L = +o.dataset.len, off = +o.getAttribute("stroke-dashoffset");
    gsap.set(o, {attr: {"stroke-dasharray": "0 2000"}}); tl.to(o, {attr: {"stroke-dasharray": L + " 2000"}, duration: 0.55, ease: "power2.out"}, 0.4 + i * g); });
  gsap.set("#dn-c", {opacity: 0, scale: 0.7, transformOrigin: "50% 50%"}); tl.to("#dn-c", {opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2)"}, 0.5 + S.length * g);
  gsap.set(".lg-i", {opacity: 0, y: 16}); tl.to(".lg-i", {opacity: 1, y: 0, duration: 0.35, stagger: g}, 0.6);
"""}


def _stackbar(d):
    labels = _pts(d) or ["", "", ""]
    n = len(labels)
    vals, ill = _vals(d, n, [45, 30, 25, 15, 10])
    tot = sum(vals) or 1
    x = 90.0
    segs = []
    for i, v in enumerate(vals):
        w = 900 * v / tot
        num = "" if ill else _esc(_fmt(v / tot * 100, "%"))
        segs.append(f'<div class="sb-s" style="left:{x:.0f}px;width:{w:.0f}px;background:{COLS[i % len(COLS)]}"><span>{num}</span></div>')
        x += w
    return "".join(segs) + '<div class="sb-frame"></div>' + _legend(labels, vals, ill, d.get("unit") or "", 1180, pct=True) + _tag(ill)


NEW["stackbar"] = {"needs": "points2", "build": _stackbar, "style": LEGEND_STYLE + TAG_STYLE + """
  .sb-s { position: absolute; top: 880px; height: 200px; display: flex; align-items: center; justify-content: center; transform-origin: 0 50%; }
  .sb-s span { font-family: var(--font-head); font-size: 50px; color: #fff; text-shadow: 0 2px 8px rgba(0,0,0,.35); }
  .sb-frame { position: absolute; left: 86px; top: 876px; width: 908px; height: 208px; border-radius: min(var(--radius), 26px); border: 4px solid var(--cardline); }""", "script": """
  var S = EZ.$$(".sb-s"), g = Math.max(0.2, Math.min(0.5, (D - 2) / (S.length || 1)));
  S.forEach(function (o, i) { gsap.set(o, {scaleX: 0}); tl.to(o, {scaleX: 1, duration: 0.5, ease: "power3.out"}, 0.4 + i * g); });
  gsap.set(".lg-i", {opacity: 0, y: 16}); tl.to(".lg-i", {opacity: 1, y: 0, duration: 0.35, stagger: g}, 0.6);
"""}


# ------------------------------------------------------------------ line / area (a trend over time)
def _line(d, smooth=False):
    labels = _pts(d, 7) or ["", "", "", ""]
    n = len(labels)
    vals, ill = _vals(d, n, [20, 32, 28, 45, 52, 61, 70])
    unit = d.get("unit") or ""
    lo, hi = min(vals + [0]), max(vals) or 1
    x0, x1, y0, y1 = 150, 960, 1340, 700
    xs = [x0 + (x1 - x0) * i / max(n - 1, 1) for i in range(n)]
    ys = [y0 - (y0 - y1) * (v - lo) / ((hi - lo) or 1) for v in vals]
    if smooth:
        dpath = f"M{xs[0]:.0f} {ys[0]:.0f} " + " ".join(f"C{xs[i - 1] + (xs[i] - xs[i - 1]) / 2:.0f} {ys[i - 1]:.0f}, {xs[i - 1] + (xs[i] - xs[i - 1]) / 2:.0f} {ys[i]:.0f}, {xs[i]:.0f} {ys[i]:.0f}"
                                                      for i in range(1, n))
    else:
        dpath = "M" + " L".join(f"{x:.0f} {y:.0f}" for x, y in zip(xs, ys))
    area = dpath + f" L{xs[-1]:.0f} {y0} L{xs[0]:.0f} {y0} Z"
    grid = "".join(f'<line x1="{x0}" y1="{y0 - k * (y0 - y1) / 4:.0f}" x2="{x1}" y2="{y0 - k * (y0 - y1) / 4:.0f}" style="stroke:var(--gridline)" stroke-width="3"/>' for k in range(5))
    dots = "".join(f'<circle class="ln-d" cx="{x:.0f}" cy="{y:.0f}" r="16" style="fill:var(--surface);stroke:var(--accent)" stroke-width="7"/>' for x, y in zip(xs, ys))
    nums = "" if ill else "".join(f'<div class="ln-v" style="left:{x - 80:.0f}px;top:{y - 76:.0f}px">{_esc(_fmt(v, unit))}</div>' for x, y, v in zip(xs, ys, vals))
    xl = "".join(f'<div class="ln-x" style="left:{x - 90:.0f}px">{_esc(t)}</div>' for x, t in zip(xs, labels))
    return (f'<svg class="abs" width="1080" height="1920" style="left:0;top:0"><defs><linearGradient id="lnG" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" style="stop-color:var(--accent);stop-opacity:.45"/><stop offset="1" style="stop-color:var(--accent);stop-opacity:0"/></linearGradient></defs>'
            f'{grid}<path id="ln-area" d="{area}" style="fill:url(#lnG)"/><path id="ln-path" d="{dpath}" fill="none" style="stroke:var(--accent)" stroke-width="10" '
            f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="3000" stroke-dashoffset="3000"/>{dots}</svg>{nums}{xl}' + _tag(ill))


_LINE_STYLE = TAG_STYLE + f"""
  .ln-x {{ position: absolute; top: 1370px; width: 180px; text-align: center; {LABEL} font-size: 30px; }}
  .ln-v {{ position: absolute; width: 160px; text-align: center; font-family: var(--font-head); font-size: 38px; color: var(--accent); }}"""
_LINE_SCRIPT = """
  var T = Math.min(2.4, D - 1.4);
  tl.to("#ln-path", {strokeDashoffset: 0, duration: T, ease: "power1.inOut"}, 0.4);
  gsap.set("#ln-area", {opacity: 0}); tl.to("#ln-area", {opacity: 1, duration: 0.8}, 0.4 + T * 0.6);
  var P = EZ.$$(".ln-d"), V = EZ.$$(".ln-v");
  P.forEach(function (o, i) { gsap.set(o, {scale: 0, transformOrigin: "50% 50%"}); tl.to(o, {scale: 1, duration: 0.3, ease: "back.out(3)"}, 0.4 + T * i / Math.max(P.length - 1, 1)); });
  V.forEach(function (o, i) { gsap.set(o, {opacity: 0, y: 10}); tl.to(o, {opacity: 1, y: 0, duration: 0.3}, 0.5 + T * i / Math.max(V.length - 1, 1)); });
  gsap.set(".ln-x", {opacity: 0}); tl.to(".ln-x", {opacity: 1, duration: 0.4, stagger: 0.08}, 0.3);
"""
NEW["line"] = {"needs": "points3", "build": lambda d: _line(d), "style": _LINE_STYLE, "script": _LINE_SCRIPT}
NEW["area"] = {"needs": "points3", "build": lambda d: _line(d, True), "style": _LINE_STYLE, "script": _LINE_SCRIPT}


# ------------------------------------------------------------------ horizontal bars (a ranking)
def _hbars(d):
    labels = _pts(d) or ["", "", ""]
    n = len(labels)
    vals, ill = _vals(d, n, [90, 72, 58, 41, 30, 22])
    unit = d.get("unit") or ""
    order = sorted(range(n), key=lambda i: -vals[i])
    hi = max(vals) or 1
    h = min(190, 800 / n)
    y0 = 1030 - n * h / 2
    out = []
    for k, i in enumerate(order):
        w = max(30, 700 * vals[i] / hi)
        num = "" if ill else f'<b style="left:{w + 20:.0f}px">{_esc(_fmt(vals[i], unit))}</b>'
        out.append(f'<div class="hb-row" style="top:{y0 + k * h:.0f}px;height:{h - 20:.0f}px"><div class="hb-l">{_esc(labels[i])}</div>'
                   f'<div class="hb-bar" style="width:{w:.0f}px;background:{COLS[k % 3]}"></div>{num}</div>')
    return "".join(out) + _tag(ill)


NEW["hbars"] = {"needs": "points2", "build": _hbars, "style": TAG_STYLE + f"""
  .hb-row {{ position: absolute; left: 90px; width: 900px; }}
  .hb-l {{ position: absolute; left: 0; top: 0; {LABEL} font-size: 38px; white-space: nowrap; }}
  .hb-bar {{ position: absolute; left: 0; top: 54px; bottom: 0; border-radius: 0 min(var(--radius), 30px) min(var(--radius), 30px) 0; transform-origin: 0 50%; }}
  .hb-row b {{ position: absolute; top: 54px; bottom: 0; display: flex; align-items: center; font-family: var(--font-head); font-size: 48px; color: var(--ink); }}""", "script": """
  var R = EZ.$$(".hb-row"), g = Math.max(0.2, Math.min(0.5, (D - 2) / (R.length || 1)));
  R.forEach(function (o, i) { var b = o.querySelector(".hb-bar"); gsap.set(b, {scaleX: 0}); tl.to(b, {scaleX: 1, duration: 0.6, ease: "power3.out"}, 0.4 + i * g);
    var l = o.querySelector(".hb-l"); gsap.set(l, {opacity: 0}); tl.to(l, {opacity: 1, duration: 0.3}, 0.6 + i * g);
    var v = o.querySelector("b"); if (v) { gsap.set(v, {opacity: 0, x: -20}); tl.to(v, {opacity: 1, x: 0, duration: 0.3}, 0.8 + i * g); } });
"""}


# ------------------------------------------------------------------ gauge / rings (one score against a goal)
def _gauge(d):
    label = (_pts(d, 1) or [""])[0]
    vals, ill = _vals(d, 1, [72])
    v = max(0.0, min(100.0, vals[0]))
    unit = d.get("unit") or ("%" if not ill else "")
    zones = "".join(f'<path d="M{540 + 380 * math.cos(math.radians(180 + a0)):.0f} {1180 + 380 * math.sin(math.radians(180 + a0)):.0f} '
                    f'A380 380 0 0 1 {540 + 380 * math.cos(math.radians(180 + a1)):.0f} {1180 + 380 * math.sin(math.radians(180 + a1)):.0f}" fill="none" '
                    f'style="stroke:{c}" stroke-width="70"/>' for a0, a1, c in ((0, 58, COLS[5]), (61, 118, COLS[2]), (121, 180, COLS[0])))
    ang = -90 + 180 * v / 100
    return (f'<svg class="abs" width="1080" height="1920" style="left:0;top:0">{zones}'
            f'<g id="gg-n" data-ang="{ang:.1f}"><line x1="540" y1="1180" x2="540" y2="860" style="stroke:var(--ink)" stroke-width="14" stroke-linecap="round"/></g>'
            f'<circle cx="540" cy="1180" r="34" style="fill:var(--ink)"/></svg>'
            f'<div id="gg-v">{"" if ill else _esc(_fmt(v, unit))}</div><div id="gg-l">{_esc(label)}</div>' + _tag(ill))


NEW["gauge"] = {"build": _gauge, "style": TAG_STYLE + f"""
  #gg-v {{ position: absolute; left: 0; width: 1080px; top: 1240px; text-align: center; font-family: var(--font-head); font-size: 120px; color: var(--ink); }}
  #gg-l {{ position: absolute; left: 0; width: 1080px; top: 1390px; text-align: center; {LABEL} font-size: 40px; }}""", "script": """
  var n = EZ.$("#gg-n"), a = +n.dataset.ang;
  gsap.set(n, {rotation: -90, svgOrigin: "540 1180"}); tl.to(n, {rotation: a, svgOrigin: "540 1180", duration: 1.6, ease: "elastic.out(1, 0.55)"}, 0.5);
  gsap.set(["#gg-v", "#gg-l"], {opacity: 0, y: 20}); tl.to(["#gg-v", "#gg-l"], {opacity: 1, y: 0, duration: 0.5, stagger: 0.2}, 1.2);
"""}


def _rings(d):
    labels = _pts(d, 3) or [""]
    n = len(labels)
    vals, ill = _vals(d, n, [80, 60, 40])
    xs = {1: [540], 2: [320, 760], 3: [200, 540, 880]}[n]
    r = {1: 260, 2: 190, 3: 140}[n]
    circ = 2 * math.pi * r
    out = ['<svg class="abs" width="1080" height="1920" style="left:0;top:0">']
    for i, (x, v) in enumerate(zip(xs, vals)):
        frac = max(0.0, min(100.0, v)) / 100
        out.append(f'<circle cx="{x}" cy="1000" r="{r}" fill="none" style="stroke:var(--cardline)" stroke-width="34"/>'
                   f'<circle class="rg-a" cx="{x}" cy="1000" r="{r}" fill="none" style="stroke:{COLS[i]}" stroke-width="34" stroke-linecap="round" '
                   f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{circ:.1f}" data-to="{circ * (1 - frac):.1f}" transform="rotate(-90 {x} 1000)"/>')
    out.append("</svg>")
    for x, t, v in zip(xs, labels, vals):
        out.append(f'<div class="rg-v" style="left:{x - 150}px">{"" if ill else _esc(_fmt(v, "%"))}</div><div class="rg-l" style="left:{x - 170}px;top:{1000 + r + 50}px">{_esc(t)}</div>')
    return "".join(out) + _tag(ill)


NEW["rings"] = {"needs": "points", "build": _rings, "style": TAG_STYLE + f"""
  .rg-v {{ position: absolute; top: 950px; width: 300px; text-align: center; font-family: var(--font-head); font-size: 76px; color: var(--ink); line-height: 1; }}
  .rg-l {{ position: absolute; width: 340px; text-align: center; {LABEL} font-size: 36px; }}""", "script": """
  EZ.$$(".rg-a").forEach(function (o, i) { tl.to(o, {strokeDashoffset: +o.dataset.to, duration: 1.2, ease: "power2.out"}, 0.4 + i * 0.25); });
  gsap.set([".rg-v", ".rg-l"], {opacity: 0}); tl.to(".rg-v", {opacity: 1, duration: 0.5, stagger: 0.25}, 0.9); tl.to(".rg-l", {opacity: 1, duration: 0.5, stagger: 0.25}, 0.6);
"""}


# ------------------------------------------------------------------ waffle (how many out of 100)
def _waffle(d):
    label = (_pts(d, 1) or [""])[0]
    vals, ill = _vals(d, 1, [35])
    k = int(round(max(0.0, min(100.0, vals[0]))))
    cells = "".join(f'<div class="wf{" on" if i < k else ""}" style="left:{243 + (i % 10) * 60}px;top:{640 + (i // 10) * 60}px"></div>' for i in range(100))
    return cells + f'<div id="wf-v">{"" if ill else _esc(str(k) + "%")}</div><div id="wf-l">{_esc(label)}</div>' + _tag(ill)


NEW["waffle"] = {"build": _waffle, "style": TAG_STYLE + f"""
  .wf {{ position: absolute; width: 52px; height: 52px; border-radius: min(var(--radius), 12px); background: var(--cardline); }}
  .wf.on {{ background: var(--accent); }}
  #wf-v {{ position: absolute; left: 0; width: 1080px; top: 1265px; text-align: center; font-family: var(--font-head); font-size: 90px; color: var(--ink); line-height: 1; }}
  #wf-l {{ position: absolute; left: 0; width: 1080px; top: 1362px; text-align: center; {LABEL} font-size: 36px; }}""", "script": """
  var C = EZ.$$(".wf");
  C.forEach(function (o, i) { gsap.set(o, {scale: 0, transformOrigin: "50% 50%"}); tl.to(o, {scale: 1, duration: 0.25, ease: "back.out(2)"}, 0.3 + i * 0.012); });
  gsap.set(["#wf-v", "#wf-l"], {opacity: 0}); tl.to(["#wf-v", "#wf-l"], {opacity: 1, duration: 0.5, stagger: 0.2}, 1.6);
"""}


# ------------------------------------------------------------------ KPI tiles (headline numbers, needs real values)
def _kpis(d):
    labels = _pts(d, 4) or [""]
    n = len(labels)
    vals, _ = _vals(d, n, [0])
    unit = d.get("unit") or ""
    w = 900 / min(n, 2) - 20
    out = []
    for i, (t, v) in enumerate(zip(labels, vals)):
        col, row = i % 2, i // 2
        out.append(f'<div class="kp" style="left:{90 + col * (w + 40) if n > 1 else 240:.0f}px;top:{700 + row * 360}px;width:{w if n > 1 else 600:.0f}px">'
                   f'<div class="kp-v" data-to="{v}" data-unit="{_esc(unit)}">0</div><div class="kp-l">{_esc(t)}</div><div class="kp-bar"></div></div>')
    return "".join(out)


NEW["kpis"] = {"needs": "values", "build": _kpis, "style": f"""
  .kp {{ position: absolute; height: 320px; padding: 36px 40px; display: flex; flex-direction: column; justify-content: center; gap: 12px; {BOX} }}
  .kp-v {{ font-family: var(--font-head); font-size: 96px; color: var(--accent); line-height: 1; }}
  .kp-l {{ {LABEL} font-size: 38px; }}
  .kp-bar {{ width: 120px; height: 8px; border-radius: 4px; background: var(--accent2); transform-origin: 0 50%; }}""", "script": """
  EZ.$$(".kp").forEach(function (o, i) { var t = 0.4 + i * 0.3, v = o.querySelector(".kp-v"), to = parseFloat(v.dataset.to) || 0, u = v.dataset.unit || "";
    gsap.set(o, {opacity: 0, y: 40}); tl.to(o, {opacity: 1, y: 0, duration: 0.5, ease: "back.out(1.6)"}, t);
    EZ.count(tl, v, 0, to, t + 0.2, 1.4, function (x) { var s = Math.round(x).toLocaleString("en-IN"); return /^[₹$€£]$/.test(u) ? u + s : s + u; });
    gsap.set(o.querySelector(".kp-bar"), {scaleX: 0}); tl.to(o.querySelector(".kp-bar"), {scaleX: 1, duration: 0.6}, t + 0.4); });
"""}


# ------------------------------------------------------------------ radar (several attributes at once)
def _radar(d):
    labels = _pts(d, 6) or ["", "", "", "", ""]
    n = max(len(labels), 3)
    vals, ill = _vals(d, n, [80, 60, 90, 55, 70, 65])
    hi = max(vals) or 1
    cx, cy, R = 540, 1010, 330
    ang = [math.radians(-90 + k * 360 / n) for k in range(n)]
    rings = "".join('<polygon points="' + " ".join(f"{cx + R * f * math.cos(a):.0f},{cy + R * f * math.sin(a):.0f}" for a in ang) +
                    '" fill="none" style="stroke:var(--gridline)" stroke-width="3"/>' for f in (0.25, 0.5, 0.75, 1.0))
    spokes = "".join(f'<line x1="{cx}" y1="{cy}" x2="{cx + R * math.cos(a):.0f}" y2="{cy + R * math.sin(a):.0f}" style="stroke:var(--gridline)" stroke-width="3"/>' for a in ang)
    poly = " ".join(f"{cx + R * v / hi * math.cos(a):.0f},{cy + R * v / hi * math.sin(a):.0f}" for v, a in zip(vals, ang))
    labs = "".join(f'<div class="rd-l" style="left:{cx + (R + 90) * math.cos(a) - 130:.0f}px;top:{cy + (R + 70) * math.sin(a) - 26:.0f}px">{_esc(t)}</div>'
                   for t, a in zip(labels, ang))
    return (f'<svg class="abs" width="1080" height="1920" style="left:0;top:0">{rings}{spokes}<polygon id="rd-p" points="{poly}" '
            f'style="fill:color-mix(in srgb, var(--accent) 35%, transparent);stroke:var(--accent)" stroke-width="6" stroke-linejoin="round"/></svg>{labs}' + _tag(ill))


NEW["radar"] = {"needs": "points3", "build": _radar, "style": TAG_STYLE + f"""
  .rd-l {{ position: absolute; width: 260px; text-align: center; {LABEL} font-size: 32px; }}""", "script": """
  gsap.set("#rd-p", {scale: 0, svgOrigin: "540 1010"}); tl.to("#rd-p", {scale: 1, svgOrigin: "540 1010", duration: 1.0, ease: "elastic.out(1, 0.6)"}, 0.5);
  gsap.set(".rd-l", {opacity: 0}); tl.to(".rd-l", {opacity: 1, duration: 0.4, stagger: 0.1}, 0.3);
"""}


# ================================================================== more explainer diagrams
def _iceberg(d):
    p = _pts(d, 5) or ["", ""]
    top, below = p[0], p[1:]
    rows = "".join(f'<div class="ib-b" style="top:{1010 + i * 105}px">{_esc(t)}</div>' for i, t in enumerate(below[:4]))
    return ('<svg class="abs" width="1080" height="1920" style="left:0;top:0">'
            '<rect x="0" y="900" width="1080" height="620" style="fill:color-mix(in srgb, var(--accent2) 22%, transparent)"/>'
            '<path id="ib-w" d="M0 900 Q 135 870 270 900 T 540 900 T 810 900 T 1080 900" fill="none" style="stroke:var(--accent2)" stroke-width="6"/>'
            '<polygon id="ib-tip" points="540,690 640,900 440,900" style="fill:var(--surface);stroke:var(--ink)" stroke-width="4" stroke-linejoin="round"/>'
            '<polygon id="ib-body" points="440,900 640,900 820,1180 700,1460 380,1460 250,1200" style="fill:color-mix(in srgb, var(--surface) 70%, var(--accent2));stroke:var(--ink)" '
            'stroke-width="4" stroke-linejoin="round" stroke-dasharray="14 10"/></svg>'
            f'<div id="ib-t">{_esc(top)}</div>{rows}')


NEW["iceberg"] = {"needs": "points2", "build": _iceberg, "style": f"""
  #ib-t {{ position: absolute; left: 660px; top: 760px; width: 360px; {LABEL} font-size: 42px; }}
  .ib-b {{ position: absolute; left: 300px; width: 480px; text-align: center; {LABEL} font-size: 36px; }}""", "script": """
  gsap.set("#ib-tip", {opacity: 0, y: 40}); tl.to("#ib-tip", {opacity: 1, y: 0, duration: 0.6, ease: "back.out(1.6)"}, 0.3);
  gsap.set("#ib-t", {opacity: 0, x: 30}); tl.to("#ib-t", {opacity: 1, x: 0, duration: 0.5}, 0.6);
  gsap.set("#ib-body", {opacity: 0}); tl.to("#ib-body", {opacity: 1, duration: 0.9}, 1.0);
  gsap.set(".ib-b", {opacity: 0, y: 20}); tl.to(".ib-b", {opacity: 1, y: 0, duration: 0.4, stagger: 0.3}, 1.3);
  tl.to("#ib-w", {x: -40, duration: 1.5, yoyo: true, repeat: Math.max(1, Math.floor(D / 1.5)), ease: "sine.inOut"}, 0);
"""}


def _layers(d):
    p = _pts(d, 5) or ["", "", ""]
    n = len(p)
    rings = []
    labs = []
    for i in range(n - 1, -1, -1):
        r = 140 + i * (300 / max(n - 1, 1))
        rings.append(f'<circle class="ly-c" cx="540" cy="1020" r="{r:.0f}" style="fill:color-mix(in srgb, {COLS[i % 3]} {55 - i * 8}%, var(--surface));stroke:var(--surface)" stroke-width="6"/>')
    for i, t in enumerate(p):
        r = 140 + i * (300 / max(n - 1, 1))
        y = 1020 - r + (40 if i else 100)
        labs.append(f'<div class="ly-t" style="top:{y - 20:.0f}px">{_esc(t)}</div>')
    return f'<svg class="abs" width="1080" height="1920" style="left:0;top:0">{"".join(rings)}</svg>' + "".join(labs)


NEW["layers"] = {"needs": "points2", "build": _layers, "style": f"""
  .ly-t {{ position: absolute; left: 290px; width: 500px; text-align: center; {LABEL} font-size: 36px; }}""", "script": """
  var C = EZ.$$(".ly-c"); C.forEach(function (o, i) { gsap.set(o, {scale: 0, svgOrigin: "540 1020"}); tl.to(o, {scale: 1, svgOrigin: "540 1020", duration: 0.5, ease: "back.out(1.6)"}, 0.3 + (C.length - 1 - i) * 0.3); });
  var T = EZ.$$(".ly-t"); T.forEach(function (o, i) { gsap.set(o, {opacity: 0}); tl.to(o, {opacity: 1, duration: 0.4}, 0.5 + i * 0.3); });
"""}


def _puzzle(d):
    p = (_pts(d, 4) + ["", "", "", ""])[:4]
    cells = [(150, 640), (550, 640), (150, 1040), (550, 1040)]
    pieces = "".join(f'<div class="pz" style="left:{x}px;top:{y}px;background:{COLS[i]}" data-dx="{(-1 if x < 540 else 1) * 160}" data-dy="{(-1 if y < 900 else 1) * 160}">'
                     f'<span>{_esc(t)}</span><i class="pz-k pz-r"></i><i class="pz-k pz-b"></i></div>' for i, ((x, y), t) in enumerate(zip(cells, p)))
    return pieces


NEW["puzzle"] = {"needs": "points2", "build": _puzzle, "style": """
  .pz { position: absolute; width: 380px; height: 380px; border-radius: 18px; display: flex; align-items: center; justify-content: center; padding: 40px; text-align: center;
        box-shadow: inset 0 0 0 6px rgba(255,255,255,.35); }
  .pz span { font-family: var(--font-body); font-weight: 800; font-size: 42px; color: #fff; text-shadow: 0 2px 8px rgba(0,0,0,.35); line-height: 1.2; }
  .pz-k { position: absolute; width: 80px; height: 80px; border-radius: 50%; background: inherit; }
  .pz-r { right: -40px; top: 150px; } .pz-b { bottom: -40px; left: 150px; }""", "script": """
  EZ.$$(".pz").forEach(function (o, i) { gsap.set(o, {opacity: 0, x: +o.dataset.dx, y: +o.dataset.dy, rotation: (i % 2 ? 12 : -12)});
    tl.to(o, {opacity: 1, x: 0, y: 0, rotation: 0, duration: 0.7, ease: "back.out(1.4)"}, 0.3 + i * 0.35); });
"""}


def _proscons(d):
    p = _pts(d, 8)
    pros, cons = [], []
    for t in p:
        low = t.lower()
        if low.startswith(("+", "pro:", "pro ", "plus:")):
            pros.append(t.split(":", 1)[-1].lstrip("+ ").strip())
        elif low.startswith(("-", "con:", "con ", "minus:")):
            cons.append(t.split(":", 1)[-1].lstrip("- ").strip())
    if not pros and not cons:
        half = (len(p) + 1) // 2
        pros, cons = p[:half], p[half:]
    col = lambda items, ok: "".join(f'<div class="pc-i"><span class="pc-m {"ok" if ok else "no"}">{"✓" if ok else "✕"}</span>{_esc(t)}</div>' for t in items[:4])
    return (f'<div class="pc" id="pc-p"><div class="pc-h">Pros</div>{col(pros, True)}</div>'
            f'<div class="pc" id="pc-c"><div class="pc-h">Cons</div>{col(cons, False)}</div>')


NEW["proscons"] = {"needs": "points2", "build": _proscons, "style": f"""
  .pc {{ position: absolute; top: 700px; width: 430px; min-height: 480px; padding: 40px 34px; display: flex; flex-direction: column; gap: 26px; {BOX} }}
  #pc-p {{ left: 80px; border-top: 10px solid var(--accent2); }} #pc-c {{ left: 570px; border-top: 10px solid var(--accent); }}
  .pc-h {{ font-family: var(--font-head); font-size: 60px; color: var(--ink); }}
  .pc-i {{ display: flex; gap: 16px; align-items: flex-start; {LABEL} font-size: 36px; }}
  .pc-m {{ flex: 0 0 50px; height: 50px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 30px; color: #fff; }}
  .pc-m.ok {{ background: var(--accent2); }} .pc-m.no {{ background: var(--accent); }}""", "script": """
  gsap.set("#pc-p", {opacity: 0, x: -80}); gsap.set("#pc-c", {opacity: 0, x: 80});
  tl.to("#pc-p", {opacity: 1, x: 0, duration: 0.6, ease: "power3.out"}, 0.3); tl.to("#pc-c", {opacity: 1, x: 0, duration: 0.6, ease: "power3.out"}, 0.6);
  gsap.set(".pc-i", {opacity: 0, y: 16}); tl.to(".pc-i", {opacity: 1, y: 0, duration: 0.3, stagger: 0.18}, 1.0);
"""}


def _gap(d):
    p = (_pts(d, 5) + ["", ""])
    now, goal, planks = p[0], p[1], [x for x in p[2:5] if x]
    k = max(len(planks), 3)
    pl = "".join(f'<div class="gp-p" style="left:{330 + i * (420 / k):.0f}px;width:{420 / k - 10:.0f}px">{_esc(planks[i]) if i < len(planks) else ""}</div>' for i in range(k))
    return ('<div class="gp-cl" id="gp-l"></div><div class="gp-cl" id="gp-r"></div>' + pl +
            f'<div class="gp-t" style="left:60px">{_esc(now)}</div><div class="gp-t" style="left:760px">{_esc(goal)}</div>'
            '<div id="gp-flag"></div>')


NEW["gap"] = {"needs": "points2", "build": _gap, "style": f"""
  .gp-cl {{ position: absolute; top: 1040px; width: 270px; height: 420px; background: color-mix(in srgb, var(--accent2) 40%, var(--surface)); border-radius: 18px 18px 0 0; }}
  #gp-l {{ left: 60px; }} #gp-r {{ left: 750px; }}
  .gp-p {{ position: absolute; top: 1040px; height: 70px; border-radius: 8px; background: var(--accent); display: flex; align-items: center; justify-content: center;
          text-align: center; font-family: var(--font-body); font-weight: 800; font-size: 22px; color: #fff; padding: 4px; line-height: 1.1; }}
  .gp-t {{ position: absolute; top: 800px; width: 270px; height: 200px; display: flex; align-items: flex-end; justify-content: center; text-align: center; {LABEL} font-size: 40px; }}
  #gp-flag {{ position: absolute; left: 960px; top: 1020px; width: 0; height: 0; border-left: 60px solid var(--accent); border-top: 30px solid transparent; border-bottom: 30px solid transparent; }}""",
              "script": """
  gsap.set([".gp-cl", ".gp-t"], {opacity: 0}); tl.to(".gp-cl", {opacity: 1, duration: 0.5, stagger: 0.2}, 0.2); tl.to(".gp-t", {opacity: 1, duration: 0.5, stagger: 0.2}, 0.5);
  var P = EZ.$$(".gp-p"), g = Math.max(0.25, Math.min(0.6, (D - 2.2) / (P.length || 1)));
  P.forEach(function (o, i) { gsap.set(o, {opacity: 0, y: -120}); tl.to(o, {opacity: 1, y: 0, duration: 0.45, ease: "bounce.out"}, 0.9 + i * g); });
  gsap.set("#gp-flag", {opacity: 0, scale: 0, transformOrigin: "0 50%"}); tl.to("#gp-flag", {opacity: 1, scale: 1, duration: 0.4, ease: "back.out(3)"}, 0.9 + P.length * g);
"""}


def _decision(d):
    p = (_pts(d, 3) + ["", "", ""])[:3]
    return ('<svg class="abs" width="1080" height="1920" style="left:0;top:0">'
            '<path class="dc-l" d="M540 900 L540 960 L290 960 L290 1060" fill="none" style="stroke:var(--accent2)" stroke-width="7" stroke-dasharray="600" stroke-dashoffset="600"/>'
            '<path class="dc-l" d="M540 900 L540 960 L790 960 L790 1060" fill="none" style="stroke:var(--accent)" stroke-width="7" stroke-dasharray="600" stroke-dashoffset="600"/></svg>'
            f'<div id="dc-q">{_esc(p[0])}</div>'
            f'<div class="dc-tag" style="left:200px">YES</div><div class="dc-tag" style="left:700px">NO</div>'
            f'<div class="dc-a" style="left:110px;border-color:var(--accent2)">{_esc(p[1])}</div><div class="dc-a" style="left:610px;border-color:var(--accent)">{_esc(p[2])}</div>')


NEW["decision"] = {"needs": "points2", "build": _decision, "style": f"""
  #dc-q {{ position: absolute; left: 240px; top: 650px; width: 600px; min-height: 250px; padding: 30px; display: flex; align-items: center; justify-content: center; text-align: center;
          rotate: 0deg; {BOX} border-width: 4px; border-color: var(--ink); {LABEL} font-size: 42px; }}
  .dc-tag {{ position: absolute; top: 990px; width: 180px; text-align: center; font-family: var(--font-body); font-size: 30px; font-weight: 800; letter-spacing: .2em; color: var(--muted); }}
  .dc-a {{ position: absolute; top: 1080px; width: 360px; min-height: 230px; padding: 26px; display: flex; align-items: center; justify-content: center; text-align: center;
          {BOX} border-width: 4px; {LABEL} font-size: 38px; }}""", "script": """
  gsap.set("#dc-q", {opacity: 0, scale: 0.85, transformOrigin: "50% 50%"}); tl.to("#dc-q", {opacity: 1, scale: 1, duration: 0.5, ease: "back.out(2)"}, 0.3);
  tl.to(".dc-l", {strokeDashoffset: 0, duration: 0.6, stagger: 0.3}, 0.9);
  gsap.set([".dc-tag", ".dc-a"], {opacity: 0, y: 20}); tl.to(".dc-tag", {opacity: 1, y: 0, duration: 0.3, stagger: 0.3}, 1.2); tl.to(".dc-a", {opacity: 1, y: 0, duration: 0.45, stagger: 0.3}, 1.4);
"""}


def _hexagons(d):
    p = _pts(d, 7) or ["", "", ""]
    pos = [(540, 1010), (540, 740), (774, 875), (774, 1145), (540, 1280), (306, 1145), (306, 875)]
    hexes = "".join(f'<div class="hx{" hx-c" if i == 0 else ""}" style="left:{x - 140}px;top:{y - 125}px"><span>{_esc(t)}</span></div>' for i, ((x, y), t) in enumerate(zip(pos, p)))
    return hexes


NEW["hexagons"] = {"needs": "points3", "build": _hexagons, "style": f"""
  .hx {{ position: absolute; width: 280px; height: 250px; clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%);
        background: color-mix(in srgb, var(--accent2) 28%, var(--surface)); display: flex; align-items: center; justify-content: center; padding: 30px 46px; text-align: center; }}
  .hx-c {{ background: var(--accent); }} .hx-c span {{ color: #fff; }}
  .hx span {{ {LABEL} font-size: 32px; }}""", "script": """
  EZ.$$(".hx").forEach(function (o, i) { gsap.set(o, {scale: 0, rotation: -30, transformOrigin: "50% 50%"}); tl.to(o, {scale: 1, rotation: 0, duration: 0.45, ease: "back.out(2)"}, 0.3 + i * 0.18); });
"""}


def _roadmap(d):
    p = _pts(d, 5) or ["", "", ""]
    n = len(p)
    road = "M120 1440 C 420 1440, 200 1190, 540 1160 S 860 940, 560 870 S 300 720, 760 690"
    pins = "".join(f'<div class="rm-pin" data-i="{i}"><span>{i + 1}</span></div><div class="rm-t" data-i="{i}">{_esc(t)}</div>' for i, t in enumerate(p))
    return (f'<svg class="abs" width="1080" height="1920" style="left:0;top:0"><path id="rm-road" d="{road}" fill="none" style="stroke:color-mix(in srgb, var(--ink) 75%, var(--surface))" stroke-width="70" stroke-linecap="round"/>'
            f'<path id="rm-dash" d="{road}" fill="none" style="stroke:var(--surface)" stroke-width="6" stroke-dasharray="26 22"/></svg>{pins}')


NEW["roadmap"] = {"needs": "points2", "build": _roadmap, "style": f"""
  .rm-pin {{ position: absolute; width: 80px; height: 80px; border-radius: 50% 50% 50% 0; rotate: -45deg; background: var(--accent); display: flex; align-items: center; justify-content: center;
            font-family: var(--font-head); font-size: 38px; color: #fff; box-shadow: var(--shadow); }}
  .rm-pin span {{ rotate: 45deg; }}
  .rm-t {{ position: absolute; width: 340px; {LABEL} font-size: 36px; }}""", "script": """
  tl.fromTo("#rm-dash", {strokeDashoffset: 600}, {strokeDashoffset: 0, duration: D, ease: "none"}, 0);
  var P = EZ.$$(".rm-pin"), T = EZ.$$(".rm-t"), g = Math.max(0.3, Math.min(0.7, (D - 2) / (P.length || 1)));
  var road = EZ.$("#rm-road"), L = road.getTotalLength();
  P.forEach(function (o, i) { var pt = road.getPointAtLength(L * (i + 0.5) / P.length); o.style.left = (pt.x - 40) + "px"; o.style.top = (pt.y - 110) + "px";
    var t = T[i]; t.style.top = (pt.y - 100) + "px"; t.style.left = (pt.x < 540 ? pt.x + 70 : pt.x - 410) + "px"; t.style.textAlign = pt.x < 540 ? "left" : "right"; });
  P.forEach(function (o, i) { gsap.set(o, {opacity: 0, y: -60}); tl.to(o, {opacity: 1, y: 0, duration: 0.45, ease: "bounce.out"}, 0.4 + i * g); });
  T.forEach(function (o, i) { gsap.set(o, {opacity: 0}); tl.to(o, {opacity: 1, duration: 0.35}, 0.6 + i * g); });
"""}

CHOICES = {
    "pie": "parts of a whole, shares (labels in points; numbers in values only if the request gives them)",
    "donut": "parts of a whole with one share in the centre (labels + optional values)",
    "stackbar": "one bar split into shares (labels + optional values)",
    "line": "a trend over time (3-7 time labels in points; values only from the request)",
    "area": "growth or a smooth trend over time (3-7 time labels)",
    "hbars": "a ranking from most to least (labels + optional values)",
    "gauge": "one score against a goal, 0-100 (one label; value only from the request)",
    "rings": "1-3 percentages as progress rings (labels + optional values)",
    "waffle": "how many out of 100 (one label; value only from the request)",
    "kpis": "2-4 headline numbers (needs values from the request and their labels)",
    "radar": "several qualities compared at once (3-6 labels)",
    "iceberg": "what people see vs the hidden part (first point above water, the rest below)",
    "layers": "layers from a core outwards (core first)",
    "puzzle": "pieces that fit together into a whole (2-4 points)",
    "proscons": "pros and cons (points prefixed 'Pro:' or 'Con:')",
    "gap": "getting from where we are to the goal (now, goal, then 1-3 bridge steps)",
    "decision": "a yes/no decision (question, if yes, if no)",
    "hexagons": "several parts of one system, centre first (3-7 points)",
    "roadmap": "milestones along a road ahead (2-5 points)",
}
FAMILIES = {"pie": ["pie", "donut", "stackbar"], "line": ["line", "area"], "gauge": ["gauge", "rings"]}
EXTEND = {"bars": ["bars", "hbars"], "timeline": ["roadmap"], "compare": ["proscons"]}
SIMILAR = {"waffle": ["pie", "rings"], "kpis": ["counter", "rings"], "radar": ["hexagons", "mindmap"], "iceberg": ["layers", "pyramid"],
           "layers": ["pyramid", "iceberg"], "puzzle": ["triad", "hexagons"], "gap": ["summit", "steps"], "decision": ["hierarchy", "compare"],
           "hexagons": ["mindmap", "triad"], "hbars": ["bars", "pie"]}
MIN = {k: 4.0 for k in NEW}
MIN.update({"waffle": 4.2, "line": 4.0, "area": 4.0, "kpis": 4.2, "roadmap": 3.8, "gap": 4.0})

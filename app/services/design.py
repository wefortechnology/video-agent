"""Topic-driven design system: every video gets its own look (colours, background, fonts, cards, titles, motion).

Gemini proposes a design for the topic (starting from the closest preset); this module validates it so text is
always readable (WCAG contrast), fills gaps from the preset, and turns it into CSS variables for the scene pages.
If Gemini is unavailable, a preset is chosen from keywords in the brief.
"""
import colorsys
import re
from typing import Dict, List, Optional, Tuple

# ------------------------------------------------------------------ building blocks
# fonts: family name -> file in assets/fonts. Latin-only display fonts fall back to a Devanagari font for Hindi.
FONT_FILES = {
    "Inter": "Inter-Variable.ttf", "Fraunces": "Fraunces-Variable.ttf", "Playfair Display": "PlayfairDisplay.ttf",
    "Montserrat": "Montserrat.ttf", "Space Grotesk": "SpaceGrotesk.ttf", "Poppins": "Poppins-Bold.ttf", "Nunito": "Nunito.ttf",
    "Bebas Neue": "BebasNeue.ttf", "DM Serif Display": "DMSerifDisplay.ttf", "Oswald": "Oswald.ttf", "Caveat": "Caveat.ttf",
    "Baloo 2": "Baloo2.ttf", "Mukta": "Mukta-Bold.ttf", "Rozha One": "RozhaOne.ttf",
    "NSD": "NotoSansDevanagari-Bold.ttf", "NSerD": "NotoSerifDevanagari-Bold.ttf",
}
# font pairs: heading font, body font, Hindi heading fallback, heading weight, uppercase?, letter spacing
FONT_PAIRS = {
    "editorial": ("Playfair Display", "Inter", "Rozha One", 800, False, "-0.01em"),
    "classic": ("DM Serif Display", "Inter", "Rozha One", 400, False, "0"),
    "elegant": ("Fraunces", "Inter", "NSerD", 700, False, "-0.01em"),
    "modern": ("Montserrat", "Inter", "Mukta", 800, False, "-0.02em"),
    "tech": ("Space Grotesk", "Inter", "Mukta", 700, False, "-0.02em"),
    "friendly": ("Poppins", "Nunito", "Baloo 2", 700, False, "-0.01em"),
    "playful": ("Baloo 2", "Nunito", "Baloo 2", 800, False, "0"),
    "news": ("Bebas Neue", "Inter", "Mukta", 400, True, "0.02em"),
    "condensed": ("Oswald", "Inter", "Mukta", 700, True, "0.01em"),
}
BACKGROUNDS = {
    "radial": "soft radial glow from the centre",
    "linear": "diagonal two-tone gradient",
    "grid": "faint graph-paper grid",
    "dots": "dot-matrix pattern",
    "paper": "flat paper with a subtle grain",
    "waves": "layered waves along the bottom that drift slowly",
    "blobs": "large soft colour blobs drifting (aurora)",
    "diagonal": "subtle diagonal stripes",
    "topo": "faint contour lines like a map",
    "split": "two-tone slanted split",
}
PARTICLES = ("none", "dots", "bokeh", "sparkles", "bubbles", "confetti")
CARDS = ("shadow", "glass", "outline", "solid")
CORNERS = {"sharp": 10, "soft": 26, "round": 46}
TITLES = ("solid", "gradient", "highlight", "underline")
TRANSITIONS = ("fade", "slide", "zoom", "wipe")

# ------------------------------------------------------------------ presets (a starting point per kind of topic)
PRESETS: Dict[str, Dict] = {
    "corporate-navy": {"for": "business, leadership, CEOs, strategy, management, careers", "dark": True,
                       "bg": "#0f1e3a", "surface": "#172a4d", "ink": "#f4f1ea", "accent": "#d4a84b", "accent2": "#5b8def", "accent3": "#e8e3d6",
                       "background": "linear", "particles": "none", "fonts": "editorial", "card": "glass", "corners": "soft",
                       "title_style": "solid", "transition": "slide"},
    "paper-explainer": {"for": "general explainers, how things work, lessons, education", "dark": False,
                        "bg": "#fbf5ec", "surface": "#ffffff", "ink": "#1c1a17", "accent": "#c4553a", "accent2": "#2f6f68", "accent3": "#d99a1e",
                        "background": "paper", "particles": "dots", "fonts": "elegant", "card": "shadow", "corners": "soft",
                        "title_style": "underline", "transition": "fade"},
    "tech-light": {"for": "internet, apps, software, AI for a general audience, gadgets", "dark": False,
                   "bg": "#f3f7fb", "surface": "#ffffff", "ink": "#0f1b2d", "accent": "#2563eb", "accent2": "#06b6d4", "accent3": "#7c3aed",
                   "background": "dots", "particles": "none", "fonts": "tech", "card": "outline", "corners": "soft",
                   "title_style": "highlight", "transition": "slide"},
    "tech-grid": {"for": "developers, cybersecurity, data, futuristic tech", "dark": True,
                  "bg": "#0a1426", "surface": "#101e38", "ink": "#e8f4ff", "accent": "#38d9e8", "accent2": "#7c8cff", "accent3": "#ffd36b",
                  "background": "grid", "particles": "dots", "fonts": "tech", "card": "glass", "corners": "sharp",
                  "title_style": "gradient", "transition": "wipe"},
    "health-fresh": {"for": "health, fitness, wellness, mental health, medicine, nutrition", "dark": False,
                     "bg": "#f1faf5", "surface": "#ffffff", "ink": "#12352a", "accent": "#16a34a", "accent2": "#0ea5a4", "accent3": "#f59e0b",
                     "background": "blobs", "particles": "bubbles", "fonts": "friendly", "card": "shadow", "corners": "round",
                     "title_style": "solid", "transition": "zoom"},
    "finance-green": {"for": "money, investing, banking, economy, budgeting, fundraising", "dark": True,
                      "bg": "#0c2a22", "surface": "#123a2f", "ink": "#f2f7f2", "accent": "#e3b341", "accent2": "#3ccf91", "accent3": "#a7f3d0",
                      "background": "topo", "particles": "none", "fonts": "modern", "card": "glass", "corners": "soft",
                      "title_style": "gradient", "transition": "slide"},
    "food-warm": {"for": "food, cooking, recipes, restaurants, nutrition at home", "dark": False,
                  "bg": "#fff4e8", "surface": "#ffffff", "ink": "#3a1f12", "accent": "#e8590c", "accent2": "#c2185b", "accent3": "#2f9e44",
                  "background": "waves", "particles": "none", "fonts": "friendly", "card": "shadow", "corners": "round",
                  "title_style": "highlight", "transition": "zoom"},
    "kids-bright": {"for": "children, school, learning for kids, fun science, parenting", "dark": False,
                    "bg": "#fff8e1", "surface": "#ffffff", "ink": "#1e1b4b", "accent": "#f97316", "accent2": "#8b5cf6", "accent3": "#10b981",
                    "background": "dots", "particles": "confetti", "fonts": "playful", "card": "outline", "corners": "round",
                    "title_style": "highlight", "transition": "zoom"},
    "history-sepia": {"for": "history, culture, heritage, biography, old times", "dark": False,
                      "bg": "#f3e7d3", "surface": "#fbf4e6", "ink": "#2b1d10", "accent": "#8b3a1a", "accent2": "#5b6b3a", "accent3": "#b8862f",
                      "background": "paper", "particles": "none", "fonts": "classic", "card": "outline", "corners": "sharp",
                      "title_style": "underline", "transition": "fade"},
    "nature-earth": {"for": "environment, climate, nature, farming, sustainability, travel outdoors", "dark": False,
                     "bg": "#eef5ea", "surface": "#ffffff", "ink": "#1d3320", "accent": "#3f8f3a", "accent2": "#2b7a9b", "accent3": "#d08a2b",
                     "background": "topo", "particles": "none", "fonts": "elegant", "card": "shadow", "corners": "soft",
                     "title_style": "solid", "transition": "fade"},
    "science-space": {"for": "science, space, physics, astronomy, research, the future", "dark": True,
                      "bg": "#0b0820", "surface": "#161236", "ink": "#f0edff", "accent": "#a78bfa", "accent2": "#22d3ee", "accent3": "#f472b6",
                      "background": "blobs", "particles": "sparkles", "fonts": "tech", "card": "glass", "corners": "soft",
                      "title_style": "gradient", "transition": "zoom"},
    "news-bold": {"for": "news, announcements, sports, trends, breaking updates, motivation", "dark": True,
                  "bg": "#111111", "surface": "#1c1c1c", "ink": "#ffffff", "accent": "#ef4444", "accent2": "#facc15", "accent3": "#e5e5e5",
                  "background": "diagonal", "particles": "none", "fonts": "news", "card": "solid", "corners": "sharp",
                  "title_style": "highlight", "transition": "wipe"},
    "social-impact": {"for": "nonprofits, community, social causes, volunteering, CSR, thank-you messages", "dark": False,
                      "bg": "#fdf3f0", "surface": "#ffffff", "ink": "#2a1a1f", "accent": "#d6336c", "accent2": "#f08c00", "accent3": "#1c7ed6",
                      "background": "split", "particles": "none", "fonts": "friendly", "card": "shadow", "corners": "round",
                      "title_style": "underline", "transition": "slide"},
    "festive-night": {"for": "festivals, Diwali, celebrations, greetings", "dark": True,
                      "bg": "#2a1145", "surface": "#3a1a5e", "ink": "#ffffff", "accent": "#ffd36b", "accent2": "#ff4f8b", "accent3": "#4dd0e1",
                      "background": "radial", "particles": "bokeh", "fonts": "elegant", "card": "glass", "corners": "soft",
                      "title_style": "gradient", "transition": "fade"},
}
LEGACY = {"festive": "festive-night", "clean": "paper-explainer", "tech": "tech-grid", "brand": "corporate-navy"}
KEYWORD_PRESETS = [
    ("festive-night", ["diwali", "deepavali", "festival", "holi", "eid", "christmas", "navratri", "दिवाली", "दीपावली", "त्योहार"]),
    ("corporate-navy", ["ceo", "leader", "leadership", "business", "strategy", "manager", "startup", "founder", "career", "office"]),
    ("tech-light", ["internet", "app", "software", " ai ", "artificial intelligence", "website", "computer", "phone", "digital"]),
    ("health-fresh", ["health", "fitness", "yoga", "wellness", "doctor", "diet", "sleep", "mental"]),
    ("finance-green", ["money", "invest", "finance", "bank", "stock market", "budget", "saving", "tax", "economy"]),
    ("food-warm", ["food", "recipe", "cook", "kitchen", "restaurant", "chef"]),
    ("kids-bright", ["kids", "children", "child", "school", "student", "class"]),
    ("history-sepia", ["history", "ancient", "empire", "heritage", "war", "king", "biography"]),
    ("nature-earth", ["climate", "environment", "nature", "forest", "farming", "water", "plastic", "travel"]),
    ("science-space", ["space", "planet", "science", "physics", "universe", "rocket", "nasa"]),
    ("news-bold", ["news", "breaking", "sports", "cricket", "football", "trend", "motivation"]),
    ("social-impact", ["nonprofit", "ngo", "community", "volunteer", "csr", "donate", "hiring", "we are hiring", "thank you"]),
]


# ------------------------------------------------------------------ colour maths
def _hex(c: str, default: str) -> str:
    c = (c or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", c):
        return "#" + c.lstrip("#").lower()
    return default


def _rgb(h: str) -> Tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _to_hex(r, g, b) -> str:
    return "#" + "".join(f"{max(0, min(255, round(x * 255))):02x}" for x in (r, g, b))


def luminance(h: str) -> float:
    def ch(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = _rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _shift_l(h: str, dl: float) -> str:
    r, g, b = _rgb(h)
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    return _to_hex(*colorsys.hls_to_rgb(hh, max(0.0, min(1.0, ll + dl)), ss))


def _shift_h(h: str, dh: float) -> str:
    r, g, b = _rgb(h)
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    return _to_hex(*colorsys.hls_to_rgb((hh + dh) % 1.0, ll, ss))


def _towards_contrast(fg: str, bg: str, target: float) -> str:
    """Lighten or darken fg until it reaches the target contrast against bg."""
    dark_bg = luminance(bg) < 0.25
    c = fg
    for _ in range(40):
        if contrast(c, bg) >= target:
            return c
        c = _shift_l(c, 0.03 if dark_bg else -0.03)
    return "#ffffff" if dark_bg else "#111111"


def _rgba(h: str, a: float) -> str:
    r, g, b = _rgb(h)
    return f"rgba({round(r * 255)},{round(g * 255)},{round(b * 255)},{a})"


# ------------------------------------------------------------------ validation
def preset_for_text(text: str) -> str:
    low = f" {text.lower()} "
    for name, words in KEYWORD_PRESETS:
        if any(w in low for w in words):
            return name
    return "paper-explainer"


def normalise(design: Optional[Dict], fallback_text: str = "", brand: Optional[Dict] = None) -> Dict:
    """Return a complete, readable design. Unknown values fall back to the chosen preset."""
    d = dict(design or {})
    name = d.get("preset") or LEGACY.get(str(d.get("theme", "")).lower()) or preset_for_text(fallback_text)
    base = dict(PRESETS.get(name) or PRESETS[preset_for_text(fallback_text)])
    out = {"preset": name if name in PRESETS else preset_for_text(fallback_text)}
    for k in ("background", "particles", "fonts", "card", "corners", "title_style", "transition"):
        allowed = {"background": BACKGROUNDS, "particles": PARTICLES, "fonts": FONT_PAIRS, "card": CARDS, "corners": CORNERS,
                   "title_style": TITLES, "transition": TRANSITIONS}[k]
        v = str(d.get(k, "")).strip().lower()
        out[k] = v if v in allowed else base[k]
    for k in ("bg", "surface", "ink", "accent", "accent2", "accent3"):
        out[k] = _hex(d.get(k, ""), base[k])
    if d.get("use_brand_colours") and brand:
        out["accent"] = _hex(brand.get("accent_color", ""), out["accent"])
        out["accent2"] = _hex(brand.get("primary_color", ""), out["accent2"])
    dark = luminance(out["bg"]) < 0.2
    out["dark"] = dark
    # readability: ink on bg and on cards, accents visible on bg
    out["ink"] = _towards_contrast(out["ink"], out["bg"], 7.0)
    if out["card"] == "solid":
        out["surface"] = _shift_l(out["bg"], 0.07 if dark else -0.05)
    if contrast(out["ink"], out["surface"]) < 4.5:
        out["surface"] = _shift_l(out["bg"], 0.06 if dark else 0.04)
        out["ink"] = _towards_contrast(out["ink"], out["surface"], 4.5)
    for k in ("accent", "accent2", "accent3"):
        out[k] = _towards_contrast(out[k], out["bg"], 3.0)
    out["mood"] = str(d.get("mood", base.get("for", "")))[:80]
    out["layout"] = d.get("layout") if d.get("layout") in ("alternate", "right", "left") else "alternate"
    return out


# ------------------------------------------------------------------ CSS for one scene
def css_vars(dz: Dict, variant: int = 0, language: str = "en") -> Tuple[str, str, List[str]]:
    """CSS variables + particle mode + the font files the page needs. `variant` gently changes the background per scene."""
    bg = dz["bg"]
    dark = dz["dark"]
    # per-scene variation inside the same design: small hue/lightness steps, never a different theme
    steps = [(0, 0), (0.02, 0.012), (-0.02, -0.01), (0.035, 0.0), (0, -0.018)]
    dh, dl = steps[variant % len(steps)]
    bgv = _shift_l(_shift_h(bg, dh), dl)
    head_f, body_f, hi_head, weight, upper, track = FONT_PAIRS[dz["fonts"]]
    head_stack = f'"{head_f}", "{hi_head}", "NSD", sans-serif'
    body_stack = f'"{body_f}", "Mukta", "NSD", sans-serif'
    ink = dz["ink"]
    card = {
        "shadow": (dz["surface"], _rgba(ink, 0.08), "0 2px 6px rgba(0,0,0,.06), 0 22px 50px rgba(0,0,0,.12)"),
        "glass": (_rgba("#ffffff" if dark else "#ffffff", 0.08 if dark else 0.55), _rgba(dz["accent"], 0.45), "0 24px 60px rgba(0,0,0,.25)"),
        "outline": ("transparent", dz["accent"], "none"),
        "solid": (dz["surface"], dz["surface"], "0 12px 30px rgba(0,0,0,.18)"),
    }[dz["card"]]
    title = dz["title_style"]
    head_a, head_b, head_c = (ink, ink, ink) if title != "gradient" else (_shift_l(ink, 0.0), dz["accent"], dz["accent2"])
    v = {
        "bg1": _shift_l(bgv, 0.05 if dark else 0.02), "bg2": bgv, "bg3": _shift_l(bgv, -0.05 if dark else -0.04), "surface": dz["surface"],
        "ink": ink, "ink2": _rgba(ink, 0.75), "muted": _rgba(ink, 0.6),
        "accent": dz["accent"], "accent2": dz["accent2"], "accent3": dz["accent3"], "ok": dz["accent2"],
        "card": card[0], "cardline": card[1], "shadow": card[2],
        "headA": head_a, "headB": head_b, "headC": head_c,
        "glow": f"0 6px 22px {_rgba(dz['accent'], 0.35)}" if (dark and title == "gradient") else "0 0 0 rgba(0,0,0,0)",
        "capbg": _rgba("#000000", 0.72) if dark else _rgba(ink, 0.9), "capfg": "#ffffff" if dark else dz["bg"],
        "capline": _rgba(dz["accent"], 0.5) if dark else "rgba(0,0,0,0)",
        "p1": _rgba(dz["accent"], 0.85 if dz["particles"] == "bokeh" else 0.35), "p2": _rgba(dz["accent"], 0.25),
        "gridop": "1", "gridline": _rgba(ink, 0.06 if dark else 0.05),
        "radius": f"{CORNERS[dz['corners']]}px", "font-head": head_stack, "font-body": body_stack,
        "head-weight": str(weight), "head-case": "uppercase" if upper else "none", "head-track": track,
        "hl": _rgba(dz["accent"], 0.28 if dark else 0.22),
    }
    css = " ".join(f"--{k}: {val};" for k, val in v.items())
    fonts = sorted({FONT_FILES[f] for f in (head_f, body_f, hi_head, "NSD", "Mukta", "Inter") if f in FONT_FILES})
    return css, dz["particles"], fonts


def font_faces(files: List[str]) -> str:
    rev = {v: k for k, v in FONT_FILES.items()}
    out = []
    for f in files:
        fam = rev.get(f)
        if fam:
            out.append(f'@font-face {{ font-family: "{fam}"; src: url("fonts/{f}"); font-weight: 100 900; }}')
    return "\n  ".join(out)


def describe_for_prompt() -> str:
    """Compact menu for the script writer."""
    pres = "; ".join(f'"{k}" ({v["for"]})' for k, v in PRESETS.items())
    return (f"presets: {pres}. backgrounds: {', '.join(BACKGROUNDS)}. particles: {', '.join(PARTICLES)}. "
            f"fonts: {', '.join(f'{k} ({v[0]})' for k, v in FONT_PAIRS.items())}. cards: {', '.join(CARDS)}. "
            f"corners: {', '.join(CORNERS)}. title_style: {', '.join(TITLES)}. transition: {', '.join(TRANSITIONS)}.")


# ------------------------------------------------------------------ background layers (HTML, CSS, animation)
def bg_layer(kind: str, RW: int, RH: int) -> Tuple[str, str, str]:
    if kind == "paper":
        html = ('<svg class="abs" width="100%" height="100%" style="left:0;top:0"><filter id="nz"><feTurbulence type="fractalNoise" baseFrequency=".85" '
                'numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .10 0"/></filter>'
                '<rect width="100%" height="100%" filter="url(#nz)"/></svg><div id="vig" class="abs" style="inset:0"></div>')
        css = "#vig { background: radial-gradient(ellipse 110% 90% at 50% 45%, rgba(0,0,0,0) 60%, rgba(60,40,20,.10) 100%); }"
        return html, css, ""
    if kind == "waves":
        w = RW * 2
        paths = []
        for i, (amp, y, op) in enumerate(((60, 0.80, 0.16), (80, 0.86, 0.22), (50, 0.92, 0.30))):
            base = RH * y
            d = f"M0 {base:.0f} " + " ".join(f"Q{(k + 0.5) * w / 8:.0f} {base - amp if k % 2 == 0 else base + amp:.0f} {(k + 1) * w / 8:.0f} {base:.0f}" for k in range(8))
            d += f" L{w} {RH} L0 {RH} Z"
            col = ["var(--accent)", "var(--accent2)", "var(--accent3)"][i]
            paths.append(f'<path class="wv" d="{d}" style="fill:{col};opacity:{op}"/>')
        html = f'<svg id="waves" class="abs" width="{w}" height="{RH}" style="left:0;top:0">{"".join(paths)}</svg>'
        js = 'EZ.$$(".wv").forEach(function (p, i) { tl.fromTo(p, {x: -i * 120}, {x: -' + str(RW) + ' * (0.25 + i * 0.12), duration: D, ease: "none"}, 0); });'
        return html, "", js
    if kind == "blobs":
        spots = [(0.15, 0.2, "--accent"), (0.85, 0.35, "--accent2"), (0.45, 0.9, "--accent3")]
        size = int(max(RW, RH) * 0.75)
        html = "".join(f'<div class="blob abs" style="width:{size}px;height:{size}px;left:{RW * x - size / 2:.0f}px;top:{RH * y - size / 2:.0f}px;'
                       f'background:radial-gradient(circle, color-mix(in srgb, var({c}) 38%, transparent) 0%, rgba(0,0,0,0) 65%)"></div>' for x, y, c in spots)
        js = 'EZ.$$(".blob").forEach(function (b, i) { tl.to(b, {x: (i - 1) * 140, y: (i % 2 ? -1 : 1) * 110, duration: D, ease: "sine.inOut"}, 0); });'
        return html, "", js
    if kind == "topo":
        cx, cy = RW * 0.78, RH * 0.25
        rings = "".join(f'<ellipse cx="0" cy="0" rx="{120 + k * 110}" ry="{90 + k * 95}" transform="rotate({k * 7})" fill="none" '
                        f'style="stroke:var(--gridline)" stroke-width="3"/>' for k in range(12))
        html = f'<svg class="abs" width="{RW}" height="{RH}" style="left:0;top:0"><g id="topo" transform="translate({cx:.0f},{cy:.0f})">{rings}</g></svg>'
        js = f'tl.to("#topo", {{rotation: 14, svgOrigin: "{cx:.0f} {cy:.0f}", duration: D, ease: "none"}}, 0);'
        return html, "", js
    return "", "", ""

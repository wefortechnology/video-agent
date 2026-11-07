"""Ideas and scripts, written by Gemini with the brand's memory injected into every prompt."""
import json
import logging
import re
from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app import db
from app.config import settings
from app.formats import WPS, get_format

log = logging.getLogger("llm")
LANG_NAME = {"en": "English", "hi": "Hindi (Devanagari script)"}


class Idea(BaseModel):
    title: str = Field(description="Working title, max 8 words")
    hook: str = Field(description="The opening line that stops the scroll")
    angle: str = Field(description="What makes this post different, one sentence")
    summary: str = Field(description="What the video will show, 2 sentences")


class IdeaList(BaseModel):
    ideas: List[Idea]


class Scene(BaseModel):
    title: str = Field(description="Short scene label, max 4 words")
    art: str = Field(default="", description="Animation for this scene, one of the listed animation names")
    points: List[str] = Field(default_factory=list, description="For checklist, card or icons: 2-3 very short items (1-4 words each) in the video language; empty otherwise")
    icons: List[str] = Field(default_factory=list, description="For icons: one icon name per point; empty otherwise")
    number: str = Field(default="", description="For counter only: a number stated in the request or brand facts, e.g. '120+' or '5 years'. Never invent one; empty otherwise")
    values: List[float] = Field(default_factory=list, description="For charts: numbers from the request or brand facts only, one per point, same order. Empty if the request gives none (the chart is then drawn as illustrative, without numbers)")
    unit: str = Field(default="", description="Unit for values, e.g. '%', '₹', ' people'; empty if none")
    ai_clip: bool = Field(default=False, description="True for the 1-3 scenes that should be a cinematic AI video clip (only when asked)")
    ai_prompt: str = Field(default="", description="For ai_clip scenes: a prompt for an AI video model")
    narration: str = Field(description="Spoken voiceover for this scene")
    caption: str = Field(description="On-screen caption, same meaning as narration, may be shorter")
    must_match: str = Field(description="2-4 English keywords (synonyms and spellings), comma separated, for the ONE main subject that must be visible in this scene's footage. At least one must appear in the footage's description tags, or the clip is rejected. Example: 'rangoli, kolam' or 'sparkler, firecracker, sparklers'")
    stock_query: str = Field(description="3 stock-footage searches for THIS scene, separated by ' | ', most specific first, each 2-4 English words, naming things that are visibly on screen. Example: 'children lighting firecrackers | fireworks night sky | diwali celebration'")


class DesignSpec(BaseModel):
    preset: str = Field(description="Closest preset name from the menu")
    mood: str = Field(description="2-6 words describing the look, e.g. 'boardroom navy and gold, confident'")
    bg: str = Field(description="Background colour, hex like #0f1e3a")
    surface: str = Field(description="Card colour, hex")
    ink: str = Field(description="Main text colour, hex, high contrast on bg")
    accent: str = Field(description="Main accent colour, hex")
    accent2: str = Field(description="Second accent, hex")
    accent3: str = Field(description="Third accent, hex")
    background: str = Field(description="Background style from the menu")
    particles: str = Field(description="Particles from the menu")
    fonts: str = Field(description="Font pair from the menu")
    card: str = Field(description="Card style from the menu")
    corners: str = Field(description="Corner style from the menu")
    title_style: str = Field(description="Title style from the menu")
    transition: str = Field(description="Scene transition from the menu")
    use_brand_colours: bool = Field(default=False, description="True only if the video is about the brand itself (its news, hiring, launch)")


class Script(BaseModel):
    design: DesignSpec
    topic_keywords: str = Field(description="2-4 English words, comma separated, that stock libraries use to tag the overall topic, e.g. 'diwali, deepavali' or 'hiring, recruitment'. Used to keep footage on topic.")
    visual_plan: str = Field(description="First think about the topic: list 8-10 concrete things a viewer expects to SEE for it (objects, places, people, actions, colours), comma separated")
    title: str
    scenes: List[Scene]
    cta: str = Field(description="Closing call to action, max 8 words, in the video language")
    post_caption: str = Field(description="Caption text for the social post, in the video language")
    hashtags: List[str] = Field(description="4-6 hashtags without the # sign")
    thumbnail_text: str = Field(default="", description="YouTube thumbnail title: 2-5 punchy words, in the video language")
    thumbnail_highlight: str = Field(default="", description="The one word from thumbnail_text to highlight")
    thumbnail_photo: str = Field(default="", description="2-4 English words to search a striking stock photo for the thumbnail (people or a clear subject)")
    thumbnail_tag: str = Field(default="", description="One short category word shown on the thumbnail, e.g. 'Leadership', 'Data', 'Funny'")


def configured() -> bool:
    return bool(settings.GEMINI_API_KEY)


_client_cache = None


def _client():
    """One long-lived client. A throwaway client gets garbage-collected mid-request and closes its connection."""
    global _client_cache
    if _client_cache is None:
        from google import genai
        from google.genai import types
        # a busy model can hold a request for minutes; give up after 90 s and try the next model instead
        _client_cache = genai.Client(api_key=settings.GEMINI_API_KEY, http_options=types.HttpOptions(timeout=90_000))
    return _client_cache


def brand_context(brand: Dict[str, Any]) -> str:
    """Everything the agent should remember about this brand: profile, standing facts, feedback, recent videos."""
    mems = db.list_memories(brand["id"], limit=60)
    facts = [m["text"] for m in mems if m["kind"] == "fact"][:15]
    feedback = [m["text"] for m in mems if m["kind"] == "feedback"][:12]
    recent = [m["text"] for m in mems if m["kind"] == "video"][:8]
    lines = [
        f"Brand: {brand['name']}",
        f"Industry: {brand['industry']}" if brand["industry"] else "",
        f"About: {brand['about']}" if brand["about"] else "",
        f"Audience: {brand['audience']}" if brand["audience"] else "",
        f"Tone of voice: {brand['tone']}",
        f"Never: {brand['avoid']}" if brand["avoid"] else "",
    ]
    if facts:
        lines.append("Things to remember about this brand:\n- " + "\n- ".join(facts))
    if feedback:
        lines.append("Past feedback from the team (follow it):\n- " + "\n- ".join(feedback))
    if recent:
        lines.append("Videos already made (do not repeat these ideas):\n- " + "\n- ".join(recent))
    return "\n".join(l for l in lines if l)


class VisualPick(BaseModel):
    chosen: List[int] = Field(description="Image numbers (0-based) to use, best first. Empty if none is acceptable.")
    reason: str = ""


def pick_visuals(scene_text: str, must: List[str], images: List[bytes], n: int, kinds: Optional[List[str]] = None) -> List[int]:
    """Gemini looks at candidate thumbnails and keeps only those that show the scene's subject and look good on a social video."""
    from google.genai import types
    parts = [f"""You are a picture editor for a short social-media video. This scene says: {scene_text!r}.
The main subject that must be visible: {', '.join(must) or 'the scene topic'}.
Below are {len(images)} candidates, numbered from 0. Each is a still frame of a VIDEO clip or a still PHOTO. Choose up to {n} that:
- clearly show the subject: real people, objects and places, or polished 2D/3D animation of it
- look high quality, bright, attractive and professional, like a brand's festive social post
- would work well full-screen in a vertical reel
Strongly prefer VIDEO over PHOTO: the post must feel like real moving footage. Pick a PHOTO only if no VIDEO is good.
Reject cheap-looking or screensaver-like animation, abstract lines, clip-art, dark or blurry frames, visible text or watermarks, other festivals (e.g. Christmas for Diwali), or anything unrelated.
Prefer variety (different angles/compositions) if you pick more than one. If none is good enough, return an empty list."""]
    images = images[:10]
    kinds = kinds or ["video"] * len(images)
    for i, b in enumerate(images):
        parts += [f"Candidate {i} ({kinds[i].upper()}):", types.Part.from_bytes(data=b, mime_type="image/jpeg")]
    out = _generate(VisualPick, parts, temperature=0.2)
    seen, res = set(), []
    for k in out.chosen:
        if k not in seen and 0 <= k < len(images):
            seen.add(k)
            res.append(k)
    log.info("vision pick: %s (%s)", res, out.reason[:100])
    return res[:n]


_cooldown: Dict[str, float] = {}  # model -> time until which it is tried last (it was busy or out of quota)


def _models():
    import time
    names = [settings.GEMINI_MODEL] + [m.strip() for m in settings.GEMINI_FALLBACK_MODELS.split(",") if m.strip() and m.strip() != settings.GEMINI_MODEL]
    now = time.time()
    return [m for m in names if _cooldown.get(m, 0) <= now] + [m for m in names if _cooldown.get(m, 0) > now]


_last_call = {"t": 0.0}


def _pace():
    """Free-tier keys allow ~5 requests a minute: keep a gap between calls instead of hitting the limit."""
    import time
    gap = settings.GEMINI_MIN_INTERVAL - (time.time() - _last_call["t"])
    if gap > 0:
        time.sleep(gap)
    _last_call["t"] = time.time()


def _generate(schema, prompt, temperature=0.8):
    """Per-minute limits: wait as long as Google says and retry the same model. Busy (503): retry once, then the next model.
    Daily quota or a bad model name: move to the next model, and try that model last for the next 10 minutes."""
    import re as _re
    import time
    from google.genai import types
    cfg = types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=temperature)
    last = None
    for model in _models():
        attempt = 0
        while attempt < 4:
            attempt += 1
            _pace()
            try:
                resp = _client().models.generate_content(model=model, contents=prompt, config=cfg)
                return schema.model_validate(json.loads(resp.text))
            except Exception as e:
                last = e
                msg = str(e)
                low = msg.lower()
                log.warning("Gemini %s attempt %d failed: %s", model, attempt, msg[:160])
                per_minute = "per minute" in low or "perminute" in low or "retry in" in low
                if ("429" in msg or "resource_exhausted" in low) and per_minute and "per day" not in low:
                    m = _re.search(r"retry in ([\d.]+)s", msg)
                    time.sleep(min(70.0, float(m.group(1)) + 1.5) if m else 20.0)
                    continue
                if any(c in low for c in ("timed out", "timeout", "deadline")):
                    _cooldown[model] = time.time() + 600
                    break
                if any(c in msg for c in ("503", "UNAVAILABLE", "500")) and attempt < 2:
                    time.sleep(4)
                    continue
                _cooldown[model] = time.time() + 600
                break
    raise last


def generate_ideas(brand: Dict[str, Any], brief: str, fmt_key: str, language: str, count: int = 5) -> Dict[str, Any]:
    fmt = get_format(fmt_key)
    if not configured():
        return {"source": "offline-template", "ideas": _offline_ideas(brand, brief, count)}
    prompt = f"""You are a social media strategist for the brand below.

{brand_context(brand)}

Request from the team: {brief!r}
Destination: {fmt['label']} ({fmt['tip']}).
Write {count} different video ideas in {LANG_NAME[language]}. Each must be a distinct angle built on what people actually SEE and feel about the topic (for Diwali: crackers, diyas, children, lit-up homes, sweets), concrete and filmable with stock footage plus captions.
No invented statistics, no real people's names, no claims the brand has not made."""
    try:
        out = _generate(IdeaList, prompt)
        return {"source": "gemini", "ideas": [i.model_dump() for i in out.ideas[:count]]}
    except Exception as e:
        log.exception("Idea generation failed")
        raise RuntimeError(f"Gemini idea generation failed: {e}") from e


AI_RULE = """- AI video clips are ON: mark 1-3 scenes with ai_clip=true where a real, cinematic moving shot helps most (the opening hook, one emotional
  or real-world moment, the ending). Never for data, charts or lists. For each, write ai_prompt in English for a video model: subject, action,
  setting, camera movement, lighting, mood, realistic style, about 8 seconds, and end with 'no text, no logos, no watermarks'. No real or famous
  people, no brand names. Other scenes: ai_clip=false, ai_prompt empty."""


HOOK_RULE = """- Scene 1 is the hook, the most important line of the video. Start with the most surprising fact, a bold claim, a number the request gives, or a
  one-sentence story already in motion. Never open with a greeting, the channel name, "Hi guys", "welcome", "in this video" or "do you know".
  No logo or brand name and no request to subscribe, like or comment anywhere in the opening.
  In the first 2 seconds the viewer must know why to keep watching."""

LOOP_RULE = """- Loop ending: this is a Short. Write the last scene so it flows straight back into scene 1 (for example it ends with a question or half-thought
  that scene 1 answers), so a replay feels seamless. Keep the cta to 2-5 words."""

LIST_RULE = """Structure: a numbered list ("N things"). The title says the number. Each chapter is one item, titled "1. ...", "2. ...", 40-70 seconds each
(minutes 0.7-1.2). Keep the most surprising item for last and tease it in the hook. Chapter 1 = the hook plus item 1 (no separate intro chapter).
The final chapter = the last item, a 2-line recap and the call to action."""


def _scene_rules(words: int, language: str) -> str:
    """Rules every scene follows (short videos and long-video chapters alike)."""
    from app.services.motion import ART_CHOICES, ICONS
    arts = "; ".join(f'"{k}" = {v}' for k, v in ART_CHOICES.items())
    return f"""- Be specific and concrete, not generic. Every narration carries one real detail (an example, an action, a fact the request gives, a feeling). Keep every line short and spoken.
- narration: about {words} words (use most of them, the pace of top explainer channels; never pad with filler), in {LANG_NAME[language]}, plain spoken language, no stage directions.
- caption: the big on-screen headline for the scene, 2-6 words, same language.
- art: the animation that best SHOWS this scene. Choose from: {arts}.
  Choose the diagram whose SHAPE says what the line means: things in order -> flow or steps; history or dates -> timeline; something that repeats -> cycle;
  levels or priorities -> pyramid; a team or delegation -> hierarchy; two factors -> matrix; narrowing down -> funnel; overlap -> venn; growth -> bars;
  ideas around one core -> mindmap; a goal -> target; two options -> compare; pros and cons -> proscons; seen vs hidden -> iceberg;
  layers -> layers; parts making a whole -> puzzle or hexagons; from now to the goal -> gap; a yes/no choice -> decision; milestones -> roadmap.
  For data use the chart that fits: shares -> pie, donut or stackbar; change over time -> line or area; a ranking -> hbars; one score -> gauge;
  percentages -> rings or waffle; headline figures -> kpis (only with numbers from the request); several qualities -> radar.
  Charts may show numbers ONLY from the request or brand facts (put them in values, with unit). Without such numbers leave values empty;
  the chart is drawn as an illustrative shape without numbers and labelled Illustrative. Never invent numbers. Never use the same animation in two scenes in a row, and across the video
  use many different diagram types instead of repeating a few. Festive animations only for festive topics. Use "photo" for about one scene in four,
  where a real picture of people, a place or an object makes the video feel real. Prefer the topic visuals (network, globe, server, lock) and the data animations (flow, checklist, compare, icons, card, counter) whenever they fit, and fill points / icons / number for them. Use spotlight rarely (an opening hook or one big announcement). Use counter only for a number the request itself gives.
  icon names: {", ".join(ICONS)}.
- points: 2-4 very short items (1-4 words each) for flow, checklist, compare (exactly two), icons, card, network (node labels); empty otherwise.
- must_match and stock_query: only used for stock footage; still fill them (English keywords and three ' | '-separated searches for what is visible).
- No invented numbers, statistics or claims. Respect "Never" and the feedback above."""


def _theme_rule() -> str:
    from app.services.design import describe_for_prompt
    return ("design: a look made for THIS topic, so every video looks different and real, like a professional channel would design it. "
            "Start from the closest preset, then choose colours that belong to the subject (a CEO video: boardroom navy and gold; healthy food: "
            "fresh greens and tomato red; space: deep violet and cyan; history: sepia and ink; kids: bright and playful). Light backgrounds suit most "
            "lessons; dark suits premium, night, tech or cinematic topics. Pick background, particles, fonts, card, corners, title_style and transition "
            "from the menus so they match the mood (serif for history and leadership, rounded for kids and health, condensed for news and sport). "
            "Festive looks only for festivals. Menus: " + describe_for_prompt())


def _clean_tags(tags: List[str]) -> List[str]:
    # the model sometimes adds a year anyway; strip it so posts do not look dated
    return [t for t in (re.sub(r"(?:19|20)\d{2}", "", h).strip("# ") for h in tags) if t]


def generate_script(brand: Dict[str, Any], brief: str, idea: Optional[Dict[str, Any]], fmt_key: str, language: str,
                    style: str = "motion", length_min: int = 0, progress=None, checkpoint=None, use_ai: bool = False,
                    structure: str = "") -> Dict[str, Any]:
    if fmt_key == "youtube":
        return generate_long_script(brand, brief, idea, language, length_min, progress, checkpoint, use_ai, structure)
    fmt = get_format(fmt_key)
    n_scenes = max(3, round(fmt["seconds"] / fmt["scene_seconds"]))
    words = int(fmt["scene_seconds"] * WPS[language])
    if not configured():
        return {"source": "offline-template", **_offline_script(brand, brief, idea, n_scenes, language)}
    idea_txt = json.dumps(idea, ensure_ascii=False) if idea else "(none, choose the best angle yourself)"
    prompt = f"""You are the scriptwriter and director for the brand below.

{brand_context(brand)}

Today's date: {date.today().isoformat()}
Request: {brief!r}
Chosen idea: {idea_txt}
Destination: {fmt['label']}, about {fmt['seconds']} seconds. {fmt['tip']}

STEP 0, topic_keywords: the words a stock library would tag this topic with (Diwali: diwali, deepavali).
STEP 0b, {_theme_rule()}
STEP 1, visual_plan: the TOPIC comes first, the brand second. List what a viewer expects to see for this topic (Diwali: lit diyas, rangoli, sparklers, fireworks, homes lit up, sweets; hiring: interviews, a team at work).

STEP 2, write exactly {n_scenes} scenes:
{HOOK_RULE}
- The brand appears naturally only near the end; the middle belongs to the topic. The last scene lands the message and leads into the call to action.
{LOOP_RULE if fmt_key in ("short", "reel") else ""}
- Every scene shows something different. Never repeat the same visual.
{_scene_rules(words, language)}
{AI_RULE if use_ai else ""}
- The last scene should be "greeting" for a festive greeting, otherwise "spotlight" (or "card" with points).
- cta: short closing call to action. post_caption: ready to paste under the post. hashtags: relevant, no # sign, and never include a year.
- thumbnail_text: 2-5 punchy words that make people click (no clickbait lies); thumbnail_highlight: the key word in it; thumbnail_photo: a stock photo search for a striking image of the subject; thumbnail_tag: one category word."""
    try:
        out = _generate(Script, prompt)
    except Exception as e:
        log.exception("Script generation failed")
        raise RuntimeError(f"Gemini script generation failed: {e}") from e
    data = out.model_dump()
    data["hashtags"] = _clean_tags(data["hashtags"])
    return {"source": "gemini", **data}


# ---- long-form YouTube: outline first, then each chapter -------------------------------------------
class ChapterPlan(BaseModel):
    title: str = Field(description="Chapter title, 2-6 words, in the video language")
    summary: str = Field(description="What this chapter explains, 1-2 sentences")
    key_points: List[str] = Field(description="3-6 things this chapter must cover, in order")
    minutes: float = Field(description="Planned length of this chapter in minutes (1-4)")


class Outline(BaseModel):
    title: str = Field(description="YouTube title, clear and specific, max 70 characters")
    topic_keywords: str = Field(description="2-4 English words, comma separated, that describe the topic")
    design: DesignSpec
    chapters: List[ChapterPlan]
    cta: str = Field(description="The closing engagement question asked in the last 5 seconds: one specific question about the topic that is easy to answer "
                                 "in a comment, max 12 words (e.g. 'Which tech term confuses you most? Tell us in the comments!')")
    pinned_comment: str = Field(default="", description="The same question as a friendly first comment the channel owner pins under the video: 1-2 sentences, "
                                                        "same language, ends with the question")
    post_caption: str = Field(description="YouTube description: 2-4 sentences on what the viewer will learn (chapters are added automatically)")
    hashtags: List[str] = Field(description="4-6 hashtags without the # sign")
    thumbnail_text: str = Field(default="", description="YouTube thumbnail title: 2-5 punchy words, in the video language")
    thumbnail_highlight: str = Field(default="", description="The one word from thumbnail_text to highlight")
    thumbnail_photo: str = Field(default="", description="2-4 English words to search a striking stock photo for the thumbnail (people or a clear subject)")
    thumbnail_tag: str = Field(default="", description="One short category word shown on the thumbnail, e.g. 'Leadership', 'Data', 'Funny'")


class ChapterScenes(BaseModel):
    scenes: List[Scene]


SCENE_SECONDS_LONG = 9  # one idea every ~9 seconds keeps a long video moving


def generate_long_script(brand, brief, idea, language, length_min: int = 0, progress=None, checkpoint=None, use_ai: bool = False,
                         structure: str = "") -> Dict[str, Any]:
    """Medium-depth YouTube video of any length: plan chapters, then write each chapter's scenes with the outline as context.
    checkpoint: a JSON file; the outline and every finished chapter are saved there, so a retry resumes instead of starting over."""
    if not configured():
        n = 8
        return {"source": "offline-template", "theme": "clean", **_offline_script(brand, brief, idea, n, language)}
    idea_txt = json.dumps(idea, ensure_ascii=False) if idea else "(none)"
    length_rule = (f"Total length: about {length_min or 5} minutes.\n{LIST_RULE}" if structure == "list" else
                   f"Total length: about {length_min} minutes. Split it into chapters of 1.5-3 minutes." if length_min else
                   "Total length: decide from how much the topic genuinely needs at a medium depth: usually 6-12 minutes, "
                   "up to 20 for a big topic, never padded. Chapters of 1.5-3 minutes.")
    plan_prompt = f"""You are planning a YouTube video for the channel below.

{brand_context(brand)}

Today's date: {date.today().isoformat()}
Request: {brief!r}
Chosen idea: {idea_txt}
Language: {LANG_NAME[language]}

Depth: MEDIUM. Explain clearly with everyday examples and analogies, go a level deeper than a quick summary, but no jargon walls or academic detail.
{length_rule}
Chapter 1 opens with a hook: the most surprising fact, a bold claim or a one-sentence story already in motion (never a greeting, "welcome to the channel"
or "in this video"), then one line promising what the viewer will learn. Keep viewers watching: tease the best point early and pay it off later.
The middle chapters are pure value: the topic's information, shown with motion graphics, with no subscribe, like or comment requests.
The last chapter recaps the key ideas and delivers the most useful takeaway BEFORE any ask; only in its final seconds comes the subscribe line and the engagement question (cta).
Cover what the request asks for, in a logical order, each chapter building on the previous one. No invented statistics or numbers.
{_theme_rule()}
Titles, summaries and key points in {LANG_NAME[language]}. Hashtags relevant, no # sign, no year.
Thumbnail: thumbnail_text 2-5 punchy words (honest, no clickbait), thumbnail_highlight the key word, thumbnail_photo a stock photo search for a striking image of the subject, thumbnail_tag one category word."""
    saved = {}
    key = [brief, idea_txt, language, length_min, structure]
    if checkpoint and checkpoint.exists():
        try:
            saved = json.loads(checkpoint.read_text(encoding="utf-8"))
            if saved.get("key") != key:
                saved = {}
        except Exception:
            saved = {}

    def save():
        if checkpoint:
            checkpoint.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")

    if saved.get("outline"):
        outline = Outline.model_validate(saved["outline"])
        log.info("Resuming long script: outline + %d chapters already written", len(saved.get("done", [])))
    else:
        try:
            outline = _generate(Outline, plan_prompt, temperature=0.6)
        except Exception as e:
            log.exception("Outline generation failed")
            raise RuntimeError(f"Gemini outline failed: {e}") from e
        saved = {"key": key, "outline": outline.model_dump(), "done": []}
        save()
    chapters = outline.chapters[:12]
    words = int(SCENE_SECONDS_LONG * WPS[language])
    toc = "\n".join(f"{i + 1}. {c.title}: {c.summary}" for i, c in enumerate(chapters))
    scenes: List[Dict[str, Any]] = []
    last_lines = ""
    for ci, ch in enumerate(chapters):
        if ci < len(saved.get("done", [])):  # written in an earlier attempt
            scenes += saved["done"][ci]
            last_lines = " ".join(x["narration"] for x in saved["done"][ci][-2:])
            continue
        if progress:
            progress(f"Writing chapter {ci + 1}/{len(chapters)}: {ch.title}", 10 + int(85 * ci / len(chapters)))
        n_sc = max(4, min(24, round(ch.minutes * 60 / SCENE_SECONDS_LONG)))
        ch_prompt = f"""You are writing one chapter of a YouTube video for the channel below.

{brand_context(brand)}

Video title: {outline.title}
Full outline:
{toc}

Now write chapter {ci + 1}: "{ch.title}" — {ch.summary}
Cover, in order: {"; ".join(ch.key_points)}
{"Previous chapter ended with: " + last_lines if last_lines else "This is the opening chapter: scene 1 is the hook (a surprising fact, bold claim or story in motion; no greeting)."}
{("This is the final chapter: recap the main ideas briefly and give the most useful takeaway first. Only the LAST scene (about the last 5 seconds, at most 16 words) carries the ask: "
   "a one-line friendly subscribe appeal, then this exact engagement question: " + outline.cta + " No subscribe, like or comment request in any earlier scene.")
  if ci == len(chapters) - 1 else "Do not recap the whole video; end the chapter with a one-line bridge to the next chapter. No subscribe, like or comment request in this chapter."}

Write exactly {n_sc} scenes (about {SCENE_SECONDS_LONG} seconds each) for this chapter only. Medium depth: explain, give an everyday example or analogy, then move on.
Do not greet the viewer again or re-introduce the video after chapter 1.
{"Scene 1 shows a bold, high-contrast visual with fast motion that matches the hook (art: spotlight, network, globe, lock, orbit, or counter only with a number from the request); no logo, no brand name." if ci == 0 else ""}
{_scene_rules(words, language)}
{AI_RULE.replace("1-3 scenes", "at most 1 scene in this chapter") if use_ai else ""}"""
        try:
            part = _generate(ChapterScenes, ch_prompt, temperature=0.7)
        except Exception as e:
            log.exception("Chapter generation failed")
            raise RuntimeError(f"Gemini failed on chapter {ci + 1}: {e}") from e
        chapter_scenes = []
        for sc in part.scenes[:n_sc]:
            d = sc.model_dump()
            d["chapter"] = ci + 1
            chapter_scenes.append(d)
        scenes += chapter_scenes
        saved["done"].append(chapter_scenes)
        save()
        last_lines = " ".join(s.narration for s in part.scenes[-2:])
    return {"source": "gemini", "title": outline.title, "topic_keywords": outline.topic_keywords, "design": outline.design.model_dump(),
            "visual_plan": "", "chapters": [{"title": c.title, "minutes": c.minutes} for c in chapters], "scenes": scenes,
            "cta": outline.cta, "pinned_comment": outline.pinned_comment, "post_caption": outline.post_caption, "hashtags": _clean_tags(outline.hashtags),
            "thumbnail_text": outline.thumbnail_text, "thumbnail_highlight": outline.thumbnail_highlight,
            "thumbnail_photo": outline.thumbnail_photo, "thumbnail_tag": outline.thumbnail_tag}


# ---- playlists: one topic, a series of episodes -----------------------------------------------------
class Episode(BaseModel):
    title: str = Field(description="Episode title in the video language, specific and clickable (for list videos include the number)")
    angle: str = Field(description="What this episode covers and how, 1-2 sentences, no overlap with other episodes")
    hook: str = Field(description="The opening line idea: a surprising fact, bold claim or story in motion (no greeting)")


class SeriesPlan(BaseModel):
    series_title: str = Field(description="Playlist title, max 60 characters, in the video language")
    series_tag: str = Field(description="A short recurring series label shown on every episode, 2-4 words (e.g. 'Tech Myth vs Fact')")
    description: str = Field(description="Playlist description: 2-3 sentences on what viewers will learn")
    episodes: List[Episode]


def plan_playlist(brand: Dict[str, Any], topic: str, fmt_key: str, language: str, count: int, length_min: int = 0,
                  structure: str = "") -> Dict[str, Any]:
    """One Gemini request: plan a series (YouTube playlist) of `count` episodes on one topic."""
    if not configured():
        raise RuntimeError("Planning a playlist needs GEMINI_API_KEY in .env")
    fmt = get_format(fmt_key)
    kind = (f"YouTube videos of about {length_min or 5} minutes" + (", each a numbered list ('N things')" if structure == "list" else "")
            if fmt_key == "youtube" else f"{fmt['label']}s of about {fmt['seconds']} seconds")
    prompt = f"""You are planning a YouTube playlist (a series) for the channel below.

{brand_context(brand)}

Today's date: {date.today().isoformat()}
Series topic: {topic!r}
Episodes: exactly {count} {kind}, in {LANG_NAME[language]}.

- One recurring format, like the best series channels: every episode follows the same pattern (series_tag), so viewers know what to expect and binge.
- Order: from the most clickable basics to deeper ideas; every episode stands alone but builds on the previous one. No two episodes overlap.
- Each episode has one clear idea that fits its length; titles are specific and honest (no clickbait lies).
- hook: the first line idea for the episode (a surprising fact, bold claim or story in motion; never a greeting).
- No invented statistics or numbers. Respect "Never" and the feedback above."""
    out = _generate(SeriesPlan, prompt, temperature=0.8)
    data = out.model_dump()
    data["episodes"] = data["episodes"][:count]
    return data


def episode_brief(topic: str, plan: Dict[str, Any], n: int) -> str:
    eps = plan["episodes"]
    ep = eps[n - 1]
    prev_t = eps[n - 2]["title"] if n > 1 else ""
    next_t = eps[n]["title"] if n < len(eps) else ""
    lines = [topic.strip(), "",
             f'This is episode {n} of {len(eps)} in the series "{plan["series_title"]}" ({plan["series_tag"]}).',
             f"Episode title: {ep['title']}. Angle: {ep['angle']}. Hook idea: {ep['hook']}"]
    if prev_t:
        lines.append(f"Previous episode: {prev_t}. Do not repeat it.")
    lines.append(f"End with one short line that makes viewers want the next episode: {next_t}." if next_t else
                 "This is the last episode: end by inviting viewers to watch the whole series.")
    return "\n".join(lines)[:3900]


# ---- offline fallback (no key): clearly flagged so nobody mistakes it for the real thing ----
def _offline_ideas(brand, brief, count):
    angles = ["The big announcement", "Behind the scenes", "Why it matters", "A quick tip", "Thank you note"]
    return [{"title": f"{a}: {brief[:30]}", "hook": f"{brand['name']}: {brief[:60]}", "angle": a,
             "summary": f"A short video about {brief}. (Offline template: add GEMINI_API_KEY for real ideas.)"}
            for a in angles[:count]]


def _offline_script(brand, brief, idea, n, language):
    title = (idea or {}).get("title") or brief[:40]
    parts = [brief] + [f"{brand['name']}"] * (n - 1)
    queries = ["office team", "city skyline", "people smiling", "handshake", "sunrise", "teamwork", "laptop work", "community"]
    scenes = [{"title": f"Scene {i + 1}", "narration": parts[i] if i == 0 else f"{brand['name']}.",
               "caption": parts[i] if i == 0 else f"{brand['name']}", "stock_query": queries[i % len(queries)]} for i in range(n)]
    return {"title": title, "scenes": scenes, "cta": brand.get("cta") or f"Follow {brand['name']}",
            "post_caption": f"{brief} #{brand['name'].replace(' ', '')}", "hashtags": [brand["name"].replace(" ", "")]}

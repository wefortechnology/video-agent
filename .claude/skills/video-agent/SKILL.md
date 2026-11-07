---
name: video-agent
description: Make, fix or extend videos with the Video Agent app in this folder (brand + prompt in, ready-to-post video out). Use when someone asks to "make a video / reel / short / YouTube video about …", "render video <id>", "redo the script", "add a diagram/animation/chart", "change the design/thumbnail/brand", "why did my video fail", or works on files in app/, web/ or assets/. Covers running the server, the create → script → render → review flow over the API, source-checked numbers for data videos, design system, 70 animations, thumbnails, AI clips, music/trending songs, Gemini free-tier limits, and how to verify a render by looking at frames.
---

# Video Agent: how to make and fix videos

The app turns a brand + brief into a finished video (YouTube 16:9 with chapters, Shorts/Reels 9:16, LinkedIn 1:1):
Gemini writes the script, outline and a topic-made design; Kokoro speaks (local, free); HyperFrames (HTML + GSAP, in
`~/.video-studio/hyperframes`) renders motion graphics; ffmpeg assembles; a procedural music bed is mixed under the voice.
It never posts anywhere. A person reviews and posts (EdZola policy: human review of all AI output, no PII, no secrets).

Read `README.md` for the full feature list. This file is the operating manual.

## 1. Run it

```bash
cd "/home/shri/Desktop/video agent/video-agent-app"
ss -ltnp | grep -q 8010 || ./run.sh          # UI + API on http://127.0.0.1:8010
```

- Starting a second copy is safe: it detects the running server and leaves its jobs alone.
- **Never restart the server while a job is `scripting` or `rendering`** (the restart marks it interrupted). Check first:
  `.venv/bin/python -c "from app import db; print([(v['id'], v['status']) for v in db.list_videos() if v['status'] in ('queued','scripting','rendering')])"`
  The user may be creating videos in the UI at the same time. If you need new code live while a job runs, render in a
  separate process instead: `.venv/bin/python -c "from app import pipeline, db; db.update_video(ID, status='rendering'); pipeline._safe(ID, pipeline._render_job)"`.
- Keys live only in `.env` (`GEMINI_API_KEY`, `PIXABAY_API_KEY`, optional `PEXELS_API_KEY`). Never print them, never paste them into prompts or chat.

## 2. Make a video (API flow)

1. **Brand** (brand id 4 = "We For Technology"): `GET /api/brands`. Brand profile + memory facts/feedback go into every prompt.
2. **Create** (writes the script in the background):
   ```bash
   curl -s -X POST localhost:8010/api/videos -H 'content-type: application/json' -d @brief.json
   ```
   `brief.json`: `{"brand_id":4, "format":"youtube|short|reel|linkedin", "language":"en|hi", "style":"motion|footage",
   "length_min":0, "use_ai":false, "voice_engine":"kokoro", "brief":"…"}`. `length_min` (YouTube only): 0 = Auto (content decides,
   medium depth), or 3-20. Brief max 4000 characters.
3. **Wait** for `status == script_ready` (`GET /api/videos/<id>`). Use a background poll; do not sleep in the foreground.
4. **Review the script before rendering** (section 3). Edit with `PUT /api/videos/<id>/script` (send the whole script JSON;
   empty fields do not overwrite).
5. **Render**: `POST /api/videos/<id>/render`, poll until `review` or `failed`.
6. **Verify** (section 6), then tell the user where the files are: `data/videos/<id>/final.mp4`, `voice_only.mp4`,
   `thumb.jpg`, `post.txt` (caption, hashtags, YouTube chapter timestamps). Also in the UI Library tab.

Render time on this laptop (no GPU, ~0.1 s per frame): 30 s reel ≈ 3-5 min, 3 min YouTube ≈ 13-18 min, 10 min ≈ 35-50 min.

## 3. Script review checklist (do this every time)

- **Numbers**: a data video may only use numbers that are in the brief or brand facts. Put the sourced numbers and their
  sources IN THE BRIEF (research first with web search: ITU, GSMA, World Bank, government data), tell Gemini "use only these".
  Then scan every scene's narration, caption, points and values for numbers and compare with the brief. Fix or remove
  anything else. Name the sources in the last scene and say when two figures measure different things (e.g. SIMs vs people).
- **Charts need values**: if a chart scene (pie, donut, stackbar, line, area, hbars, bars, gauge, rings, waffle, kpis, radar)
  has empty `values`, either fill them from the brief (`values`, `unit`) or accept the Illustrative tag (no numbers shown).
  Single-value charts read a "74%" in their own headline as a fallback.
- **Art choice fits meaning**: sequence → flow/steps/timeline/roadmap, loop → cycle, priorities → pyramid, team → hierarchy,
  two factors → matrix, narrowing → funnel, overlap → venn, shares → pie, trend → line, ranking → hbars, one score → gauge,
  seen vs hidden → iceberg, yes/no → decision. Data scenes need `points` (and `values`). Prefer variety; the code also enforces it.
- Captions (on-screen headline) 2-6 words; narration short and spoken; no real people's quotes, no brand claims, no PII.
- `design.preset` suits the topic (see section 4). Change with `{"design": {"preset": "<name>"}}` in the script.

## 4. Design system (`app/services/design.py`)

Every video gets a look made for its topic: colours, background (radial, linear, grid, dots, paper, waves, blobs, diagonal,
topo, split), particles, font pair (Hindi headings fall back to Rozha One / Mukta / Baloo 2), cards, corners, title style,
transition. Gemini starts from one of 14 presets: corporate-navy, paper-explainer, tech-light, tech-grid, health-fresh,
finance-green, food-warm, kids-bright, history-sepia, nature-earth, science-space, news-bold, social-impact, festive-night.
`normalise()` fixes unreadable colours (contrast ≥ 7 for text). Without Gemini a preset is picked from brief keywords.

## 5. Animations (`app/services/motion.py`, `diagrams.py`, `charts.py`)

70 animations. Families rotate layouts on every repeat (flow → chevrons → winding path; compare → balance → before/after →
pros/cons; pie → donut → stacked bar; photo → polaroid → circle; …). `assign_arts()` also: no family twice in a row, caps on
headline-only scenes, a diagram seen in the last 6 scenes gives way to a similar one, and a variant is only used if it can
show all of the scene's data. Design space is 1080×1920; keep visuals inside y 600-1460 so the 16:9 crop (headline on one
side, visual on the other, alternating) keeps them.

**Adding an animation**: add a builder + `NEW["name"] = {"needs": ..., "build": fn, "style": css, "script": js}` in
`diagrams.py` or `charts.py`, add a one-line meaning to `CHOICES`, optionally a family/`SIMILAR` entry and a minimum length
in `_MIN`/`MIN`. Use only CSS variables (`--ink`, `--accent`, `--card`, `--radius`, `--font-head`…), never fixed colours.
In SVG use `style="stroke:var(--accent)"` (attributes do not take CSS variables). Use `EZ.rand()`, never `Math.random()`.
GSAP `svgOrigin` is in the parent's coordinates: for a group inside `translate(540,1000)` use `svgOrigin: "0 0"`.
Never tween `scale` from exactly 0 together with `svgOrigin` (use 0.01). Render a test scene and LOOK at it before finishing.

Free extras available but not yet wired in: all GSAP bonus plugins ship in `node_modules/gsap/dist` (SplitText, DrawSVG,
MorphSVG, MotionPath, Physics2D, ScrambleText; free for commercial use since April 2025) and `lottie-web` (MIT). Check
LottieFiles licence terms per animation before using any.

## 6. Verify a render (always, before reporting success)

```bash
F=data/videos/<id>/final.mp4; D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 $F)
for k in $(seq 0 15); do t=$(python3 -c "print(1.5+$k*($D-2)/15)"); ffmpeg -y -loglevel error -ss $t -i $F -frames:v 1 -vf scale=320:-1 /tmp/q_$(printf %02d $k).png; done
ffmpeg -y -loglevel error -pattern_type glob -i '/tmp/q_*.png' -filter_complex tile=4x4 /tmp/sheet.png   # then Read it
ffmpeg -hide_banner -i $F -af volumedetect -vn -f null - 2>&1 | grep max_volume                        # must not be 0 dB
```

Look for: text overlapping text or captions, labels outside bars, empty scenes, wrong numbers, off-topic photos, festive
art in non-festive videos. Fix the template or the script and re-render; say what you checked and what you could not
(you cannot hear the voice or music: ask the user to listen).

## 7. Thumbnails, music, AI clips

- **Thumbnail** (`thumbnail.py`): designed, not a frame. Big 2-5 word title with one highlighted word, a photo from
  `thumbnail_photo` (Pixabay) or the video's own photos, tag, channel name. YouTube 1280×720, Shorts 1080×1920.
  When re-making one by hand, pick a photo that matches the topic (check tags in `data/cache/search/*.json`), and never
  overwrite a good thumbnail with a test.
- **Logo**: the brand's `logo_path` (upload in the Brand tab or `POST /api/brands/<id>/logo`) appears small in the top-right corner
  of every motion scene (`render.add_logo`), big on the end card and next to the channel name on the thumbnail. The brand is read
  when a render starts, so a logo uploaded mid-render only shows after a re-render. We For Technology's master copy:
  `assets/brands/we-for-technology/logo_w_mark.png`.
- **Pace** (researched Nov 2026: top explainers speak 165-205 words/min): `VOICE_SPEED_HI` (default 1.15 ≈ 175 wpm on real script lines) and
  `VOICE_SPEED_EN` (default 0.9 ≈ 197 wpm) in `.env`; Kokoro 1.0 measures Hindi 178 / English 219 wpm. Scripts are sized with
  `WPS` in `formats.py` (hi 2.9, en 3.1 words/s) so lines fill their animation; scenes end 0.4 s after the voice; fades are 0.25/0.2 s.
  Dead air comes from short lines + animation minimums, not from the voice speed.
- **Captions**: word-by-word (karaoke): the spoken word gets an accent pill (`kit.js` finish(), colours from `cues.capact*`).
- **Music**: procedural beds (festive / uplift / quirky for funny briefs), ducked under the voice. **Never add copyrighted or
  "trending" songs to a file.** For a trending song, give the user `voice_only.mp4` and tell them to add the song in the
  YouTube Shorts / Instagram editor ("Add sound"), where it is licensed.
- **AI clips** (`use_ai`): the script marks 1-3 hero scenes with `ai_clip` + `ai_prompt`. Per scene: an uploaded clip
  (`POST /api/videos/<id>/clips/<scene>`, e.g. made in the Gemini app with the user's Pro plan) → the API
  (`AI_VIDEO_MODELS`) → animation. It never fails a video. The current key has **no video quota on the free tier**
  (`limit: 0`), so only uploads work until billing is enabled.

## 7b. What makes them watch (built into the prompts, `llm.py`)

- `HOOK_RULE`: scene 1 = surprising fact, bold claim, a number from the brief, or a story in motion. Never a greeting / "in this video".
- `LOOP_RULE` (short, reel): the last line flows back into the first; end card is 2 s.
- `LIST_RULE` (YouTube `structure: "list"`): numbered items as chapters of 40-70 s, best item last and teased in the hook.
  The UI's YouTube "Structure" option sets it; 4-6 min numbered lists are the format the research found strongest.

### YouTube video anatomy (user's brief, Nov 2026; enforced in `generate_long_script` + `_render_motion`)

- **Start (0-3 s):** opens straight on the hook: no chapter card before chapter 1 (the 0:00 chapter stamp is still written), no logo intro,
  no brand name, no subscribe request. Scene 1 uses a bold, high-contrast, fast-moving art (spotlight/network/globe/lock/orbit).
- **Middle:** pure value shown with motion graphics; no subscribe/like/comment asks in any middle chapter.
- **End (last ~5 s):** the best takeaway comes first; only the LAST scene carries a short subscribe line + the engagement question (`cta`,
  shown on the end card). The same question is saved as `pinned_comment.txt` (UI: "Comment to pin"). The user posts and pins it
  by hand after publishing; the app never posts anything.

## 7c. Playlists (a series on one topic)

`POST /api/playlists` `{"brand_id", "topic", "format": "short|reel|youtube|linkedin", "language", "style", "count": 2-10,
"length_min" (youtube), "structure" (youtube: "list" or "")}` → `llm.plan_playlist` (1 Gemini request: series title, recurring
`series_tag`, episodes), then one video per episode (`videos.playlist_id`, `episode`) with `llm.episode_brief` (series context,
no overlap with the previous episode, last line teases the next). Scripts run one after another in the single worker.
`POST /api/playlists/<id>/render` renders every `script_ready` episode. `post.txt` gets "Part n/N · <series>".
Quota: a Short costs 1 request, a 5-min YouTube list about 6-8. Review the scripts (section 3) before "Render all".

## 8. Gemini free tier (the main source of slowness and failures)

- Not a trial: limits reset continuously. ~5 requests/min (rolling) and ~20/day per model, daily reset at midnight Pacific
  (~1:30 pm IST). Each model has its own quota; the app paces calls (`GEMINI_MIN_INTERVAL=13`), rotates
  `GEMINI_MODEL` + `GEMINI_FALLBACK_MODELS`, times out stuck calls after 90 s, waits on per-minute 429s, and resumes long
  scripts from `data/videos/<id>/script_partial.json` (press Retry / `POST /script/redo`).
- A long YouTube script costs 1 + chapters requests (5-9). Do not waste quota on throwaway tests; test templates without Gemini.
- The $300 Google Cloud trial does not apply to AI Studio Gemini API usage.

## 9. Known pitfalls (already fixed; do not reintroduce)

- A throwaway `genai.Client()` closes mid-request: keep the cached client in `llm._client()`.
- f-string prompts: literal braces must be doubled (`{{arts}}`), and do not nest double quotes inside them.
- Times like "12:00 PM: lunch" are split on `": "`, not `":"`.
- Long-form videos render at 24 fps; every segment (motion, AI clip, end card) must use the same fps before concat.
- Keep `data/`, `.env`, `.venv/` out of git. Do not delete user videos or brands without asking.

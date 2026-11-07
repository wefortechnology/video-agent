# Video Agent

Give it a brand and a prompt. It suggests ideas, writes a script, adds a voiceover, footage, captions, logo and an end card, and hands you a video for LinkedIn, Instagram Reels, YouTube Shorts or YouTube. It remembers each brand.

Free to run, locally, with no trial credits: Gemini writes the words, your own footage library and free stock footage (Pixabay / Pexels) supply the pictures, Kokoro (local) speaks, ffmpeg assembles. It never posts anywhere; a person reviews, approves and posts.

## Run

```bash
cd video-agent-app
./run.sh            # first run creates .venv and .env
# open http://127.0.0.1:8010
```

Edit `.env` (keys stay in this file only):

| Key | Where to get it | Needed for |
|---|---|---|
| `GEMINI_API_KEY` | aistudio.google.com/apikey | ideas, scripts, designs. Free tier works (about 5 requests/min and ~20/day per model; the app paces calls, rotates models, resumes long scripts). On a paid key set `GEMINI_MIN_INTERVAL=0`. |
| `PIXABAY_API_KEY` | pixabay.com/api/docs | stock footage |
| `PEXELS_API_KEY` | pexels.com/api (new keys were paused in Nov 2026) | stock footage (optional) |

Footage needs no key at all if you upload your own clips (Brands tab, "Your footage").

Without keys it still renders, using a template script and a branded background, so you can test the whole flow.

Requirements: Python 3.12, ffmpeg (with libass), and the Kokoro model files in `~/.video-studio/models`.

## How a video is made

1. **Brands tab:** name, colours, logo, tone, language, things to never say. Add standing facts the agent should always remember.
2. **Create tab:** pick brand, format, language, write a brief. Get 5 ideas, choose one (or skip).
3. **Script:** the agent writes scenes (voiceover, caption, footage search). You edit anything.
4. **Render:** voice + footage + captions + logo + end card (about a minute on this laptop for a 15 to 25s video).
5. **Review:** watch with sound, download, copy the post text, approve. Notes you type under "Feedback" are saved to the brand's memory and shape every future script.

## Two styles

- **Motion graphics (default):** every scene is a 2D animation rendered with HyperFrames (HTML + GSAP), the engine from the old `video-studio`.
  - **A design made for each topic** (`app/services/design.py`): with the script, Gemini designs the look for the topic: colours, background style (radial, linear, grid, dots, paper, waves, blobs, diagonal, topo, split), particles (none, dots, bokeh, sparkles, bubbles, confetti), font pair (editorial, classic, elegant, modern, tech, friendly, playful, news, condensed; Hindi headings use Rozha One, Mukta or Baloo 2), card style (shadow, glass, outline, solid), corners, title style (solid, gradient, highlight, underline) and transition (fade, slide, zoom, wipe). It starts from the closest of 14 presets (corporate, explainer, tech, health, finance, food, kids, history, nature, science, news, social impact, festive...). Colours are checked in code for readable contrast; without Gemini a preset is chosen from keywords. Pick another preset in the script editor to change the look. Each scene shifts the background slightly, and on 16:9 the headline alternates left and right.
  - **Real photos inside the design:** the `photo` animation frames a Pixabay photo (slow zoom, label) so explainers show real people and places.
  - **70 animations, never the same picture twice** (`motion.py` + `diagrams.py` + `charts.py`): festive (`diya`, `rangoli`, `sweets`, `fireworks`, `greeting`); diagrams chosen by meaning (`flow`, `steps`, `timeline`, `cycle`, `pyramid`, `hierarchy`, `matrix`, `funnel`, `venn`, `bars`, `mindmap`, `target`, `compare`, `checklist`, `icons`, `card`, `counter` with a number from the brief only); more diagrams (`iceberg`, `layers`, `puzzle`, `proscons`, `gap`, `decision`, `hexagons`, `roadmap`); data charts (`pie`, `donut`, `stackbar`, `line`, `area`, `hbars`, `gauge`, `rings`, `waffle`, `kpis`, `radar`): numbers appear only from the brief (scene `values` + `unit`), otherwise the chart is drawn as a shape without numbers and tagged Illustrative; topic visuals (`network`, `globe`, `server`, `lock`, `photo`); headline scenes (`spotlight`, `orbit`, `quote`); `chapter` cards. Common ones have alternative layouts that rotate on every repeat: flow (boxes, chevrons, winding path), checklist (rows, sticky notes, numbered tiles), compare (cards, balance, before/after), icons (row, list, triangle), network (graph, hub, chain), orbit (rings, ripples, geometric), quote (left, centred, speech bubble), photo (frame, polaroid, circle), timeline (straight, zig-zag), target (rings, summit), cycle (circle, loop track), shares (pie, donut, stacked bar), trends (line, area), bars (columns, horizontal ranking), scores (gauge, rings), timeline (+ roadmap), compare (+ pros/cons). A diagram shown in the last 6 scenes gives way to a similar one. `assign_arts` also stops any family being over-used and never shows the same family twice in a row.
  - **Layouts:** 9:16 full design; 16:9 (YouTube) headline on the left, visual on the right; 1:1 the vertical design centred.
  - **Long YouTube videos:** choose Length (Auto or 3-20 min). Gemini plans chapters first (medium depth), then writes each chapter with the outline as context. Each chapter opens with a chapter card, and the description gets YouTube chapter timestamps. Rendered at 24 fps.
  - **Sound:** procedural music bed (festive or uplift) ducked under the voice, whoosh on cuts, chime on the end card (`MUSIC=false` to turn off).
  - **Render time on this laptop (no GPU):** about 0.1 s per frame. Roughly: 30 s reel 3-4 min, 10 min YouTube 30-40 min, 20 min YouTube 60-80 min. Scenes render two at a time.
  - Needs Node 22+ and `~/.video-studio/hyperframes`. Templates and themes: `app/services/motion.py`; page shell: `app/motion/base.html`.
- **AI video clips (optional, Create tab: "AI video clips" On/Off):** with it on, the script marks 1-3 hero scenes (hook, a real-world moment, the ending) and writes a video prompt for each. Per scene the app uses, in order: a clip you uploaded for that scene (make it in the Gemini app's Videos with your Pro plan: Copy prompt, generate, download, Upload clip), then the Gemini API (`AI_VIDEO_MODELS`, only if the key has video quota), otherwise the scene stays an animation. It never fails a video; the result line says what happened, e.g. "AI clips: 1 uploaded, 1 fell back to animation (no video quota on the free tier)". Settings: `AI_VIDEO_API`, `AI_VIDEO_MODELS`, `AI_MAX_CLIPS`.
- **Stock footage:** your own clips first, then Pixabay/Pexels video or photos, chosen by tags and checked by Gemini looking at the thumbnails.

## Footage order

Per scene: 1) the brand's own uploaded clips (matched by your tags and filename), 2) Pixabay/Pexels stock, 3) a branded gradient. Own footage is reused if there are fewer clips than scenes.

## Memory

Stored in `data/app.db` (SQLite), per brand: profile, facts you add, feedback, and the titles of videos already approved (so ideas do not repeat). All of it is injected into the Gemini prompt. Personal data (emails, phone numbers, Aadhaar-like numbers, API keys) is rejected at every input.

## Layout

```
app/            FastAPI backend (config, db, pipeline, services/llm|stock|voice|render)
web/            the UI (plain HTML/JS, no build step)
assets/fonts/   Noto Sans Devanagari + Inter for captions
data/           database, logos, rendered videos (git-ignored)
```

## Formats

LinkedIn 1:1 (~40s) · Instagram Reel 9:16 (~25s) · YouTube Short 9:16 (~45s) · YouTube 16:9 (~2.5 min). Edit `app/formats.py` to change lengths.

## Not built yet

- Optional AI-generated clips (local Wan / LTX on a GPU machine) as a footage source.
- Hindi voice bake-off: Kokoro vs Chatterbox Multilingual vs Svara-TTS (Setup tab has a voice tester for Kokoro and Gemini).
- Festive templates for other festivals (Holi, Eid, Christmas...); today only Diwali has its own.
- Google Drive export.

## Tested

Rendered end to end (Hindi 9:16, English 1:1 and 9:16), with real Gemini ideas and scripts and an uploaded clip. Not yet exercised: Gemini TTS and Pixabay/Pexels downloads (no keys yet). Gemini sometimes answers 503 (busy); the app retries and falls back to other models.

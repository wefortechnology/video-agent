const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
let CFG = null, BRANDS = [], curBrand = null, curVideo = null, poll = null;

async function api(path, opts = {}) {
  const res = await fetch("/api" + path, opts.body && !(opts.body instanceof FormData)
    ? { ...opts, headers: { "Content-Type": "application/json" }, body: JSON.stringify(opts.body) } : opts);
  if (!res.ok) {
    let msg = res.statusText;
    try { const j = await res.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch {}
    throw new Error(msg);
  }
  return res.headers.get("content-type")?.includes("json") ? res.json() : res;
}
function toast(msg, err = false) {
  const t = $("#toast"); t.textContent = msg; t.className = err ? "err" : ""; t.style.display = "block";
  clearTimeout(toast.t); toast.t = setTimeout(() => (t.style.display = "none"), err ? 7000 : 3500);
}
const guard = (fn) => async (...a) => { try { await fn(...a); } catch (e) { toast(e.message, true); } };

// ---------- tabs
document.querySelectorAll("nav button").forEach((b) => b.onclick = () => {
  document.querySelectorAll("nav button").forEach((x) => x.classList.toggle("active", x === b));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.id === "tab-" + b.dataset.tab));
  if (b.dataset.tab === "library") loadLibrary();
  if (b.dataset.tab === "playlists") loadPlaylists();
  if (b.dataset.tab === "brands") renderBrands();
  if (b.dataset.tab === "setup") renderSetup();
});

// ---------- init
async function init() {
  CFG = await api("/config");
  $("#c-format").innerHTML = Object.entries(CFG.formats).map(([k, f]) => `<option value="${k}">${esc(f.label)}</option>`).join("");
  await loadBrands();
  $("#c-format").onchange = formatHint; formatHint();
  if (!CFG.motion) { $("#c-style").value = "footage"; $("#c-style").querySelector('[value="motion"]').disabled = true; }
  $("#c-lang").onchange = fillVoices; $("#c-brand").onchange = () => { const b = BRANDS.find((x) => x.id == $("#c-brand").value); if (b) { $("#c-lang").value = b.language; fillVoices(b.voice); } };
  fillVoices();
  const sel = $("#v-engine"); sel.innerHTML = Object.entries(CFG.voice_engines).map(([k, v]) => `<option value="${k}" ${v.available ? "" : "disabled"}>${k}${v.available ? "" : " (not available)"}</option>`).join("");
  sel.value = CFG.voice_engine; $("#v-lang").onchange = fillTestVoices; fillTestVoices();
}
function formatHint() {
  const k = $("#c-format").value;
  $("#c-lenwrap").classList.toggle("hidden", k !== "youtube");
  $("#c-structwrap").classList.toggle("hidden", k !== "youtube");
  $("#c-formathint").textContent = CFG.formats[k].tip + (CFG.formats[k].h > CFG.formats[k].w ? "" : " Motion graphics are designed vertical; they look best as a Reel or Short.");
}
function fillVoices(keep) {
  const l = $("#c-lang").value, vs = CFG.kokoro_voices[l] || [];
  $("#c-voice").innerHTML = `<option value="">Default</option>` + vs.map((v) => `<option>${v}</option>`).join("");
  if (typeof keep === "string") $("#c-voice").value = keep;
}
function fillTestVoices() { $("#v-voice").innerHTML = (CFG.kokoro_voices[$("#v-lang").value] || []).map((v) => `<option>${v}</option>`).join(""); }

async function loadBrands() {
  BRANDS = await api("/brands");
  const opts = BRANDS.map((b) => `<option value="${b.id}">${esc(b.name)}</option>`).join("");
  $("#c-brand").innerHTML = opts || `<option value="">Create a brand first (Brands tab)</option>`;
  $("#l-brand").innerHTML = `<option value="">All brands</option>` + opts;
  $("#p-brand").innerHTML = opts;
  const b = BRANDS[0]; if (b) { $("#c-lang").value = b.language; fillVoices(b.voice); }
}

// ---------- create: ideas
$("#c-ideas").onclick = guard(async () => {
  const body = reqBody(); $("#c-ideas").disabled = true; $("#c-ideas").textContent = "Thinking...";
  try {
    const r = await api("/ideas", { method: "POST", body: { ...body, count: 5 } });
    $("#c-ideas-card").classList.remove("hidden");
    $("#c-ideas-src").textContent = r.source === "gemini" ? "" : "Offline template ideas: add GEMINI_API_KEY in .env for real ones.";
    $("#c-ideas-list").innerHTML = r.ideas.map((i, n) => `<div class="idea"><b>${esc(i.title)}</b><small>${esc(i.angle)}</small><div>${esc(i.summary)}</div><i>“${esc(i.hook)}”</i><button class="primary" data-n="${n}">Use this idea</button></div>`).join("");
    document.querySelectorAll("#c-ideas-list button").forEach((b) => b.onclick = guard(() => startVideo(r.ideas[b.dataset.n])));
  } finally { $("#c-ideas").disabled = false; $("#c-ideas").textContent = "Suggest ideas"; }
});
$("#c-direct").onclick = guard(() => startVideo(null));
function reqBody() {
  if (!$("#c-brand").value) throw new Error("Create a brand first (Brands tab)");
  const brief = $("#c-brief").value.trim(); if (brief.length < 3) throw new Error("Write a short brief first");
  return { brand_id: +$("#c-brand").value, brief, format: $("#c-format").value, language: $("#c-lang").value,
           length_min: $("#c-format").value === "youtube" ? +$("#c-len").value : 0,
           structure: $("#c-format").value === "youtube" ? $("#c-struct").value : "" };
}
async function startVideo(idea) {
  const body = { ...reqBody(), idea, voice_engine: CFG.voice_engine, style: $("#c-style").value, use_ai: $("#c-ai").value === "1" };
  const v = await api("/videos", { method: "POST", body });
  openVideo(v.id);
}

// ---------- create: video panel
async function openVideo(id) {
  document.querySelector('nav [data-tab="create"]').click();
  $("#c-video-card").classList.remove("hidden"); $("#c-video-card").scrollIntoView({ behavior: "smooth" });
  clearInterval(poll); await refresh(id); poll = setInterval(() => refresh(id), 1500);
}
async function refresh(id) {
  const v = await api("/videos/" + id); curVideo = v;
  $("#c-video-title").textContent = v.title || "Script and video";
  $("#c-status").textContent = v.status === "failed" ? "Failed: " + v.error : v.step; $("#c-status").className = "status " + (v.status === "failed" ? "failed" : "");
  $("#c-bar").style.width = (v.status === "script_ready" || v.status === "review" || v.status === "approved" ? 100 : v.progress) + "%";
  const busy = ["queued", "scripting", "rendering"].includes(v.status);
  if (!busy) clearInterval(poll);
  renderScript(v, busy); renderResult(v);
}
function renderScript(v, busy) {
  const box = $("#c-script"); if (!v.script || v.status === "review" || v.status === "approved") { box.classList.add("hidden"); if (!v.script && v.status === "failed") showRetry(); return; }
  if (busy && box.dataset.vid == v.id && box.querySelector(":focus")) return; // don't clobber typing
  box.classList.remove("hidden"); box.dataset.vid = v.id;
  const s = v.script;
  box.innerHTML = (s.source === "offline-template" ? `<p class="hint">Offline template script: add GEMINI_API_KEY in .env for a real one.</p>` : "") +
    `<label>Title<input id="s-title" value="${esc(s.title)}"></label>` +
    (v.style === "motion" ? `<label>Look (design made for this topic${s.design && s.design.mood ? ": " + esc(s.design.mood) : ""})<select id="s-theme">${Object.entries(CFG.themes || {}).map(([k, d]) => `<option value="${k}" ${(s.design || {}).preset === k ? "selected" : ""}>${k}: ${esc(d)}</option>`).join("")}</select></label>
      <p class="hint">Keep the suggested look, or pick another preset (its colours, fonts and background replace the suggestion).</p>` : "") +
    (s.chapters && s.chapters.length ? `<p class="hint">${s.chapters.length} chapters · ${s.scenes.length} scenes · planned about ${Math.round(s.chapters.reduce((a, c) => a + (c.minutes || 0), 0))} min. Rendering takes roughly 3-4x the video length.</p>` : "") +
    s.scenes.map((sc, i) => `${sc.chapter && (i === 0 || s.scenes[i - 1].chapter !== sc.chapter) && s.chapters ? `<h3>Chapter ${sc.chapter}: ${esc((s.chapters[sc.chapter - 1] || {}).title || "")}</h3>` : ""}<div class="scene" data-i="${i}" data-ch="${sc.chapter || 0}"><div class="n">Scene ${i + 1}</div>
      ${v.style === "motion" ? `<label>Animation<select class="s-art"><option value="">Auto</option>${Object.entries(CFG.arts || {}).map(([k, d]) => `<option value="${k}" ${sc.art === k ? "selected" : ""}>${k}: ${esc(d)}</option>`).join("")}</select></label>` : ""}
      <label>Voiceover<textarea class="s-narr" rows="2">${esc(sc.narration)}</textarea></label>
      <div class="grid2"><label>${v.style === "motion" ? "Headline on screen (2-5 words)" : "On-screen caption"}<input class="s-cap" value="${esc(sc.caption)}"></label>
      <label class="${v.style === "motion" && sc.art !== "photo" ? "hidden" : ""}">${v.style === "motion" ? "Photo search (English, separated by |)" : "Footage searches (English, separated by |)"}<input class="s-q" value="${esc(sc.stock_query)}"></label>
      <label class="${v.style === "motion" && sc.art !== "photo" ? "hidden" : ""}">Must show (keywords, any one)<input class="s-m" value="${esc(sc.must_match || "")}"></label>
      <label class="${v.style === "motion" ? "" : "hidden"}">Points (checklist / card / icons, comma separated)<input class="s-pts" value="${esc((sc.points || []).join(", "))}"></label>
      <label class="${v.style === "motion" ? "" : "hidden"}">Icons (for icons: ${esc(Object.keys(CFG.icons || {}).join(", "))})<input class="s-ics" value="${esc((sc.icons || []).join(", "))}"></label>
      <label class="${v.style === "motion" ? "" : "hidden"}">Number (counter only, from your brief)<input class="s-num" value="${esc(sc.number || "")}"></label>
      <label class="${v.style === "motion" ? "" : "hidden"}">Chart values (only real numbers, comma separated, one per point)<input class="s-vals" value="${esc((sc.values || []).join(", "))}"></label>
      <label class="${v.style === "motion" ? "" : "hidden"}">Unit (%, ₹, people...)<input class="s-unit" value="${esc(sc.unit || "")}"></label></div>
      <div class="${v.use_ai ? "" : "hidden"}"><label><input type="checkbox" class="s-ai" style="width:auto;display:inline" ${sc.ai_clip ? "checked" : ""}> AI video clip for this scene</label>
        <label class="${sc.ai_clip ? "" : "hidden"}">AI video prompt (paste into the Gemini app's Videos, then upload the clip)<textarea class="s-aip" rows="3">${esc(sc.ai_prompt || "")}</textarea></label>
        <div class="row ${sc.ai_clip ? "" : "hidden"}"><button type="button" class="s-copy" data-i="${i}">Copy prompt</button>
          <label class="filebtn">${(v.clips || []).includes(i) ? "Replace clip ✓" : "Upload clip"}<input type="file" class="s-up" data-i="${i}" accept="video/*"></label></div></div></div>`).join("") +
    `<label>Call to action (end card)<input id="s-cta" value="${esc(s.cta)}"></label>
     <label>Post caption<textarea id="s-post" rows="3">${esc(s.post_caption)}</textarea></label>
     <label class="${s.pinned_comment !== undefined ? "" : "hidden"}">Comment to pin (the same question as the video's last line)<textarea id="s-pin" rows="2">${esc(s.pinned_comment || "")}</textarea></label>
     <label>Hashtags (comma separated)<input id="s-tags" value="${esc((s.hashtags || []).join(", "))}"></label>
     <div class="row"><button class="primary" id="s-render">Save and render video</button><button id="s-redo">Rewrite script</button></div>`;
  $("#s-render").disabled = busy; $("#s-redo").disabled = busy;
  document.querySelectorAll(".s-copy").forEach((b) => b.onclick = () => { const t = b.closest(".scene").querySelector(".s-aip").value; navigator.clipboard?.writeText(t); toast("Prompt copied"); });
  document.querySelectorAll(".s-up").forEach((inp) => inp.onchange = guard(async (e) => {
    const f = e.target.files[0]; if (!f) return; const fd = new FormData(); fd.append("file", f);
    toast("Uploading clip..."); await api(`/videos/${v.id}/clips/${inp.dataset.i}`, { method: "POST", body: fd }); toast("Clip attached to scene " + (+inp.dataset.i + 1)); refresh(v.id); }));
  document.querySelectorAll(".s-ai").forEach((c) => c.onchange = () => { c.closest(".scene").querySelectorAll(".s-aip, .s-copy").forEach((x) => x.closest("label, .row").classList.toggle("hidden", !c.checked)); });
  $("#s-render").onclick = guard(async () => { await api(`/videos/${v.id}/script`, { method: "PUT", body: collectScript() }); await api(`/videos/${v.id}/render`, { method: "POST" }); openVideo(v.id); });
  $("#s-redo").onclick = guard(async () => { await api(`/videos/${v.id}/script/redo`, { method: "POST" }); openVideo(v.id); });
}
function showRetry() {
  const box = $("#c-script"); box.classList.remove("hidden");
  box.innerHTML = `<button class="primary" id="s-retry">Retry</button>`;
  $("#s-retry").onclick = guard(async () => { await api(`/videos/${curVideo.id}/script/redo`, { method: "POST" }); openVideo(curVideo.id); });
}
function collectScript() {
  return {
    title: $("#s-title").value,
    design: (() => { const sel = $("#s-theme")?.value, cur = (curVideo.script || {}).design; if (!sel) return cur || null; return cur && cur.preset === sel ? cur : { preset: sel }; })(),
    scenes: [...document.querySelectorAll(".scene")].map((e) => ({ title: "", narration: e.querySelector(".s-narr").value, caption: e.querySelector(".s-cap").value, stock_query: e.querySelector(".s-q").value, must_match: e.querySelector(".s-m").value, art: e.querySelector(".s-art")?.value || "",
      points: e.querySelector(".s-pts").value.split(",").map((x) => x.trim()).filter(Boolean),
      icons: e.querySelector(".s-ics").value.split(",").map((x) => x.trim()).filter(Boolean), number: e.querySelector(".s-num").value.trim(), chapter: +e.dataset.ch || 0, ai_clip: !!e.querySelector(".s-ai")?.checked, ai_prompt: e.querySelector(".s-aip")?.value || "",
      values: e.querySelector(".s-vals").value.split(",").map((x) => parseFloat(x.replace(/[^0-9.\-]/g, ""))).filter((x) => !isNaN(x)), unit: e.querySelector(".s-unit").value })),
    cta: $("#s-cta").value, post_caption: $("#s-post").value, pinned_comment: $("#s-pin")?.value || "", hashtags: $("#s-tags").value.split(",").map((x) => x.trim().replace(/^#/, "")).filter(Boolean),
  };
}
function renderResult(v) {
  const box = $("#c-result");
  if (!["review", "approved"].includes(v.status) && !(v.status === "failed" && v.has_file)) { box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  const f = CFG.formats[v.format];
  box.innerHTML = `<div class="result"><video controls src="/api/videos/${v.id}/file?t=${Date.parse(v.updated_at)}" poster="/api/videos/${v.id}/thumb?t=${Date.parse(v.updated_at)}"></video>
    <div><p class="hint">${esc(f.label)} · ${v.style === "motion" ? "Motion graphics" : "Footage"} · ${v.language === "hi" ? "हिन्दी" : "English"} · <span class="badge ${v.status}">${v.status}</span></p>
    <label>Thumbnail</label><a href="/api/videos/${v.id}/thumb?download=true" title="Download thumbnail"><img class="thumbprev" src="/api/videos/${v.id}/thumb?t=${Date.parse(v.updated_at)}" alt="Thumbnail" style="max-width:260px;max-height:260px;border-radius:10px;display:block;margin:4px 0 10px"></a>
    <label>Post text (copy this)<textarea class="post" readonly>${esc(v.post_text)}</textarea></label>
    ${v.pinned_comment ? `<label>Comment to pin (post it yourself right after publishing, then pin it)<textarea class="post" readonly rows="2">${esc(v.pinned_comment)}</textarea></label>` : ""}
    <div class="row"><a href="/api/videos/${v.id}/file?download=true"><button class="primary">Download MP4</button></a>
    <a href="/api/videos/${v.id}/voice-only"><button title="Add a licensed trending song in YouTube Shorts / Instagram">Voice only (no music)</button></a>
    <a href="/api/videos/${v.id}/thumb?download=true"><button>Thumbnail</button></a>
    ${v.status === "review" ? `<button id="r-approve">Approve</button>` : ""}<button id="r-edit">Edit script</button></div>
    <p class="hint">Watch it with sound before approving. This tool never posts anywhere; you post it yourself.</p>
    <label>Feedback for next time (saved to this brand's memory)<input id="r-fb" placeholder="e.g. Captions too fast; use warmer footage"></label>
    <button id="r-fbsave">Save feedback</button></div></div>`;
  const ap = $("#r-approve"); if (ap) ap.onclick = guard(async () => { await api(`/videos/${v.id}/approve`, { method: "POST" }); toast("Approved and remembered"); refresh(v.id); });
  $("#r-edit").onclick = guard(async () => { await api(`/videos/${v.id}/script`, { method: "PUT", body: { ...v.script, scenes: v.script.scenes } }); refresh(v.id); });
  $("#r-fbsave").onclick = guard(async () => { await api(`/videos/${v.id}/feedback`, { method: "POST", body: { note: $("#r-fb").value } }); $("#r-fb").value = ""; toast("Saved to brand memory"); });
}

// ---------- library
$("#l-brand").onchange = loadLibrary;
async function loadLibrary() {
  const vs = await api("/videos" + ($("#l-brand").value ? "?brand_id=" + $("#l-brand").value : ""));
  $("#l-list").innerHTML = vs.length ? vs.map((v) => `<div class="lcard" data-id="${v.id}">${["review", "approved"].includes(v.status) ? `<img src="/api/videos/${v.id}/thumb?t=${Date.parse(v.updated_at)}" alt="">` : `<div class="ph"></div>`}
    <div><b>${esc(v.title || "Untitled")}</b><br><small>${esc(CFG.formats[v.format]?.label || v.format)} · ${v.created_at.slice(0, 10)}</small><br><span class="badge ${v.status}">${v.status}</span></div></div>`).join("") : `<p class="hint">No videos yet.</p>`;
  document.querySelectorAll(".lcard").forEach((c) => c.onclick = () => openVideo(+c.dataset.id));
}

// ---------- brands
$("#b-new").onclick = () => { curBrand = null; fillBrandForm({}); };
function renderBrands() {
  $("#b-list").innerHTML = BRANDS.map((b) => `<button data-id="${b.id}" class="${curBrand?.id === b.id ? "sel" : ""}">${esc(b.name)}</button>`).join("") || `<p class="hint">No brands yet.</p>`;
  document.querySelectorAll("#b-list button").forEach((x) => x.onclick = () => { curBrand = BRANDS.find((b) => b.id == x.dataset.id); fillBrandForm(curBrand); renderBrands(); });
  if (!curBrand && BRANDS[0]) { curBrand = BRANDS[0]; fillBrandForm(curBrand); renderBrands(); } else if (!curBrand) fillBrandForm({});
}
function fillBrandForm(b) {
  $("#b-title").textContent = b.id ? "Edit: " + b.name : "New brand";
  const set = { name: b.name, industry: b.industry, lang: b.language || "en", tone: b.tone || "warm, clear, professional", primary: b.primary_color || "#1F4E79", accent: b.accent_color || "#F2A900", about: b.about, audience: b.audience, avoid: b.avoid, cta: b.cta };
  for (const [k, v] of Object.entries(set)) $("#b-" + k).value = v ?? "";
  $("#b-del").classList.toggle("hidden", !b.id); $("#b-memory").classList.toggle("hidden", !b.id); $("#b-footage").classList.toggle("hidden", !b.id);
  if (b.id) { loadMemories(); loadFootage(); }
}
function brandBody() {
  return { name: $("#b-name").value.trim(), industry: $("#b-industry").value, about: $("#b-about").value, audience: $("#b-audience").value, tone: $("#b-tone").value, language: $("#b-lang").value, primary_color: $("#b-primary").value, accent_color: $("#b-accent").value, avoid: $("#b-avoid").value, cta: $("#b-cta").value };
}
$("#b-save").onclick = guard(async () => {
  const body = brandBody(); if (!body.name) throw new Error("Brand name is required");
  const saved = curBrand?.id ? await api("/brands/" + curBrand.id, { method: "PUT", body }) : await api("/brands", { method: "POST", body });
  await loadBrands(); curBrand = BRANDS.find((b) => b.id === saved.id); renderBrands(); toast("Brand saved");
});
$("#b-del").onclick = guard(async () => {
  if (!confirm(`Delete "${curBrand.name}" with its memory and all its videos?`)) return;
  await api("/brands/" + curBrand.id, { method: "DELETE" }); curBrand = null; await loadBrands(); renderBrands();
});
$("#b-logo").onchange = guard(async (e) => {
  if (!curBrand?.id) throw new Error("Save the brand first, then upload the logo");
  const fd = new FormData(); fd.append("file", e.target.files[0]);
  await api(`/brands/${curBrand.id}/logo`, { method: "POST", body: fd }); toast("Logo uploaded"); await loadBrands();
});
async function loadMemories() {
  const ms = await api(`/brands/${curBrand.id}/memories`);
  $("#m-list").innerHTML = ms.map((m) => `<li><div><span class="k">${m.kind}</span>${esc(m.text)}</div><button data-id="${m.id}" title="Forget">✕</button></li>`).join("") || `<li class="hint">Nothing yet.</li>`;
  document.querySelectorAll("#m-list button").forEach((b) => b.onclick = guard(async () => { await api("/memories/" + b.dataset.id, { method: "DELETE" }); loadMemories(); }));
}
$("#m-add").onclick = guard(async () => { await api(`/brands/${curBrand.id}/memories`, { method: "POST", body: { kind: "fact", text: $("#m-text").value } }); $("#m-text").value = ""; loadMemories(); });

async function loadFootage() {
  const fs = await api(`/brands/${curBrand.id}/footage`);
  $("#f-list").innerHTML = fs.map((f) => `<li><div><span class="k">${Math.round(f.duration)}s</span>${esc(f.filename)} <small class="hint">${esc(f.tags || "no tags")}</small></div><button data-id="${f.id}" title="Remove">✕</button></li>`).join("") || `<li class="hint">No clips yet.</li>`;
  document.querySelectorAll("#f-list button").forEach((b) => b.onclick = guard(async () => { await api("/footage/" + b.dataset.id, { method: "DELETE" }); loadFootage(); }));
}
$("#f-file").onchange = guard(async (e) => {
  const file = e.target.files[0]; if (!file) return;
  const fd = new FormData(); fd.append("file", file); fd.append("tags", $("#f-tags").value);
  toast("Uploading " + file.name + "..."); await api(`/brands/${curBrand.id}/footage`, { method: "POST", body: fd });
  e.target.value = ""; $("#f-tags").value = ""; toast("Clip added"); loadFootage();
});

// ---------- setup
function renderSetup() {
  const row = (name, ok, note = "") => `<div class="srow"><span>${name}</span><span class="${ok ? "ok" : "no"}">${ok ? "Ready" : "Missing"} <small class="hint">${esc(note)}</small></span></div>`;
  $("#s-list").innerHTML = row("Gemini (ideas and scripts)", CFG.gemini, CFG.gemini ? CFG.gemini_model : "add GEMINI_API_KEY to .env") +
    row("Pexels footage", CFG.pexels, "add PEXELS_API_KEY to .env") + row("Pixabay footage (optional)", CFG.pixabay, "add PIXABAY_API_KEY to .env") +
    Object.entries(CFG.voice_engines).map(([k, v]) => row("Voice: " + k, v.available, v.note || v.cost)).join("");
}
$("#v-go").onclick = guard(async () => {
  $("#v-msg").textContent = "Generating..."; const t = Date.now();
  try {
    const res = await api("/voice/test", { method: "POST", body: { text: $("#v-text").value, language: $("#v-lang").value, engine: $("#v-engine").value, voice: $("#v-voice").value } });
    const a = $("#v-audio"); a.src = URL.createObjectURL(await res.blob()); a.classList.remove("hidden"); a.play();
    $("#v-msg").textContent = `Done in ${((Date.now() - t) / 1000).toFixed(1)}s`;
  } catch (e) { $("#v-msg").textContent = ""; throw e; }
});

guard(init)();

// ---------- playlists
$("#p-format").onchange = () => $("#p-ytwrap").classList.toggle("hidden", $("#p-format").value !== "youtube");
$("#p-go").onclick = guard(async () => {
  if (!$("#p-brand").value) throw new Error("Create a brand first (Brands tab)");
  const topic = $("#p-topic").value.trim(); if (topic.length < 3) throw new Error("Write the series topic first");
  const [len, structure] = $("#p-yt").value.split("|"), yt = $("#p-format").value === "youtube";
  const btn = $("#p-go"); btn.disabled = true; btn.textContent = "Planning the episodes...";
  try {
    await api("/playlists", { method: "POST", body: { brand_id: +$("#p-brand").value, topic, format: $("#p-format").value, language: $("#p-lang").value,
      style: $("#p-style").value, count: +$("#p-count").value, length_min: yt ? +len : 0, structure: yt ? structure : "", voice_engine: CFG.voice_engine } });
    toast("Playlist planned: scripts are being written one after another"); $("#p-topic").value = ""; loadPlaylists();
  } finally { btn.disabled = false; btn.textContent = "Plan playlist and write scripts"; }
});
let ppoll = null;
async function loadPlaylists() {
  const ps = await api("/playlists");
  $("#p-list").innerHTML = ps.length ? ps.map((p) => {
    const ready = p.videos.filter((v) => v.status === "script_ready").length;
    return `<div class="card"><div class="row between"><h2>${esc(p.title)}</h2><span class="badge">${esc((p.plan || {}).series_tag || "")}</span></div>
      <p class="hint">${esc((p.plan || {}).description || "")} · ${esc(CFG.formats[p.format]?.label || p.format)} · ${p.language === "hi" ? "हिन्दी" : "English"}${p.length_min ? " · about " + p.length_min + " min" : ""}${p.structure === "list" ? " · numbered list" : ""}</p>
      <table class="eps">${p.videos.map((v) => `<tr><td>${v.episode}.</td><td>${esc(v.title)}</td>
        <td><span class="badge ${v.status}">${esc(v.status)}</span> <small class="hint">${esc(v.status === "failed" ? v.error.slice(0, 120) : v.step)}</small></td>
        <td><button data-open="${v.id}">Open</button></td></tr>`).join("")}</table>
      <div class="row"><button class="primary" data-render="${p.id}" ${ready ? "" : "disabled"}>Render all ready (${ready})</button></div></div>`;
  }).join("") : `<p class="hint">No playlists yet.</p>`;
  document.querySelectorAll("[data-open]").forEach((b) => b.onclick = () => openVideo(+b.dataset.open));
  document.querySelectorAll("[data-render]").forEach((b) => b.onclick = guard(async () => {
    const r = await api(`/playlists/${b.dataset.render}/render`, { method: "POST" }); toast(`Rendering ${r.started.length} episode(s), one after another`); loadPlaylists(); }));
  clearTimeout(ppoll);
  const busy = ps.some((p) => p.videos.some((v) => ["queued", "scripting", "rendering"].includes(v.status)));
  if (busy && $("#tab-playlists").classList.contains("active")) ppoll = setTimeout(loadPlaylists, 4000);
}

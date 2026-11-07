/* VeoDrive Video Studio · HyperFrames scene kit.
 *
 * Every scene composition includes, in order:
 *   <script src="cues.js"></script>   (written by render-scene.sh from narration timing)
 *   <script src="gsap.min.js"></script>
 *   <script src="kit.js"></script>
 * then builds ONE paused timeline and calls EZ.finish(tl, {...}).
 *
 * Timing comes from the narration: EZ.b(3) is when beat 3 starts (seconds,
 * scene-local), EZ.e(3) when it ends, EZ.at(3, 0.6) 60% through beat 3.
 * Never hard-code times for things the voice talks about.
 * Determinism: no Math.random()/Date.now() (HyperFrames rule); use EZ.rand().
 */
(function () {
  var C = window.CUES || {duration: 10, beats: [], series: "", tag: false};
  function beat(n) {
    var b = C.beats[n - 1];
    if (!b) throw new Error("No beat " + n + " (scene has " + C.beats.length + ")");
    return b;
  }
  var seed = 7;

  window.EZ = {
    cues: C,
    duration: C.duration,
    /** Beat n (1-based) start / end, and a point a fraction f through it. */
    b: function (n) { return beat(n).start; },
    e: function (n) { return beat(n).end; },
    at: function (n, f) { var x = beat(n); return x.start + (f || 0) * (x.end - x.start); },
    /** Deterministic pseudo-random in [0,1). */
    rand: function () { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; },
    $: function (sel) { return document.querySelector(sel); },
    $$: function (sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); },

    /** Roll a number in el from `from` to `to`. fmt optional (n) => string. */
    count: function (tl, el, from, to, t, dur, fmt) {
      var o = {v: from};
      el = typeof el === "string" ? document.querySelector(el) : el;
      fmt = fmt || function (n) { return Math.round(n).toLocaleString("en-IN"); };
      el.textContent = fmt(from);
      tl.to(o, {v: to, duration: dur || 1.2, ease: "power2.out", onUpdate: function () { el.textContent = fmt(o.v); }}, t);
    },

    /** Reveal text character by character (typewriter) at t over dur seconds. */
    type: function (tl, el, t, dur) {
      el = typeof el === "string" ? document.querySelector(el) : el;
      var full = el.textContent, o = {n: 0};
      el.textContent = "";
      tl.set(el, {opacity: 1}, t);
      tl.to(o, {n: full.length, duration: dur || full.length * 0.035, ease: "none",
        onUpdate: function () { el.textContent = full.slice(0, Math.round(o.n)); }}, t);
    },

    /** Fade + rise in (the house reveal). */
    rise: function (tl, targets, t, opts) {
      opts = opts || {};
      tl.fromTo(targets, {opacity: 0, y: opts.y == null ? 30 : opts.y},
        {opacity: 1, y: 0, duration: opts.d || 0.7, ease: "power3.out", stagger: opts.stagger || 0}, t);
    },

    /** Pop in with a gentle overshoot (for chips, tokens, numbers). */
    pop: function (tl, targets, t, opts) {
      opts = opts || {};
      tl.fromTo(targets, {opacity: 0, scale: 0.6}, {opacity: 1, scale: 1, duration: opts.d || 0.45,
        ease: "back.out(2)", stagger: opts.stagger || 0}, t);
    },

    /** Draw a strike-through: element must contain a .strike-line child. */
    strike: function (tl, el, t) {
      var line = (typeof el === "string" ? document.querySelector(el) : el).querySelector(".strike-line");
      tl.fromTo(line, {scaleX: 0}, {scaleX: 1, duration: 0.45, ease: "power2.inOut"}, t);
    },

    /** Gentle attention pulse. */
    pulse: function (tl, targets, t, amount) {
      tl.to(targets, {scale: amount || 1.06, duration: 0.18, ease: "sine.out", yoyo: true, repeat: 1}, t);
    },

    /** Horizontal shake, for contradictions. */
    shake: function (tl, targets, t) {
      tl.to(targets, {keyframes: [{x: -10}, {x: 10}, {x: -6}, {x: 0}], duration: 0.32, ease: "none"}, t);
    },

    /**
     * Fly a token element from (x0,y0) to (x1,y1) on a gentle arc, popping in
     * at the start and landing with a small squash. Coordinates are px in the
     * 1920x1080 frame (token's top-left). Returns landing time.
     */
    fly: function (tl, el, x0, y0, x1, y1, t, dur, lift) {
      dur = dur || 0.9;
      var mid = {x: (x0 + x1) / 2, y: Math.min(y0, y1) - (lift == null ? 120 : lift)};
      tl.set(el, {x: x0, y: y0, left: 0, top: 0, opacity: 0, scale: 0.7}, 0);
      tl.to(el, {opacity: 1, scale: 1, duration: 0.18, ease: "power1.out"}, t);
      tl.to(el, {keyframes: {x: [x0, mid.x, x1], y: [y0, mid.y, y1], easeEach: "sine.inOut"}, duration: dur, ease: "power1.inOut"}, t);
      tl.to(el, {scale: 0.85, duration: 0.08, yoyo: true, repeat: 1}, t + dur - 0.04);
      return t + dur;
    },

    /**
     * Options: {tag: bool (ILLUSTRATIVE DATA), seriesAt: seconds, series: false}.
     * Add standard chrome (series label, optional ILLUSTRATIVE DATA tag,
     * burned-in captions from narration timing), fade the scene in/out,
     * and register the timeline with HyperFrames.
     */
    finish: function (tl, opts) {
      opts = opts || {};
      var root = document.getElementById("root");
      var id = root.getAttribute("data-composition-id");
      if (C.series && opts.series !== false) {
        var s = document.createElement("div"); s.id = "ez-series"; s.textContent = C.series; root.appendChild(s);
        // seriesAt: delay the label (e.g. until a dark opening has faded to cream).
        if (opts.seriesAt) { gsap.set(s, {opacity: 0}); tl.to(s, {opacity: 0.8, duration: 0.5}, opts.seriesAt); }
      }
      if (opts.tag) {
        var g = document.createElement("div"); g.id = "ez-tag"; g.textContent = "ILLUSTRATIVE DATA"; root.appendChild(g);
      }
      if (C.captions !== false) {
        var cap = document.createElement("div"); cap.id = "ez-caption"; root.appendChild(cap);
        var chunks = [];
        C.beats.forEach(function (b) { (b.captions || []).forEach(function (c) { chunks.push(c); }); });
        var ACT = C.capact || "#FFD54A", ACTFG = C.capactfg || "#111111", FG = C.capfg || "#ffffff";
        chunks.forEach(function (c, i) {
          // one line per chunk; the word being spoken is highlighted (karaoke style)
          var line = document.createElement("div"); line.className = "ez-cl";
          var words = (c.words && c.words.length) ? c.words : [{w: c.text, s: c.start, e: c.end}];
          words.forEach(function (w, k) {
            var sp = document.createElement("span"); sp.className = "ez-w"; sp.textContent = w.w; line.appendChild(sp);
            if (k < words.length - 1) line.appendChild(document.createTextNode(" "));
            tl.set(sp, {backgroundColor: ACT, color: ACTFG}, w.s);
            tl.set(sp, {backgroundColor: "rgba(0,0,0,0)", color: FG}, w.e);
          });
          cap.appendChild(line);
          gsap.set(line, {display: "none"});
          var next = chunks[i + 1];
          tl.set(line, {display: "block"}, c.start);
          tl.set(line, {display: "none"}, next ? next.start : c.end + 0.05);
          tl.set(cap, {opacity: 1}, c.start);
          if (!next || next.start - c.end > 0.25) tl.set(cap, {opacity: 0}, c.end);
        });
      }
      // Scene fade in/out on a constant cream background, so cuts feel seamless.
      var stage = document.getElementById("stage") || root;
      tl.fromTo(stage, {opacity: 0}, {opacity: 1, duration: 0.25}, 0);
      tl.to(stage, {opacity: 0, duration: 0.2}, C.duration - 0.2);
      tl.set({}, {}, C.duration); // pin timeline length to the scene duration
      window.__timelines = window.__timelines || {};
      window.__timelines[id] = tl;
    }
  };
})();

(function () {
  var box = document.getElementById("cmp");
  if (!box) return;
  var range = document.getElementById("cmp-range");
  var stills = document.getElementById("cmp-stills");
  var tag = document.getElementById("cmp-tag");
  var group = document.querySelector(".levels");
  var stat = document.getElementById("cmp-stat");
  var capFt = document.getElementById("cmp-cap-ft");
  var capPct = document.getElementById("cmp-cap-pct");
  var playBtn = document.getElementById("cmp-play");
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var levels = [], landmarks = [], current = null, todayKm2 = null, version = "";

  function src(name) { return "figures/compare/" + name + (version ? "?v=" + version : ""); }
  function file(ft) { return src(ft === 0 ? "today.jpg" : ft + "ft.jpg"); }
  function byFt(ft) { return levels.filter(function (l) { return l.ft === ft; })[0]; }
  function esc(t) { var d = document.createElement("span"); d.textContent = t; return d.innerHTML; }
  function altFor(ft) {
    return ft === 0 ? "The old town today, dry streets between white buildings"
      : "The old town at +" + ft + " ft: aqua water between white buildings, landmarks in red";
  }

  // swap a still: the new image fades in over the old one once it has loaded
  function fadeTo(holder, url, alt) {
    holder.dataset.want = url;
    var on = holder.querySelector("img.on:last-child");
    if (on && on.dataset.url === url) return;
    var img = new Image();
    img.alt = alt;
    img.draggable = false;
    img.dataset.url = url;
    img.onload = function () {
      if (holder.dataset.want !== url) return;  // a newer level was asked for meanwhile
      holder.append(img);
      img.getBoundingClientRect();  // commit opacity 0 so the fade runs
      img.classList.add("on");
      setTimeout(function () {
        if (holder.dataset.want !== url) return;
        holder.querySelectorAll("img").forEach(function (o) { if (o !== img) o.remove(); });
      }, reduce ? 0 : 500);
    };
    img.src = url;
  }

  // ---- drag to compare ----
  function todayText() {
    return "<b>Today</b> at mean higher high water" +
      (todayKm2 == null ? "" : ", " + todayKm2.toFixed(2) + " km² of city land, mostly tidal marsh, is already under water");
  }

  function levelText() {
    var p = current.pct == null ? "" : current.pct.toFixed(1) + "%";
    return "<b>" + p + "</b> of the city's land newly under water at +" + current.ft + " ft";
  }

  function describe() {
    // the side that fills more of the frame is described; near the middle, both are
    var pos = Number(range.value);
    if (!current || pos > 60) stat.innerHTML = todayText();
    else if (pos < 40) stat.innerHTML = levelText();
    else stat.innerHTML = todayText() + "<br>" + levelText();
  }

  function move() { box.style.setProperty("--pos", range.value + "%"); describe(); }
  range.addEventListener("input", move);
  box.style.setProperty("--pos", range.value + "%");

  var rows = Array.prototype.slice.call(document.querySelectorAll(".gauge .row"));

  function show(level) {
    fadeTo(stills, file(level.ft), altFor(level.ft));
    current = level;
    tag.textContent = "+" + level.ft + " FT";
    capFt.textContent = "+" + level.ft + " ft";
    capPct.textContent = level.pct == null ? "" : level.pct.toFixed(1) + "% of the city's land newly under water";
    describe();
    group.querySelectorAll("button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(Number(b.dataset.ft) === level.ft));
    });
    rows.forEach(function (r) { r.classList.toggle("on", Number(r.dataset.ft) === level.ft); });
  }

  // ---- play: the water rises a foot at a time on the right of the divider ----
  var timer = null;
  var playIcon = playBtn.querySelector("path"), playLabel = playBtn.querySelector("span");
  var PLAY = "M1 0l9 5-9 5z", PAUSE = "M1 0h3v10H1zM6 0h3v10H6z";

  function idle(label) {
    clearTimeout(timer);
    timer = null;
    playBtn.setAttribute("aria-pressed", "false");
    playIcon.setAttribute("d", PLAY);
    playLabel.textContent = label || "Play 1–9 ft";
  }

  function slideTo(target) {
    // move the divider so the flooded side fills most of the frame
    var from = Number(range.value);
    if (reduce) { range.value = target; move(); return; }
    var t0 = Date.now();
    (function frame() {
      var k = Math.min(1, (Date.now() - t0) / 500), e = 1 - Math.pow(1 - k, 3);
      range.value = from + (target - from) * e;
      move();
      if (k < 1) setTimeout(frame, 16);
    })();
  }

  function play() {
    if (!levels.length) return;
    levels.forEach(function (l) { new Image().src = file(l.ft); });
    if (Number(range.value) > 30) slideTo(18);
    playBtn.setAttribute("aria-pressed", "true");
    playIcon.setAttribute("d", PAUSE);
    playLabel.textContent = "Pause";
    var i = 0;
    (function tick() {
      show(levels[i]);
      i += 1;
      if (i < levels.length) timer = setTimeout(tick, 1100);
      else idle("Replay 1–9 ft");
    })();
  }

  playBtn.addEventListener("click", function () { if (timer) idle(); else play(); });

  function build() {
    levels.forEach(function (level) {
      var b = document.createElement("button");
      b.type = "button";
      b.id = "cmp-level-" + level.ft;
      b.dataset.ft = level.ft;
      b.textContent = "+" + level.ft + (levels.length > 6 ? "" : " ft");
      b.setAttribute("aria-label", "+" + level.ft + " ft");
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () { idle(); show(level); window.slrHash.set("ft", level.ft); });
      b.addEventListener("pointerenter", function () { new Image().src = file(level.ft); });
      group.append(b);
    });
    if (levels.length > 6) {
      var unit = document.createElement("span");
      unit.className = "unit";
      unit.textContent = "ft";
      group.append(unit);
    }
    show(byFt(7) || levels[levels.length - 1]);
    var asked = Number(window.slrHash.get().ft);
    if (byFt(asked)) window.slrShow(asked);  // a shared link opens on its level
  }

  // shareable state in the URL: #ft=5 (comparison level), #spot=fx,fy (map pin), #water=4 (plan view)
  window.slrHash = {
    keys: ["ft", "spot", "water"],
    get: function () {
      var o = {}, keys = this.keys;
      location.hash.replace(/^#/, "").split("&").forEach(function (kv) {
        var p = kv.split("=");
        if (p.length === 2 && keys.indexOf(p[0]) >= 0) o[p[0]] = decodeURIComponent(p[1]);
      });
      return o;
    },
    set: function (k, v) {
      var o = this.get();
      if (v == null) delete o[k]; else o[k] = String(v);
      var s = this.keys.filter(function (key) { return key in o; }).map(function (key) { return key + "=" + o[key]; }).join("&");
      history.replaceState(null, "", s ? "#" + s : location.pathname + location.search);
    }
  };

  // ---- hero: the old town floods behind the title, a foot at a time ----
  function hero() {
    var holder = document.getElementById("hero-stills");
    if (!holder) return;
    var badge = document.getElementById("hero-badge");
    var ftEl = document.getElementById("hero-ft"), pctEl = document.getElementById("hero-pct");
    var seq = [0].concat(levels.map(function (l) { return l.ft; }));
    function paint(f) {
      fadeTo(holder, file(f), "");
      var l = byFt(f);
      ftEl.textContent = f === 0 ? "Today" : "+" + f + " ft";
      pctEl.textContent = f === 0 ? "the old town at today's high tide"
        : l && l.pct != null ? l.pct.toFixed(1) + "% of the city's land newly under water" : "";
      badge.hidden = false;
    }
    if (reduce) { paint(seq[seq.length - 1]); return; }
    var i = 0, timer = null, visible = true;
    function tick() {
      paint(seq[i]);
      var hold = seq[i] === 0 ? 500 : i === seq.length - 1 ? 4500 : 950;  // move at once, linger on +9 ft
      i = (i + 1) % seq.length;
      timer = setTimeout(function () { timer = null; if (visible && !document.hidden) tick(); }, hold);
    }
    new IntersectionObserver(function (es) {
      visible = es[0].isIntersecting;
      if (visible && !timer) tick();
    }).observe(holder);
    document.addEventListener("visibilitychange", function () { if (!document.hidden && visible && !timer) tick(); });
  }

  // other sections (gauge, years, map, landmark cards) open a level here
  window.slrShow = function (ft) {
    var level = byFt(ft);
    if (!level) return;
    idle();
    show(level);
    window.slrHash.set("ft", ft);
    box.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
  };

  // ---- landmark rings on the picture; each opens its card (window.slrCard, below) ----
  function hotspots() {
    var layer = document.createElement("div");
    layer.className = "hotspots";
    landmarks.forEach(function (m) {
      if (m.fx == null) return;
      var b = document.createElement("button");
      b.type = "button";
      b.className = "hot";
      b.id = "hot-" + m.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      b.style.left = m.fx * 100 + "%";
      b.style.top = m.fy * 100 + "%";
      b.title = m.name;
      b.setAttribute("aria-label", m.name + ": when the water reaches it");
      b.addEventListener("click", function () { if (window.slrCard) window.slrCard(box, m, m.fx, m.fy); });
      layer.append(b);
    });
    box.append(layer);
  }

  // ---- the gauge rows open their level in the comparison ----
  rows.forEach(function (row) {
    var cell = row.querySelector(".lvl");
    var ft = parseInt(cell.textContent, 10);
    row.dataset.ft = ft;
    var b = document.createElement("button");
    b.type = "button";
    b.id = "gauge-level-" + ft;
    b.textContent = cell.textContent;
    b.setAttribute("aria-label", "Show +" + ft + " ft in the comparison");
    cell.textContent = "";
    cell.append(b);
    row.addEventListener("click", function () { window.slrShow(ft); });
  });

  // ---- step through the rise: Next / Back, the level timeline, arrow keys or a swipe ----
  function buildStory() {
    var section = document.getElementById("story");
    var holder = document.getElementById("story-stills");
    var fill = document.getElementById("story-fill");
    var mark = document.getElementById("story-mark");
    var card = document.getElementById("story-card");
    var count = document.getElementById("story-count");
    var prevBtn = document.getElementById("story-prev");
    var nextBtn = document.getElementById("story-next");
    var dots = document.getElementById("story-dots");
    var frame = section.querySelector(".story-frame");
    if (!levels.length) return;
    var top = levels[levels.length - 1].ft;
    var steps = [0].concat(levels.filter(function (l) { return l.ft % 2 === 1; }).map(function (l) { return l.ft; }));

    function em(m) { return "<em>" + esc(m.name) + "</em>"; }
    function since(level, ft) { return level < ft ? " (from +" + level + " ft)" : ""; }
    function joined(list) {
      return list.length < 2 ? list.join("") : list.slice(0, -1).join(", ") + " and " + list[list.length - 1];
    }

    // what changes between the previous step and this one: the sea reaching a landmark, or
    // low-lying ground there flooding while it is still cut off from the sea (NOAA's low class)
    function events(prev, ft) {
      var out = [];
      var sea = landmarks.filter(function (m) { return m.sea_at != null && m.sea_at > prev && m.sea_at <= ft; });
      var low = landmarks.filter(function (m) {
        return m.floods_at != null && m.floods_at > prev && m.floods_at <= ft && (m.sea_at == null || m.sea_at > ft);
      });
      if (sea.length) out.push("The sea reaches " + joined(sea.map(function (m) { return em(m) + since(m.sea_at, ft); })) + ".");
      if (low.length) {
        out.push("Low-lying ground at " + joined(low.map(function (m) { return em(m) + since(m.floods_at, ft); })) +
          " is under water, not yet connected to the sea.");
      }
      return out;
    }

    var cards = steps.map(function (ft, i) {
      var lv = ft === 0 ? "Today" : "+" + ft + " ft";
      var big = ft === 0
        ? "<b>" + (todayKm2 == null ? "" : todayKm2.toFixed(2) + " km²") + "</b> of city land, mostly tidal marsh, already under water at mean higher high water"
        : "<b>" + byFt(ft).pct.toFixed(1) + "%</b> of the city's land newly under water";
      var ev = ft === 0 ? [] : events(steps[i - 1], ft);
      if (!ev.length) ev.push(ft === 0 ? "None of the landmarks in view is wet yet." : "No new landmark in view is reached.");
      if (i === steps.length - 1) {
        var dry = landmarks.filter(function (m) { return m.floods_at == null; });
        if (dry.length) ev.push("Still dry at +" + ft + " ft: " + joined(dry.map(em)) + ".");
      }
      return '<span class="lv">' + lv + '</span><span class="big">' + big + "</span>" +
        ev.map(function (t) { return '<span class="reach">' + t + "</span>"; }).join("");
    });

    steps.forEach(function (ft, i) {
      var b = document.createElement("button");
      b.type = "button";
      b.id = "story-dot-" + ft;
      b.textContent = ft === 0 ? "Today" : "+" + ft;
      b.setAttribute("aria-label", ft === 0 ? "Today" : "+" + ft + " ft");
      b.addEventListener("click", function () { go(i); });
      dots.append(b);
    });

    var at = 0;
    function go(i) {
      at = Math.max(0, Math.min(steps.length - 1, i));
      var ft = steps[at];
      card.innerHTML = cards[at];
      card.classList.remove("in");
      card.getBoundingClientRect();  // restart the card's entrance
      card.classList.add("in");
      fadeTo(holder, file(ft), altFor(ft));
      var h = (ft / top) * 100 + "%";
      fill.style.height = h;
      mark.style.bottom = h;
      mark.textContent = ft === 0 ? "Today" : "+" + ft + " ft";
      count.textContent = "Step " + (at + 1) + " of " + steps.length;
      prevBtn.disabled = at === 0;
      var next = steps[at + 1];
      nextBtn.querySelector("span").textContent = next == null ? "Start again" : "Raise to +" + next + " ft";
      dots.querySelectorAll("button").forEach(function (b, k) {
        b.classList.toggle("done", k < at);
        b.setAttribute("aria-current", k === at ? "step" : "false");
      });
      dots.style.setProperty("--done", (at / (steps.length - 1)) * 100 + "%");
      if (next != null) new Image().src = file(next);
    }

    nextBtn.addEventListener("click", function () { go(at === steps.length - 1 ? 0 : at + 1); });
    prevBtn.addEventListener("click", function () { go(at - 1); });
    section.addEventListener("keydown", function (e) {
      if (e.target.closest && e.target.closest("input, textarea")) return;
      if (e.key === "ArrowRight") { go(at + 1); e.preventDefault(); }
      if (e.key === "ArrowLeft") { go(at - 1); e.preventDefault(); }
    });
    var x0 = null;
    frame.addEventListener("pointerdown", function (e) { x0 = e.clientX; });
    frame.addEventListener("pointerup", function (e) {
      if (x0 == null) return;
      var dx = e.clientX - x0;
      x0 = null;
      if (Math.abs(dx) > 40) go(at + (dx < 0 ? 1 : -1));
      else go(at === steps.length - 1 ? 0 : at + 1);  // a tap on the picture moves on too
    });
    section.hidden = false;
    go(0);
  }

  // numbers come from levels.json (written by make covers from scripts/covers/every_foot.py,
  // whose odd levels equal outputs/land_loss.csv)
  fetch("figures/compare/levels.json", { cache: "no-cache" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (data) {
      todayKm2 = data.today_km2;
      version = data.version || "";
      levels = data.levels;
      landmarks = data.landmarks || [];
      box.querySelector(".before").src = src("today.jpg");
      build();
      hotspots();
      hero();
      buildStory();
    })
    .catch(function () {
      levels = [1, 3, 5, 7, 9].map(function (ft) { return { ft: ft, pct: null }; });
      build();
    });
})();

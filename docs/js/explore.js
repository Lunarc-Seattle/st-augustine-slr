// Landmark cards, tap-anywhere map, guess-first, scenario years and storms.
// Every number comes from a JSON file written by make covers; nothing here is typed in by hand.
(function () {
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var NS = "http://www.w3.org/2000/svg";
  function esc(t) { var d = document.createElement("span"); d.textContent = t; return d.innerHTML; }
  function getJSON(url) {
    return fetch(url, { cache: "no-cache" }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }
  function svg(tag, attrs, parent) {
    var n = document.createElementNS(NS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.append(n);
    return n;
  }
  function show(ft) { if (window.slrShow) window.slrShow(ft); }

  // ---- landmark cards (Library of Congress photos frozen in data/frozen/loc, see SOURCES.md) ----
  var PHOTOS = {
    "Castillo de San Marcos": {
      src: "figures/landmarks/castillo.jpg", url: "https://www.loc.gov/item/2020720780/",
      alt: "The coquina walls and a corner bastion of the Castillo de San Marcos"
    },
    "Plaza de la Constitución": {
      src: "figures/landmarks/plaza.jpg", url: "https://www.loc.gov/item/2020720801/",
      alt: "The 1813 Constitution Monument under live oaks in the Plaza de la Constitución"
    },
    "Ponce de León landing, 1513": {
      src: "figures/landmarks/ponce.jpg", url: "https://www.loc.gov/item/2020720884/",
      alt: "Entrance arch of the Fountain of Youth Archaeological Park",
      caption: "Pictured: the Fountain of Youth Archaeological Park, often identified as the likely site of the 1513 landing"
    }
  };

  function whenHtml(m) {
    if (m.floods_at == null) return "Still dry at +9 ft.";
    if (m.sea_at === m.floods_at) return "The sea reaches it at <b>+" + m.sea_at + " ft</b>.";
    return "Low-lying ground here floods from <b>+" + m.floods_at + " ft</b>, cut off from the sea; " +
      (m.sea_at == null ? "the sea itself does not reach it by +9 ft." : "the sea itself arrives at <b>+" + m.sea_at + " ft</b>.");
  }

  var openCard = null;
  function closeCard() { if (openCard) { openCard.remove(); openCard = null; } }
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeCard(); });
  document.addEventListener("pointerdown", function (e) {
    if (openCard && !openCard.contains(e.target) && !(e.target.closest && e.target.closest(".hot, .spot-mark"))) closeCard();
  });

  // frame: the picture the landmark sits on (fx, fy are fractions of it); the card goes into the
  // frame's section, so the picture's overflow clipping never cuts it off
  window.slrCard = function (frame, m, fx, fy) {
    var container = frame.closest("section") || frame.parentNode;
    closeCard();
    var p = PHOTOS[m.name];
    var see = m.sea_at != null ? m.sea_at : m.floods_at;
    var c = document.createElement("div");
    c.className = "lm-card";
    c.setAttribute("role", "dialog");
    c.setAttribute("aria-label", m.name);
    c.innerHTML = (p ? '<img src="' + p.src + '" alt="' + esc(p.alt) + '">' : "") +
      '<div class="body"><h3>' + esc(m.name) + '</h3><span class="lm-when">' + whenHtml(m) + "</span>" +
      (see != null ? '<button type="button" class="see">See it at +' + see + " ft</button>" : "") +
      (p ? '<span class="credit">' + (p.caption ? esc(p.caption) + ". " : "") +
        'Photo: Carol M. Highsmith, 2020, <a href="' + p.url + '">Library of Congress</a></span>'
        : '<span class="credit">The Library of Congress has no photo identified as this place.</span>') +
      '</div><button type="button" class="x" aria-label="Close">×</button>';
    var fr = frame.getBoundingClientRect(), co = container.getBoundingClientRect();
    var px = fr.left - co.left + fx * fr.width, py = fr.top - co.top + fy * fr.height;
    container.append(c);
    var cw = c.offsetWidth, ch = c.offsetHeight;
    var left = co.width < 520 ? (co.width - cw) / 2 : fx > 0.55 ? px - cw - 18 : px + 18;
    var topY = fy > 0.5 ? py - ch - 18 : py + 18;
    c.style.left = Math.max(0, Math.min(co.width - cw, left)) + "px";
    c.style.top = Math.max(0, topY) + "px";
    c.querySelector(".x").addEventListener("click", closeCard);
    var btn = c.querySelector(".see");
    if (btn) btn.addEventListener("click", function () { closeCard(); show(see); });
    c.querySelector(".x").focus({ preventScroll: true });
    openCard = c;
  };

  var data = Promise.all([
    getJSON("figures/compare/levels.json"),
    getJSON("figures/years.json").catch(function () { return null; })
  ]);

  // ---- tap anywhere: the data image holds, per 10 m pixel, the first level (red) and first sea level (green) ----
  Promise.all([data, getJSON("figures/floodmap.json")]).then(function (res) {
    var levels = res[0][0].levels, landmarks = res[0][0].landmarks || [], years = res[0][1], info = res[1];
    var section = document.getElementById("spot");
    var fig = document.getElementById("spot-map");
    var cardEl = document.getElementById("spot-card");
    var codes = info.codes, W = info.width, H = info.height, px = null;
    var raw = new Image();
    raw.onload = function () {
      var cv = document.createElement("canvas");
      cv.width = W; cv.height = H;
      var ctx = cv.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(raw, 0, 0);
      px = ctx.getImageData(0, 0, W, H).data;
      var h = window.slrHash.get();
      if (h.water != null) setMode("water", Number(h.water));
      if (h.spot) {  // a shared link: drop the pin where it was
        var xy = h.spot.split(",").map(Number);
        if (xy.length === 2 && xy.every(isFinite)) { at(xy[0], xy[1]); section.scrollIntoView({ block: "start" }); }
      }
    };
    raw.src = "figures/floodmap-data.png";

    var ramp = document.getElementById("spot-ramp");
    info.colors.bands.forEach(function (c) { var s = document.createElement("span"); s.style.background = c; ramp.append(s); });
    var keys = document.getElementById("spot-keys");
    [["today", "Under water today (mostly marsh)"], ["dry", "Dry at +9 ft"], ["sea", "Open water"]].forEach(function (k) {
      var s = document.createElement("span");
      s.innerHTML = '<i style="background:' + info.colors[k[0]] + '"></i>' + k[1];
      keys.append(s);
    });

    var pin = document.createElement("span");
    pin.className = "spot-pin";
    pin.hidden = true;
    fig.append(pin);

    // plan view of the water at one level, painted pixel by pixel from the data image
    var canvas = document.createElement("canvas");
    canvas.width = W; canvas.height = H; canvas.hidden = true;
    fig.insertBefore(canvas, pin);
    var cctx = canvas.getContext("2d"), paintBuf = cctx.createImageData(W, H);
    function rgb(c) { return [1, 3, 5].map(function (k) { return parseInt(c.slice(k, k + 2), 16); }); }
    var COL = { sea: rgb(info.colors.sea), today: rgb(info.colors.today), dry: rgb(info.colors.dry),
      flood: rgb(info.colors.bands[3]), low: rgb(info.colors.bands[7]) };
    var waterRow = document.getElementById("spot-water-row"), waterIn = document.getElementById("spot-water");
    var waterOut = document.getElementById("spot-water-out"), waterSub = document.getElementById("spot-water-sub");
    var bWhen = document.getElementById("spot-mode-when"), bWater = document.getElementById("spot-mode-water");
    function paintWater(L) {
      if (!px) return;
      var d = paintBuf.data, off = codes.level_offset;
      for (var i = 0; i < px.length; i += 4) {
        var r = px[i], g = px[i + 1], c = null;
        if (r === codes.outside) { d[i + 3] = 0; continue; }
        if (r === codes.water) c = COL.sea;
        else if (r === off) c = COL.today;
        else if (r > off && r < codes.dry && r - off <= L) c = g !== codes.dry && g - off <= L ? COL.flood : COL.low;
        else c = COL.dry;
        d[i] = c[0]; d[i + 1] = c[1]; d[i + 2] = c[2]; d[i + 3] = 255;
      }
      cctx.putImageData(paintBuf, 0, 0);
      var l = levels.filter(function (x) { return x.ft === L; })[0];
      waterOut.textContent = L === 0 ? "Today" : "+" + L + " ft";
      waterSub.textContent = L === 0 ? "Today's high tide: open water and tidal marsh only."
        : l && l.pct != null ? l.pct.toFixed(1) + "% of the city's land newly under water. Deep aqua: the sea; pale aqua: low-lying ground cut off from it." : "";
    }
    var playing = null;
    function setMode(mode, L) {
      var water = mode === "water";
      bWhen.setAttribute("aria-pressed", String(!water));
      bWater.setAttribute("aria-pressed", String(water));
      canvas.hidden = !water; waterRow.hidden = !water; waterSub.hidden = !water;
      ramp.parentNode.hidden = water;
      if (water) {
        if (L != null && L >= 0 && L <= 9) waterIn.value = L;
        paintWater(Number(waterIn.value));
        window.slrHash.set("water", waterIn.value);
      } else window.slrHash.set("water", null);
    }
    bWhen.addEventListener("click", function () { setMode("when"); });
    bWater.addEventListener("click", function () { setMode("water"); });
    waterIn.addEventListener("input", function () { paintWater(Number(waterIn.value)); window.slrHash.set("water", waterIn.value); });
    document.getElementById("spot-water-play").addEventListener("click", function () {
      clearTimeout(playing);
      var L = 0;
      (function step() {
        waterIn.value = L; paintWater(L); window.slrHash.set("water", L);
        if (L++ < 9) playing = setTimeout(step, reduce ? 0 : 700);
      })();
    });

    function yearOf(ft) {
      if (!years) return "";
      var y = years.scenarios[years.default].crossing[ft];
      return y ? " Under NOAA's " + years.default + " scenario that is around <b>" + y + "</b>." : " NOAA's " + years.default + " scenario does not reach it by " + years.years[years.years.length - 1] + ".";
    }

    function describe(r, g) {
      var lv, what = "", why = "", ft = null;
      if (r === codes.outside) { lv = "Outside the city"; why = "The analysis covers land inside the city limits only."; }
      else if (r === codes.water) { lv = "Open water"; why = "A river, creek or bay today: Census water, so it never counts as land lost."; }
      else if (r === codes.dry) { lv = "Dry at +9 ft"; why = "This spot stays above every level mapped here, up to 9 ft above today's high tide."; }
      else if (r === codes.level_offset) { lv = "Wet today"; why = "Already under water at today's mean higher high water, mostly tidal marsh."; }
      else {
        ft = r - codes.level_offset;
        var sea = g === codes.dry ? null : g - codes.level_offset;
        var l = levels.filter(function (x) { return x.ft === ft; })[0];
        lv = "+" + ft + " ft";
        what = "This spot first floods at +" + ft + " ft." + yearOf(ft);
        why = sea === ft ? "The sea comes straight in at this level."
          : sea == null ? "It floods as low-lying ground cut off from the sea; the sea itself does not reach it by +9 ft."
          : "It floods first as low-lying ground cut off from the sea; the sea itself arrives at +" + sea + " ft.";
        if (l && l.pct != null) why += " By then " + l.pct.toFixed(1) + "% of the city's land is newly under water.";
      }
      cardEl.innerHTML = '<span class="lv">' + lv + "</span>" + (what ? '<span class="what">' + what + "</span>" : "") +
        '<span class="why">' + why + "</span>" + (ft ? '<button type="button" class="see" id="spot-see">See +' + ft + " ft in the comparison</button>" : "");
      var b = document.getElementById("spot-see");
      if (b) b.addEventListener("click", function () { show(ft); });
    }

    function at(fx, fy) {
      pin.hidden = false;
      pin.style.left = fx * 100 + "%";
      pin.style.top = fy * 100 + "%";
      if (!px) { cardEl.innerHTML = '<span class="why">Loading the map data…</span>'; return; }
      var x = Math.min(W - 1, Math.max(0, Math.floor(fx * W))), y = Math.min(H - 1, Math.max(0, Math.floor(fy * H)));
      var i = (y * W + x) * 4;
      describe(px[i], px[i + 1]);
      window.slrHash.set("spot", fx.toFixed(4) + "," + fy.toFixed(4));
      var share = document.createElement("button");
      share.type = "button";
      share.id = "spot-share";
      share.textContent = "Copy a link to this spot";
      share.addEventListener("click", function () {
        var done = function () { share.textContent = "Link copied"; setTimeout(function () { share.textContent = "Copy a link to this spot"; }, 1800); };
        if (navigator.clipboard) navigator.clipboard.writeText(location.href).then(done, function () { prompt("Copy this link", location.href); });
        else prompt("Copy this link", location.href);
      });
      cardEl.append(share);
    }

    fig.addEventListener("click", function (e) {
      if (e.target.closest(".spot-mark, .lm-card")) return;
      var r = fig.getBoundingClientRect();
      closeCard();
      at((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
    });

    var byName = {};
    landmarks.forEach(function (m) { byName[m.name] = m; });
    info.landmarks.forEach(function (p) {
      var m = byName[p.name] || { name: p.name, floods_at: null, sea_at: null };
      var b = document.createElement("button");
      b.type = "button";
      b.className = "spot-mark";
      b.id = "spot-mark-" + p.name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
      b.style.left = p.fx * 100 + "%";
      b.style.top = p.fy * 100 + "%";
      b.setAttribute("aria-label", p.name);
      b.title = p.name;
      b.addEventListener("click", function () { at(p.fx, p.fy); window.slrCard(fig, m, p.fx, p.fy); });
      fig.append(b);
    });
    section.hidden = false;
  }).catch(function () {});

  // ---- guess first: the gauge is veiled until the reader commits to a number ----
  data.then(function (res) {
    var l3 = res[0].levels.filter(function (l) { return l.ft === 3; })[0];
    var box = document.getElementById("guess");
    if (!l3 || l3.pct == null || !box) return;
    var gauge = document.querySelector(".gauge");
    var range = document.getElementById("guess-range"), out = document.getElementById("guess-out");
    var go = document.getElementById("guess-go"), skip = document.getElementById("guess-skip");
    var result = document.getElementById("guess-result");
    gauge.classList.add("veiled");
    box.hidden = false;
    var segs = [].slice.call(gauge.querySelectorAll(".seg-slr, .seg-low"));
    segs.forEach(function (sg) { sg.dataset.w = sg.style.width; sg.style.width = "0%"; });  // they grow on reveal
    range.addEventListener("input", function () { out.textContent = range.value + "%"; });
    function reveal(guessed) {
      gauge.classList.remove("veiled");
      setTimeout(function () { segs.forEach(function (sg) { sg.style.width = sg.dataset.w; }); }, 50);
      go.disabled = true; range.disabled = true; skip.hidden = true;
      var truth = l3.pct;
      if (guessed == null) { result.innerHTML = "<b>" + truth.toFixed(1) + "%</b> of the city's land at +3 ft."; return; }
      var gap = guessed - truth, size = Math.abs(gap).toFixed(1);
      result.innerHTML = "<b>" + truth.toFixed(1) + "%</b>. You guessed " + guessed + "%: " +
        (Math.abs(gap) < 3 ? "spot on." : size + " points " + (gap < 0 ? "too low." : "too high.")) +
        " Your guess is the black tick on the +3 ft bar.";
      var track = document.querySelector('.gauge .row[data-ft="3"] .track');
      if (track) { var t = document.createElement("span"); t.className = "guess-tick"; t.style.left = guessed + "%"; track.append(t); }
    }
    go.addEventListener("click", function () { reveal(Number(range.value)); });
    skip.addEventListener("click", function () { reveal(null); });
  }).catch(function () {});

  // ---- when: NOAA 2022 scenarios, the year each level is reached ----
  data.then(function (res) {
    var Y = res[1];
    if (!Y) return;
    var section = document.getElementById("when"), chart = document.getElementById("when-chart");
    var group = document.getElementById("when-scen"), infoEl = document.getElementById("when-info");
    var names = Object.keys(Y.scenarios), years = Y.years, current = Y.default;
    var ageIn = document.getElementById("age-year"), ageOut = document.getElementById("age-out");
    ageIn.max = new Date().getFullYear();
    function ages() {
      var born = Number(ageIn.value), now = new Date().getFullYear();
      if (!ageIn.value || born < 1900 || born > now) {
        ageOut.textContent = "Type a year to see how old you would be as each foot arrives.";
        return;
      }
      var S = Y.scenarios[current], bits = [];
      [1, 2, 3].forEach(function (f) {
        var y = S.crossing[f];
        bits.push(y ? "<b>+" + f + " ft</b> around " + y + (y - born > 110 ? ", long after your lifetime" : ": you would be about <b>" + (y - born) + "</b>")
          : "<b>+" + f + " ft</b> not by " + years[years.length - 1]);
      });
      ageOut.innerHTML = "Under the " + esc(current) + " scenario, " + bits.join("; ") + ".";
    }
    ageIn.addEventListener("input", ages);
    var w = 1000, h = 430, m = { l: 56, r: 24, t: 14, b: 34 };
    var x0 = years[0], x1 = years[years.length - 1], top = 10;
    function sx(y) { return m.l + (y - x0) / (x1 - x0) * (w - m.l - m.r); }
    function sy(ft) { return h - m.b - Math.min(ft, top) / top * (h - m.t - m.b); }
    var s = svg("svg", { viewBox: "0 0 " + w + " " + h, role: "img", "aria-label": "Sea-level rise by year under NOAA's five scenarios" }, chart);
    var clip = svg("clipPath", { id: "when-clip" }, svg("defs", {}, s));
    svg("rect", { x: m.l, y: m.t, width: w - m.l - m.r, height: h - m.t - m.b }, clip);
    for (var ft = 1; ft <= 9; ft++) {
      svg("line", { x1: m.l, x2: w - m.r, y1: sy(ft), y2: sy(ft), class: "grid" }, s);
      svg("text", { x: m.l - 8, y: sy(ft) + 4, "text-anchor": "end", class: "axis" }, s).textContent = "+" + ft + " ft";
    }
    for (var yr = 2020; yr <= x1; yr += 20) {
      if (yr < x0) continue;
      svg("text", { x: sx(yr), y: h - 10, "text-anchor": "middle", class: "axis" }, s).textContent = yr;
    }
    var plot = svg("g", { "clip-path": "url(#when-clip)" }, s);
    var band = svg("path", { fill: "var(--flood)", opacity: 0.16 }, plot);
    var lines = {};
    names.forEach(function (n) {
      lines[n] = svg("path", { class: "when-chart-line", stroke: "var(--muted)", opacity: 0.35,
        d: "M" + years.map(function (yy, i) { return sx(yy) + "," + sy(Y.scenarios[n].median_ft[i]); }).join("L") }, plot);
    });
    var dots = svg("g", {}, s);

    function pick(n) {
      current = n;
      var S = Y.scenarios[n];
      names.forEach(function (k) {
        lines[k].setAttribute("stroke", k === n ? "var(--teal)" : "var(--muted)");
        lines[k].setAttribute("stroke-width", k === n ? 3.5 : 1.5);
        lines[k].setAttribute("opacity", k === n ? 1 : 0.35);
      });
      band.setAttribute("d", "M" + years.map(function (yy, i) { return sx(yy) + "," + sy(S.p83_ft[i]); }).join("L") +
        "L" + years.slice().reverse().map(function (yy, i) { return sx(yy) + "," + sy(S.p17_ft[years.length - 1 - i]); }).join("L") + "Z");
      dots.innerHTML = "";
      var reached = [];
      for (var f = 1; f <= 9; f++) {
        var y = S.crossing[f];
        if (!y) continue;
        reached.push(f);
        var g = svg("g", { class: "dot-g", tabindex: 0, role: "button", "aria-label": "+" + f + " ft around " + y + ": show it in the comparison" }, dots);
        svg("circle", { cx: sx(y), cy: sy(f), r: 7, fill: "var(--accent)", class: "dot" }, g);
        svg("text", { x: sx(y) + 11, y: sy(f) - 7, class: "lbl" }, g).textContent = y;
        (function (lv) {
          g.addEventListener("click", function () { show(lv); });
          g.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); show(lv); } });
        })(f);
      }
      var bits = reached.slice(0, 3).map(function (f) { return "<b>+" + f + " ft</b> around " + S.crossing[f]; });
      var last = reached[reached.length - 1];
      if (reached.length > 3) bits.push("up to <b>+" + last + " ft</b> around " + S.crossing[last]);
      var missed = !reached.length ? "no level is reached by " + x1 + "."
        : last < 9 ? " +" + (last + 1) + " ft is not reached by " + x1 + "." : "";
      infoEl.innerHTML = "Under the <b>" + esc(n) + "</b> scenario: " + (bits.length ? bits.join(", ") + "." : "") + missed;
      group.querySelectorAll("button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.s === n)); });
      ages();
    }
    names.forEach(function (n) {
      var b = document.createElement("button");
      b.type = "button";
      b.id = "when-" + n.toLowerCase().replace(/[^a-z]+/g, "-");
      b.dataset.s = n;
      b.textContent = n;
      b.addEventListener("click", function () { pick(n); });
      group.append(b);
    });
    document.getElementById("when-note").innerHTML = 'Source: Sweet et al. 2022, NOAA Technical Report NOS 01, ' +
      '<a href="' + Y.source + '">' + esc(Y.file) + "</a>, cell " + esc(Y.cell) +
      ". Relative sea level, vertical land motion included, shifted by the file's own offsets (" + Y.offset_cm_1992_to_2005 +
      " cm) to the 1983–2001 tidal epoch the flood layers are measured from. Years between the file's decades are interpolated, so read them as “around”.";
    pick(Y.default);
    section.hidden = false;
  }).catch(function () {});

  // ---- the string of pearls: each landmark on a 0-9 ft line ----
  data.then(function (res) {
    var box = document.getElementById("pearl-line");
    var L = (res[0].landmarks || []).slice().sort(function (a, b) {
      return (a.floods_at == null ? 99 : a.floods_at) - (b.floods_at == null ? 99 : b.floods_at);
    });
    if (!box || !L.length) return;
    var w = 1000, lane = 46, m = { l: 260, r: 70, t: 14, b: 30 }, h = m.t + m.b + lane * L.length;
    function sx(ft) { return m.l + ft / 9 * (w - m.l - m.r); }
    var s = svg("svg", { viewBox: "0 0 " + w + " " + h, role: "img", "aria-label": "The level at which water reaches each landmark" });
    box.insertBefore(s, box.querySelector(".note"));
    for (var f = 0; f <= 9; f++) {
      svg("line", { x1: sx(f), x2: sx(f), y1: m.t, y2: h - m.b + 4, class: "grid" }, s);
      svg("text", { x: sx(f), y: h - 8, "text-anchor": "middle", class: "axis" }, s).textContent = f === 0 ? "today" : "+" + f;
    }
    function pearl(ft, y, solid, mk) {
      var g = svg("g", { class: "pearl", tabindex: 0, role: "button",
        "aria-label": mk.name + (solid ? ": the sea arrives at +" : ": low-lying ground floods at +") + ft + " ft" }, s);
      svg("circle", { cx: sx(ft), cy: y, r: 13, fill: "#ffffff", opacity: 0.9 }, g);
      svg("circle", { cx: sx(ft), cy: y, r: 9, fill: solid ? "var(--accent)" : "#ffffff", stroke: "var(--accent)", "stroke-width": 3 }, g);
      svg("title", {}, g).textContent = (solid ? "The sea arrives at +" : "Low-lying ground floods at +") + ft + " ft";
      g.addEventListener("click", function () { show(ft); });
      g.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); show(ft); } });
    }
    L.forEach(function (mk, i) {
      var y = m.t + lane * i + lane / 2;
      svg("text", { x: m.l - 18, y: y + 5, "text-anchor": "end", class: "name" }, s).textContent = mk.name;
      if (mk.floods_at == null) {
        svg("line", { x1: sx(0), x2: sx(9), y1: y, y2: y, stroke: "var(--rule)", "stroke-width": 2 }, s);
        svg("text", { x: sx(9) + 10, y: y + 4, class: "axis" }, s).textContent = "dry";
        return;
      }
      var a = mk.floods_at, b = mk.sea_at;
      svg("line", { x1: sx(0), x2: sx(a), y1: y, y2: y, stroke: "var(--rule)", "stroke-width": 2 }, s);
      if (b != null && b > a) svg("line", { x1: sx(a), x2: sx(b), y1: y, y2: y, class: "thread" }, s);
      if (b == null || b > a) pearl(a, y, false, mk);
      if (b != null) pearl(b, y, true, mk);
    });
    box.hidden = false;
  }).catch(function () {});

  // ---- the headline numbers count up the first time they come into view ----
  if (!reduce && "IntersectionObserver" in window) {
    document.querySelectorAll(".fact b").forEach(function (el) {
      var text = el.textContent, hit = text.match(/[\d.]+/);
      if (!hit) return;
      var target = parseFloat(hit[0]), dec = (hit[0].split(".")[1] || "").length;
      el.setAttribute("aria-label", text);
      el.textContent = text.replace(hit[0], (0).toFixed(dec));
      var io = new IntersectionObserver(function (es) {
        if (!es[0].isIntersecting) return;
        io.disconnect();
        var t0 = Date.now();
        (function step() {
          var k = Math.min(1, (Date.now() - t0) / 900), e = 1 - Math.pow(1 - k, 3);
          el.textContent = text.replace(hit[0], (target * e).toFixed(dec));
          if (k < 1) setTimeout(step, 16);
        })();
      }, { threshold: 0.6 });
      io.observe(el);
    });
  }

  // ---- cross-section: USGS 3DEP ground, NOAA tide datum, NOAA flood classes ----
  Promise.all([data, getJSON("figures/sections.json")]).then(function (res) {
    var levels = res[0][0].levels, S = res[1];
    var section = document.getElementById("cut"), chart = document.getElementById("cut-chart");
    var pickEl = document.getElementById("cut-pick"), lvIn = document.getElementById("cut-level");
    var lvOut = document.getElementById("cut-out"), infoEl = document.getElementById("cut-info");
    var keys = Object.keys(S.sections), FT = 0.3048, cur = keys[0];
    var w = 1000, h = 380, m = { l: 52, r: 16, t: 28, b: 34 };

    function draw() {
      var sec = S.sections[cur], L = Number(lvIn.value), lm = L * FT, sm = sec.samples;
      var dmax = sm[sm.length - 1].d;
      // past the city limit there is no Census water, so ground below today's high tide is the bay
      sm.forEach(function (p) { p.open = p.water || (!p.city && p.z < 0); });
      var land = sm.filter(function (p) { return !p.open && p.city; });
      var zmax = Math.max.apply(null, land.map(function (p) { return p.z; }).concat([9 * FT + 0.5]));
      var zmin = -2;
      function sx(d) { return m.l + d / dmax * (w - m.l - m.r); }
      function sy(z) { return m.t + (zmax - Math.max(zmin, Math.min(zmax, z))) / (zmax - zmin) * (h - m.t - m.b); }
      var exag = ((h - m.t - m.b) / (zmax - zmin)) / ((w - m.l - m.r) / dmax);
      chart.innerHTML = "";
      var s = svg("svg", { viewBox: "0 0 " + w + " " + h, role: "img", "aria-label": sec.title + " at +" + L + " ft" }, chart);
      // height grid in feet above today's high tide
      for (var f = 0; f <= 9; f += 3) {
        svg("line", { x1: m.l, x2: w - m.r, y1: sy(f * FT), y2: sy(f * FT), stroke: "var(--rule)" }, s);
        svg("text", { x: m.l - 6, y: sy(f * FT) + 4, "text-anchor": "end", class: "axis" }, s).textContent = f === 0 ? "MHHW" : "+" + f + " ft";
      }
      // water, one column per sample: open water rises with the sea everywhere; land floods by NOAA's class
      var col = (w - m.l - m.r) / (sm.length - 1);
      var wetLand = 0, seaLand = 0;
      sm.forEach(function (p) {
        var top = null, fill = null;
        if (p.open) { top = Math.max(lm, 0); fill = "#8fb2b6"; }
        else if (p.first != null && p.first <= L) {
          top = Math.max(lm, p.z); wetLand++;
          var sea = p.sea != null && p.sea <= L;
          if (sea) seaLand++;
          fill = p.first === 0 ? "#e9b9a0" : sea ? "#18a7b5" : "#9adfe5";
          if (p.first === 0 && L > 0) fill = sea ? "#18a7b5" : "#9adfe5";
        }
        if (top == null) return;
        var bottom = Math.min(p.z, top);
        svg("rect", { x: sx(p.d) - col / 2, width: col + 0.6, y: sy(top), height: Math.max(0, sy(bottom) - sy(top)) + 0.6, fill: fill }, s);
      });
      // ground
      var d = "M" + sx(0) + "," + (h - m.b) + sm.map(function (p) { return "L" + sx(p.d) + "," + sy(p.z); }).join("") + "L" + sx(dmax) + "," + (h - m.b) + "Z";
      svg("path", { d: d, fill: "#e2d3bc" }, s);
      svg("path", { d: "M" + sm.map(function (p) { return sx(p.d) + "," + sy(p.z); }).join("L"), fill: "none", stroke: "#a98f6f", "stroke-width": 1.5 }, s);
      // today's high tide and the chosen level
      svg("line", { x1: m.l, x2: w - m.r, y1: sy(0), y2: sy(0), stroke: "#0f6e7a", "stroke-dasharray": "4 4" }, s);
      if (L > 0) {
        svg("line", { x1: m.l, x2: w - m.r, y1: sy(lm), y2: sy(lm), stroke: "var(--accent)", "stroke-dasharray": "6 4", "stroke-width": 1.5 }, s);
        svg("text", { x: w - m.r, y: sy(lm) - 6, "text-anchor": "end", class: "lbl", fill: "var(--accent)" }, s).textContent = "+" + L + " ft";
      }
      // landmarks and the water at each end
      sec.marks.forEach(function (mk) {
        var p = sm.reduce(function (a, b) { return Math.abs(b.d - mk.d) < Math.abs(a.d - mk.d) ? b : a; });
        svg("line", { x1: sx(mk.d), x2: sx(mk.d), y1: sy(p.z) - 4, y2: m.t + 4, stroke: "var(--accent)", "stroke-width": 1.2 }, s);
        svg("circle", { cx: sx(mk.d), cy: m.t + 4, r: 4, fill: "var(--accent)" }, s);
        svg("text", { x: sx(mk.d) + 7, y: m.t + 8, class: "lbl" }, s).textContent = mk.name;
      });
      // Census FULLNAME abbreviates feature types (Riv, Crk); spell them out for the label only
      function spell(n) { return n.replace(/\bRiv$/, "River").replace(/\bCrk$/, "Creek"); }
      if (sec.west_water) svg("text", { x: sx(0) + 4, y: h - m.b - 8, class: "wname" }, s).textContent = spell(sec.west_water);
      if (sec.east_water) svg("text", { x: sx(dmax) - 4, y: h - m.b - 8, "text-anchor": "end", class: "wname" }, s).textContent = spell(sec.east_water);
      for (var dd = 0; dd <= dmax; dd += 500) {
        svg("text", { x: sx(dd), y: h - 10, "text-anchor": "middle", class: "axis" }, s).textContent = dd === 0 ? "0" : dd / 1000 + " km";
      }
      svg("text", { x: m.l, y: m.t - 12, class: "axis" }, s).textContent = "West ← → East · vertical scale ×" + Math.round(exag);
      var l = levels.filter(function (x) { return x.ft === L; })[0];
      lvOut.textContent = L === 0 ? "Today" : "+" + L + " ft";
      var share = land.length ? Math.round(wetLand / land.length * 100) : 0, seaShare = land.length ? Math.round(seaLand / land.length * 100) : 0;
      infoEl.innerHTML = (L === 0 ? "Today" : "At <b>+" + L + " ft</b>") + ", " + share + "% of the land along this line is under water" +
        (wetLand ? ": " + seaShare + "% from the sea, " + (share - seaShare) + "% low-lying ground cut off from it." : ".") +
        (l && l.pct != null && L > 0 ? " Citywide: " + l.pct.toFixed(1) + "%." : "");
    }
    keys.forEach(function (k) {
      var b = document.createElement("button");
      b.type = "button";
      b.id = "cut-" + k;
      b.textContent = S.sections[k].title;
      b.addEventListener("click", function () {
        cur = k;
        pickEl.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
        draw();
      });
      b.setAttribute("aria-pressed", String(k === cur));
      pickEl.append(b);
    });
    lvIn.addEventListener("input", draw);
    document.getElementById("cut-note").textContent = "Ground: USGS 3DEP elevations every " + S.sections[cur].step_m +
      " m. Datum: NOAA tide station " + S.datum.station + " (" + S.datum.epoch + " epoch), MHHW " + S.datum.mhhw_minus_navd88_m +
      " m above NAVD88. Water: NOAA's flood layers at each point, which use their own elevation model, so the line and the water can differ by a few tens of centimetres. Vertical scale exaggerated.";
    draw();
    section.hidden = false;
  }).catch(function () {});

  // ---- storms: HURDAT2 tracks within the radius, by year and closest approach ----
  getJSON("figures/storms.json").then(function (D) {
    var section = document.getElementById("storms"), chart = document.getElementById("storm-chart");
    var infoEl = document.getElementById("storm-info");
    var all = D.storms, hu = all.filter(function (s) { return /^[1-5]$/.test(s.category); });
    document.getElementById("storms-note").innerHTML = "<b>" + all.length + "</b> storm tracks, from depressions to hurricanes, passed within " +
      D.radius_km + " km of the city between " + D.first_year + " and " + D.last_year + "; <b>" + hu.length +
      "</b> of them at hurricane strength while in range.";
    var w = 1000, h = 320, m = { l: 56, r: 24, t: 24, b: 34 };
    function sx(y) { return m.l + (y - D.first_year) / (D.last_year - D.first_year) * (w - m.l - m.r); }
    function sy(km) { return m.t + km / D.radius_km * (h - m.t - m.b); }
    var R = { TD: 3, TS: 4.5, other: 3, 1: 6.5, 2: 8, 3: 9.5, 4: 11, 5: 12.5 };
    var FILL = { TD: "var(--today)", other: "var(--today)", TS: "var(--flood)" };
    var s = svg("svg", { viewBox: "0 0 " + w + " " + h, role: "img", "aria-label": "Storms near St. Augustine by year and distance" }, chart);
    [0, 25, 50, 75, 100].forEach(function (km) {
      if (km > D.radius_km) return;
      svg("line", { x1: m.l, x2: w - m.r, y1: sy(km), y2: sy(km), class: "grid" }, s);
      svg("text", { x: m.l - 8, y: sy(km) + 4, "text-anchor": "end", class: "axis" }, s).textContent = km + " km";
    });
    for (var yr = 1860; yr <= D.last_year; yr += 20) {
      svg("text", { x: sx(yr), y: h - 10, "text-anchor": "middle", class: "axis" }, s).textContent = yr;
    }
    var g = svg("g", {}, s), current = null;
    function cat(st) { return /^[1-5]$/.test(st.category) ? "Category " + st.category + " hurricane" : st.category === "TS" ? "tropical storm" : st.category === "TD" ? "tropical depression" : "post- or sub-tropical system"; }
    function pick(st, dot) {
      if (current) current.classList.remove("on");
      current = dot; dot.classList.add("on");
      infoEl.innerHTML = "<b>" + esc(st.name === "Unnamed" ? "An unnamed storm" : st.name) + "</b>, " + st.date + ": passed " +
        st.closest_km.toFixed(0) + " km from the city as a " + cat(st) + ", winds up to " + st.max_wind_kt + " kt (" +
        Math.round(st.max_wind_kt * 1.15078) + " mph) while within " + D.radius_km + " km.";
    }
    function draw(list) {
      g.innerHTML = "";
      list.slice().sort(function (a, b) { return (R[a.category] || 3) - (R[b.category] || 3); }).reverse().forEach(function (st) {
        var isHu = /^[1-5]$/.test(st.category);
        var dot = svg("circle", {
          cx: sx(st.year), cy: sy(st.closest_km), r: R[st.category] || 3, class: "dot", tabindex: 0, role: "button",
          fill: isHu ? "var(--accent)" : FILL[st.category] || "var(--today)", "fill-opacity": isHu ? 0.55 + 0.1 * Number(st.category) : 0.8,
          "aria-label": (st.name === "Unnamed" ? "Unnamed storm" : st.name) + ", " + st.year
        }, g);
        dot.addEventListener("click", function () { pick(st, dot); });
        dot.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(st, dot); } });
        if (isHu && Number(st.category) >= 2 && st.name !== "Unnamed") {
          var right = sx(st.year) > w * 0.85;  // keep labels near the right edge inside the chart
          svg("text", { x: sx(st.year) + (right ? -14 : 12), y: sy(st.closest_km) + 4, class: "lbl", "text-anchor": right ? "end" : "start" }, g)
            .textContent = st.name + " " + st.year;
        }
      });
    }
    var bAll = document.getElementById("storm-all"), bHu = document.getElementById("storm-hu");
    bAll.addEventListener("click", function () { draw(all); bAll.setAttribute("aria-pressed", "true"); bHu.setAttribute("aria-pressed", "false"); });
    bHu.addEventListener("click", function () { draw(hu); bHu.setAttribute("aria-pressed", "true"); bAll.setAttribute("aria-pressed", "false"); });
    draw(all);
    section.hidden = false;
  }).catch(function () {});
})();

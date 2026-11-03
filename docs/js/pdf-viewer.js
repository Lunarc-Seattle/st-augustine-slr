(function () {
  var lib = window.pdfjsLib;
  if (lib) lib.GlobalWorkerOptions.workerSrc = "vendor/pdf.worker.min.js";
  var MAX_PIXELS = 24e6;  // keep big zooms of the 11.9 MB map inside canvas limits

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    for (var k in attrs) node.setAttribute(k, attrs[k]);
    if (text) node.textContent = text;
    return node;
  }

  document.querySelectorAll(".plate").forEach(function (plate, i) {
    var url = plate.dataset.pdf;
    var name = url.split("/").pop();
    var actions = plate.querySelector(".actions");
    var viewBtn = el("button", { type: "button", id: "view-" + i, "aria-expanded": "false" }, "View vector PDF");
    var saveBtn = el("a", { class: "button", href: url, download: name }, "Download PDF");
    var status = el("span", { class: "status", role: "status" });
    actions.append(viewBtn, saveBtn, status);
    if (!lib) { viewBtn.disabled = true; status.textContent = "The PDF viewer could not load. The image above is the same figure."; }

    var viewer = null, doc = null, zoom = 1, rendering = null;

    function render() {
      if (!doc) return;
      var box = viewer.querySelector(".canvas-box");
      var label = viewer.querySelector(".zoom");
      label.textContent = Math.round(zoom * 100) + "%";
      if (rendering) rendering.cancel();
      doc.getPage(1).then(function (page) {
        var base = page.getViewport({ scale: 1 });
        var cssScale = (box.clientWidth - 2) / base.width * zoom;
        var dpr = window.devicePixelRatio || 1;
        var px = base.width * base.height * cssScale * cssScale * dpr * dpr;
        if (px > MAX_PIXELS) dpr = Math.sqrt(MAX_PIXELS / (base.width * base.height * cssScale * cssScale));
        var vp = page.getViewport({ scale: cssScale * dpr });
        var canvas = box.querySelector("canvas") || box.appendChild(document.createElement("canvas"));
        canvas.width = Math.floor(vp.width); canvas.height = Math.floor(vp.height);
        canvas.style.width = Math.floor(vp.width / dpr) + "px";
        canvas.style.height = Math.floor(vp.height / dpr) + "px";
        status.textContent = "Rendering…";
        rendering = page.render({ canvasContext: canvas.getContext("2d"), viewport: vp });
        return rendering.promise.then(function () { status.textContent = ""; rendering = null; });
      }).catch(function (err) {
        if (err && err.name === "RenderingCancelledException") return;
        status.textContent = "This PDF could not be rendered here. The image above is the same figure.";
      });
    }

    function step(factor) { zoom = Math.min(4, Math.max(1, zoom * factor)); render(); }

    viewBtn.addEventListener("click", function () {
      if (viewer) {
        var open = viewer.hidden;
        viewer.hidden = !open;
        plate.querySelector(".sheet").hidden = open;
        viewBtn.textContent = open ? "Show image" : "View vector PDF";
        viewBtn.setAttribute("aria-expanded", String(open));
        if (open) render();
        return;
      }
      viewer = el("div", { class: "viewer" });
      var bar = el("div", { class: "viewer-bar" });
      var out = el("button", { type: "button", id: "zoom-out-" + i, "aria-label": "Zoom out" }, "−");
      var label = el("span", { class: "zoom", "aria-live": "polite" }, "100%");
      var inn = el("button", { type: "button", id: "zoom-in-" + i, "aria-label": "Zoom in" }, "+");
      var fit = el("button", { type: "button", id: "zoom-fit-" + i }, "Fit width");
      out.addEventListener("click", function () { step(1 / 1.5); });
      inn.addEventListener("click", function () { step(1.5); });
      fit.addEventListener("click", function () { zoom = 1; render(); });
      bar.append(out, label, inn, fit, el("span", { class: "status" }, "Vector rendering: zoom in for street-level detail."));
      viewer.append(bar, el("div", { class: "canvas-box" }));
      plate.querySelector(".sheet").after(viewer);
      plate.querySelector(".sheet").hidden = true;
      viewBtn.textContent = "Show image";
      viewBtn.setAttribute("aria-expanded", "true");
      status.textContent = "Loading " + name + "…";
      lib.getDocument(url).promise.then(function (d) { doc = d; render(); })
        .catch(function () { status.textContent = "This PDF could not be loaded. The image above is the same figure."; plate.querySelector(".sheet").hidden = false; });
    });
  });
})();

"""20 s MP4 of the project page in use, 1920x1080 at 30 fps, for the README and LinkedIn.

Serves docs/ locally, drives Chrome with Playwright (a scripted cursor that drags, clicks and
types) and records Chrome's own screencast frames, then resamples them to a steady 30 fps.
No audio.

Needs playwright (with Chrome installed) and ffmpeg with libx264; neither is a project
dependency. Set FFMPEG to ffmpeg's path if it is not on PATH.
Run from the repo root: python scripts/covers/video_web.py
"""

import base64
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

VIDEO = Path("docs/media/st-augustine-web.mp4")
VIEW_W, VIEW_H, SCALE = 1440, 810, 4 / 3  # 1920x1080 device pixels
FPS, SECONDS = 30, 20
MAX_SPEED = 1.25
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")

# a visible cursor and a ripple on each click, drawn by the page itself
CURSOR = """
addEventListener('DOMContentLoaded', () => {
  const c = document.createElement('div');
  c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M3 2l7 19 2.6-7.4L20 11z" ' +
    'fill="#2b3136" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  Object.assign(c.style, {position: 'fixed', left: '0', top: '0', zIndex: 99999, pointerEvents: 'none',
    transform: 'translate(-3px,-2px)', filter: 'drop-shadow(0 2px 3px rgba(0,0,0,.35))'});
  document.body.append(c);
  addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  addEventListener('mousedown', e => {
    const r = document.createElement('div');
    Object.assign(r.style, {position: 'fixed', left: e.clientX - 18 + 'px', top: e.clientY - 18 + 'px', width: '36px',
      height: '36px', borderRadius: '50%', border: '3px solid #e4472b', zIndex: 99998, pointerEvents: 'none',
      transition: 'transform .45s ease, opacity .45s ease'});
    document.body.append(r);
    requestAnimationFrame(() => { r.style.transform = 'scale(1.8)'; r.style.opacity = '0'; });
    setTimeout(() => r.remove(), 500);
  }, true);
});
"""

SCROLL = """
([sel, offset, ms]) => new Promise(done => {
  const el = document.querySelector(sel);
  const y0 = scrollY, y1 = el.getBoundingClientRect().top + scrollY - offset, t0 = performance.now();
  (function step(now) {
    const k = Math.min(1, (now - t0) / ms), e = k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
    scrollTo(0, y0 + (y1 - y0) * e);
    k < 1 ? requestAnimationFrame(step) : done();
  })(t0);
})
"""


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main():
    port = free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "-d", "docs"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    frames = []
    try:
        time.sleep(1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page(
                viewport={"width": VIEW_W, "height": VIEW_H},
                device_scale_factor=SCALE,
                color_scheme="light",
                reduced_motion="no-preference",
            )
            page.add_init_script(CURSOR)
            page.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            page.wait_for_selector("#cmp-level-9")
            page.wait_for_timeout(600)
            page.mouse.move(VIEW_W * 0.62, VIEW_H * 0.55)

            cdp = page.context.new_cdp_session(page)

            def on_frame(ev):
                frames.append((ev["metadata"]["timestamp"], base64.b64decode(ev["data"])))
                cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

            cdp.on("Page.screencastFrame", on_frame)
            cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 1920, "maxHeight": 1080})
            wait = page.wait_for_timeout

            def glide(x, y, ms=500):
                page.mouse.move(x, y, steps=max(2, ms // 16))

            def rect(sel):
                return page.locator(sel).bounding_box()

            def scroll(sel, offset=24, ms=700):
                page.evaluate(SCROLL, [sel, offset, ms])

            # 1. hero: the old town rising behind the title
            wait(2000)
            # 2. compare: drag the divider both ways, open the Castillo card, jump to its level
            scroll("#compare-title", 16)
            b = rect("#cmp")
            y = b["y"] + b["height"] * 0.62
            glide(b["x"] + b["width"] * 0.5, y, 400)
            page.mouse.down()
            glide(b["x"] + b["width"] * 0.14, y, 650)
            glide(b["x"] + b["width"] * 0.82, y, 700)
            glide(b["x"] + b["width"] * 0.42, y, 400)
            page.mouse.up()
            h = rect("#hot-castillo-de-san-marcos")
            glide(h["x"] + h["width"] / 2, h["y"] + h["height"] / 2, 500)
            page.mouse.click(h["x"] + h["width"] / 2, h["y"] + h["height"] / 2)
            wait(1100)
            s = rect(".lm-card .see")
            glide(s["x"] + s["width"] / 2, s["y"] + s["height"] / 2, 400)
            page.mouse.click(s["x"] + s["width"] / 2, s["y"] + s["height"] / 2)
            wait(600)
            # 3. section: raise the water on real ground
            scroll("#cut", 10)
            r = rect("#cut-level")
            ry = r["y"] + r["height"] / 2
            glide(r["x"] + r["width"] * 3 / 9, ry, 400)
            page.mouse.down()
            glide(r["x"] + r["width"] * 0.99, ry, 1100)
            page.mouse.up()
            wait(500)
            # 4. your spot: tap a street, then the plan view of the water
            scroll("#spot", 10)
            m = rect("#spot-map")
            # a street in the old town that the sea reaches at +3 ft (picked from floodmap-data.png)
            sx, sy = m["x"] + m["width"] * 0.3963, m["y"] + m["height"] * 0.6556
            glide(sx, sy, 500)
            page.mouse.click(sx, sy)
            wait(700)
            w = rect("#spot-mode-water")
            glide(w["x"] + w["width"] / 2, w["y"] + w["height"] / 2, 400)
            page.mouse.click(w["x"] + w["width"] / 2, w["y"] + w["height"] / 2)
            r = rect("#spot-water")
            ry = r["y"] + r["height"] / 2
            glide(r["x"] + r["width"] * 3 / 9, ry, 300)
            page.mouse.down()
            glide(r["x"] + 2, ry, 300)
            glide(r["x"] + r["width"] - 2, ry, 1000)
            page.mouse.up()
            wait(400)
            # 5. when: type a birth year
            scroll("#when", 10)
            a = rect("#age-year")
            glide(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2, 400)
            page.mouse.click(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
            page.keyboard.type("1998", delay=140)
            wait(1500)
            cdp.send("Page.stopScreencast")
            browser.close()
    finally:
        server.terminate()

    # resample to a steady frame rate: each output frame shows the latest screencast frame; if the
    # run took longer than SECONDS, play it back evenly faster (at most MAX_SPEED) so it all fits
    frames.sort(key=lambda f: f[0])
    t0 = frames[0][0]
    span = frames[-1][0] - t0
    speed = min(MAX_SPEED, max(1.0, span / SECONDS))
    VIDEO.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        j = 0
        for i in range(FPS * SECONDS):
            t = t0 + i / FPS * speed
            while j + 1 < len(frames) and frames[j + 1][0] <= t:
                j += 1
            Path(tmp, f"{i:05d}.jpg").write_bytes(frames[j][1])
        subprocess.run(
            [
                FFMPEG,
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(FPS),
                "-i",
                f"{tmp}/%05d.jpg",
                "-vf",
                "scale=1920:1080:flags=lanczos:in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "slow",
                "-crf",
                "18",
                "-color_range",
                "tv",
                "-colorspace",
                "bt709",
                "-color_primaries",
                "bt709",
                "-color_trc",
                "bt709",
                "-movflags",
                "+faststart",
                str(VIDEO),
            ],
            check=True,
        )
    print(
        VIDEO,
        f"{VIDEO.stat().st_size / 1e6:.1f} MB; recorded {span:.1f} s in {len(frames)} frames, played at {speed:.2f}x",
    )


if __name__ == "__main__":
    main()

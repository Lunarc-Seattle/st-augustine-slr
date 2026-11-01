"""20 s MP4 of the rise, 1920x1080 at 30 fps, for the README and LinkedIn.

The 2.5D view from persp.py is rendered at 16:9 for every foot from 0 to 9, then cross-faded
with a slow push-in. The counter, the share of city land and the landmark ledger are read from
docs/figures/compare/levels.json (written by make covers); nothing is typed in. No audio.

Needs ffmpeg with libx264 (not a project dependency): set FFMPEG to its path if it is not on PATH.
Run from the repo root after make covers: PYTHONPATH=src .venv/bin/python scripts/covers/video_rise.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
import pearls as pearl_lib
import persp

OUT = Path("outputs/covers/video")
VIDEO = Path("docs/media/st-augustine-rise.mp4")
W, H, FPS, SECONDS = 1920, 1080, 30, 20
RENDER_DPI = 200  # stills at 2400x1350, so the push-in never upsamples
T_INTRO, STEP, FADE = 2.0, 1.45, 0.6  # today hold, seconds per foot, cross-fade
ZOOM_END = 1.10
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
PAGE = "lunarc-seattle.github.io/st-augustine-slr"

DATA = json.loads(Path("docs/figures/compare/levels.json").read_text())
PCT = {lv["ft"]: lv["pct"] for lv in DATA["levels"]}
TOP = max(PCT)

INK, TEAL, ACCENT, MUTED = (43, 49, 54), (15, 110, 122), (228, 71, 43), (106, 111, 108)
BASK = "/System/Library/Fonts/Supplemental/Baskerville.ttc"
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"


def font(path, size, index):
    return ImageFont.truetype(path, size, index=index)


F_EYEBROW = font(AVENIR, 26, 2)
F_TITLE = font(BASK, 70, 0)
F_TITLE_I = font(BASK, 70, 2)
F_BIG = font(BASK, 168, 1)
F_SUB = font(AVENIR, 36, 5)
F_LEDGER = font(BASK, 34, 2)
F_LEDGER_SUB = font(AVENIR, 24, 5)
F_SMALL = font(AVENIR, 22, 5)
F_PILL = font(AVENIR, 32, 2)


def stills():
    """The 2.5D view at every foot, 16:9; pearls turn by the every-foot first flood level."""
    OUT.mkdir(parents=True, exist_ok=True)
    persp.W, persp.H = 1200, 675
    persp.PEARL_SHOW_LEVEL = False
    first = pearl_lib.load(26917, persp.EVERY_FOOT / "sites_every_foot.csv").set_index("name")["floods_at"]
    persp.PEARLS["floods_at"] = [first[n] for n in persp.PEARLS["name"]]
    images = {}
    for lv in range(TOP + 1):
        path = OUT / f"rise_{lv}ft.png"
        if not path.exists():
            fig = persp.render(lv, with_text=False)
            fig.savefig(path, dpi=RENDER_DPI, facecolor=persp.C["paper"])
            plt.close(fig)
            print("still", lv)
        images[lv] = Image.open(path).convert("RGB")
    return images


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def state(t):
    """(lower level, upper level, blend 0-1) at time t."""
    if t < T_INTRO:
        return 0, 0, 0.0
    k = (t - T_INTRO) / STEP
    i = min(int(k), TOP)
    if i >= TOP:
        return TOP, TOP, 0.0
    return i, i + 1, ease((k - i) * STEP / FADE)


def events():
    """(level, text, detail) for each landmark: low-lying ground first, then the sea."""
    out = []
    for m in DATA["landmarks"]:
        f, s = m["floods_at"], m["sea_at"]
        if f is not None and (s is None or f < s):
            out.append((f, m["name"], f"low-lying ground floods at +{f} ft"))
        if s is not None:
            out.append((s, m["name"], f"the sea arrives at +{s} ft"))
    return sorted(out, key=lambda e: e[0])


EVENTS = events()


def veil():
    """White fade behind the text: left column and bottom band."""
    x = np.arange(W)[None, :]
    y = np.arange(H)[:, None]
    left = np.clip(1 - x / (W * 0.46), 0, 1) * 0.95
    bottom = np.clip((y - H * 0.62) / (H * 0.38), 0, 1) * 0.85 * np.clip(1 - x / (W * 0.9), 0, 1)
    return Image.fromarray((255 * np.minimum(0.93, np.maximum(left, bottom))).astype(np.uint8), "L")


VEIL = veil()


def text(d, xy, s, f, fill, alpha=1.0, anchor="la"):
    d.text(xy, s, font=f, fill=(*fill, int(255 * alpha)), anchor=anchor)


def frame(images, t):
    lo, hi, a = state(t)
    img = Image.blend(images[lo], images[hi], a) if hi != lo else images[lo]
    # slow push-in toward the bayfront
    z = 1 + (ZOOM_END - 1) * ease(t / SECONDS)
    sw, sh = img.width / z, img.height / z
    cx, cy = img.width * 0.56, img.height * 0.46
    x0 = min(max(0, cx - sw / 2), img.width - sw)
    y0 = min(max(0, cy - sh / 2), img.height - sh)
    img = img.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + sw, y0 + sh))
    img.paste(Image.new("RGB", (W, H), (255, 255, 255)), mask=VEIL)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    intro = ease(t / 0.8)
    level = hi if a > 0.5 else lo
    # title
    text(d, (96, 88), "ST. AUGUSTINE, FLORIDA  ·  SEA-LEVEL RISE", F_EYEBROW, ACCENT, intro)
    text(d, (96, 128), "St. Augustine", F_TITLE, INK, intro)
    text(d, (96, 210), "under rising water", F_TITLE_I, TEAL, intro)
    # landmark ledger: each line appears when its level is reached, on a white card so the scene's labels stay behind
    shown = sum(1 for lv, _, _ in EVENTS if lv <= level)
    if shown:
        d.rounded_rectangle((76, 326, 640, 340 + 84 * shown + 8), radius=14, fill=(255, 255, 255, 215))
    y = 340
    for lv, name, detail in EVENTS:
        if lv > level:
            break
        reached = T_INTRO + (lv - 1) * STEP + FADE / 2
        al = ease((t - reached) / 0.35)
        sea = detail.startswith("the sea")
        cx_, cy_ = 112, y + 22
        d.ellipse(
            (cx_ - 11, cy_ - 11, cx_ + 11, cy_ + 11),
            fill=(*ACCENT, int(255 * al)) if sea else (255, 255, 255, int(255 * al)),
            outline=(*ACCENT, int(255 * al)),
            width=4,
        )
        text(d, (138, y), name, F_LEDGER, INK, al)
        text(d, (140, y + 42), detail, F_LEDGER_SUB, MUTED, al)
        y += 84
    # counter
    big = "Today" if level == 0 else f"+{level} ft"
    text(d, (92, H - 120), big, F_BIG, TEAL if level else INK, intro, anchor="ls")
    sub = (
        f"{DATA['today_km2']:.2f} km² of city land already under water at high tide"
        if level == 0
        else f"{PCT[level]:.1f}% of the city's land newly under water"
    )
    text(d, (98, H - 70), sub, F_SUB, ACCENT if level else INK, intro)
    # tide staff on the right
    sx, top_y, bot_y = W - 86, 230, H - 230
    d.rounded_rectangle((sx - 7, top_y, sx + 7, bot_y), radius=7, fill=(255, 255, 255, 230), outline=(51, 57, 63, 60))
    cont = lo + (hi - lo) * a
    fy = bot_y - (bot_y - top_y) * cont / TOP
    d.rounded_rectangle((sx - 7, fy, sx + 7, bot_y), radius=7, fill=(24, 167, 181, 255))
    for f in (0, 3, 6, 9):
        yy = bot_y - (bot_y - top_y) * f / TOP
        text(d, (sx - 22, yy), "today" if f == 0 else f"+{f}", F_SMALL, MUTED, 1, anchor="rm")
    # closing card
    end = ease((t - (T_INTRO + TOP * STEP + 0.6)) / 0.6)
    if end > 0:
        label = f"Explore it interactively:  {PAGE}"
        w = d.textlength(label, font=F_PILL)
        bx, by = W - 96 - w - 56, H - 150
        d.rounded_rectangle((bx, by, bx + w + 56, by + 76), radius=38, fill=(43, 49, 54, int(240 * end)))
        text(d, (bx + 28, by + 38), label, F_PILL, (255, 255, 255), end, anchor="lm")
    text(
        d,
        (W - 96, 70),
        "NOAA SLR Viewer · Census TIGER/Line · © OpenStreetMap · heights and water ×5",  # noqa: RUF001 (multiplication sign on screen)
        F_SMALL,
        MUTED,
        0.9,
        anchor="rm",
    )
    img = img.convert("RGBA")
    img.alpha_composite(lay)
    return img.convert("RGB")


def main():
    images = stills()
    VIDEO.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{W}x{H}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "17",
        "-vf",
        "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
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
    ]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = FPS * SECONDS
    for i in range(n):
        enc.stdin.write(frame(images, i / FPS).tobytes())
        if i % 60 == 0:
            print(f"frame {i}/{n}", flush=True)
    enc.stdin.close()
    if enc.wait():
        raise SystemExit("ffmpeg failed")
    frame(images, SECONDS - 0.5).save(OUT / "rise_last_frame.png")
    print(VIDEO, f"{VIDEO.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Break a reference VIDEO into frames for analysis. Needs PyAV + Pillow
(`python3 -m pip install --user av pillow`; PyAV ships its own ffmpeg libs).

Prints fps / size / duration and a motion timeline (mean frame difference),
saves every Nth frame and a labelled contact sheet. Look at the sheet first,
then measure single frames with analyze_image.py.

Usage:
  video_frames.py VIDEO --out DIR [--every 3] [--sheet-step 4] [--cols 5]
Timing note: convert source frames to timeline frames:  f_tl = (f_src - f_start) * fps_tl / fps_src
"""
import argparse
import os
import sys

try:
    import av
    from PIL import Image, ImageChops, ImageDraw, ImageStat
except ImportError:
    sys.exit("needs PyAV and Pillow: python3 -m pip install --user av pillow")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=int, default=3, help="save every Nth source frame")
    ap.add_argument("--sheet-step", type=int, default=4, help="every Nth SAVED frame goes on the sheet")
    ap.add_argument("--cols", type=int, default=5)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    c = av.open(a.video)
    s = c.streams.video[0]
    fps = float(s.average_rate)
    print(f"fps {fps:g}  frames {s.frames}  size {s.width}x{s.height}  duration {float(c.duration) / 1e6:.2f}s")
    saved, prev, motion = [], None, []
    for i, fr in enumerate(c.decode(s)):
        if i % a.every:
            continue
        im = fr.to_image()
        p = os.path.join(a.out, f"f{i:05d}.png")
        im.save(p)
        saved.append((i, p))
        small = im.convert("L").resize((240, max(1, 240 * im.height // im.width)))
        if prev is not None:
            motion.append((i, ImageStat.Stat(ImageChops.difference(small, prev)).mean[0]))
        prev = small

    print("motion (source frame: diff), only frames that change:")
    print(" ".join(f"{i}:{d:.1f}" for i, d in motion if d > 0.3) or "  none")

    sel = saved[::a.sheet_step]
    W = 320
    H = W * s.height // s.width
    rows = (len(sel) + a.cols - 1) // a.cols
    sheet = Image.new("RGB", (a.cols * W, rows * (H + 16)), "white")
    dr = ImageDraw.Draw(sheet)
    for k, (i, p) in enumerate(sel):
        x, y = (k % a.cols) * W, (k // a.cols) * (H + 16)
        sheet.paste(Image.open(p).convert("RGB").resize((W, H)), (x, y + 16))
        dr.text((x + 4, y + 2), f"frame {i}  t={i / fps:.2f}s", fill="black")
    sp = os.path.join(a.out, "sheet.png")
    sheet.save(sp)
    print(f"saved {len(saved)} frames, contact sheet -> {sp}")


if __name__ == "__main__":
    main()

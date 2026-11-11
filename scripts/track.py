#!/usr/bin/env python3
"""Track elements of a reference VIDEO and extract animation stages.
Needs PyAV + Pillow (`python3 -m pip install --user av pillow`).

For every element: bounding box per frame (pixels within a color tolerance,
optionally inside a region), motion stages (where width, height or center
change), and for each stage the closest easing curve. Frames are converted to
timeline frames: f_tl = (f_src - start) * fps_tl / fps_src.

Usage:
  track.py VIDEO|FRAMES_DIR --el card=#201f20:30 --el photo=#4fa8c4:40@700,150,520,560 \\
           [--every 2] [--fps-tl 30] [--start auto|<src frame>] [--json out.json]

FRAMES_DIR: a folder of fNNNNN.png frames from video_frames.py (NNNNN = source
frame number); pass --fps-src then.

Element spec: NAME=#RRGGBB[:tolerance][@x,y,w,h]  (tolerance = max channel diff, default 24)
"""
import argparse
import glob
import json
import os
import re
import sys

try:
    import av
    from PIL import Image, ImageChops
except ImportError:
    sys.exit("needs PyAV and Pillow: python3 -m pip install --user av pillow")

CURVES = {
    "linear": lambda u: u,
    "in3": lambda u: u ** 3,
    "out3": lambda u: 1 - (1 - u) ** 3,
    "io3": lambda u: 4 * u ** 3 if u < 0.5 else 1 - 4 * (1 - u) ** 3,
    "io4": lambda u: 8 * u ** 4 if u < 0.5 else 1 - 8 * (1 - u) ** 4,
    "back": lambda u: 1 + 2.70158 * (u - 1) ** 3 + 1.70158 * (u - 1) ** 2,
}


def parse_el(spec):
    name, _, rest = spec.partition("=")
    color, _, region = rest.partition("@")
    hexc, _, tol = color.partition(":")
    hexc = hexc.lstrip("#")
    rgb = tuple(int(hexc[i:i + 2], 16) for i in (0, 2, 4))
    box = tuple(int(v) for v in region.split(",")) if region else None
    return {"name": name, "rgb": rgb, "tol": int(tol or 24), "region": box}


def bbox(img, el):
    if el["region"]:
        x, y, w, h = el["region"]
        img = img.crop((x, y, x + w, y + h))
        ox, oy = x, y
    else:
        ox = oy = 0
    diff = ImageChops.difference(img, Image.new("RGB", img.size, el["rgb"]))
    r, g, b = diff.split()
    mx = ImageChops.lighter(ImageChops.lighter(r, g), b)
    mask = mx.point(lambda v: 255 if v <= el["tol"] else 0)
    bb = mask.getbbox()
    if not bb:
        return None
    x0, y0, x1, y1 = bb
    return {"x0": x0 + ox, "y0": y0 + oy, "x1": x1 + ox, "y1": y1 + oy,
            "w": x1 - x0, "h": y1 - y0, "cx": ox + (x0 + x1) / 2, "cy": oy + (y0 + y1) / 2}


def stages(track, key, eps=1.5, gap=3, min_len=3):
    """Contiguous frame ranges where track[key] changes by more than eps."""
    pts = [(f, b[key]) for f, b in track if b]
    moving = [(pts[i][0], pts[i + 1][0]) for i in range(len(pts) - 1) if abs(pts[i + 1][1] - pts[i][1]) > eps]
    out = []
    for a, b in moving:
        if out and a - out[-1][1] <= gap:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return [s for s in out if s[1] - s[0] >= min_len]


def fit_curve(track, key, f0, f1):
    pts = [(f, b[key]) for f, b in track if b and f0 <= f <= f1]
    if len(pts) < 3:
        return None
    v0, v1 = pts[0][1], pts[-1][1]
    if v1 == v0:
        return None
    best = None
    for name, fn in CURVES.items():
        err = sum((fn((f - f0) / (f1 - f0)) - (v - v0) / (v1 - v0)) ** 2 for f, v in pts) / len(pts)
        if best is None or err < best[1]:
            best = (name, err)
    return {"curve": best[0], "rmse": round(best[1] ** 0.5, 3), "from": round(v0, 1), "to": round(v1, 1)}


def frames(a):
    """Yield (source frame number, RGB image) from a video or a frames folder."""
    if os.path.isdir(a.video):
        if not a.fps_src:
            sys.exit("--fps-src is required for a frames folder")
        files = sorted(glob.glob(os.path.join(a.video, "f*.png")))
        for f in files:                      # already subsampled by video_frames.py: use all
            yield int(re.search(r"f(\d+)\.png$", f).group(1)), Image.open(f).convert("RGB")
        return
    c = av.open(a.video)
    s = c.streams.video[0]
    a.fps_src = float(s.average_rate)
    for i, fr in enumerate(c.decode(s)):
        if i % a.every == 0:
            yield i, fr.to_image().convert("RGB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--el", action="append", required=True, help="NAME=#RRGGBB[:tol][@x,y,w,h]")
    ap.add_argument("--every", type=int, default=2, help="use every Nth video frame (video input only)")
    ap.add_argument("--fps-tl", type=float, default=30)
    ap.add_argument("--start", default="auto", help="source frame that becomes timeline frame 0")
    ap.add_argument("--fps-src", type=float, help="source fps when reading a frames folder")
    ap.add_argument("--json")
    a = ap.parse_args()
    els = [parse_el(s) for s in a.el]

    tracks = {e["name"]: [] for e in els}
    for i, img in frames(a):
        for e in els:
            tracks[e["name"]].append((i, bbox(img, e)))
    fps = a.fps_src

    result = {"fps_src": fps, "fps_tl": a.fps_tl, "elements": {}}
    all_stages = []
    for name, tr in tracks.items():
        el_st = []
        for key in ("w", "h", "cx", "cy"):
            for f0, f1 in stages(tr, key):
                fit = fit_curve(tr, key, f0, f1)
                if fit:
                    el_st.append({"param": key, "src": [f0, f1], **fit})
                    all_stages.append(f0)
        result["elements"][name] = {"stages": sorted(el_st, key=lambda x: x["src"][0]),
                                    "track": [(f, b) for f, b in tr]}
    start = (min(all_stages) if all_stages else 0) if a.start == "auto" else int(a.start)
    k = a.fps_tl / fps
    result["start_src"] = start
    print(f"fps {fps:g} -> timeline {a.fps_tl:g}; timeline frame 0 = source frame {start}")
    for name, data in result["elements"].items():
        print(f"\n{name}:")
        if not data["stages"]:
            print("  no motion (or element not found)")
        for st in data["stages"]:
            st["tl"] = [round((st["src"][0] - start) * k, 1), round((st["src"][1] - start) * k, 1)]
            print(f"  {st['param']:>2}  src {st['src'][0]:>4}-{st['src'][1]:<4} tl {st['tl'][0]:>6}-{st['tl'][1]:<6} "
                  f"{st['from']:>7} -> {st['to']:<7} {st['curve']:6} (rmse {st['rmse']})")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(result, f, indent=1)
        print(f"\n-> {a.json}")


if __name__ == "__main__":
    main()

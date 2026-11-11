#!/usr/bin/env python3
"""Compare a screenshot from Resolve with the reference, element by element.
Needs Pillow.

1. Scale the render to the reference (--scale, or from the widths when the
   aspect ratios match) and find the best shift by brute-force matching of
   downscaled grayscale images (or pass --shift dx,dy).
2. Save a difference heatmap and an onion-skin overlay.
3. For every element (color + tolerance, optional region in REFERENCE px):
   bounding box in both images, center offset in px, width/height ratio and
   median color of each.

Usage:
  compare.py ref.png render.png --el "card=#201f20:14" --el "name=#eaeaea:20@650,700,620,110"
             [--el-render "card=#1f1f1f:14"] [--scale S] [--shift dx,dy] [--out DIR] [--json report.json]

--el-render overrides the color/tolerance used in the render for an element
with the same name (when Resolve shifts colors slightly). Offsets are in
reference px: positive dx = render is to the right, dy = lower.
"""
import argparse
import json
import os
import sys

try:
    from PIL import Image, ImageChops, ImageOps, ImageStat
except ImportError:
    sys.exit("needs Pillow: python3 -m pip install --user pillow")


def parse_el(spec):
    name, _, rest = spec.partition("=")
    color, _, region = rest.partition("@")
    hexc, _, tol = color.partition(":")
    hexc = hexc.lstrip("#")
    return {"name": name, "rgb": tuple(int(hexc[i:i + 2], 16) for i in (0, 2, 4)), "tol": int(tol or 24),
            "region": tuple(int(v) for v in region.split(",")) if region else None}


def mask_of(img, el, region=None):
    diff = ImageChops.difference(img, Image.new("RGB", img.size, el["rgb"]))
    r, g, b = diff.split()
    m = ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v <= el["tol"] else 0)
    if region:
        x, y, w, h = region
        keep = Image.new("L", img.size, 0)
        keep.paste(255, (x, y, x + w, y + h))
        m = ImageChops.multiply(m, keep)
    return m


def measure(img, el, region):
    m = mask_of(img, el, region)
    bb = m.getbbox()
    if not bb:
        return None
    x0, y0, x1, y1 = bb
    data = (lambda im: list(im.get_flattened_data()) if hasattr(im, "get_flattened_data") else list(im.getdata()))
    px = [p for p, keep in zip(data(img.crop(bb)), data(m.crop(bb))) if keep]
    med = tuple(sorted(c[i] for c in px)[len(px) // 2] for i in range(3)) if px else (0, 0, 0)
    return {"box": [x0, y0, x1 - x0, y1 - y0], "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2,
            "w": x1 - x0, "h": y1 - y0, "color": "#%02x%02x%02x" % med}


def _search(ref, ren, small, center, rng):
    """Best (err, dx, dy) in ref px around `center` (ref px), searching ±rng small px."""
    k = small / ref.width
    a = ImageOps.grayscale(ref).resize((small, max(1, int(ref.height * k))))
    b = ImageOps.grayscale(ren).resize((max(1, int(ren.width * k)), max(1, int(ren.height * k))))
    cx, cy = round(center[0] * k), round(center[1] * k)
    best = (None, 0, 0)
    for dy in range(cy - rng, cy + rng + 1):
        for dx in range(cx - rng, cx + rng + 1):
            canvas = Image.new("L", a.size, 0)
            canvas.paste(b, (dx, dy))
            ov = (max(0, dx), max(0, dy), min(a.width, dx + b.width), min(a.height, dy + b.height))
            if ov[2] - ov[0] < a.width * 0.5 or ov[3] - ov[1] < a.height * 0.5:
                continue
            err = ImageStat.Stat(ImageChops.difference(a.crop(ov), canvas.crop(ov))).mean[0]
            if best[0] is None or err < best[0]:
                best = (err, dx / k, dy / k)
    return best


def best_shift(ref, ren, max_frac=0.15):
    """Translation of `ren` (already scaled) that best matches `ref`, in ref px:
    coarse search at 200 px width, then refine at 1/4 and full resolution."""
    _, dx, dy = _search(ref, ren, 200, (0, 0), int(200 * max_frac))
    for small in (min(ref.width, 500), ref.width):
        step = ref.width / small
        _, dx, dy = _search(ref, ren, small, (dx, dy), max(2, int(2.5 * ref.width / 200 / step)))
    return round(dx), round(dy)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ref")
    ap.add_argument("render")
    ap.add_argument("--el", action="append", default=[])
    ap.add_argument("--el-render", action="append", default=[])
    ap.add_argument("--scale", type=float, help="render px -> reference px factor")
    ap.add_argument("--shift", help="dx,dy of the scaled render in reference px (skip auto search)")
    ap.add_argument("--out", default="compare-out")
    ap.add_argument("--json")
    a = ap.parse_args()

    ref = Image.open(a.ref).convert("RGB")
    ren = Image.open(a.render).convert("RGB")
    scale = a.scale
    if scale is None:
        ra, rb = ref.width / ref.height, ren.width / ren.height
        if abs(ra - rb) / ra > 0.02:
            sys.exit(f"aspect ratios differ ({ra:.3f} vs {rb:.3f}): pass --scale (render px -> reference px)")
        scale = ref.width / ren.width
    ren_s = ren.resize((max(1, round(ren.width * scale)), max(1, round(ren.height * scale))), Image.LANCZOS)
    dx, dy = (tuple(int(v) for v in a.shift.split(",")) if a.shift else best_shift(ref, ren_s))
    aligned = Image.new("RGB", ref.size, (0, 0, 0))
    aligned.paste(ren_s, (dx, dy))

    os.makedirs(a.out, exist_ok=True)
    diff = ImageChops.difference(ref, aligned)
    heat = ImageOps.autocontrast(ImageOps.grayscale(diff), cutoff=1)
    heat.save(os.path.join(a.out, "diff.png"))
    Image.blend(ref, aligned, 0.5).save(os.path.join(a.out, "onion.png"))

    overrides = {e["name"]: e for e in map(parse_el, a.el_render)}
    report = {"scale": round(scale, 4), "shift": [dx, dy], "elements": {}}
    print(f"scale {scale:.4f}, shift {dx},{dy} (reference px)")
    print(f"{'element':14s} {'dx':>6s} {'dy':>6s} {'w ratio':>8s} {'h ratio':>8s}  ref color -> render color")
    for el in map(parse_el, a.el):
        r = measure(ref, el, el["region"])
        q = measure(aligned, overrides.get(el["name"], el), el["region"])
        row = {"ref": r, "render": q}
        if r and q:
            row.update(dx=round(q["cx"] - r["cx"], 1), dy=round(q["cy"] - r["cy"], 1),
                       w_ratio=round(q["w"] / r["w"], 3) if r["w"] else None,
                       h_ratio=round(q["h"] / r["h"], 3) if r["h"] else None)
            print(f"{el['name']:14s} {row['dx']:6.1f} {row['dy']:6.1f} {row['w_ratio']:8.3f} {row['h_ratio']:8.3f}"
                  f"  {r['color']} -> {q['color']}")
        else:
            print(f"{el['name']:14s} not found in {'reference' if not r else 'render'}")
        report["elements"][el["name"]] = row
    found = [r for r in report["elements"].values() if "dx" in r]
    if len(found) >= 2:
        mdx = sorted(r["dx"] for r in found)[len(found) // 2]
        mdy = sorted(r["dy"] for r in found)[len(found) // 2]
        report["common_offset"] = [mdx, mdy]
        print(f"\ncommon offset (median): {mdx:+.1f}, {mdy:+.1f} px — move the whole template by this;")
        print("per-element error after removing it:")
        for name, r in report["elements"].items():
            if "dx" in r:
                print(f"  {name:12s} {r['dx'] - mdx:+6.1f} {r['dy'] - mdy:+6.1f}")
    print(f"\n-> {a.out}/diff.png, {a.out}/onion.png")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()

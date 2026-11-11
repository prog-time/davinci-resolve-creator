#!/usr/bin/env python3
"""Measure a reference image for a Resolve template. Needs Pillow.

Prints JSON: background color, palette, content bbox, element boxes (with
estimated corner radius), gaps between rows, scale factor to the target frame.

Usage:
  analyze_image.py IMG [--frame 1920x1080] [--fit 0.9] [--threshold 24]
                       [--region x,y,w,h ...] [--sample x,y ...]
                       [--crop x,y,w,h --zoom 3 --crop-out crop.png]

  --region  color stats (median/min/max HEX) of a rectangle, repeatable
  --sample  exact pixel color, repeatable
  --roi     analyze only this box (e.g. the card) to find elements INSIDE it;
            background = the box's border color; output coords stay in image px
  --crop    save a zoomed crop to look at details (radius, icons, text)
All coordinates are image pixels, Y from the top.
"""
import argparse
import json
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is required: python3 -m pip install --user pillow")


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(x) for x in c[:3])


def median(vals):
    s = sorted(vals)
    return s[len(s) // 2]


def stats(px):
    chans = list(zip(*px))
    return {"median": hexc([median(c) for c in chans]),
            "min": hexc([min(c) for c in chans]),
            "max": hexc([max(c) for c in chans]),
            "pixels": len(px)}


def runs(flags, min_len=2, merge_gap=2):
    out, start = [], None
    for i, f in enumerate(flags + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            if out and start - out[-1][1] <= merge_gap:
                out[-1] = (out[-1][0], i)
            else:
                out.append((start, i))
            start = None
    return [(a, b) for a, b in out if b - a >= min_len]


def parse_box(s):
    v = [int(float(x)) for x in s.split(",")]
    if len(v) != 4:
        raise argparse.ArgumentTypeError("expected x,y,w,h")
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--frame", default="1920x1080")
    ap.add_argument("--fit", type=float, default=0.9, help="content fills this share of the frame")
    ap.add_argument("--threshold", type=int, default=24, help="color distance from background")
    ap.add_argument("--colors", type=int, default=8)
    ap.add_argument("--region", type=parse_box, action="append", default=[])
    ap.add_argument("--sample", action="append", default=[])
    ap.add_argument("--roi", type=parse_box)
    ap.add_argument("--crop", type=parse_box)
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--crop-out", default="crop.png")
    a = ap.parse_args()

    full = Image.open(a.image).convert("RGB")
    res = {"image": {"width": full.width, "height": full.height}}
    ox, oy = 0, 0
    img = full
    if a.roi:
        ox, oy, rw, rh = a.roi
        img = full.crop((ox, oy, ox + rw, oy + rh))
        res["roi"] = a.roi
    W, H = img.size
    px = img.load()

    border = [px[x, 0] for x in range(W)] + [px[x, H - 1] for x in range(W)] + \
             [px[0, y] for y in range(H)] + [px[W - 1, y] for y in range(H)]
    bg = tuple(median(c) for c in zip(*border))
    res["background"] = hexc(bg)

    q = img.quantize(colors=a.colors)
    pal = q.getpalette()
    counts = sorted(q.getcolors(), reverse=True)
    res["palette"] = [{"hex": hexc(pal[i * 3:i * 3 + 3]), "share": round(n / (W * H), 4)} for n, i in counts]

    def is_fg(c):
        return max(abs(c[0] - bg[0]), abs(c[1] - bg[1]), abs(c[2] - bg[2])) > a.threshold

    fg = [[is_fg(px[x, y]) for x in range(W)] for y in range(H)]
    rows = [any(r) for r in fg]
    cols = [any(fg[y][x] for y in range(H)) for x in range(W)]
    rr, cc = runs(rows), runs(cols)
    if rr and cc:
        bx0, bx1, by0, by1 = cc[0][0], cc[-1][1], rr[0][0], rr[-1][1]
        res["content_bbox"] = {"x": bx0 + ox, "y": by0 + oy, "w": bx1 - bx0, "h": by1 - by0}
    else:
        bx0, by0, bx1, by1 = 0, 0, W, H
        res["content_bbox"] = None

    # element boxes: row bands, then column runs inside each band
    boxes = []
    for y0, y1 in rr:
        band_cols = [any(fg[y][x] for y in range(y0, y1)) for x in range(W)]
        for x0, x1 in runs(band_cols, merge_gap=6):
            ys = [y for y in range(y0, y1) if any(fg[y][x0:x1])]
            top, bot = ys[0], ys[-1] + 1
            first = next((x for x in range(x0, x1) if fg[top][x]), x0)
            region = [px[x, y] for y in range(top, bot) for x in range(x0, x1) if fg[y][x]]
            boxes.append({"x": x0 + ox, "y": top + oy, "w": x1 - x0, "h": bot - top,
                          "radius_est": first - x0, **stats(region)})
    res["elements"] = boxes[:60]
    res["row_gaps"] = [rr[i + 1][0] - rr[i][1] for i in range(len(rr) - 1)]

    fw, fh = (int(v) for v in a.frame.lower().split("x"))
    cw, ch = (bx1 - bx0), (by1 - by0)
    s = min(fw * a.fit / cw, fh * a.fit / ch) if cw and ch else 1.0
    res["scale"] = {"frame": [fw, fh], "factor": round(s, 4),
                    "content_in_frame": [round(cw * s), round(ch * s)],
                    "map": f"frame_x = {round((fw - cw * s) / 2, 1)} + (x - {bx0 + ox}) * {round(s, 4)}; "
                           f"frame_y = {round((fh - ch * s) / 2, 1)} + (y - {by0 + oy}) * {round(s, 4)}"}
    px, W, H = full.load(), full.width, full.height  # regions/samples/crop use the full image

    res["regions"] = []
    for x, y, w, h in a.region:
        reg = [px[i, j] for j in range(max(0, y), min(H, y + h)) for i in range(max(0, x), min(W, x + w))]
        res["regions"].append({"box": [x, y, w, h], **(stats(reg) if reg else {})})
    res["samples"] = []
    for s_ in a.sample:
        x, y = (int(float(v)) for v in s_.split(","))
        res["samples"].append({"xy": [x, y], "hex": hexc(px[x, y])})

    if a.crop:
        x, y, w, h = a.crop
        c = full.crop((x, y, x + w, y + h)).resize((w * a.zoom, h * a.zoom), Image.NEAREST)
        c.save(a.crop_out)
        res["crop"] = a.crop_out

    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

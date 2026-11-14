"""Draw the scrapbook decor as transparent PNGs (frame-pixel size, rotation baked in).

Run with a Python that has Pillow:  python make_assets.py PHOTO OUT_DIR
Geometry comes from geometry.py (shared with spec.py).
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geometry import G  # noqa: E402

random.seed(7)
SS = 2  # supersampling


def shadowed(img, blur=10, offset=(6, 10), alpha=110, pad=40):
    """Add a soft drop shadow; returns a bigger canvas (pad on each side)."""
    w, h = img.size
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: v * alpha // 255)
    sh.paste((0, 0, 0, 255), (pad + offset[0], pad + offset[1]), a)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh)
    out.alpha_composite(img, (pad, pad))
    return out


def torn_poly(w, h, amp=7, step=14, sides="lrb"):
    pts = []
    for x in range(0, w + 1, step):   # top (straight unless 't')
        pts.append((x, random.uniform(0, amp) if "t" in sides else 0))
    for y in range(0, h + 1, step):   # right
        pts.append((w - (random.uniform(0, amp) if "r" in sides else 0), y))
    for x in range(w, -1, -step):     # bottom
        pts.append((x, h - (random.uniform(0, amp) if "b" in sides else 0)))
    for y in range(h, -1, -step):     # left
        pts.append(((random.uniform(0, amp) if "l" in sides else 0), y))
    return pts


def noise_tex(img, strength=6):
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a:
                n = random.randint(-strength, strength)
                px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)), max(0, min(255, b + n)), a)
    return img


def paper():
    w, h = G["paper_w"], G["paper_h"]
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(x * SS, y * SS) for x, y in torn_poly(w, h, amp=9, sides="lrbt")], fill=(251, 251, 249, 255))
    for k in range(G["line_n"]):                                  # ruled lines
        y = (G["line_y0"] + k * G["line_step"]) * SS
        d.line([(30 * SS, y), ((w - 30) * SS, y)], fill=(200, 205, 214, 255), width=2 * SS)
    for k in range(G["hole_n"]):                                  # punched holes -> transparent
        cx, cy, r = (G["hole_x0"] + k * G["hole_step"]) * SS, G["hole_y"] * SS, G["hole_d"] * SS / 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 0))
    img = img.resize((w, h), Image.LANCZOS)
    return shadowed(noise_tex(img, 4), blur=14, offset=(0, 12), alpha=120)


def fit_crop(photo, box_w, box_h, focus=(0.48, 0.32), zoom=1.0):
    pw, ph = photo.size
    scale = max(box_w / pw, box_h / ph) * zoom
    rw, rh = int(pw * scale), int(ph * scale)
    im = photo.resize((rw, rh), Image.LANCZOS)
    x0 = int(min(max(focus[0] * rw - box_w / 2, 0), rw - box_w))
    y0 = int(min(max(focus[1] * rh - box_h / 2, 0), rh - box_h))
    return im.crop((x0, y0, x0 + box_w, y0 + box_h))


def polaroid(photo, w, h, angle, focus, zoom):
    card = Image.new("RGBA", (w, h), (247, 247, 244, 255))
    m = int(w * 0.075)
    win = fit_crop(photo, w - 2 * m, h - m - int(h * 0.15), focus, zoom)
    card.paste(win, (m, m))
    card = noise_tex(card, 3)
    return shadowed(card, blur=10, offset=(6, 10), alpha=120).rotate(angle, resample=Image.BICUBIC, expand=True)


def clip(angle):
    w, h = 70, 190
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col, lw = (150, 158, 168, 255), 5 * SS

    def loop(x0, y0, x1, y1):
        r = (x1 - x0) / 2
        d.arc([x0, y0, x1, y0 + 2 * r], 180, 360, fill=col, width=lw)
        d.arc([x0, y1 - 2 * r, x1, y1], 0, 180, fill=col, width=lw)
        return r
    s = SS
    r = loop(6 * s, 4 * s, 64 * s, 186 * s)            # outer loop
    d.line([(6 * s, (4 + 29) * s), (6 * s, (186 - 29) * s)], fill=col, width=lw)
    d.line([(64 * s, (4 + 29) * s), (64 * s, 120 * s)], fill=col, width=lw)
    loop(18 * s, 20 * s, 52 * s, 170 * s)               # inner loop
    d.line([(18 * s, 37 * s), (18 * s, 153 * s)], fill=col, width=lw)
    d.line([(52 * s, 37 * s), (52 * s, 150 * s)], fill=col, width=lw)
    img = img.resize((w, h), Image.LANCZOS)
    return shadowed(img, blur=3, offset=(3, 4), alpha=90, pad=12).rotate(angle, resample=Image.BICUBIC, expand=True)


def tape(angle):
    w, h = G["tape_w"], G["tape_h"]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(0, 0)] + [(x, random.uniform(0, 6)) for x in range(10, w, 10)] + [(w, 0)]
    pts += [(w - random.uniform(0, 14), y) for y in range(0, h, 7)] + [(w, h)]
    pts += [(x, h - random.uniform(0, 6)) for x in range(w, 0, -10)] + [(0, h)]
    pts += [(random.uniform(0, 14), y) for y in range(h, 0, -7)]
    d.polygon(pts, fill=(22, 22, 24, 250))
    for _ in range(140):                                       # scratches / glare
        x, y = random.uniform(10, w - 10), random.uniform(8, h - 8)
        L = random.uniform(5, 40)
        d.line([(x, y), (x + L, y + random.uniform(-2, 2))], fill=(210, 210, 215, random.randint(30, 120)), width=1)
    img = img.filter(ImageFilter.SMOOTH)
    return shadowed(img, blur=6, offset=(4, 6), alpha=110, pad=16).rotate(angle, resample=Image.BICUBIC, expand=True)


def sticky(angle):
    w, h = G["sticky_w"], G["sticky_h"]
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grad = Image.new("RGBA", (w, h))
    gd = ImageDraw.Draw(grad)
    for y in range(h):
        k = y / h
        gd.line([(0, y), (w, y)], fill=(int(248 - 8 * k), int(206 - 14 * k), int(84 - 10 * k), 255))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon([(0, 0), (w, 0), (w, h - 26), (w - 30, h), (0, h)], fill=255)
    img.paste(grad, (0, 0), m)
    ImageDraw.Draw(img).polygon([(w, h - 26), (w - 30, h), (w - 30, h - 26)], fill=(214, 170, 60, 255))  # curl
    return shadowed(noise_tex(img, 3), blur=10, offset=(5, 9), alpha=110).rotate(angle, resample=Image.BICUBIC,
                                                                                 expand=True)


def pin():
    s = 56
    img = Image.new("RGBA", (s * SS, s * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([10 * SS, 8 * SS, 46 * SS, 44 * SS], fill=(205, 30, 38, 255))
    d.ellipse([16 * SS, 12 * SS, 30 * SS, 24 * SS], fill=(255, 140, 140, 200))
    img = img.resize((s, s), Image.LANCZOS)
    return shadowed(img, blur=4, offset=(4, 6), alpha=120, pad=12)


def underline():
    w, h = G["ul_w"], 60
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(x * SS, (30 + 6 * math.sin(x / 70.0) + random.uniform(-1, 1)) * SS) for x in range(12, w - 12, 6)]
    for k, wdt in ((0, 16), (1, 12)):
        off = [(x, y + (k * 7 - 3) * SS) for x, y in pts]
        d.line(off, fill=(214, 44, 40, 235 - 40 * k), width=wdt * SS, joint="curve")
    return img.resize((w, h), Image.LANCZOS)


def main():
    photo = Image.open(sys.argv[1]).convert("RGB")
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)
    items = {
        "paper": paper(),
        "polaroid_l": polaroid(photo, G["pl_w"], G["pl_h"], G["pl_angle"], (0.47, 0.28), 1.35),
        "polaroid_r": polaroid(photo, G["pr_w"], G["pr_h"], G["pr_angle"], (0.5, 0.45), 1.0),
        "clip_l": clip(G["clip_l_angle"]),
        "clip_r": clip(G["clip_r_angle"]),
        "tape": tape(G["tape_angle"]),
        "sticky": sticky(G["sticky_angle"]),
        "pin": pin(),
        "underline": underline(),
    }
    for name, im in items.items():
        p = os.path.join(out, f"sb-{name}.png")
        im.save(p)
        print(f"{p}: {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main()

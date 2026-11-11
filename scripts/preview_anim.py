#!/usr/bin/env python3
"""Animated preview of a template without Resolve. Needs Pillow + lupa.

Evaluates every Fusion expression with a real Lua runtime (time, comp.RenderEnd,
iif, min/max, math, string, Point, Text, references to other nodes' inputs and
UserControls) and renders the node graph frame by frame:
Background (+ gradient) with Rectangle/Ellipse masks (corner radius, soft edge,
outline), Text+ (font, size, anchors, color, EffectMask), Loader images,
Merge (Center/Size placement, Blend, EffectMask) and Transform (Center as an
offset, Pivot, Size, Angle). Other tools pass their input through.

Approximate: no Fusion filtering, CharacterSpacing ignored, LineSpacing approximated.

Usage:
  preview_anim.py SPEC.py [--variant NAME] [--frames 150] [--step 2] [--scale 0.25]
                  [--out DIR] [--sheet-every 10]
Outputs DIR/<Name>.gif and DIR/<Name>-frames.png (contact sheet with frame numbers).
"""
import argparse
import importlib.util
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fusion_lib as fl  # noqa: E402

try:
    import lupa
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    sys.exit("needs Pillow and lupa: python3 -m pip install --user pillow lupa")

LUA_PRELUDE = """
local function mk(getter)
  return setmetatable({}, { __index = function(_, k) return getter(k) end })
end
function Point(x, y) return { X = x, Y = y } end
function Text(s) return s end
function iif(c, a, b) if c then return a else return b end end
min, max, abs, floor, ceil = math.min, math.max, math.abs, math.floor, math.ceil
return mk
"""


class Evaluator:
    """Input values per frame: static values or Lua-evaluated expressions."""

    def __init__(self, tools, render_end):
        self.by = {t.name: t for t in tools}
        self.lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        self.mk = self.lua.execute(LUA_PRELUDE)
        self.g = self.lua.globals()
        self.render_end = render_end
        self.cache, self.compiled, self.busy = {}, {}, set()
        self.time = 0
        for name in self.by:
            self.g[name] = self.mk(self._getter(name))
        self.g["comp"] = self.lua.table_from({"RenderEnd": render_end, "RenderStart": 0})

    def _getter(self, node):
        def get(key):
            v = self.value(node, key)
            if isinstance(v, tuple) and len(v) == 2:
                return self.lua.table_from({"X": v[0], "Y": v[1]})
            if isinstance(v, str):
                return self.lua.table_from({"Value": v})
            return v
        return get

    def at(self, frame):
        self.time = frame
        self.g["time"] = frame
        self.cache.clear()

    def _compile(self, expr):
        if expr not in self.compiled:
            code = expr[1:] if expr.startswith(":") else "return " + expr
            fn = self.lua.eval(f"function(src) return load(src, 'expr', 't', _G) end")(code)
            if fn is None:
                raise ValueError(f"cannot compile expression: {expr[:80]}")
            self.compiled[expr] = fn
        return self.compiled[expr]

    def value(self, node, key, default=None):
        k = (node, key)
        if k in self.cache:
            return self.cache[k]
        t = self.by.get(node)
        inp = t.inputs.get(key) if t else None
        if inp is None:
            return default
        if inp.expr and k not in self.busy:
            self.busy.add(k)
            try:
                v = self._compile(inp.expr)()
                if lupa.lua_type(v) == "table":
                    v = (float(v["X"]), float(v["Y"])) if v["X"] is not None else v["Value"]
            except Exception:
                v = inp.value                               # fall back to the static value
            finally:
                self.busy.discard(k)
        else:
            v = inp.value
        if v is None:
            v = default
        self.cache[k] = v
        return v


class Renderer:
    def __init__(self, tools, ev, scale):
        self.by = {t.name: t for t in tools}
        self.ev = ev
        self.s = scale
        self.W, self.H = fl.frame()
        self.w, self.h = max(1, int(self.W * scale)), max(1, int(self.H * scale))
        self.memo = {}
        self.fonts = {}

    def v(self, node, key, default=None):
        return self.ev.value(node, key, default)

    def blank(self):
        return Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))

    def rgba(self, node, prefix, suffix=""):
        return tuple(int(255 * max(0, min(1, float(self.v(node, f"{prefix}{c}{suffix}", 1.0)))))
                     for c in ("Red", "Green", "Blue", "Alpha"))

    # ---- masks ----
    def mask(self, name):
        t = self.by.get(name)
        if t is None:
            return None
        m = Image.new("L", (self.w, self.h), 0)
        d = ImageDraw.Draw(m)
        cx, cy = self.v(name, "Center", (0.5, 0.5))
        mw = float(self.v(name, "Width", 0.1)) * self.W * self.s
        unit = self.W if t.kind == "EllipseMask" else self.H
        mh = float(self.v(name, "Height", 0.1)) * unit * self.s
        x0, y0 = cx * self.w - mw / 2, (1 - cy) * self.h - mh / 2
        box = [x0, y0, x0 + max(mw, 0), y0 + max(mh, 0)]
        if mw <= 0 or mh <= 0:
            return m
        if t.kind == "EllipseMask":
            if self.v(name, "Solid", 1) == 0:
                bw = max(1, int(round(float(self.v(name, "BorderWidth", 0.001)) * self.W * self.s)))
                d.ellipse(box, outline=255, width=bw)
            else:
                d.ellipse(box, fill=255)
        else:
            r = float(self.v(name, "CornerRadius", 0)) * min(mw, mh) / 2
            d.rounded_rectangle(box, radius=r, fill=255)
        soft = float(self.v(name, "SoftEdge", 0) or 0)
        if soft:
            m = m.filter(ImageFilter.GaussianBlur(soft * self.W * self.s))
        return m

    def apply_mask(self, img, tool):
        if "EffectMask" not in tool.inputs:
            return img
        m = self.mask(tool.inputs["EffectMask"].src)
        if m is None:
            return img
        a = img.split()[3]
        img.putalpha(Image.composite(a, Image.new("L", img.size, 0), m))
        return img

    # ---- nodes ----
    def render(self, name):
        if name in self.memo:
            return self.memo[name].copy()
        t = self.by.get(name)
        img = self.blank() if t is None else getattr(self, f"r_{t.kind}", self.r_passthrough)(t)
        self.memo[name] = img
        return img.copy()

    def src(self, t, key):
        inp = t.inputs.get(key)
        return self.render(inp.src) if inp and inp.src else self.blank()

    def r_passthrough(self, t):
        return self.src(t, "Input")

    def r_Background(self, t):
        top = self.rgba(t.name, "TopLeft")
        img = Image.new("RGBA", (self.w, self.h), top)
        if "BottomLeftRed" in t.inputs:
            bot = self.rgba(t.name, "BottomLeft")
            d = ImageDraw.Draw(img)
            for y in range(self.h):
                k = y / max(1, self.h - 1)
                d.line([(0, y), (self.w, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(top, bot)))
        return self.apply_mask(img, t)

    def font(self, family, style, px):
        key = (family, style, px)
        if key not in self.fonts:
            path = fl._find_font(family, style)
            try:
                self.fonts[key] = ImageFont.truetype(path, px) if path else ImageFont.load_default(px)
            except Exception:
                self.fonts[key] = ImageFont.load_default()
        return self.fonts[key]

    def r_TextPlus(self, t):
        img = self.blank()
        txt = self.v(t.name, "StyledText", "")
        if not txt:
            return img
        family, style = self.v(t.name, "Font", "Inter"), self.v(t.name, "Style", "Regular")
        em = float(self.v(t.name, "Size", 0.05)) * self.W / fl.text_size_k(family, style) * self.s
        f = self.font(family, style, max(4, int(round(em))))
        cx, cy = self.v(t.name, "Center", (0.5, 0.5))
        ha = {-1: "l", 0: "m", 1: "r"}.get(self.v(t.name, "HorizontalLeftCenterRight", 0), "m")
        va = {-1: "a", 0: "m", 1: "d"}.get(self.v(t.name, "VerticalTopCenterBottom", 0), "m")
        ls = float(self.v(t.name, "LineSpacing", 1.0) or 1.0)
        asc, desc = f.getmetrics()
        spacing = max(0, (asc + desc) * ls - (asc + desc) + 4)
        d = ImageDraw.Draw(img)
        try:
            d.multiline_text((cx * self.w, (1 - cy) * self.h), str(txt), font=f, fill=self.rgba(t.name, "", "1"),
                             anchor=ha + va, align={"l": "left", "m": "center", "r": "right"}[ha], spacing=spacing)
        except ValueError:
            d.multiline_text((cx * self.w, (1 - cy) * self.h), str(txt), font=f, fill=self.rgba(t.name, "", "1"))
        return self.apply_mask(img, t)

    def r_Loader(self, t):
        path = getattr(t, "path", "")
        if path and os.path.exists(path):
            im = Image.open(path).convert("RGBA")
        else:                                              # missing asset: grey placeholder
            im = Image.new("RGBA", (512, 512), (128, 128, 128, 255))
        return im.resize((max(1, int(im.width * self.s)), max(1, int(im.height * self.s))))

    def r_Merge(self, t):
        bg = self.src(t, "Background")
        fg = self.src(t, "Foreground")
        cx, cy = self.v(t.name, "Center", (0.5, 0.5))
        size = float(self.v(t.name, "Size", 1.0))
        if fg.size != bg.size or (cx, cy) != (0.5, 0.5) or size != 1.0:
            fg = fg.resize((max(1, int(fg.width * size)), max(1, int(fg.height * size))))
            layer = self.blank()
            layer.paste(fg, (int(cx * self.w - fg.width / 2), int((1 - cy) * self.h - fg.height / 2)), fg)
            fg = layer
        fg = self.apply_mask(fg, t)
        blend = max(0.0, min(1.0, float(self.v(t.name, "Blend", 1.0))))
        if blend < 1:
            fg.putalpha(fg.split()[3].point(lambda a: int(a * blend)))
        bg.alpha_composite(fg)
        return bg

    def r_Transform(self, t):
        img = self.src(t, "Input")
        cx, cy = self.v(t.name, "Center", (0.5, 0.5))
        px, py = self.v(t.name, "Pivot", (0.5, 0.5))
        size = max(1e-4, float(self.v(t.name, "Size", 1.0)))
        ang = math.radians(float(self.v(t.name, "Angle", 0.0) or 0.0))
        if (cx, cy) == (0.5, 0.5) and size == 1.0 and ang == 0:
            return img
        Px, Py = px * self.w, (1 - py) * self.h
        dx, dy = (cx - 0.5) * self.w, -(cy - 0.5) * self.h
        c, sn = math.cos(ang), math.sin(ang)
        a, b = c / size, -sn / size
        d, e = sn / size, c / size
        c0 = Px - (c * (Px + dx) - sn * (Py + dy)) / size
        f0 = Py - (sn * (Px + dx) + c * (Py + dy)) / size
        return img.transform(img.size, Image.AFFINE, (a, b, c0, d, e, f0), resample=Image.BILINEAR)

    def frame(self, out):
        self.memo.clear()
        return self.render(out)


def load_spec(path):
    spec = importlib.util.spec_from_file_location("template_spec", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render_animation(tools, out_name, frames, step=2, scale=0.25, bg="#202020", render_end=None):
    """Return a list of (frame, RGB image) for frames 0..frames-1 every `step`."""
    ev = Evaluator(tools, render_end or frames)
    r = Renderer(tools, ev, scale)
    base = tuple(int(c * 255) for c in fl.hex_rgb(bg))
    shots = []
    for f in range(0, frames, step):
        ev.at(f)
        img = r.frame(out_name)
        canvas = Image.new("RGB", img.size, base)
        canvas.paste(img, (0, 0), img)
        shots.append((f, canvas))
    return shots


def save_outputs(shots, out_dir, title, fps=30, step=2, sheet_every=10):
    os.makedirs(out_dir, exist_ok=True)
    gif = os.path.join(out_dir, f"{title}.gif")
    imgs = [im.convert("P", palette=Image.ADAPTIVE) for _, im in shots]
    imgs[0].save(gif, save_all=True, append_images=imgs[1:], duration=int(1000 * step / fps), loop=0)
    pick = [(f, im) for f, im in shots if f % sheet_every == 0]
    w, h = pick[0][1].size
    cols = 5
    sheet = Image.new("RGB", (cols * w, ((len(pick) + cols - 1) // cols) * (h + 14)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (f, im) in enumerate(pick):
        x, y = (i % cols) * w, (i // cols) * (h + 14)
        sheet.paste(im, (x, y + 14))
        d.text((x + 3, y + 1), f"frame {f}", fill="black")
    sp = os.path.join(out_dir, f"{title}-frames.png")
    sheet.save(sp)
    return gif, sp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--variant")
    ap.add_argument("--frames", type=int, default=150, help="clip length; also comp.RenderEnd")
    ap.add_argument("--step", type=int, default=2)
    ap.add_argument("--scale", type=float, default=0.25)
    ap.add_argument("--sheet-every", type=int, default=10)
    ap.add_argument("--out", default="out/preview")
    a = ap.parse_args()
    mod = load_spec(a.spec)
    fl.set_frame(*getattr(mod, "FRAME", (1920, 1080)))
    title = a.variant or next(iter(mod.VARIANTS))
    res = mod.build(mod.VARIANTS[title], getattr(mod, "ANIM", "expr"))
    shots = render_animation(res[0], res[2], a.frames, a.step, a.scale, getattr(mod, "PREVIEW_BG", "#202020"))
    gif, sheet = save_outputs(shots, a.out, title, step=a.step, sheet_every=a.sheet_every)
    print(f"{gif}\n{sheet}")


if __name__ == "__main__":
    main()

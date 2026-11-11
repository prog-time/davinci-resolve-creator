"""Builder for DaVinci Resolve / Fusion macro (.setting) files.

Coordinates: helpers take pixel values in a reference frame (default 1920x1080,
Y from the top) and convert them to Fusion's normalized space
(Center: 0..1, Y up). Call set_frame(1080, 1920) for vertical video.

Status of every node/feature (verified in Resolve or not) is tracked in
references/verified.md. Factories marked UNVERIFIED must be checked with
make_test_pack.py before they are used in a user template.
"""

import os
import re
import shutil
import subprocess
import tempfile

FRAME_W, FRAME_H = 1920, 1080

# RectangleMask units: Width = fraction of frame WIDTH, Height = fraction of frame
# HEIGHT. VERIFIED in Resolve 21.2 (2026-11-11): a 35x35 px handle built with
# Height=px/FRAME_W rendered as 35x19.7 px (= 35*1080/1920).
MASK_UNIT = "height"

# Text+ Size -> pixels. Text+ sizes by the font's LINE HEIGHT (hhea ascent +
# descent), not by em:  Size = em_px / FRAME_W * (asc+desc)/upm / TEXT_LINE_K.
# VERIFIED in Resolve 21.2 (2026-11-11): Inter (line 1.21 em) needs K=1.51
# (text 386 vs 587 px without it); Phosphor-Thin (line 1.0 em) came out 1.16-1.21x
# too big with Inter's K -> matches line-height scaling. TEXT_SIZE_K is the
# fallback when the font file is not found.
TEXT_LINE_K = 0.8023
TEXT_SIZE_K = 1.51


def set_frame(w, h):
    global FRAME_W, FRAME_H
    FRAME_W, FRAME_H = int(w), int(h)


def frame():
    return FRAME_W, FRAME_H


def fx(px):
    return round(px / FRAME_W, 5)


def fy(py):
    return round(1 - py / FRAME_H, 5)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(round(int(h[i:i + 2], 16) / 255, 4) for i in (0, 2, 4))


# ---------- Lua serialization ----------

class Raw:
    def __init__(self, s):
        self.s = s


def FuID(s):
    return Raw("FuID { %s }" % lua_str(s))


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def lua_val(v):
    if isinstance(v, Raw):
        return v.s
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return repr(round(v, 6))
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return lua_str(v)
    if isinstance(v, (tuple, list)):
        return "{ " + ", ".join(lua_val(x) for x in v) + " }"
    raise TypeError(v)


class Inp:
    """An Input: constant value, expression, or link to another tool's output."""

    def __init__(self, value=None, expr=None, src=None, src_out="Output"):
        self.value, self.expr, self.src, self.src_out = value, expr, src, src_out

    def render(self):
        parts = []
        if self.src:
            parts += ["SourceOp = %s" % lua_str(self.src), "Source = %s" % lua_str(self.src_out)]
        if self.value is not None:
            parts.append("Value = %s" % lua_val(self.value))
        if self.expr:
            parts.append("Expression = %s" % lua_str(self.expr))
        return "Input { %s, }" % ", ".join(parts)


class Tool:
    def __init__(self, name, kind, pos=(0, 0)):
        self.name, self.kind, self.pos = name, kind, pos
        self.inputs = {}
        self.user_controls = []  # (id, dict)

    def set(self, key, value=None, expr=None):
        self.inputs[key] = Inp(value=value, expr=expr)
        return self

    def link(self, key, src, src_out="Output"):
        self.inputs[key] = Inp(src=src, src_out=src_out)
        return self

    def color(self, prefix, hexcol, alpha=1.0, suffix=""):
        r, g, b = hex_rgb(hexcol)
        for ch, v in (("Red", r), ("Green", g), ("Blue", b), ("Alpha", alpha)):
            self.set(f"{prefix}{ch}{suffix}", v)
        return self

    def follow_color(self, master, prefix="", suffix="1", channels=("Red", "Green", "Blue")):
        """Make this tool's color channels follow the master tool (expression link)."""
        for ch in channels:
            key = f"{prefix}{ch}{suffix}"
            cur = self.inputs.get(key)
            self.set(key, cur.value if cur else None, expr=f"{master}.{key}")
        return self

    def user_control(self, cid, **spec):
        self.user_controls.append((cid, spec))
        return self

    def render(self, ind="\t\t\t\t"):
        out = [f"{ind}{self.name} = {self.kind} {{", f"{ind}\tCtrlWZoom = false,", f"{ind}\tInputs = {{"]
        for k, v in self.inputs.items():
            key = k if k.isidentifier() else f'["{k}"]'
            out.append(f"{ind}\t\t{key} = {v.render()},")
        out.append(f"{ind}\t}},")
        out.append(f"{ind}\tViewInfo = OperatorInfo {{ Pos = {{ {self.pos[0]}, {self.pos[1]} }} }},")
        if self.user_controls:
            out.append(f"{ind}\tUserControls = ordered() {{")
            for cid, spec in self.user_controls:
                body = ", ".join(f"{k} = {lua_val(v)}" for k, v in spec.items())
                out.append(f"{ind}\t\t{cid} = {{ {body} }},")
            out.append(f"{ind}\t}},")
        out.append(f"{ind}}},")
        return "\n".join(out)

    def refs(self):
        """Names of tools this tool depends on (links + expression references)."""
        names = set()
        for inp in self.inputs.values():
            if inp.src:
                names.add(inp.src)
            if inp.expr:
                # strip string literals, then take `Name.` (not `..` concatenation)
                code = re.sub(r'"(?:\\.|[^"\\])*"', '""', inp.expr)
                names.update(re.findall(r"(?<![\w.])([A-Za-z_]\w*)\.(?=[A-Za-z_])", code))
        return names


class Spline:
    """BezierSpline animating one Number input. UNVERIFIED in Resolve (Test 8).

    keys: list of (frame, value). ease=True gives flat handles (ease in/out).
    """
    kind = "BezierSpline"

    def __init__(self, name, keys, ease=True):
        self.name, self.keys, self.ease = name, sorted(keys), ease
        self.pos = (0, 0)
        self.inputs, self.user_controls = {}, []

    def render(self, ind="\t\t\t\t"):
        rows = []
        for i, (f, v) in enumerate(self.keys):
            parts = [lua_val(float(v))]
            if i > 0:
                pf, pv = self.keys[i - 1]
                lv = v if self.ease else v - (v - pv) / 3
                parts.append(f"LH = {{ {round(f - (f - pf) / 3, 4)}, {round(lv, 6)} }}")
            if i < len(self.keys) - 1:
                nf, nv = self.keys[i + 1]
                rv = v if self.ease else v + (nv - v) / 3
                parts.append(f"RH = {{ {round(f + (nf - f) / 3, 4)}, {round(rv, 6)} }}")
            if not self.ease:
                parts.append("Flags = { Linear = true }")
            rows.append(f"{ind}\t\t[{f}] = {{ {', '.join(parts)} }},")
        return "\n".join([f"{ind}{self.name} = BezierSpline {{",
                          f"{ind}\tSplineColor = {{ Red = 205, Green = 205, Blue = 16 }},",
                          f"{ind}\tNameSet = true,",
                          f"{ind}\tKeyFrames = {{", *rows, f"{ind}\t}}", f"{ind}}},"])

    def refs(self):
        return set()


class XYPath(Tool):
    """XYPath animating a Point input from two splines. UNVERIFIED (Test 8)."""

    def __init__(self, name, x_spline, y_spline):
        super().__init__(name, "XYPath")
        self.link("X", x_spline, "Value").link("Y", y_spline, "Value")

    def render(self, ind="\t\t\t\t"):
        out = [f"{ind}{self.name} = XYPath {{", f"{ind}\tShowKeyPoints = false,",
               f"{ind}\tDrawMode = \"ModifyOnly\",", f"{ind}\tCtrlWZoom = false,", f"{ind}\tInputs = {{"]
        for k, v in self.inputs.items():
            out.append(f"{ind}\t\t{k} = {v.render()},")
        out += [f"{ind}\t}},", f"{ind}}},"]
        return "\n".join(out)


def animate_number(tool, key, keys, ease=True):
    """Keyframe tool.inputs[key]; returns the Spline to add to the tool list."""
    sp = Spline(f"{tool.name}{key.replace('.', '')}", keys, ease)
    tool.link(key, sp.name, "Value")
    return sp


def animate_point(tool, key, keys, ease=True):
    """keys: list of (frame, (x, y)) in normalized coords. Returns [splineX, splineY, path]."""
    base = f"{tool.name}{key}"
    sx = Spline(base + "X", [(f, p[0]) for f, p in keys], ease)
    sy = Spline(base + "Y", [(f, p[1]) for f, p in keys], ease)
    path = XYPath(base + "Path", sx.name, sy.name)
    tool.link(key, path.name, "Value")
    return [sx, sy, path]


# ---------- node factories (verified) ----------

def _frame(t):
    t.set("Width", FRAME_W).set("Height", FRAME_H).set("UseFrameFormatSettings", 1)
    t.set("Gamut.SLogVersion", FuID("SLog2"))
    return t


def background(name, hexcol, alpha=1.0, bottom_hex=None, mask=None, pos=(0, 0)):
    t = _frame(Tool(name, "Background", pos))
    if bottom_hex:
        t.set("Type", FuID("Vertical"))
        t.color("TopLeft", hexcol, alpha)
        t.color("BottomLeft", bottom_hex, alpha)
    else:
        t.color("TopLeft", hexcol, alpha)
    if mask:
        t.link("EffectMask", mask, "Mask")
    return t


def rect_mask(name, cx, cy, w, h, radius=0.0, soft=0.0, unit=None, pos=(0, 0)):
    """cx, cy, w, h in reference-frame pixels (Y from top).

    radius: CornerRadius 0..1 (fraction of the shorter half-side).
    soft: SoftEdge (UNVERIFIED, used for shadows).
    unit: override MASK_UNIT ("width" | "height") — only for diagnostics (Test 05).
    """
    unit = unit or MASK_UNIT
    t = Tool(name, "RectangleMask", pos)
    t.set("Filter", FuID("Fast Gaussian"))
    t.set("MaskWidth", FRAME_W).set("MaskHeight", FRAME_H)
    t.set("PixelAspect", (1, 1)).set("UseFrameFormatSettings", 1)
    t.set("ClippingMode", FuID("None"))
    t.set("Center", (fx(cx), fy(cy)))
    t.set("Width", round(w / FRAME_W, 5))
    t.set("Height", round(h / (FRAME_W if unit == "width" else FRAME_H), 5))
    t.set("CornerRadius", radius)
    if soft:
        t.set("SoftEdge", soft)
    return t


def ellipse_mask(name, cx, cy, w, h, border_px=None, soft=0.0, pos=(0, 0)):
    """EllipseMask in reference px (Y from top).

    Units differ from RectangleMask: BOTH Width and Height are fractions of frame
    WIDTH (VERIFIED 21.2: Height=px/FRAME_H drew a 210 px circle 1.78x taller).
    border_px: outline only (Solid = 0, BorderWidth as fraction of frame width;
    looks right in 21.2, not measured precisely — Test 13).
    """
    t = Tool(name, "EllipseMask", pos)
    t.set("Filter", FuID("Fast Gaussian"))
    t.set("MaskWidth", FRAME_W).set("MaskHeight", FRAME_H)
    t.set("PixelAspect", (1, 1)).set("UseFrameFormatSettings", 1)
    t.set("ClippingMode", FuID("None"))
    t.set("Center", (fx(cx), fy(cy)))
    t.set("Width", round(w / FRAME_W, 5))
    t.set("Height", round(h / FRAME_W, 5))
    if border_px:
        t.set("Solid", 0)
        t.set("BorderWidth", round(border_px / FRAME_W, 6))
    if soft:
        t.set("SoftEdge", soft)
    return t


def text(name, txt, x, y, size_px, hexcol, font="Inter", style="Regular",
         h_anchor=-1, v_anchor=-1, line_spacing=None, scale_expr=None, alpha=1.0, pos=(0, 0)):
    """x, y = anchor point in px. h_anchor: -1 left, 0 center, 1 right.
    v_anchor: -1 top, 0 center, 1 bottom. size_px = font size (em) in frame px;
    converted with TEXT_SIZE_K (calibrated)."""
    t = _frame(Tool(name, "TextPlus", pos))
    t.set("Center", (fx(x), fy(y)))
    t.set("StyledText", txt)
    t.set("Font", font).set("Style", style)
    base = round(size_px / FRAME_W * text_size_k(font, style), 6)
    if scale_expr:
        t.set("Size", base, expr=f"{scale_expr}*{base}")
    else:
        t.set("Size", base)
    t.set("HorizontalLeftCenterRight", h_anchor)
    t.set("VerticalTopCenterBottom", v_anchor)
    if h_anchor == -1:
        t.set("HorizontalJustificationNew", 0)  # UNVERIFIED: left justify multi-line
    if line_spacing:
        t.set("LineSpacing", line_spacing)
    t.color("", hexcol, alpha=alpha, suffix="1")
    return t


def font_line_height(path):
    """(hhea ascent + |descent|) / unitsPerEm read straight from a TTF/OTF file."""
    import struct
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] == b"ttcf":
        data_off = struct.unpack(">I", data[12:16])[0]
    else:
        data_off = 0
    num = struct.unpack(">H", data[data_off + 4:data_off + 6])[0]
    tables = {}
    for i in range(num):
        rec = data_off + 12 + 16 * i
        tag = data[rec:rec + 4].decode("latin-1")
        tables[tag] = struct.unpack(">I", data[rec + 8:rec + 12])[0]
    upm = struct.unpack(">H", data[tables["head"] + 18:tables["head"] + 20])[0]
    asc, desc = struct.unpack(">hh", data[tables["hhea"] + 4:tables["hhea"] + 8])
    return (asc + abs(desc)) / upm


_K_CACHE = {}


def text_size_k(font, style="Regular"):
    """Size multiplier for a font: line height / TEXT_LINE_K (fallback TEXT_SIZE_K)."""
    key = (font, style)
    if key not in _K_CACHE:
        k = TEXT_SIZE_K
        try:
            path = _find_font(font, style)
            if path:
                k = font_line_height(path) / TEXT_LINE_K
        except Exception:
            pass
        _K_CACHE[key] = k
    return _K_CACHE[key]


def merge(name, bg, fg, blend=1.0, pos=(0, 0)):
    t = Tool(name, "Merge", pos)
    t.link("Background", bg).link("Foreground", fg)
    t.set("PerformDepthMerge", 0)
    t.set("Blend", blend)
    return t


def transform(name, src, center=(0.5, 0.5), size=1.0, pivot=None, pos=(0, 0)):
    """Center is an OFFSET: (0.5, 0.5) = no move (VERIFIED 21.2 — putting the
    element's own position into Center moved it twice as far). Scale/rotate
    around a point by setting pivot=(x, y) normalized, keeping Center at 0.5."""
    t = Tool(name, "Transform", pos)
    t.link("Input", src)
    t.set("Center", center).set("Size", size)
    if pivot:
        t.set("Pivot", pivot)
    return t


# ---------- assets + Loader (UNVERIFIED in titles — see verified.md) ----------

APPSTORE_CONTAINERS = os.path.expanduser("~/Library/Containers")
WEBSITE_FUSION = os.path.expanduser("~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion")


def resolve_fusion_dirs():
    """Fusion user dirs of installed Resolve builds (App Store containers first)."""
    dirs = []
    if os.path.isdir(APPSTORE_CONTAINERS):
        for d in sorted(os.listdir(APPSTORE_CONTAINERS)):
            p = os.path.join(APPSTORE_CONTAINERS, d, "Data/Library/Application Support/Fusion")
            if d.startswith("com.blackmagic-design.DaVinciResolve") and os.path.isdir(p):
                dirs.append(p)
    if os.path.isdir(WEBSITE_FUSION):
        dirs.append(WEBSITE_FUSION)
    return dirs


# How Loader paths are written into the .setting:
#   "absolute" — full path into the detected Fusion folder (works today, but ties the
#                template to this machine and Resolve build);
#   "pathmap"  — "Fusion:Assets/<group>/<file>", resolved by Resolve itself (portable).
#                UNVERIFIED: enable after Test 15 of the test pack passes
#                (env DRT_ASSET_PATHS=pathmap or ASSET_PATHS = "pathmap" in the spec).
ASSET_PATHS = os.environ.get("DRT_ASSET_PATHS", "absolute")


def asset_dir(group):
    """Folder on this machine where --install copies the group's images."""
    dirs = resolve_fusion_dirs()
    return os.path.join(dirs[0] if dirs else WEBSITE_FUSION, "Assets", group)


def asset_path(group, filename, mode=None):
    """Path written into the Loader (see ASSET_PATHS)."""
    if (mode or ASSET_PATHS) == "pathmap":
        return f"Fusion:Assets/{group}/{filename}"
    return os.path.join(asset_dir(group), filename)


def manifest_path(pack):
    """Install manifest of a pack: lines 'asset <path>' / 'template <path>'."""
    dirs = resolve_fusion_dirs()
    return os.path.join(dirs[0] if dirs else WEBSITE_FUSION, "Assets", ".drt-manifests", f"{pack}.txt")


class LoaderTool(Tool):
    """Loader for a still image, held on every frame (Loop over a long global range)."""

    def __init__(self, name, path):
        super().__init__(name, "Loader")
        self.path = path
        ext = os.path.splitext(path)[1].lower()
        self.fmt = {".png": "PNGFormat", ".jpg": "JpegFormat", ".jpeg": "JpegFormat",
                    ".tif": "TiffFormat", ".tiff": "TiffFormat"}.get(ext, "PNGFormat")
        self.set("Gamut.SLogVersion", FuID("SLog2"))
        if self.fmt == "PNGFormat":
            self.set(f"Clip1.{self.fmt}.PostMultiply", 1)

    def render(self, ind="\t\t\t\t"):
        clip = [f'ID = "Clip1"', f"Filename = {lua_str(self.path)}", f'FormatID = "{self.fmt}"',
                "StartFrame = -1", "LengthSetManually = true", "TrimIn = 0", "TrimOut = 0",
                "ExtendFirst = 0", "ExtendLast = 0", "Loop = 1", "AspectMode = 0", "Depth = 0",
                "TimeCode = 0", "GlobalStart = -1000", "GlobalEnd = 100000"]
        out = [f"{ind}{self.name} = Loader {{", f"{ind}\tClips = {{",
               f"{ind}\t\tClip {{ {', '.join(clip)}, }},", f"{ind}\t}},",
               f"{ind}\tCtrlWZoom = false,", f"{ind}\tInputs = {{"]
        for k, v in self.inputs.items():
            key = k if k.isidentifier() else f'["{k}"]'
            out.append(f"{ind}\t\t{key} = {v.render()},")
        out += [f"{ind}\t}},", f"{ind}\tViewInfo = OperatorInfo {{ Pos = {{ {self.pos[0]}, {self.pos[1]} }} }},",
                f"{ind}}},"]
        return "\n".join(out)


def loader(name, path):
    return LoaderTool(name, path)


# ---------- node factories (UNVERIFIED — see references/verified.md) ----------

def shadow(prefix, cx, cy, w, h, radius=0.0, hexcol="#000000", alpha=0.45,
           offset=(0, 12), soft=0.02):
    """Soft rectangular shadow from verified primitives (mask + Background).
    Returns [mask, background]; merge the background UNDER the element."""
    m = rect_mask(f"{prefix}Mask", cx + offset[0], cy + offset[1], w, h, radius, soft=soft)
    return [m, background(prefix, hexcol, alpha=alpha, mask=m.name)]


def blur(name, src, size=10.0):
    t = Tool(name, "Blur")
    t.link("Input", src)
    t.set("XBlurSize", size)
    return t


def soft_glow(name, src, threshold=0.2, gain=1.0, size=10.0):
    t = Tool(name, "SoftGlow")
    t.link("Input", src)
    t.set("Threshold", threshold).set("Gain", gain).set("XGlowSize", size)
    return t


def _shape_xy(cx, cy):
    # shape space: origin at frame center, units of frame width, Y up
    return round((cx - FRAME_W / 2) / FRAME_W, 5), round((FRAME_H / 2 - cy) / FRAME_W, 5)


def s_rectangle(name, cx, cy, w, h, hexcol, radius=0.0, alpha=1.0):
    t = Tool(name, "sRectangle")
    x, y = _shape_xy(cx, cy)
    t.set("Translate.X", x).set("Translate.Y", y)
    t.set("Width", round(w / FRAME_W, 5)).set("Height", round(h / FRAME_W, 5))
    t.set("CornerRadius", radius)
    t.color("", hexcol, alpha)
    return t


def s_ellipse(name, cx, cy, w, h, hexcol, alpha=1.0):
    t = Tool(name, "sEllipse")
    x, y = _shape_xy(cx, cy)
    t.set("Translate.X", x).set("Translate.Y", y)
    t.set("Width", round(w / FRAME_W, 5)).set("Height", round(h / FRAME_W, 5))
    t.color("", hexcol, alpha)
    return t


def s_merge(name, inputs):
    t = Tool(name, "sMerge")
    for i, src in enumerate(inputs, 1):
        t.link(f"Input{i}", src)
    return t


def s_render(name, src):
    t = _frame(Tool(name, "sRender"))
    t.link("Input", src)
    return t


# ---------- animation ----------

def add_anim_controls(xf, frames=12, slide=0.04):
    """User controls on the master Transform: AnimOn, AnimFrames, SlideDist."""
    xf.set("AnimOn", 1).set("AnimFrames", frames).set("SlideDist", slide)
    xf.user_control("AnimOn", LINKS_Name="Animation", LINKID_DataType="Number",
                    INPID_InputControl="CheckboxControl", INP_Integer=False, INP_Default=1,
                    CBC_TriState=False, ICS_ControlPage="Controls")
    xf.user_control("AnimFrames", LINKS_Name="Anim Frames", LINKID_DataType="Number",
                    INPID_InputControl="SliderControl", INP_Integer=True, INP_Default=frames,
                    INP_MinScale=1, INP_MaxScale=60, INP_MinAllowed=1, ICS_ControlPage="Controls")
    xf.user_control("SlideDist", LINKS_Name="Slide Distance", LINKID_DataType="Number",
                    INPID_InputControl="SliderControl", INP_Default=slide, INP_MinScale=0.0,
                    INP_MaxScale=0.3, ICS_ControlPage="Controls")
    return xf


def animation(src, ctrl, mode="expr", frames=12, slide=0.04, outro=True, prefix=""):
    """Wrap `src` with intro/outro and a transparent canvas.

    mode:
      "expr"   — expressions driven by ctrl.AnimOn/AnimFrames/SlideDist
                 (needs add_anim_controls(ctrl)); intro + optional outro. UNVERIFIED.
      "keys"   — keyframes (BezierSpline/XYPath), intro only. UNVERIFIED.
      "static" — no animation (bisection / safe fallback).
    Returns (tools, output_name). Output node is f"{prefix}MrgOut".
    """
    tools = []
    xf = transform(f"{prefix}XfAnim", src)
    canvas = background(f"{prefix}BgCanvas", "#000000", alpha=0.0)
    out = merge(f"{prefix}MrgOut", canvas.name, xf.name)
    if mode == "expr":
        p_in = f"min(1, max(0, time/{ctrl}.AnimFrames))"
        p_out = f"min(1, max(0, (comp.RenderEnd - time)/{ctrl}.AnimFrames))"
        p = f"min({p_in}, {p_out})" if outro else p_in
        p = f"iif({ctrl}.AnimOn > 0.5, {p}, 1)"
        q = f"(1-{p})"
        xf.set("Center", (0.5, 0.5), expr=f"Point(0.5, 0.5 - {ctrl}.SlideDist*{q}*{q}*{q})")
        out.set("Blend", 1.0, expr=p)
        tools += [xf, canvas, out]
    elif mode == "keys":
        tools += animate_point(xf, "Center", [(0, (0.5, 0.5 - slide)), (frames, (0.5, 0.5))])
        tools.append(animate_number(out, "Blend", [(0, 0.0), (frames, 1.0)]))
        tools += [xf, canvas, out]
    elif mode == "static":
        tools += [xf, canvas, out]
    else:
        raise ValueError(f"unknown animation mode {mode!r}")
    return tools, out.name


# ---------- macro ----------

class Publish:
    def __init__(self, op, source, name=None, group=None, default=None):
        self.op, self.source, self.name, self.group, self.default = op, source, name, group, default


def publish_color(op, prefix, name, group, suffix=""):
    return [Publish(op, f"{prefix}Red{suffix}", name, group),
            Publish(op, f"{prefix}Green{suffix}", None, group),
            Publish(op, f"{prefix}Blue{suffix}", None, group),
            Publish(op, f"{prefix}Alpha{suffix}", None, group)]


def publish_font(op, name, group):
    """Font + Style in one ControlGroup (UNVERIFIED that Resolve groups them)."""
    return [Publish(op, "Font", name, group), Publish(op, "Style", None, group)]


RESERVED = {
    # Lua keywords
    "and", "break", "do", "else", "elseif", "end", "false", "for", "function", "goto", "if",
    "in", "local", "nil", "not", "or", "repeat", "return", "then", "true", "until", "while",
    # .setting / expression words
    "Name", "Input", "Output", "Inputs", "Outputs", "Value", "Source", "SourceOp", "Tools",
    "Expression", "Text", "Point", "comp", "time", "self", "tool", "fusion", "app", "math",
    "iif", "min", "max", "abs", "floor", "ceil", "Width", "Height", "Center", "Size",
    # tool kinds
    "Background", "Merge", "Transform", "TextPlus", "RectangleMask", "EllipseMask", "Blur", "Pivot",
    "SoftGlow", "Loader", "MediaIn", "MediaOut", "sRectangle", "sEllipse", "sMerge", "sRender",
    "BezierSpline", "XYPath", "MacroOperator", "GroupOperator",
}
EXPR_GLOBALS = {"comp", "self", "math", "tool", "fusion", "app", "string", "table", "os"}
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def check_names(name, tools, publishes, output_tool, main_input=None):
    """Unique, safe node names; every link/expression/publish points to a real node."""
    errs = []
    names = [t.name for t in tools]
    seen = set()
    for n in [name] + names:
        if not NAME_RE.match(n):
            errs.append(f"bad node name {n!r} (letters, digits, _ only)")
        if n in RESERVED:
            errs.append(f"reserved node name {n!r} — use a prefix, e.g. Txt{n} / Xf{n}")
        if n in seen:
            errs.append(f"duplicate node name {n!r}")
        seen.add(n)
    known = set(names)
    for t in tools:
        for r in t.refs() - EXPR_GLOBALS:
            if r not in known:
                errs.append(f"{t.name}: references unknown node {r!r}")
    for p in publishes:
        if p.op not in known:
            errs.append(f"publish {p.source!r}: unknown node {p.op!r}")
    if output_tool not in known:
        errs.append(f"output node {output_tool!r} not found")
    if main_input and main_input[0] not in known:
        errs.append(f"main input node {main_input[0]!r} not found")
    if errs:
        raise ValueError("node check failed:\n  " + "\n  ".join(errs))


def macro(name, tools, publishes, output_tool, main_input=None):
    """Render a MacroOperator. main_input=(tool, input) adds MainInput1 (Effects)."""
    check_names(name, tools, publishes, output_tool, main_input)
    lines = ["{", "\tTools = ordered() {", f"\t\t{name} = MacroOperator {{",
             "\t\t\tCtrlWZoom = false,", "\t\t\tNameSet = true,", "\t\t\tInputs = ordered() {"]
    if main_input:
        lines.append(f"\t\t\t\tMainInput1 = InstanceInput {{ SourceOp = {lua_str(main_input[0])}, "
                     f"Source = {lua_str(main_input[1])}, }},")
    for i, p in enumerate(publishes, 1):
        parts = [f"SourceOp = {lua_str(p.op)}", f"Source = {lua_str(p.source)}"]
        if p.name:
            parts.append(f"Name = {lua_str(p.name)}")
        if p.group is not None:
            parts.append(f"ControlGroup = {p.group}")
        if p.default is not None:
            parts.append(f"Default = {lua_val(p.default)}")
        lines.append(f"\t\t\t\tInput{i} = InstanceInput {{ {', '.join(parts)}, }},")
    lines += ["\t\t\t},", "\t\t\tOutputs = {",
              f"\t\t\t\tMainOutput1 = InstanceOutput {{ SourceOp = {lua_str(output_tool)}, Source = \"Output\", }},",
              "\t\t\t},",
              "\t\t\tViewInfo = GroupInfo { Pos = { 0, 0 } },",
              "\t\t\tTools = ordered() {"]
    for t in tools:
        lines.append(t.render())
    lines += ["\t\t\t},", "\t\t},", "\t},", f"\tActiveTool = {lua_str(name)}", "}", ""]
    return "\n".join(lines)


def layout(tools, step=110):
    """Spread nodes left to right in the Fusion flow view."""
    for i, t in enumerate(tools):
        t.pos = (i * step, 0)
    return tools


# ---------- validation ----------

def validate(src):
    """Structural check: balanced braces/parens outside strings, closed strings.
    Also runs `luac -p` when luac is installed."""
    stack, i, n = [], 0, len(src)
    pairs = {"}": "{", ")": "(", "]": "["}
    while i < n:
        c = src[i]
        if c == '"':
            i += 1
            while i < n and src[i] != '"':
                if src[i] == "\\":
                    i += 1
                if i < n and src[i] == "\n":
                    raise ValueError(f"newline inside string at {i}")
                i += 1
            if i >= n:
                raise ValueError("unterminated string")
        elif c in "{([":
            stack.append((c, i))
        elif c in "})]":
            if not stack or stack[-1][0] != pairs[c]:
                raise ValueError(f"unbalanced {c} at {i}: ...{src[max(0, i - 80):i + 1]}")
            stack.pop()
        i += 1
    if stack:
        raise ValueError(f"unclosed {stack[-1]}")
    luac_check(src)
    return True


def luac_check(src):
    """`luac -p` on 'return <src>'. Returns True/False/None (None = luac missing)."""
    luac = shutil.which("luac") or shutil.which("luac5.4") or shutil.which("luac5.1")
    if not luac:
        return None
    fd, path = tempfile.mkstemp(suffix=".lua")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("return " + src)
        r = subprocess.run([luac, "-p", path], capture_output=True, text=True)
        if r.returncode != 0:
            raise ValueError("luac: " + (r.stderr or r.stdout).strip())
        return True
    finally:
        os.unlink(path)


# ---------- preview PNG (optional, needs Pillow) ----------

FONT_DIRS = [os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", "/System/Library/Fonts",
             "/System/Library/Fonts/Supplemental", os.path.expanduser("~/.local/share/fonts"),
             "/usr/share/fonts", os.path.expandvars(r"%WINDIR%\Fonts")]


def _find_font(family, style):
    want = [f"{family}-{style}".lower().replace(" ", ""), f"{family}{style}".lower().replace(" ", ""),
            family.lower().replace(" ", "")]
    files = []
    for d in FONT_DIRS:
        if os.path.isdir(d):
            for root, _, names in os.walk(d):
                files += [os.path.join(root, fn) for fn in names if fn.lower().endswith((".ttf", ".otf", ".ttc"))]
    stems = [(os.path.splitext(os.path.basename(f))[0].lower().replace(" ", ""), f) for f in files]
    for w in want[:2]:                       # exact family-style first
        for stem, f in stems:
            if stem == w or stem.startswith(w + "-") or stem == w + "regular":
                return f
    for w in want:                           # then prefix match
        for stem, f in sorted(stems):
            if stem.startswith(w):
                return f
    return None


def render_preview(tools, path, width=400, output=None, bg="#181818"):
    """Approximate thumbnail from the node list (masks+backgrounds, Text+).
    Expressions are ignored; merges with Blend 0 hide their foreground.
    Returns path or None when Pillow is not installed."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    W, H = FRAME_W, FRAME_H
    img = Image.new("RGBA", (W, H), tuple(int(c * 255) for c in hex_rgb(bg)) + (255,))
    by = {t.name: t for t in tools}
    hidden = set()
    if output in by:  # draw only nodes that feed the output
        seen, todo = set(), [output]
        while todo:
            n = todo.pop()
            if n in seen or n not in by:
                continue
            seen.add(n)
            todo += [i.src for i in by[n].inputs.values() if i.src]
        hidden |= set(by) - seen
    for t in tools:
        if t.kind == "Merge" and t.inputs.get("Blend") and t.inputs["Blend"].value == 0 \
                and not t.inputs["Blend"].expr and t.inputs.get("Foreground"):
            todo = [t.inputs["Foreground"].src]
            while todo:
                n = todo.pop()
                hidden.add(n)
                tn = by.get(n)
                if tn and tn.kind == "Merge":
                    todo += [tn.inputs[k].src for k in ("Background", "Foreground") if k in tn.inputs]

    def v(t, k, d=None):
        return t.inputs[k].value if k in t.inputs and t.inputs[k].value is not None else d

    def rgba(t, prefix, suffix=""):
        return tuple(int(255 * v(t, f"{prefix}{c}{suffix}", 1.0)) for c in ("Red", "Green", "Blue", "Alpha"))

    for t in tools:
        if t.name in hidden:
            continue
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if t.kind == "Background":
            col = rgba(t, "TopLeft")
            if col[3] == 0:
                continue
            m = by.get(t.inputs["EffectMask"].src) if "EffectMask" in t.inputs else None
            box = [0, 0, W, H]
            if m:
                cx, cy = v(m, "Center")
                mw = v(m, "Width") * W
                mh = v(m, "Height") * (W if (MASK_UNIT == "width" or m.kind == "EllipseMask") else H)
                x0, y0 = cx * W - mw / 2, (1 - cy) * H - mh / 2
                box = [x0, y0, x0 + mw, y0 + mh]
                if m.kind == "EllipseMask":
                    if v(m, "Solid", 1) == 0:
                        bw = max(1, int(round(v(m, "BorderWidth", 0.001) * W)))
                        d.ellipse(box, outline=col, width=bw)
                    else:
                        d.ellipse(box, fill=col)
                else:
                    r = v(m, "CornerRadius", 0) * min(mw, mh) / 2
                    d.rounded_rectangle(box, radius=r, fill=col)
            else:
                d.rectangle(box, fill=col)
            if "BottomLeftRed" in t.inputs:  # vertical gradient inside the shape
                bot = rgba(t, "BottomLeft")
                y0, y1 = int(box[1]), max(int(box[1]) + 1, int(box[3]))
                grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                gd = ImageDraw.Draw(grad)
                for y in range(max(0, y0), min(H, y1)):
                    k = (y - y0) / (y1 - y0)
                    gd.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * k) for a, b in zip(col, bot)))
                layer = Image.composite(grad, layer, layer.split()[3])
        elif t.kind == "Merge" and "Foreground" in t.inputs and \
                getattr(by.get(t.inputs["Foreground"].src), "kind", "") == "Loader":
            ld = by[t.inputs["Foreground"].src]
            if not os.path.exists(ld.path):
                continue
            ph = Image.open(ld.path).convert("RGBA")
            sz = v(t, "Size", 1.0)
            ph = ph.resize((max(1, int(ph.width * sz)), max(1, int(ph.height * sz))))
            cx, cy = v(t, "Center", (0.5, 0.5))
            layer.paste(ph, (int(cx * W - ph.width / 2), int((1 - cy) * H - ph.height / 2)))
            m = by.get(t.inputs["EffectMask"].src) if "EffectMask" in t.inputs else None
            if m:
                mk = Image.new("L", (W, H), 0)
                mcx, mcy = v(m, "Center")
                mw = v(m, "Width") * W
                mh = v(m, "Height") * (W if m.kind == "EllipseMask" else H)
                bx = [mcx * W - mw / 2, (1 - mcy) * H - mh / 2, mcx * W + mw / 2, (1 - mcy) * H + mh / 2]
                if m.kind == "EllipseMask":
                    ImageDraw.Draw(mk).ellipse(bx, fill=255)
                else:
                    ImageDraw.Draw(mk).rounded_rectangle(bx, radius=v(m, "CornerRadius", 0) * min(mw, mh) / 2, fill=255)
                layer.putalpha(Image.composite(layer.split()[3], Image.new("L", (W, H), 0), mk))
        elif t.kind == "TextPlus":
            txt = v(t, "StyledText", "")
            if not txt:
                continue
            size = max(4, int(v(t, "Size", 0.05) * W / text_size_k(v(t, "Font", "Inter"), v(t, "Style", "Regular"))))
            fp = _find_font(v(t, "Font", "Inter"), v(t, "Style", "Regular"))
            try:
                font = ImageFont.truetype(fp, size) if fp else ImageFont.load_default(size)
            except Exception:
                font = ImageFont.load_default()
            cx, cy = v(t, "Center", (0.5, 0.5))
            ha = {-1: "l", 0: "m", 1: "r"}[v(t, "HorizontalLeftCenterRight", 0)]
            va = {-1: "a", 0: "m", 1: "d"}[v(t, "VerticalTopCenterBottom", 0)]
            d.multiline_text((cx * W, (1 - cy) * H), txt, font=font, fill=rgba(t, "", "1"),
                             anchor=ha + va, align={"l": "left", "m": "center", "r": "right"}[ha])
        else:
            continue
        img = Image.alpha_composite(img, layer)
    img = img.convert("RGB")
    img.thumbnail((width, width))
    img.save(path)
    return path

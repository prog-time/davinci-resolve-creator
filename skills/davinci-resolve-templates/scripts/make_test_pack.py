#!/usr/bin/env python3
"""Diagnostic test pack: one tiny title per Fusion feature.

Install the pack, drop each title on the timeline, put the playhead in the
MIDDLE of the clip and compare with the expected result (printed below and in
references/verified.md). The first test that fails points to the culprit.

Usage: make_test_pack.py [--out DIR] [--group "DRT Tests"] [--install]
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fusion_lib as fl  # noqa: E402
from fusion_lib import Publish, background, merge, rect_mask, text  # noqa: E402
from pack_drfx import pack  # noqa: E402


def t_text():
    t = text("TxtTest", "ТЕСТ 1 TEXT", 960, 540, 120, "#ff3333", h_anchor=0, v_anchor=0)
    return [t], [Publish("TxtTest", "StyledText", "Text")], "TxtTest", \
        "red text \"ТЕСТ 1 TEXT\" centered, Cyrillic readable"


def t_background():
    return [background("BgTest", "#33ff33")], [], "BgTest", "the whole frame is green"


def t_mask():
    m = rect_mask("MaskTest", 960, 540, 600, 300, 0.2)
    return [m, background("BgTest", "#3366ff", mask="MaskTest")], [], "BgTest", \
        "blue rounded rectangle 600x300 (width exactly 2x the height)"


def t_merge():
    c = background("BgCanvas", "#000000", alpha=0.0)
    t = text("TxtTest", "ТЕСТ 4 MERGE", 960, 540, 120, "#ffffff", h_anchor=0, v_anchor=0)
    return [c, t, merge("MrgOut", "BgCanvas", "TxtTest")], [], "MrgOut", \
        "white text, the video on the track below shows through (transparent background)"


def t_mask_height():
    tools = [background("BgCanvas", "#000000", alpha=0.0)]
    stack = "BgCanvas"
    for tag, unit, x, col in (("A", "width", 480, "#ff9900"), ("B", "height", 1440, "#00ccff")):
        tools.append(rect_mask(f"Mask{tag}", x, 540, 800, 200, 0.0, unit=unit))
        tools.append(background(f"Bg{tag}", col, mask=f"Mask{tag}"))
        tools.append(merge(f"MrgBg{tag}", stack, f"Bg{tag}"))
        tools.append(text(f"Txt{tag}", tag, x, 540, 120, "#000000", style="Bold", h_anchor=0, v_anchor=0))
        tools.append(merge(f"MrgTxt{tag}", f"MrgBg{tag}", f"Txt{tag}"))
        stack = f"MrgTxt{tag}"
    return tools, [], stack, ("two 800x200 stripes: B (cyan) must be exactly 4:1 — "
                              "MASK_UNIT='height' is verified; A is squashed")


def t_left_justify():
    t = text("TxtTest", "Первая строка подлиннее\nВторая\nТретья строка", 200, 300, 80, "#ffffff")
    c = background("BgCanvas", "#000000", alpha=0.0)
    return [c, t, merge("MrgOut", "BgCanvas", "TxtTest")], [], "MrgOut", \
        "3 lines, all aligned LEFT, top of the first line at (200, 300)"


def t_text_scale():
    c = background("BgCanvas", "#000000", alpha=0.0)
    m = rect_mask("MaskRuler", 860, 540, 20, 100)
    r = background("BgRuler", "#ff3333", mask="MaskRuler")
    t = text("TxtTest", "Hxg", 900, 540, 100, "#ffffff", v_anchor=0)
    tools = [c, m, r, merge("MrgRuler", "BgCanvas", "BgRuler"), t, merge("MrgOut", "MrgRuler", "TxtTest")]
    return tools, [], "MrgOut", ("red 100 px ruler and text at Size=100px. Compare the height of \"H\" with the ruler "
                                 "and record the ratio in verified.md (Text+ Size calibration)")


def _box():
    c = background("BgBase", "#000000", alpha=0.0)
    m = rect_mask("MaskBox", 960, 540, 400, 400, 0.15)
    b = background("BgBox", "#ff3399", mask="MaskBox")
    return [c, m, b, merge("MrgBox", "BgBase", "BgBox")]


def t_anim_expr():
    tools = _box()
    xf = fl.transform("XfCtl", "MrgBox")
    fl.add_anim_controls(xf, frames=24, slide=0.2)
    anim, out = fl.animation("XfCtl", "XfCtl", mode="expr")
    return tools + [xf] + anim, [Publish("XfCtl", "AnimFrames", "Frames")], out, \
        ("pink square: transparent on the first frame, slides up and fades in over 24 frames; "
         "slides back out at the end of the clip. Mid-clip it is still, centered")


def t_anim_keys():
    tools = _box()
    anim, out = fl.animation("MrgBox", None, mode="keys", frames=24, slide=0.2)
    return tools + anim, [], out, \
        "like test 7 but entrance only (keyframes); does not leave at the clip end"


def t_shapes():
    r = fl.s_rectangle("ShpRect", 760, 540, 400, 200, "#ffcc00", radius=0.05)
    e = fl.s_ellipse("ShpEllipse", 1160, 540, 200, 200, "#00ccff")
    sm = fl.s_merge("ShpMerge", ["ShpRect", "ShpEllipse"])
    sr = fl.s_render("ShpRender", "ShpMerge")
    return [r, e, sm, sr], [], "ShpRender", \
        "yellow 400x200 rectangle on the left and a cyan 200x200 CIRCLE on the right"


def t_shadow():
    tools = [background("BgCanvas", "#dddddd")]
    tools += fl.shadow("BgShadow", 960, 540, 500, 250, 0.2, offset=(0, 20), soft=0.03)
    tools += [merge("MrgShadow", "BgCanvas", "BgShadow"),
              rect_mask("MaskCard", 960, 540, 500, 250, 0.2),
              background("BgCard", "#ffffff", mask="MaskCard"),
              merge("MrgCard", "MrgShadow", "BgCard"),
              text("TxtGlow", "GLOW", 960, 860, 120, "#ff6600", style="Bold", h_anchor=0, v_anchor=0),
              fl.soft_glow("FxGlow", "TxtGlow", threshold=0.0, gain=2.0, size=20),
              merge("MrgOut", "MrgCard", "FxGlow")]
    return tools, [], "MrgOut", "white card with a soft downward shadow on grey; below it an orange \"GLOW\" with a glow"


def t_font_group():
    t = text("TxtTest", "Шрифт Font", 960, 540, 140, "#ffffff", h_anchor=0, v_anchor=0)
    pubs = [Publish("TxtTest", "StyledText", "Text")] + fl.publish_font("TxtTest", "Font", 1)
    return [t], pubs, "TxtTest", "in the Inspector, Font and Style sit side by side in one group \"Font\""


def t_ring():
    c = background("BgCanvas", "#000000", alpha=0.0)
    m = fl.ellipse_mask("MaskRing", 960, 540, 400, 400, border_px=8)
    r = background("BgRing", "#ff3399", mask="MaskRing")
    t = text("TxtIcon", "\ue2c2", 960, 540, 200, "#ffffff", font="Phosphor-Thin", h_anchor=0, v_anchor=0)
    tools = [c, m, r, merge("MrgRing", "BgCanvas", "BgRing"), t, merge("MrgOut", "MrgRing", "TxtIcon")]
    return tools, [], "MrgOut", ("pink RING Ø400, ~8 px thick (not a disc), a white "
                                 "Phosphor Thin house icon centered inside")


# ---------- tests 14-20: open items of references/verified.md ----------

GROUP = "DRT Tests"
TARGET = "drt-target.png"            # 400x400 test image, see make_target()


def make_target(path):
    """400x400 PNG: grid every 50 px, border, circles, size label (needs Pillow)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (400, 400), (30, 120, 220, 255))
    d = ImageDraw.Draw(im)
    for k in range(0, 401, 50):
        d.line([(k, 0), (k, 400)], fill=(255, 255, 255, 160), width=2)
        d.line([(0, k), (400, k)], fill=(255, 255, 255, 160), width=2)
    d.rectangle([0, 0, 399, 399], outline=(255, 220, 0, 255), width=8)
    d.ellipse([100, 100, 300, 300], outline=(255, 220, 0, 255), width=8)
    d.text((140, 190), "400x400", fill=(255, 255, 255, 255))
    im.save(path)
    return path


def _loader_test(path, label):
    tools = [background("BgCanvas", "#000000", alpha=0.0), fl.loader("LdTarget", path)]
    m = merge("MrgTarget", "BgCanvas", "LdTarget")
    m.set("Center", (0.5, 0.5)).set("Size", 0.5)
    ring = rect_mask("MaskFrame", 960, 540, 208, 208)          # red 208x208 under a 200x200 image = 4 px frame
    tools += [m, ring,
              background("BgFrame", "#ff3333", mask="MaskFrame"),
              merge("MrgFrame", "BgCanvas", "BgFrame"),
              merge("MrgFrameHole", "MrgFrame", "MrgTarget"),
              text("TxtLabel", label, 960, 820, 40, "#ffffff", h_anchor=0, v_anchor=0)]
    tools.append(merge("MrgOut", "MrgFrameHole", "TxtLabel"))
    return tools


def t_loader():
    tools = _loader_test(fl.asset_path(GROUP, TARGET), "Loader: absolute path")
    return tools, [], "MrgOut", ("blue 400x400 grid image shown at 200x200 (Merge.Size 0.5) exactly inside "
                                 "the red 4 px frame on every frame; empty frame = Loader failed, "
                                 "image bigger/smaller than the frame = Merge.Size is not pixel-for-pixel")


def t_loader_pathmap():
    tools = _loader_test(f"Fusion:Assets/{GROUP}/{TARGET}", "Loader: Fusion: path map")
    return tools, [], "MrgOut", ("same as test 14, but the Loader path is 'Fusion:Assets/...' (path map). "
                                 "Works = templates with images become portable between machines")


def t_text_mask():
    c = background("BgCanvas", "#000000", alpha=0.0)
    m = rect_mask("MaskReveal", 760, 540, 800, 300, soft=0.02)
    t = text("TxtTest", "МАСКА MASK", 960, 540, 160, "#ffffff", style="Bold", h_anchor=0, v_anchor=0)
    t.link("EffectMask", "MaskReveal", "Mask")
    return [c, m, t, merge("MrgOut", "BgCanvas", "TxtTest")], [], "MrgOut", \
        "only the LEFT part of the white text is visible, fading out softly around the middle (soft edge)"


def t_math():
    tools = [background("BgCanvas", "#000000", alpha=0.0)]
    tools.append(fl.ellipse_mask("MaskDot", 960, 540, 60, 60))
    tools.append(background("BgDot", "#00e5ff", mask="MaskDot"))
    xf = fl.transform("XfOrbit", "BgDot")
    xf.set("Center", (0.5, 0.5), expr="Point(0.5 + 0.15*math.cos(time*2*math.pi/60), "
                                      "0.5 + 0.2667*math.sin(time*2*math.pi/60))")
    tools += [xf, merge("MrgOut", "BgCanvas", "XfOrbit")]
    return tools, [], "MrgOut", "a cyan dot circles the frame center (radius ~290 px), one turn every 60 frames"


def t_render_end():
    tools = [background("BgCanvas", "#000000", alpha=0.0), rect_mask("MaskBox", 960, 540, 500, 300),
             background("BgBox", "#ff8800", mask="MaskBox")]
    tools.append(text("TxtLabel", "fades out in the last 30 frames", 960, 760, 40, "#ffffff", h_anchor=0, v_anchor=0))
    tools.append(merge("MrgBox", "BgCanvas", "BgBox"))
    tools.append(merge("MrgLabel", "MrgBox", "TxtLabel"))
    out = merge("MrgOut", "BgCanvas", "MrgLabel")
    out.set("Blend", 1.0, expr="min(1, max(0, (comp.RenderEnd - time)/30))")
    tools.append(out)
    return tools, [], "MrgOut", ("orange box fully visible, fades out over the LAST 30 frames of the clip "
                                 "(trim the clip: the fade must move with the clip end)")


def _advance(font, style, em, text_):
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    path = fl._find_font(font, style)
    return ImageFont.truetype(path, int(em)).getlength(text_) if path else None


def _ticks(prefix, xs, y, col, h=40):
    out, stack = [], None
    for i, x in enumerate(xs):
        out.append(rect_mask(f"Mask{prefix}{i}", x, y, 3, h))
        out.append(background(f"Bg{prefix}{i}", col, mask=f"Mask{prefix}{i}"))
    return out


def t_char_spacing():
    em, cs, n, x0, y = 100, 1.5, 8, 360, 480
    tools = [background("BgCanvas", "#000000", alpha=0.0)]
    t = text("TxtTest", "I" * n, x0, y, em, "#ffffff", font="Inter", style="Regular", v_anchor=0)
    t.set("CharacterSpacing", cs)
    tools.append(t)
    stack = merge("MrgText", "BgCanvas", "TxtTest")
    tools.append(stack)
    adv = _advance("Inter", "Regular", em, "I")
    expect = "8 letters I with CharacterSpacing 1.5"
    if adv:
        k = fl.text_size_k("Inter", "Regular")
        add_step = adv + (cs - 1) * em * k          # model A: extra (cs-1)*Size*1920 px per char
        mul_step = adv * cs                          # model B: advance * cs
        tools += _ticks("A", [x0 + adv / 2 + i * add_step for i in range(n)], y + 90, "#ff3333")
        tools += _ticks("B", [x0 + adv / 2 + i * mul_step for i in range(n)], y + 150, "#33ff66")
        prev = "MrgText"
        for i, tl in enumerate([t for t in tools if t.kind == "Background" and t.name[2:3] in "AB"]):
            m = merge(f"MrgTick{i}", prev, tl.name)
            tools.append(m)
            prev = m.name
        stack = tools[-1]
        expect += (": the letters line up with the RED ticks (model A, additive) or the GREEN ticks "
                   "(model B, multiplicative). Report which one, or neither")
    return tools, [], stack.name, expect


def t_line_spacing():
    em, ls, n, x, y0 = 80, 1.5, 4, 700, 260
    tools = [background("BgCanvas", "#000000", alpha=0.0)]
    t = text("TxtTest", "\n".join(["HHH"] * n), x, y0, em, "#ffffff", font="Inter", style="Regular", v_anchor=-1)
    t.set("LineSpacing", ls)
    tools += [t, merge("MrgText", "BgCanvas", "TxtTest")]
    expect = "4 lines HHH with LineSpacing 1.5"
    try:
        path = fl._find_font("Inter", "Regular")
        line = fl.font_line_height(path) * em if path else None
    except Exception:
        line = None
    if line:
        prev = "MrgText"
        for i in range(n):
            yy = y0 + i * line * ls
            tools += [rect_mask(f"MaskL{i}", x - 60, yy, 60, 3), background(f"BgL{i}", "#ff3333", mask=f"MaskL{i}"),
                      merge(f"MrgL{i}", prev, f"BgL{i}")]
            prev = f"MrgL{i}"
        expect += (": the red ticks on the left mark the predicted TOP of each line "
                   "(step = font line height x 1.5). Report the measured step if they drift")
    return tools, [], tools[-1].name, expect


TESTS = [
    ("Test 01 Text", t_text), ("Test 02 Background", t_background), ("Test 03 Rect Mask", t_mask),
    ("Test 04 Merge", t_merge), ("Test 05 Mask Height", t_mask_height),
    ("Test 06 Left Justify", t_left_justify), ("Test 07 Anim Expr", t_anim_expr),
    ("Test 08 Anim Keys", t_anim_keys), ("Test 09 Shapes", t_shapes), ("Test 10 Shadow Glow", t_shadow),
    ("Test 11 Text Scale", t_text_scale), ("Test 12 Font Group", t_font_group),
    ("Test 13 Ellipse Ring", t_ring),
    ("Test 14 Loader", t_loader), ("Test 15 Loader Path Map", t_loader_pathmap),
    ("Test 16 Text Mask", t_text_mask), ("Test 17 Math", t_math), ("Test 18 Render End", t_render_end),
    ("Test 19 Char Spacing", t_char_spacing), ("Test 20 Line Spacing", t_line_spacing),
]

CHECKLIST_HEAD = """# DRT Tests — checklist

Install `DRT Tests.drfx`, restart Resolve, put each title on a timeline (5 s or
longer) and check it with the playhead in the middle of the clip (tests 07, 08,
17, 18: play the whole clip). Fill the "Result" column with OK / FAIL and a
note, then paste this file back to Claude: it updates `references/verified.md`
and the calibration constants.

| Test | Expected | Result |
|---|---|---|
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="out/tests")
    ap.add_argument("--group", default="DRT Tests")
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()
    global GROUP
    GROUP = a.group
    fl.set_frame(1920, 1080)
    os.makedirs(a.out, exist_ok=True)
    try:
        target = make_target(os.path.join(a.out, TARGET))
    except ImportError:
        target = None
        print("Pillow missing: test image for tests 14-15 not generated")
    files, rows = [], []
    for title, fn in TESTS:
        tools, pubs, out, expect = fn()
        fl.layout(tools)
        src = fl.macro(title.replace(" ", ""), tools, pubs, out)
        fl.validate(src)
        p = os.path.join(a.out, f"{title}.setting")
        with open(p, "w", encoding="utf-8") as f:
            f.write(src)
        files.append(p)
        rows.append(f"| {title} | {expect} | |")
        print(f"{title}: {expect}")
    checklist = os.path.join(a.out, f"{a.group} checklist.md")
    with open(checklist, "w", encoding="utf-8") as f:
        f.write(CHECKLIST_HEAD + "\n".join(rows) + "\n")
    print(f"\nchecklist -> {checklist}")
    drfx = os.path.join(a.out, f"{a.group}.drfx")
    pack(drfx, files, a.group, "Titles")
    print(f"\n-> {drfx}")
    if a.install:
        if target:
            import shutil
            dst = fl.asset_path(a.group, TARGET)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(target, dst)
            print(f"asset -> {dst}")
        subprocess.run([os.path.join(HERE, "install_macos.sh"), drfx], check=False)


if __name__ == "__main__":
    main()

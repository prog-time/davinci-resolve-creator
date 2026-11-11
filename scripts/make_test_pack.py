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


TESTS = [
    ("Test 01 Text", t_text), ("Test 02 Background", t_background), ("Test 03 Rect Mask", t_mask),
    ("Test 04 Merge", t_merge), ("Test 05 Mask Height", t_mask_height),
    ("Test 06 Left Justify", t_left_justify), ("Test 07 Anim Expr", t_anim_expr),
    ("Test 08 Anim Keys", t_anim_keys), ("Test 09 Shapes", t_shapes), ("Test 10 Shadow Glow", t_shadow),
    ("Test 11 Text Scale", t_text_scale), ("Test 12 Font Group", t_font_group),
    ("Test 13 Ellipse Ring", t_ring),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="out/tests")
    ap.add_argument("--group", default="DRT Tests")
    ap.add_argument("--install", action="store_true")
    a = ap.parse_args()
    fl.set_frame(1920, 1080)
    os.makedirs(a.out, exist_ok=True)
    files = []
    for title, fn in TESTS:
        tools, pubs, out, expect = fn()
        fl.layout(tools)
        src = fl.macro(title.replace(" ", ""), tools, pubs, out)
        fl.validate(src)
        p = os.path.join(a.out, f"{title}.setting")
        with open(p, "w", encoding="utf-8") as f:
            f.write(src)
        files.append(p)
        print(f"{title}: {expect}")
    drfx = os.path.join(a.out, f"{a.group}.drfx")
    pack(drfx, files, a.group, "Titles")
    print(f"\n-> {drfx}")
    if a.install:
        subprocess.run([os.path.join(HERE, "install_macos.sh"), drfx], check=False)


if __name__ == "__main__":
    main()

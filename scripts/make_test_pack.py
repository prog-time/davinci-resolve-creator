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
    return [t], [Publish("TxtTest", "StyledText", "Текст")], "TxtTest", \
        "красный текст «ТЕСТ 1 TEXT» по центру, кириллица читается"


def t_background():
    return [background("BgTest", "#33ff33")], [], "BgTest", "весь кадр зелёный"


def t_mask():
    m = rect_mask("MaskTest", 960, 540, 600, 300, 0.2)
    return [m, background("BgTest", "#3366ff", mask="MaskTest")], [], "BgTest", \
        "синий скруглённый прямоугольник 600×300 (ширина ровно в 2 раза больше высоты)"


def t_merge():
    c = background("BgCanvas", "#000000", alpha=0.0)
    t = text("TxtTest", "ТЕСТ 4 MERGE", 960, 540, 120, "#ffffff", h_anchor=0, v_anchor=0)
    return [c, t, merge("MrgOut", "BgCanvas", "TxtTest")], [], "MrgOut", \
        "белый текст, под ним видно видео с нижней дорожки (фон прозрачный)"


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
    return tools, [], stack, ("две полосы 800×200: ровно 4:1 должна быть B (голубая) — "
                              "MASK_UNIT='height' проверен; A — сплющенная")


def t_left_justify():
    t = text("TxtTest", "Первая строка подлиннее\nВторая\nТретья строка", 200, 300, 80, "#ffffff")
    c = background("BgCanvas", "#000000", alpha=0.0)
    return [c, t, merge("MrgOut", "BgCanvas", "TxtTest")], [], "MrgOut", \
        "3 строки, все выровнены по ЛЕВОМУ краю, верх первой строки у точки (200, 300)"


def t_text_scale():
    c = background("BgCanvas", "#000000", alpha=0.0)
    m = rect_mask("MaskRuler", 860, 540, 20, 100)
    r = background("BgRuler", "#ff3333", mask="MaskRuler")
    t = text("TxtTest", "Hxg", 900, 540, 100, "#ffffff", v_anchor=0)
    tools = [c, m, r, merge("MrgRuler", "BgCanvas", "BgRuler"), t, merge("MrgOut", "MrgRuler", "TxtTest")]
    return tools, [], "MrgOut", ("красная планка 100 px и текст Size=100px. Сравните высоту «H» с планкой "
                                 "и запишите отношение в verified.md (калибровка Text+ Size)")


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
    return tools + [xf] + anim, [Publish("XfCtl", "AnimFrames", "Кадров")], out, \
        ("розовый квадрат: на первом кадре прозрачный, за 24 кадра выезжает снизу и проявляется; "
         "в конце клипа уходит обратно. Середина клипа — неподвижен по центру")


def t_anim_keys():
    tools = _box()
    anim, out = fl.animation("MrgBox", None, mode="keys", frames=24, slide=0.2)
    return tools + anim, [], out, \
        "как тест 7, но только появление (ключевые кадры); в конце клипа не исчезает"


def t_shapes():
    r = fl.s_rectangle("ShpRect", 760, 540, 400, 200, "#ffcc00", radius=0.05)
    e = fl.s_ellipse("ShpEllipse", 1160, 540, 200, 200, "#00ccff")
    sm = fl.s_merge("ShpMerge", ["ShpRect", "ShpEllipse"])
    sr = fl.s_render("ShpRender", "ShpMerge")
    return [r, e, sm, sr], [], "ShpRender", \
        "жёлтый прямоугольник 400×200 слева и голубой КРУГ 200×200 справа"


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
    return tools, [], "MrgOut", "белая карточка с мягкой тенью вниз на сером; ниже оранжевое «GLOW» со свечением"


def t_font_group():
    t = text("TxtTest", "Шрифт", 960, 540, 140, "#ffffff", h_anchor=0, v_anchor=0)
    pubs = [Publish("TxtTest", "StyledText", "Текст")] + fl.publish_font("TxtTest", "Шрифт", 1)
    return [t], pubs, "TxtTest", "в Inspector поля Font и Style стоят рядом в одной группе «Шрифт»"


def t_ring():
    c = background("BgCanvas", "#000000", alpha=0.0)
    m = fl.ellipse_mask("MaskRing", 960, 540, 400, 400, border_px=8)
    r = background("BgRing", "#ff3399", mask="MaskRing")
    t = text("TxtIcon", "\ue2c2", 960, 540, 200, "#ffffff", font="Phosphor-Thin", h_anchor=0, v_anchor=0)
    tools = [c, m, r, merge("MrgRing", "BgCanvas", "BgRing"), t, merge("MrgOut", "MrgRing", "TxtIcon")]
    return tools, [], "MrgOut", ("розовое КОЛЬЦО Ø400 с толщиной ~8 px (не круг), внутри белая "
                                 "иконка-домик Phosphor Thin по центру")


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

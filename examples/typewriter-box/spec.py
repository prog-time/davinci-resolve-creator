"""Typewriter Box — selection-box title with typewriter text on a cross grid.

Reference: screenshot 1542x786, scaled x1.245 to a 1920x1080 frame.
Box 684x129 (left edge fixed, width slider), border 4, corner handles 35,
text Inter SemiBold 72 px, cursor "|" appended to the typed text.
"""
import math
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/davinci-resolve-templates/scripts"))
import fusion_lib as fl  # noqa: E402
from fusion_lib import Publish, background, merge, publish_color, rect_mask, text, transform  # noqa: E402

GROUP = "Prog-time"
CATEGORY = "Titles"
FRAME = (1920, 1080)
ANIM = "expr"
fl.set_frame(*FRAME)
FW, FH = FRAME

BOX_W, BOX_H = 684, 129
L = (FW - BOX_W) / 2           # box left edge (fixed; width grows to the right)
CY = FH / 2
B = 4                          # border thickness
HANDLE = 35
PAD = 43                       # text left padding
GRID_STEP = 46

VARIANTS = {
    "Typewriter Box": dict(
        text="typewriter effect", accent="#4708f4", fill="#dfdcf1", ink="#2b2a31",
        bg="#eeeeee", grid="#dedede",
    ),
}

LX = fl.fx(L)
W = "XfCard.BoxW"
WB = round(B / FW, 5)

TYPE_EXPR = """: local s = TxtSource.StyledText.Value or ""
local f = math.max(1, XfCard.TypeFrames)
local t = time - XfCard.TypeStart
local n = -1
if t >= 0 then n = math.floor(t / f) + 1 end
local out, i = "", 0
for ch in string.gmatch(s, "[^\\128-\\191][\\128-\\191]*") do
  if i < n then out = out .. ch end
  i = i + 1
end
local typing = t >= 0 and n < i
local b = math.max(1, XfCard.BlinkFrames)
local on = XfCard.CursorOn > 0.5 and (typing or math.floor(time / b) % 2 == 0)
if on then out = out .. "\\226\\128\\138|" end
return Text(out)"""


def right_x(frac):
    """Expression: x = left edge + frac * box width."""
    return f"{LX} + {frac}*{W}" if frac != 1 else f"{LX} + {W}"


def build(v, anim="expr"):
    tools = []

    def add(t):
        tools.append(t)
        return t

    # --- backdrop: background + cross grid (Text+ rows of "+") ---
    add(background("BgBase", v["bg"]))
    cols, rows = math.ceil(FW / GRID_STEP) + 2, math.ceil(FH / GRID_STEP) + 2
    # calibrated from the first Resolve render (2026-11-11): Size 66px/cs 1.08/ls 0.575
    # (without TEXT_SIZE_K) gave crosses ~17 px, step 34.1 x 31.3 px -> scaled to 32 px / 46 px
    grid = add(text("TxtGrid", "\n".join(["+" * cols] * rows), FW / 2, FH / 2, 82.3, v["grid"],
                    font="Inter", style="ExtraLight", h_anchor=0, v_anchor=0))
    grid.set("CharacterSpacing", 0.774)
    grid.set("LineSpacing", 0.449)
    add(merge("MrgGrid", "BgBase", "TxtGrid"))

    # --- box on a transparent canvas ---
    add(background("BgBoxCanvas", "#000000", alpha=0.0))
    stack = "BgBoxCanvas"

    def piece(name, cx, cy, w, h, color, x_expr=None, w_expr=None):
        nonlocal stack
        m = add(rect_mask(f"Mask{name}", cx, cy, w, h))
        if x_expr:
            m.set("Center", m.inputs["Center"].value, expr=f"Point({x_expr}, {fl.fy(cy)})")
        if w_expr:
            m.set("Width", m.inputs["Width"].value, expr=w_expr)
        bg = add(background(f"Bg{name}", color, mask=m.name))
        stack = add(merge(f"Mrg{name}", stack, bg.name)).name
        return bg

    top, bot = CY - BOX_H / 2, CY + BOX_H / 2
    piece("Fill", L + BOX_W / 2, CY, BOX_W, BOX_H, v["fill"], x_expr=right_x(0.5), w_expr=W)
    piece("EdgeTop", L + BOX_W / 2, top, BOX_W + B, B, v["accent"], x_expr=right_x(0.5), w_expr=f"{W} + {WB}")
    piece("EdgeBottom", L + BOX_W / 2, bot, BOX_W + B, B, v["accent"],
          x_expr=right_x(0.5), w_expr=f"{W} + {WB}").follow_color("BgEdgeTop", "TopLeft", "")
    piece("EdgeLeft", L, CY, B, BOX_H + B, v["accent"]).follow_color("BgEdgeTop", "TopLeft", "")
    piece("EdgeRight", L + BOX_W, CY, B, BOX_H + B, v["accent"],
          x_expr=right_x(1)).follow_color("BgEdgeTop", "TopLeft", "")
    for tag, x, y, right in (("TL", L, top, False), ("TR", L + BOX_W, top, True),
                             ("BL", L, bot, False), ("BR", L + BOX_W, bot, True)):
        piece(f"Handle{tag}", x, y, HANDLE, HANDLE, v["accent"],
              x_expr=right_x(1) if right else None).follow_color("BgEdgeTop", "TopLeft", "")

    # --- text: TxtSource holds the published text (not rendered), TxtTyped shows it ---
    add(text("TxtSource", v["text"], L + PAD, CY, 72, v["ink"], font="Inter", style="SemiBold", v_anchor=0))
    typed = add(text("TxtTyped", v["text"] + " |", L + PAD, CY, 72, v["ink"],
                     font="Inter", style="SemiBold", v_anchor=0))
    typed.set("StyledText", typed.inputs["StyledText"].value, expr=TYPE_EXPR)
    stack = add(merge("MrgText", stack, "TxtTyped")).name

    # --- master transform + controls ---
    card = add(transform("XfCard", stack))
    controls = [
        ("BoxW", "Box Width", round(BOX_W / FW, 5), dict(INP_MinScale=0.05, INP_MaxScale=1.0)),
        ("TypeFrames", "Frames per Char", 2, dict(INP_Integer=True, INP_MinScale=1, INP_MaxScale=10, INP_MinAllowed=1)),
        ("TypeStart", "Type Start", 6, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=120, INP_MinAllowed=0)),
        ("BlinkFrames", "Blink Frames", 15, dict(INP_Integer=True, INP_MinScale=2, INP_MaxScale=60, INP_MinAllowed=1)),
        ("FadeFrames", "Fade Frames", 6, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=60, INP_MinAllowed=0)),
    ]
    for cid, label, default, extra in controls:
        card.set(cid, default)
        card.user_control(cid, LINKS_Name=label, LINKID_DataType="Number", INPID_InputControl="SliderControl",
                          INP_Default=default, ICS_ControlPage="Controls", **extra)
    card.set("CursorOn", 1)
    card.user_control("CursorOn", LINKS_Name="Cursor", LINKID_DataType="Number",
                      INPID_InputControl="CheckboxControl", INP_Integer=False, INP_Default=1,
                      CBC_TriState=False, ICS_ControlPage="Controls")

    out = add(merge("MrgOut", "MrgGrid", "XfCard"))
    out.set("Blend", 1.0, expr="iif(XfCard.FadeFrames < 1, 1, min(1, max(0, time/XfCard.FadeFrames)))")
    fl.layout(tools)

    g = iter(range(1, 100))
    pubs = [Publish("TxtSource", "StyledText", "Текст")]
    pubs += fl.publish_font("TxtTyped", "Шрифт", next(g))
    pubs += [Publish("XfCard", "BoxW", "Рамка: ширина"),
             Publish("XfCard", "TypeFrames", "Печать: кадров на букву"),
             Publish("XfCard", "TypeStart", "Печать: старт, кадр"),
             Publish("XfCard", "CursorOn", "Курсор: вкл."),
             Publish("XfCard", "BlinkFrames", "Курсор: мигание, кадров"),
             Publish("XfCard", "FadeFrames", "Появление рамки, кадров")]
    pubs += publish_color("BgEdgeTop", "TopLeft", "Акцент (обводка, маркеры)", next(g))
    pubs += publish_color("BgFill", "TopLeft", "Заливка рамки", next(g))
    pubs += publish_color("TxtTyped", "", "Текст и курсор", next(g), suffix="1")
    pubs += publish_color("BgBase", "TopLeft", "Фон", next(g))
    pubs += publish_color("TxtGrid", "", "Сетка", next(g), suffix="1")
    pubs += [Publish("TxtGrid", "Size", "Сетка: размер"),
             Publish("TxtGrid", "CharacterSpacing", "Сетка: шаг по X"),
             Publish("TxtGrid", "LineSpacing", "Сетка: шаг по Y"),
             Publish("XfCard", "Center", "Позиция"),
             Publish("XfCard", "Size", "Масштаб")]
    return tools, pubs, out.name

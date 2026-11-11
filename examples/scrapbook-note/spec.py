"""Scrapbook Note — notebook sheet, two polaroids with clips, tape, sticky note.

Every part flies in from its own side; the title is "hand-written" (soft wipe +
pen), the red marker underline draws left->right, the body types letter by
letter, the sticky text is written with a wipe. Decor = PNG assets
(make_assets.py), texts = live Text+.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/davinci-resolve-templates/scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fusion_lib as fl  # noqa: E402
from fusion_lib import Publish, background, merge, publish_color, rect_mask, text, transform  # noqa: E402
from geometry import G  # noqa: E402

GROUP = "Prog-time"
PACK = "Scrapbook Note"
CATEGORY = "Titles"
FRAME = (1920, 1080)
ANIM = "expr"
PREVIEW_BG = "#463c37"
fl.set_frame(*FRAME)
FW, FH = FRAME

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = ["paper", "polaroid_l", "polaroid_r", "clip_l", "clip_r", "tape", "sticky", "pin", "underline"]
ASSETS = {f"sb-{p}.png": os.path.join(HERE, "assets", f"sb-{p}.png") for p in PARTS}
INTRO_END = 140

VARIANTS = {
    "Scrapbook Note": dict(
        title="Важная встреча", title_c="#2b2fb5",
        body=("Встречаемся в пятницу в 18:00\nв коворкинге на Садовой, 12.\nБерите ноутбуки, идеи и\n"
              "хорошее настроение. Обсудим\nзаявки и распределим задачи."),
        body_c="#2b2b2b", sticky="Мечтай смело,\nработай упорно", sticky_c="#283a8a", pen_c="#333333",
    ),
}

C = "XfBlock"
T = f"((time - {C}.AnimStart)*{C}.Speed)"


def clamp01(e):
    return f"min(1, max(0, {e}))"


def prog(a, b):
    return clamp01(f"({T} - {a})/{b - a}")


def out3(x):
    return f"(1 - (1-{x})^3)"


def back(x):
    return f"(1 + 2.70158*({x}-1)^3 + 1.70158*({x}-1)^2)"


def on(e, off="1"):
    return f"iif({C}.AnimOn > 0.5, {e}, {off})"


def typing(src, start, per_char):
    return (f''': local s = {src}.StyledText.Value or ""
local t = (time - {C}.AnimStart)*{C}.Speed - {start}
local n = -1
if t >= 0 then n = math.floor(t / {per_char}) + 1 end
if {C}.AnimOn < 0.5 then n = 100000 end
local out, i = "", 0
for ch in string.gmatch(s, "[^\\128-\\191][\\128-\\191]*") do
  if i < n then out = out .. ch end
  i = i + 1
end
return Text(out)''')


# name, asset, center key, (start, end), dx px, dy px (screen, + = right/down), start angle, start size, ease
MOVES = [
    ("Paper", "paper", "paper_c", (0, 18), 0, 800, -3, 1.0, "out3"),
    ("PolL", "polaroid_l", "pl_c", (10, 26), -900, 0, 20, 1.0, "out3"),
    ("PolR", "polaroid_r", "pr_c", (16, 32), 900, 0, -20, 1.0, "out3"),
    ("ClipL", "clip_l", "clip_l_c", (32, 42), 0, -150, 0, 1.0, "out3"),
    ("ClipR", "clip_r", "clip_r_c", (34, 44), 0, -150, 0, 1.0, "out3"),
    ("Tape", "tape", "tape_c", (24, 34), 0, -500, 0, 1.3, "out3"),
    ("Sticky", "sticky", "sticky_c", (30, 46), 500, 500, -15, 1.0, "out3"),
    ("Pin", "pin", "pin_c", (44, 52), 0, 0, 0, 0.0, "back"),
]


def build(v, anim="expr"):
    tools = []

    def add(t):
        tools.append(t)
        return t

    def pt(xy):
        return (fl.fx(xy[0]), fl.fy(xy[1]))

    add(background("BgClear", "#000000", alpha=0.0))
    layers = {}

    def place(name, asset, center):
        add(fl.loader(f"Ld{name}", fl.asset_path(GROUP, f"sb-{asset}.png")))
        m = add(merge(f"MrgPlace{name}", "BgClear", f"Ld{name}"))
        m.set("Center", pt(center)).set("Size", 1.0)
        return m

    for name, asset, ckey, (a, b), dx, dy, ang, size0, ease in MOVES:
        place(name, asset, G[ckey])
        e = (out3 if ease == "out3" else back)(prog(a, b))
        xf = add(transform(f"Xf{name}", f"MrgPlace{name}", pivot=pt(G[ckey])))
        if dx or dy:
            xf.set("Center", (0.5, 0.5), expr=on(
                f"Point(0.5 + {dx / FW:.5f}*(1-{e}), 0.5 - {dy / FH:.5f}*(1-{e}))", "Point(0.5, 0.5)"))
        if ang:
            xf.set("Angle", 0.0, expr=on(f"{ang}*(1-{e})", "0"))
        if size0 != 1.0:
            xf.set("Size", 1.0, expr=on(f"max(0.001, {size0} + {1 - size0}*{e})"))
        layers[name] = (xf.name, on(f"min(1, 4*{prog(a, b)})"))

    # ---------- title: written by a soft wipe, pen leads the edge ----------
    w = prog(48, 84)
    left = G["title_left"] - 12
    tm = add(rect_mask("MaskTitle", left + 400, G["title_cy"], 800, 240, soft=0.008))
    tm.set("Width", 0.4, expr=f"{C}.TitleW*{on(w)}")
    tm.set("Center", pt((left + 400, G["title_cy"])), expr=f"Point({fl.fx(left)} + {C}.TitleW*{on(w)}/2, {fl.fy(G['title_cy'])})")
    title = add(text("TxtTitle", v["title"], G["title_left"], G["title_cy"], 120, v["title_c"],
                     font="Caveat", style="Bold", v_anchor=0))
    title.link("EffectMask", "MaskTitle", "Mask")
    pen = add(text("TxtPen", "", left + 30, G["title_cy"] - 40, 64, v["pen_c"],
                   font="Font Awesome 6 Free", style="Solid", h_anchor=-1, v_anchor=1))
    pen_tip = (left + 8, G["title_cy"] + 18)                       # glyph bottom-left = pen tip
    pen.set("Center", pt(pen_tip), expr=(
        f"Point({fl.fx(left + 8)} + {C}.TitleW*{w}, {fl.fy(G['title_cy'] + 18)} + 0.012*math.sin({T}*1.7))"))
    pen_blend = on(f"min(1, 8*{w}, 8*(1-{w}))", "0")

    # ---------- underline: marker drawn left -> right ----------
    under = place("Under", "underline", G["ul_c"])
    ul_left = G["ul_c"][0] - G["ul_w"] / 2
    u = out3(prog(82, 96))
    um = add(rect_mask("MaskUnder", G["ul_c"][0], G["ul_c"][1], G["ul_w"], 80))
    um.set("Width", G["ul_w"] / FW, expr=f"{C}.UnderLen*{on(u)}")
    um.set("Center", pt(G["ul_c"]), expr=f"Point({fl.fx(ul_left)} + {C}.UnderLen*{on(u)}/2, {fl.fy(G['ul_c'][1])})")
    under.link("EffectMask", "MaskUnder", "Mask")

    # ---------- body: typed letter by letter ----------
    add(text("TxtBodySrc", v["body"], G["body_left"], G["body_top"], 44, v["body_c"],
             font="Courier New", style="Bold", v_anchor=-1, line_spacing=1.0))
    body = add(text("TxtBody", v["body"], G["body_left"], G["body_top"], 44, v["body_c"],
                    font="Courier New", style="Bold", v_anchor=-1, line_spacing=1.0))
    body.set("StyledText", v["body"], expr=typing("TxtBodySrc", 92, 0.35))

    # ---------- sticky text: written by a wipe, rotated with the note ----------
    sx, sy = G["sticky_text_c"]
    sw = prog(96, 124)
    sm = add(rect_mask("MaskSticky", sx, sy, 380, 200, soft=0.008))
    sm.set("Width", 380 / FW, expr=f"{380 / FW:.5f}*{on(sw)}")
    sm.set("Center", pt((sx, sy)), expr=f"Point({fl.fx(sx - 190)} + {380 / FW:.5f}*{on(sw)}/2, {fl.fy(sy)})")
    st = add(text("TxtSticky", v["sticky"], sx, sy, 50, v["sticky_c"], font="Caveat", style="SemiBold",
                  h_anchor=0, v_anchor=0, line_spacing=0.85))
    st.link("EffectMask", "MaskSticky", "Mask")
    add(transform("XfStickyText", "TxtSticky", pivot=pt((sx, sy)))).set("Angle", -4.0)

    # ---------- composite (bottom -> top) ----------
    stack = "BgClear"
    order = [layers["Paper"], ("TxtTitle", "1"), ("MrgPlaceUnder", "1"), ("TxtBody", "1"),
             layers["PolL"], layers["ClipL"], layers["PolR"], layers["ClipR"], layers["Tape"],
             layers["Sticky"], layers["Pin"], ("XfStickyText", "1"), ("TxtPen", pen_blend)]
    for k, (node, blend) in enumerate(order):
        m = add(merge(f"MrgStack{k:02d}", stack, node))
        if blend != "1":
            m.set("Blend", 1.0, expr=blend)
        stack = m.name

    blk = add(transform(C, stack))
    ctrls = [
        ("TitleW", "Title Width", round(720 / FW, 4), dict(INP_MinScale=0.05, INP_MaxScale=0.8)),
        ("UnderLen", "Underline Length", round(G["ul_w"] / FW, 4), dict(INP_MinScale=0.05, INP_MaxScale=0.8)),
        ("AnimStart", "Anim Start", 0, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=120)),
        ("Speed", "Speed", 1.0, dict(INP_MinScale=0.25, INP_MaxScale=4.0, INP_MinAllowed=0.05)),
        ("Hold", "Hold", 90, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=600, INP_MinAllowed=0)),
        ("OutFrames", "Out Frames", 10, dict(INP_Integer=True, INP_MinScale=1, INP_MaxScale=60, INP_MinAllowed=1)),
    ]
    for cid, lbl, default, extra in ctrls:
        blk.set(cid, default)
        blk.user_control(cid, LINKS_Name=lbl, LINKID_DataType="Number", INPID_InputControl="SliderControl",
                         INP_Default=default, ICS_ControlPage="Controls", **extra)
    for cid, lbl in (("AnimOn", "Animation"), ("OutOn", "Fade Out")):
        blk.set(cid, 1)
        blk.user_control(cid, LINKS_Name=lbl, LINKID_DataType="Number", INPID_InputControl="CheckboxControl",
                         INP_Integer=False, INP_Default=1, CBC_TriState=False, ICS_ControlPage="Controls")

    add(background("BgOut", "#000000", alpha=0.0))
    out = add(merge("MrgOut", "BgOut", C))
    intro_end = f"({C}.AnimStart + {INTRO_END}/{C}.Speed)"
    out.set("Blend", 1.0, expr=(f"iif({C}.OutOn > 0.5, "
                                f"{clamp01(f'1 - (time - {intro_end} - {C}.Hold)/{C}.OutFrames')}, 1)"))
    fl.layout(tools)

    g = iter(range(1, 100))
    pubs = [Publish("TxtTitle", "StyledText", "Заголовок"),
            Publish("TxtBodySrc", "StyledText", "Текст"),
            Publish("TxtSticky", "StyledText", "Стикер: текст")]
    for node, label in (("TxtTitle", "Заголовок"), ("TxtBody", "Текст"), ("TxtSticky", "Стикер")):
        pubs += fl.publish_font(node, f"{label}: шрифт", next(g))
        pubs.append(Publish(node, "Size", f"{label}: размер"))
    pubs += publish_color("TxtTitle", "", "Заголовок: цвет", next(g), suffix="1")
    pubs += publish_color("TxtBody", "", "Текст: цвет", next(g), suffix="1")
    pubs += publish_color("TxtSticky", "", "Стикер: цвет текста", next(g), suffix="1")
    pubs += publish_color("TxtPen", "", "Перо: цвет", next(g), suffix="1")
    pubs += [Publish(C, "TitleW", "Заголовок: ширина письма (доля кадра)"),
             Publish(C, "UnderLen", "Подчёркивание: длина (доля кадра)"),
             Publish("TxtBody", "LineSpacing", "Текст: межстрочный"),
             Publish(C, "AnimOn", "Анимация вкл."),
             Publish(C, "AnimStart", "Анимация: старт, кадр"),
             Publish(C, "Speed", "Анимация: скорость"),
             Publish(C, "OutOn", "Затухание вкл."),
             Publish(C, "Hold", "Пауза перед затуханием, кадров"),
             Publish(C, "OutFrames", "Затухание, кадров"),
             Publish(C, "Center", "Позиция"),
             Publish(C, "Size", "Масштаб")]
    return tools, pubs, out.name

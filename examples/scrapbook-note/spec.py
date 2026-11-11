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
from fusion_anim import Timeline, place_image  # noqa: E402
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

tl = Timeline("XfBlock")
C = tl.C

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

    def asset(name):
        return fl.asset_path(GROUP, f"sb-{name}.png")

    add(background("BgClear", "#000000", alpha=0.0))
    layers = {}
    for name, part, ckey, (a, b), dx, dy, ang, size0, ease_name in MOVES:
        place_image(add, name, asset(part), G[ckey])
        add(tl.slide(f"Xf{name}", f"MrgPlace{name}", a, b, dx, dy, ang, size0, fl.pt(G[ckey]), ease_name))
        layers[name] = (f"Xf{name}", tl.on(f"min(1, 4*{tl.prog(a, b)})"))

    # title: written by a soft wipe, pen leads the edge
    w = tl.prog(48, 84)
    left, cy = G["title_left"] - 12, G["title_cy"]
    add(tl.wipe_mask("MaskTitle", left, cy, 800, 240, f"{C}.TitleW", w)).set("Width", 0.4, expr=f"{C}.TitleW*{tl.on(w)}")
    add(text("TxtTitle", v["title"], G["title_left"], cy, 120, v["title_c"], font="Caveat", style="Bold",
             v_anchor=0)).link("EffectMask", "MaskTitle", "Mask")
    pen = add(text("TxtPen", "", left + 30, cy - 40, 64, v["pen_c"],
                   font="Font Awesome 6 Free", style="Solid", h_anchor=-1, v_anchor=1))
    pen.set("Center", fl.pt((left + 8, cy + 18)), expr=(
        f"Point({fl.fx(left + 8)} + {C}.TitleW*{w}, {fl.fy(cy + 18)} + 0.012*math.sin({tl.T}*1.7))"))
    pen_blend = tl.on(f"min(1, 8*{w}, 8*(1-{w}))", "0")

    # underline: marker drawn left -> right
    under = place_image(add, "Under", asset("underline"), G["ul_c"])
    add(tl.wipe_mask("MaskUnder", G["ul_c"][0] - G["ul_w"] / 2, G["ul_c"][1], G["ul_w"], 80,
                  f"{C}.UnderLen", tl.eased(82, 96), soft=0))
    under.link("EffectMask", "MaskUnder", "Mask")

    # body: typed letter by letter
    for node in ("TxtBodySrc", "TxtBody"):
        add(text(node, v["body"], G["body_left"], G["body_top"], 44, v["body_c"],
                 font="Courier New", style="Bold", v_anchor=-1, line_spacing=1.0))
    tools[-1].set("StyledText", v["body"], expr=tl.typing("TxtBodySrc", 92, 0.35))

    # sticky text: written by a wipe, rotated with the note
    sx, sy = G["sticky_text_c"]
    add(tl.wipe_mask("MaskSticky", sx - 190, sy, 380, 200, f"{380 / FW:.5f}", tl.prog(96, 124)))
    add(text("TxtSticky", v["sticky"], sx, sy, 50, v["sticky_c"], font="Caveat", style="SemiBold",
             h_anchor=0, v_anchor=0, line_spacing=0.85)).link("EffectMask", "MaskSticky", "Mask")
    add(transform("XfStickyText", "TxtSticky", pivot=fl.pt((sx, sy)))).set("Angle", -4.0)

    # composite (bottom -> top)
    stack = "BgClear"
    order = [layers["Paper"], ("TxtTitle", "1"), ("MrgPlaceUnder", "1"), ("TxtBody", "1"),
             layers["PolL"], layers["ClipL"], layers["PolR"], layers["ClipR"], layers["Tape"],
             layers["Sticky"], layers["Pin"], ("XfStickyText", "1"), ("TxtPen", pen_blend)]
    for k, (node, blend) in enumerate(order):
        m = add(merge(f"MrgStack{k:02d}", stack, node))
        if blend != "1":
            m.set("Blend", 1.0, expr=blend)
        stack = m.name

    _, out = tl.output(add, stack, [
        ("TitleW", "Title Width", round(720 / FW, 4), dict(INP_MinScale=0.05, INP_MaxScale=0.8)),
        ("UnderLen", "Underline Length", round(G["ul_w"] / FW, 4), dict(INP_MinScale=0.05, INP_MaxScale=0.8)),
        "AnimStart", "Speed", "Hold", "OutFrames"], intro_end=INTRO_END)
    fl.layout(tools)

    g = iter(range(1, 100))
    pubs = [Publish("TxtTitle", "StyledText", "Заголовок"),
            Publish("TxtBodySrc", "StyledText", "Текст"),
            Publish("TxtSticky", "StyledText", "Стикер: текст")]
    for node, label in (("TxtTitle", "Заголовок"), ("TxtBody", "Текст"), ("TxtSticky", "Стикер")):
        pubs += fl.publish_font(node, f"{label}: шрифт", next(g))
        pubs.append(Publish(node, "Size", f"{label}: размер"))
    for node, label in (("TxtTitle", "Заголовок: цвет"), ("TxtBody", "Текст: цвет"),
                        ("TxtSticky", "Стикер: цвет текста"), ("TxtPen", "Перо: цвет")):
        pubs += publish_color(node, "", label, next(g), suffix="1")
    pubs += [Publish(C, "TitleW", "Заголовок: ширина письма (доля кадра)"),
             Publish(C, "UnderLen", "Подчёркивание: длина (доля кадра)"),
             Publish("TxtBody", "LineSpacing", "Текст: межстрочный")]
    pubs += tl.publish([("AnimOn", "Анимация вкл."), ("AnimStart", "Анимация: старт, кадр"),
                        ("Speed", "Анимация: скорость"), ("OutOn", "Затухание вкл."),
                        ("Hold", "Пауза перед затуханием, кадров"), ("OutFrames", "Затухание, кадров"),
                        ("Center", "Позиция"), ("Size", "Масштаб")])
    return tools, pubs, out.name

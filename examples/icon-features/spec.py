"""Icon Features — 3 columns: thin ring + line icon (Phosphor-Thin) + 3-line label.

Reference: screenshot 958x278 (crop), scaled x1.6 into the lower third of a
1920x1080 frame. Columns pop in one by one, labels slide up; block fades out.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/davinci-resolve-templates/scripts"))
import fusion_lib as fl  # noqa: E402
from fusion_lib import Publish, background, merge, publish_color, text, transform  # noqa: E402

GROUP = "Prog-time"
PACK = "Icon Features"
CATEGORY = "Titles"
FRAME = (1920, 1080)
ANIM = "expr"
PREVIEW_BG = "#ebe7e1"
fl.set_frame(*FRAME)
FW, FH = FRAME

S = 1.6
GAP = round(298 * S)              # column spacing, px
RING_D = round(131 * S)           # 210
RING_STROKE = 2 * S               # 3.2
TOP = 1080 - 80 - 213 * S         # block top (bottom 80 px from frame edge)
RING_CY = TOP + 65.5 * S
LABEL_TOP = TOP + 137 * S - 11    # cap top minus (ascent - cap) of Inter 44px
ICON_PX = 120
LABEL_PX = 44
LINE_SPACING = 0.74               # 40 px step / 54 px natural line box (UNVERIFIED)

ICONS = {"armchair": "", "potted-plant": "", "palette": ""}

FIT = [(f"TxtLabel{i}", GAP - 30) for i in (1, 2, 3)]

VARIANTS = {
    "Icon Features": dict(
        ink="#3b3632", label="#161615",
        cols=[("armchair", "Гармонично\nв любом\nинтерьере"),
              ("potted-plant", "Подходит\nдля живых\nрастений"),
              ("palette", "Уникальный\nдекор\nсвоими руками")],
    ),
}

CTRL = "XfBlock"


def clamp01(e):
    return f"min(1, max(0, {e}))"


def build(v, anim="expr"):
    tools = []

    def add(t):
        tools.append(t)
        return t

    add(background("BgCanvas", "#000000", alpha=0.0))
    stack = "BgCanvas"
    for i, (icon, label) in enumerate(v["cols"], 1):
        k = i - 1
        cx = FW / 2 + (k - 1) * GAP
        t0 = f"(time - {CTRL}.AnimStart - {k}*{CTRL}.Stagger)"
        p = clamp01(f"{t0}/{CTRL}.PopFrames")
        q = clamp01(f"({t0} - 4)/12")

        # ring + icon on their own canvas, scaled around the ring center (pop)
        add(background(f"BgCol{i}", "#000000", alpha=0.0))
        ring_m = add(fl.ellipse_mask(f"MaskRing{i}", cx, RING_CY, RING_D, RING_D, border_px=RING_STROKE))
        ring = add(background(f"BgRing{i}", v["ink"], mask=ring_m.name))
        ic = add(text(f"TxtIcon{i}", ICONS[icon], cx, RING_CY, ICON_PX, v["ink"],
                      font="Phosphor-Thin", style="Regular", h_anchor=0, v_anchor=0))
        if i > 1:
            ic.follow_color("TxtIcon1")
            ic.set("Size", ic.inputs["Size"].value, expr="TxtIcon1.Size")
            ring_m.set("BorderWidth", ring_m.inputs["BorderWidth"].value, expr="MaskRing1.BorderWidth")
        for ch in ("Red", "Green", "Blue"):
            ring.set(f"TopLeft{ch}", ring.inputs[f"TopLeft{ch}"].value, expr=f"TxtIcon1.{ch}1")
        add(merge(f"MrgRing{i}", f"BgCol{i}", f"BgRing{i}"))
        add(merge(f"MrgIcon{i}", f"MrgRing{i}", f"TxtIcon{i}"))
        # Center stays (0.5, 0.5) = no offset; Pivot = ring center so pop scales in place
        pop = add(transform(f"XfPop{i}", f"MrgIcon{i}", pivot=(fl.fx(cx), fl.fy(RING_CY))))
        # easeOutBack: 1 + 2.70158*(p-1)^3 + 1.70158*(p-1)^2
        pop.set("Size", 1.0, expr=f"iif({CTRL}.AnimOn > 0.5, max(0.001, 1 + 2.70158*({p}-1)^3 + 1.70158*({p}-1)^2), 1)")

        # label: slide up + fade
        lb = add(text(f"TxtLabel{i}", label, cx, LABEL_TOP, LABEL_PX, v["label"], font="Inter",
                      style="ExtraBold", h_anchor=0, v_anchor=-1, line_spacing=LINE_SPACING))
        if i > 1:
            lb.follow_color("TxtLabel1")
            lb.set("LineSpacing", LINE_SPACING, expr="TxtLabel1.LineSpacing")
        slide = add(transform(f"XfSlide{i}", f"TxtLabel{i}"))
        slide.set("Center", (0.5, 0.5),
                  expr=f"Point(0.5, 0.5 - iif({CTRL}.AnimOn > 0.5, 0.03*(1-{q})^3, 0))")

        # column = icon (fades in fast with pop) + label (fades with slide)
        add(merge(f"MrgColIcon{i}", f"BgCol{i}", f"XfPop{i}")).set(
            "Blend", 1.0, expr=f"iif({CTRL}.AnimOn > 0.5, min(1, 4*{p}), 1)")
        add(merge(f"MrgColLabel{i}", f"MrgColIcon{i}", f"XfSlide{i}")).set(
            "Blend", 1.0, expr=f"iif({CTRL}.AnimOn > 0.5, {q}, 1)")
        col = add(transform(f"XfCol{i}", f"MrgColLabel{i}"))
        col.set("Center", (0.5, 0.5), expr=f"Point(0.5 + {k - 1}*({CTRL}.ColGap - {round(GAP / FW, 5)}), 0.5)")
        stack = add(merge(f"MrgCol{i}", stack, f"XfCol{i}")).name

    blk = add(transform(CTRL, stack))
    ctrls = [
        ("ColGap", "Column Gap", round(GAP / FW, 5), dict(INP_MinScale=0.05, INP_MaxScale=0.5)),
        ("AnimStart", "Anim Start", 0, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=120)),
        ("Stagger", "Stagger", 8, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=30, INP_MinAllowed=0)),
        ("PopFrames", "Pop Frames", 10, dict(INP_Integer=True, INP_MinScale=1, INP_MaxScale=40, INP_MinAllowed=1)),
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
    out = add(merge("MrgOut", "BgOut", CTRL))
    out.set("Blend", 1.0, expr=f"iif({CTRL}.OutOn > 0.5, {clamp01(f'(comp.RenderEnd - time)/{CTRL}.OutFrames')}, 1)")
    fl.layout(tools)

    g = iter(range(1, 100))
    pubs = []
    for i in range(1, 4):
        pubs += [Publish(f"TxtIcon{i}", "StyledText", f"Колонка {i}: иконка"),
                 Publish(f"TxtLabel{i}", "StyledText", f"Колонка {i}: текст")]
    pubs += publish_color("TxtIcon1", "", "Иконки и кольца: цвет", next(g), suffix="1")
    pubs += publish_color("TxtLabel1", "", "Текст: цвет", next(g), suffix="1")
    pubs += [Publish("TxtIcon1", "Size", "Иконка: размер"),
             Publish("MaskRing1", "BorderWidth", "Кольцо: толщина"),
             Publish("TxtLabel1", "LineSpacing", "Текст: межстрочный"),
             Publish(CTRL, "ColGap", "Расстояние между колонками")]
    for i in range(1, 4):
        pubs += fl.publish_font(f"TxtLabel{i}", f"Колонка {i}: шрифт", next(g))
    pubs += [Publish(CTRL, "AnimOn", "Анимация вкл."),
             Publish(CTRL, "AnimStart", "Анимация: старт, кадр"),
             Publish(CTRL, "Stagger", "Анимация: задержка между колонками"),
             Publish(CTRL, "PopFrames", "Анимация: pop, кадров"),
             Publish(CTRL, "OutOn", "Выход вкл."),
             Publish(CTRL, "OutFrames", "Выход, кадров"),
             Publish(CTRL, "Center", "Позиция"),
             Publish(CTRL, "Size", "Масштаб")]
    return tools, pubs, out.name

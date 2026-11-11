"""Subscribe Bar — avatar photo (spiral zoom-in), grey bar, like/bell icons,
red SUBSCRIBE button that gets "pressed" and turns into grey "Subscribed".

Reference: 554x360 screenshot, scaled x1.4, block centered in 1920x1080.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/davinci-resolve-templates/scripts"))
import fusion_lib as fl  # noqa: E402
from fusion_anim import Timeline, clamp01, place_image  # noqa: E402
from fusion_lib import Publish, background, merge, publish_color, rect_mask, text, transform  # noqa: E402

GROUP = "Prog-time"
PACK = "Subscribe Bar"
CATEGORY = "Titles"
FRAME = (1920, 1080)
ANIM = "expr"
PREVIEW_BG = "#34333d"
fl.set_frame(*FRAME)
FW, FH = FRAME

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = {"subscribe-avatar.png": os.path.join(HERE, "assets", "subscribe-avatar.png")}
PHOTO = fl.asset_path(GROUP, "subscribe-avatar.png")

S = 1.4


def P(x, y):
    """Reference px (554x360 screenshot) -> frame px, block centered."""
    return 960 + (x - 274.5) * S, 540 + (y - 158) * S


AV = P(274.5, 100)            # avatar center
AV_D, PH_D = 143 * S, 119 * S  # ring outer / photo diameter
BAR = P(274.5, 241)
BAR_W, BAR_H = 502 * S, 93 * S
BTN = P(274, 241)
BTN_W, BTN_H = 243 * S, 51 * S
LIKE = P(78.5, 241.5)
BELL = P(469.5, 240.5)

FIT = [("TxtBtnRed", BTN_W - 30), ("TxtBtnGray", BTN_W - 30)]

VARIANTS = {
    "Subscribe Bar": dict(
        bar="#e6e6e6", like="#4a94d1", bell="#e8ac43", btn_red="#ff0000", btn_gray="#3e3e3e",
        btn_text="#ffffff", text_before="SUBSCRIBE", text_after="Subscribed",
    ),
}

tl = Timeline("XfBlock", speed=False)
C, T = tl.C, tl.T


def stage(k):
    """Progress 0..1 of the k-th slide (k=0 bar, 1 like, 2 bell, 3 button)."""
    return clamp01(f"({T} - {C}.PhotoFrames - {k}*{C}.Step)/10")


def build(v, anim="expr"):
    tools = []

    def add(t):
        tools.append(t)
        return t

    # avatar: ring + circular photo, spiral zoom-in
    add(background("BgAvCanvas", "#000000", alpha=0.0))
    add(fl.ellipse_mask("MaskAvRing", *AV, AV_D, AV_D))
    ring = add(background("BgAvRing", v["bar"], mask="MaskAvRing"))
    add(merge("MrgAvRing", "BgAvCanvas", "BgAvRing"))
    add(fl.ellipse_mask("MaskPhoto", *AV, PH_D, PH_D))
    place_image(add, "Photo", PHOTO, AV, round(PH_D / 512, 5), canvas="MrgAvRing", mask="MaskPhoto",
                merge_name="MrgPhoto")
    p = clamp01(f"{T}/{C}.PhotoFrames")
    q = f"(1-{p})"
    av = add(transform("XfAvatar", "MrgPhoto", pivot=fl.pt(AV)))
    av.set("Size", 1.0, expr=tl.on(f"max(0.001, 1 - {q}^3)"))
    av.set("Angle", 0.0, expr=tl.on(f"-360*{q}^2"))
    theta = f"(2*math.pi*1.25*{q})"
    av.set("Center", (0.5, 0.5), expr=tl.on(
        f"Point(0.5 + 0.12*{q}*math.cos({theta}), 0.5 + 0.12*{FW / FH:.4f}*{q}*math.sin({theta}))",
        "Point(0.5, 0.5)"))

    # bar and icons: slide up / slide down
    add(rect_mask("MaskBar", *BAR, BAR_W, BAR_H, round(14 * S / (BAR_H / 2), 3)))
    add(background("BgBar", v["bar"], mask="MaskBar"))
    ring.follow_color("BgBar", "TopLeft", "")
    add(tl.slide_y("XfBar", "BgBar", stage(0), direction=+1))
    for name, glyph, pos, size, col, k, direction in (("Like", "\uf164", LIKE, 44, "like", 1, -1),
                                                      ("Bell", "\uf0f3", BELL, 38, "bell", 2, +1)):
        add(text(f"Txt{name}", glyph, *pos, size, v[col], font="Font Awesome 6 Free", style="Solid",
                 h_anchor=0, v_anchor=0))
        add(tl.slide_y(f"Xf{name}", f"Txt{name}", stage(k), direction=direction))

    # button: red state, grey state, press
    add(rect_mask("MaskBtn", *BTN, BTN_W, BTN_H, round(10 * S / (BTN_H / 2), 3)))
    add(background("BgBtnCanvas", "#000000", alpha=0.0))
    for state, key in (("Red", "text_before"), ("Gray", "text_after")):
        add(background(f"BgBtn{state}", v[f"btn_{state.lower()}"], mask="MaskBtn"))
        add(merge(f"MrgBtn{state}", "BgBtnCanvas", f"BgBtn{state}"))
        add(text(f"TxtBtn{state}", v[key], *BTN, 36, v["btn_text"], style="Bold", h_anchor=0, v_anchor=0))
        add(merge(f"MrgBtn{state}Txt", f"MrgBtn{state}", f"TxtBtn{state}"))
    tools[-2].follow_color("TxtBtnRed")
    tp = f"({C}.PhotoFrames + 3*{C}.Step + 10 + {C}.PressDelay)"       # press start
    bump = f"max(0, 1 - abs({T} - {tp} - 4)/4)"                        # 0..1..0 over 8 frames
    add(merge("MrgBtnState", "MrgBtnRedTxt", "MrgBtnGrayTxt")).set(
        "Blend", 0.0, expr=tl.on(clamp01(f"({T} - {tp} - 4)/2")))
    add(transform("XfPress", "MrgBtnState", pivot=fl.pt(BTN))).set(
        "Size", 1.0, expr=tl.on(f"1 - 0.1*{bump}"))
    add(tl.slide_y("XfBtn", "XfPress", stage(3), direction=+1))

    # composite
    add(background("BgCanvas", "#000000", alpha=0.0))
    stack = "BgCanvas"
    for k, node in enumerate(("XfBar", "XfLike", "XfBell", "XfBtn")):
        stack = add(merge(f"MrgL{node[2:]}", stack, node)).name
        tools[-1].set("Blend", 1.0, expr=tl.on(stage(k)))
    m = add(merge("MrgLAvatar", stack, "XfAvatar"))
    m.set("Blend", 1.0, expr=tl.on(f"min(1, 3*{p})"))

    def frames(cid, label, default, lo, hi, minimum):
        return (cid, label, default, dict(INP_Integer=True, INP_MinScale=lo, INP_MaxScale=hi, INP_MinAllowed=minimum))
    _, out = tl.output(add, m.name, ["AnimStart", frames("PhotoFrames", "Photo Frames", 18, 1, 60, 1),
                                     frames("Step", "Step", 6, 0, 30, 0),
                                     frames("PressDelay", "Press Delay", 15, 0, 120, 0), "OutFrames"],
                       fade="clip_end")
    fl.layout(tools)

    g = iter(range(1, 100))
    pubs = [Publish("TxtBtnRed", "StyledText", "Кнопка: текст до"),
            Publish("TxtBtnGray", "StyledText", "Кнопка: текст после")]
    for node, prefix, label, suffix in (("BgBtnRed", "TopLeft", "Кнопка: цвет до", ""),
                                        ("BgBtnGray", "TopLeft", "Кнопка: цвет после", ""),
                                        ("TxtBtnRed", "", "Кнопка: цвет текста", "1"),
                                        ("BgBar", "TopLeft", "Плашка и кольцо", ""),
                                        ("TxtLike", "", "Like: цвет", "1"),
                                        ("TxtBell", "", "Колокольчик: цвет", "1")):
        pubs += publish_color(node, prefix, label, next(g), suffix=suffix)
    pubs += [Publish("TxtLike", "StyledText", "Like: иконка"),
             Publish("TxtBell", "StyledText", "Колокольчик: иконка")]
    pubs += tl.publish([("AnimOn", "Анимация вкл."), ("AnimStart", "Анимация: старт, кадр"),
                        ("PhotoFrames", "Фото: кадров на спираль"), ("Step", "Шаг между элементами"),
                        ("PressDelay", "Нажатие: кадров после кнопки"), ("OutOn", "Выход вкл."),
                        ("OutFrames", "Выход, кадров"), ("Center", "Позиция"), ("Size", "Масштаб")])
    return tools, pubs, out.name

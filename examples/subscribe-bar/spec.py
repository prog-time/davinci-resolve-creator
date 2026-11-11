"""Subscribe Bar — avatar photo (spiral zoom-in), grey bar, like/bell icons,
red SUBSCRIBE button that gets "pressed" and turns into grey "Subscribed".

Reference: 554x360 screenshot, scaled x1.4, block centered in 1920x1080.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/davinci-resolve-templates/scripts"))
import fusion_lib as fl  # noqa: E402
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

VARIANTS = {
    "Subscribe Bar": dict(
        bar="#e6e6e6", like="#4a94d1", bell="#e8ac43", btn_red="#ff0000", btn_gray="#3e3e3e",
        btn_text="#ffffff", text_before="SUBSCRIBE", text_after="Subscribed",
    ),
}

C = "XfBlock"
T = f"(time - {C}.AnimStart)"


def clamp01(e):
    return f"min(1, max(0, {e}))"


def stage(k):
    """Progress 0..1 of the k-th slide (k=0 bar, 1 like, 2 bell, 3 button)."""
    return clamp01(f"({T} - {C}.PhotoFrames - {k}*{C}.Step)/10")


def on(e):
    return f"iif({C}.AnimOn > 0.5, {e}, 1)"


def slide_y(s, direction):
    """direction +1 = slideUp (comes from below), -1 = slideDown (comes from above)."""
    return f"Point(0.5, 0.5 - {direction}*iif({C}.AnimOn > 0.5, 0.04*(1-{s})^3, 0))"


def build(v, anim="expr"):
    tools = []

    def add(t):
        tools.append(t)
        return t

    def piv(pt):
        return (fl.fx(pt[0]), fl.fy(pt[1]))

    # ---------- avatar: ring + circular photo ----------
    add(background("BgAvCanvas", "#000000", alpha=0.0))
    add(fl.ellipse_mask("MaskAvRing", *AV, AV_D, AV_D))
    ring = add(background("BgAvRing", v["bar"], mask="MaskAvRing"))
    add(merge("MrgAvRing", "BgAvCanvas", "BgAvRing"))
    add(fl.loader("LdPhoto", PHOTO))
    add(fl.ellipse_mask("MaskPhoto", *AV, PH_D, PH_D))
    ph = add(merge("MrgPhoto", "MrgAvRing", "LdPhoto"))
    ph.set("Center", piv(AV)).set("Size", round(PH_D / 512, 5))
    ph.link("EffectMask", "MaskPhoto", "Mask")

    p = clamp01(f"{T}/{C}.PhotoFrames")
    q = f"(1-{p})"
    av = add(transform("XfAvatar", "MrgPhoto", pivot=piv(AV)))
    av.set("Size", 1.0, expr=on(f"max(0.001, 1 - {q}^3)"))
    av.set("Angle", 0.0, expr=on(f"-360*{q}^2"))
    theta = f"(2*math.pi*1.25*{q})"
    av.set("Center", (0.5, 0.5), expr=(
        f"iif({C}.AnimOn > 0.5, Point(0.5 + 0.12*{q}*math.cos({theta}), "
        f"0.5 + 0.12*{FW / FH:.4f}*{q}*math.sin({theta})), Point(0.5, 0.5))"))

    # ---------- bar ----------
    add(rect_mask("MaskBar", *BAR, BAR_W, BAR_H, round(14 * S / (BAR_H / 2), 3)))
    add(background("BgBar", v["bar"], mask="MaskBar"))
    ring.follow_color("BgBar", "TopLeft", "")
    add(transform("XfBar", "BgBar")).set("Center", (0.5, 0.5), expr=slide_y(stage(0), +1))

    # ---------- icons ----------
    add(text("TxtLike", "", *LIKE, 44, v["like"], font="Font Awesome 6 Free", style="Solid",
             h_anchor=0, v_anchor=0))
    add(transform("XfLike", "TxtLike")).set("Center", (0.5, 0.5), expr=slide_y(stage(1), -1))
    add(text("TxtBell", "", *BELL, 38, v["bell"], font="Font Awesome 6 Free", style="Solid",
             h_anchor=0, v_anchor=0))
    add(transform("XfBell", "TxtBell")).set("Center", (0.5, 0.5), expr=slide_y(stage(2), +1))

    # ---------- button: red state, grey state, press ----------
    radius = round(10 * S / (BTN_H / 2), 3)
    add(rect_mask("MaskBtn", *BTN, BTN_W, BTN_H, radius))
    add(background("BgBtnCanvas", "#000000", alpha=0.0))
    add(background("BgBtnRed", v["btn_red"], mask="MaskBtn"))
    add(merge("MrgBtnRed", "BgBtnCanvas", "BgBtnRed"))
    add(text("TxtBtnRed", v["text_before"], *BTN, 36, v["btn_text"], style="Bold", h_anchor=0, v_anchor=0))
    add(merge("MrgBtnRedTxt", "MrgBtnRed", "TxtBtnRed"))
    add(background("BgBtnGray", v["btn_gray"], mask="MaskBtn"))
    add(merge("MrgBtnGray", "BgBtnCanvas", "BgBtnGray"))
    tg = add(text("TxtBtnGray", v["text_after"], *BTN, 36, v["btn_text"], style="Bold", h_anchor=0, v_anchor=0))
    tg.follow_color("TxtBtnRed")
    add(merge("MrgBtnGrayTxt", "MrgBtnGray", "TxtBtnGray"))

    tp = f"({C}.PhotoFrames + 3*{C}.Step + 10 + {C}.PressDelay)"       # press start
    bump = f"max(0, 1 - abs({T} - {tp} - 4)/4)"                        # 0..1..0 over 8 frames
    state = add(merge("MrgBtnState", "MrgBtnRedTxt", "MrgBtnGrayTxt"))
    state.set("Blend", 0.0, expr=f"iif({C}.AnimOn > 0.5, {clamp01(f'({T} - {tp} - 4)/2')}, 1)")
    press = add(transform("XfPress", "MrgBtnState", pivot=piv(BTN)))
    press.set("Size", 1.0, expr=f"iif({C}.AnimOn > 0.5, 1 - 0.1*{bump}, 1)")
    add(transform("XfBtn", "XfPress")).set("Center", (0.5, 0.5), expr=slide_y(stage(3), +1))

    # ---------- composite ----------
    add(background("BgCanvas", "#000000", alpha=0.0))
    stack = "BgCanvas"
    for k, node in enumerate(("XfBar", "XfLike", "XfBell", "XfBtn")):
        m = add(merge(f"MrgL{node[2:]}", stack, node))
        m.set("Blend", 1.0, expr=on(stage(k)))
        stack = m.name
    m = add(merge("MrgLAvatar", stack, "XfAvatar"))
    m.set("Blend", 1.0, expr=on(f"min(1, 3*{p})"))

    blk = add(transform(C, m.name))
    ctrls = [
        ("AnimStart", "Anim Start", 0, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=120)),
        ("PhotoFrames", "Photo Frames", 18, dict(INP_Integer=True, INP_MinScale=1, INP_MaxScale=60, INP_MinAllowed=1)),
        ("Step", "Step", 6, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=30, INP_MinAllowed=0)),
        ("PressDelay", "Press Delay", 15, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=120, INP_MinAllowed=0)),
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
    out.set("Blend", 1.0, expr=f"iif({C}.OutOn > 0.5, {clamp01(f'(comp.RenderEnd - time)/{C}.OutFrames')}, 1)")
    fl.layout(tools)

    g = iter(range(1, 100))
    pubs = [Publish("TxtBtnRed", "StyledText", "Кнопка: текст до"),
            Publish("TxtBtnGray", "StyledText", "Кнопка: текст после")]
    pubs += publish_color("BgBtnRed", "TopLeft", "Кнопка: цвет до", next(g))
    pubs += publish_color("BgBtnGray", "TopLeft", "Кнопка: цвет после", next(g))
    pubs += publish_color("TxtBtnRed", "", "Кнопка: цвет текста", next(g), suffix="1")
    pubs += publish_color("BgBar", "TopLeft", "Плашка и кольцо", next(g))
    pubs += publish_color("TxtLike", "", "Like: цвет", next(g), suffix="1")
    pubs += publish_color("TxtBell", "", "Колокольчик: цвет", next(g), suffix="1")
    pubs += [Publish("TxtLike", "StyledText", "Like: иконка"),
             Publish("TxtBell", "StyledText", "Колокольчик: иконка"),
             Publish(C, "AnimOn", "Анимация вкл."),
             Publish(C, "AnimStart", "Анимация: старт, кадр"),
             Publish(C, "PhotoFrames", "Фото: кадров на спираль"),
             Publish(C, "Step", "Шаг между элементами"),
             Publish(C, "PressDelay", "Нажатие: кадров после кнопки"),
             Publish(C, "OutOn", "Выход вкл."),
             Publish(C, "OutFrames", "Выход, кадров"),
             Publish(C, "Center", "Позиция"),
             Publish(C, "Size", "Масштаб")]
    return tools, pubs, out.name

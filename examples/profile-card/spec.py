"""Profile Card — recreated from "animate card.mov" (60 fps, retimed to 30 fps).

Dark card pops from a point (590x590), white frame and photo grow inside, card
extends to 590x808 pushing the photo up, name / role / company type on letter by
letter, then the card shrinks to 91% while two tinted photo copies fan out.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/davinci-resolve-templates/scripts"))
import fusion_lib as fl  # noqa: E402
from fusion_anim import Timeline, ease, place_image  # noqa: E402
from fusion_lib import Publish, background, merge, publish_color, rect_mask, text, transform  # noqa: E402

GROUP = "Prog-time"
PACK = "Profile Card"
CATEGORY = "Titles"
FRAME = (1920, 1080)
ANIM = "expr"
PREVIEW_BG = "#f6fef3"
fl.set_frame(*FRAME)
FW, FH = FRAME

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = {"profile-photo.png": os.path.join(HERE, "assets", "profile-photo.png")}
PHOTO = fl.asset_path(GROUP, "profile-photo.png")
IMG_W = 772                       # asset width (photo shown at 386 px)

CX, CY = 960, 540
CARD_W, CARD_H0, CARD_H1 = 590, 590, 808
WHITE = (960, 428.5, 525)
PH = (960, 430, 386, 407)
SHIFT = 111.5                     # photo group offset (px) before the card extends
INTRO_END = 126                   # last animated frame of the intro (timeline frames at Speed 1)

VARIANTS = {
    "Profile Card": dict(
        card="#201f20", white="#eaeaea", name_c="#eaeaea", role_c="#53acc0", company_c="#b6b5b6",
        tint="#53acc0", name="ИМЯ ФАМИЛИЯ", role="ДОЛЖНОСТЬ", company="Компания",
    ),
}

tl = Timeline("XfBlock")
C = tl.C
# key, color key, style, em px, center y, CharacterSpacing, typing start, frames per char
TEXTS = [("Name", "name_c", "Bold", 84, 755.6, 0.938, 69, 1.5),
         ("Role", "role_c", "Bold", 38, 833.2, 1.224, 81, 3),
         ("Company", "company_c", "Light", 27, 892.2, None, 87, 1.8)]
LABELS = {"Name": "Имя", "Role": "Должность", "Company": "Компания"}


def build(v, anim="expr"):
    tools = []

    def add(t):
        tools.append(t)
        return t

    e_ext = tl.eased(57, 81, "io4")          # card extension 0..1
    e_fan = tl.eased(105, 126, "io3")        # final shrink + fan 0..1
    ph_c = fl.pt(PH[:2])

    # card
    m = add(rect_mask("MaskCard", CX, CY, CARD_W, CARD_H1, round(30 / (CARD_W / 2), 4)))
    m.set("Height", m.inputs["Height"].value, expr=tl.on(f"({CARD_H0} + {CARD_H1 - CARD_H0}*{e_ext})/{FH}",
                                                          f"{CARD_H1 / FH:.5f}"))
    add(background("BgCard", v["card"], mask="MaskCard"))
    add(tl.grow("XfCardPop", "BgCard", 0, 33, fl.pt((CX, CY)), "io4"))

    # inner group: white frame, photo copies, photo
    add(background("BgInCanvas", "#000000", alpha=0.0))
    add(rect_mask("MaskWhite", WHITE[0], WHITE[1], WHITE[2], WHITE[2], round(20 / (WHITE[2] / 2), 4)))
    add(background("BgWhite", v["white"], mask="MaskWhite"))
    add(tl.grow("XfWhite", "BgWhite", 20, 38, fl.pt(WHITE[:2])))
    stack = add(merge("MrgInWhite", "BgInCanvas", "XfWhite")).name

    add(rect_mask("MaskPhoto", PH[0], PH[1], PH[2], PH[3], round(22 / (PH[2] / 2), 4)))
    add(fl.loader("LdPhoto", PHOTO))

    def photo_layer(prefix):
        add(background(f"Bg{prefix}Canvas", "#000000", alpha=0.0))
        return place_image(add, prefix, None, PH[:2], round(PH[2] / IMG_W, 5), canvas=f"Bg{prefix}Canvas",
                           mask="MaskPhoto", loader="LdPhoto", merge_name=f"Mrg{prefix}").name

    for i, angle in ((1, -9), (2, 6)):
        base = photo_layer(f"Copy{i}")
        tint = add(background(f"BgTint{i}", v["tint"], mask="MaskPhoto"))
        if i > 1:
            tint.follow_color("BgTint1", "TopLeft", "")
        add(merge(f"MrgTint{i}", base, f"BgTint{i}", blend=0.6))
        xc = add(transform(f"XfCopy{i}", f"MrgTint{i}", pivot=ph_c))
        xc.set("Angle", float(angle), expr=tl.on(f"{angle}*{e_fan}", str(float(angle))))
        stack = add(merge(f"MrgInCopy{i}", stack, f"XfCopy{i}")).name
        tools[-1].set("Blend", 1.0, expr=tl.on(f"min(1, 6*{e_fan})"))

    add(tl.grow("XfPhoto", photo_layer("Photo"), 36, 51, ph_c))
    stack = add(merge("MrgInPhoto", stack, "XfPhoto")).name
    inner = add(transform("XfInner", stack))
    inner.set("Center", (0.5, 0.5), expr=tl.on(f"Point(0.5, 0.5 - {SHIFT / FH:.5f}*(1 - {e_ext}))",
                                               "Point(0.5, 0.5)"))

    # texts: source nodes hold the published text, display nodes type it
    add(background("BgCanvas", "#000000", alpha=0.0))
    stack = add(merge("MrgCardPop", "BgCanvas", "XfCardPop")).name
    stack = add(merge("MrgInner", stack, "XfInner")).name
    for key, ckey, style, size, y, cs, start, per in TEXTS:
        txt = v[key.lower()]
        add(text(f"Txt{key}Src", txt, CX, y, size, v[ckey], font="Oswald", style=style, h_anchor=0, v_anchor=0))
        t = add(text(f"Txt{key}", txt, CX, y, size, v[ckey], font="Oswald", style=style, h_anchor=0, v_anchor=0))
        if cs:
            t.set("CharacterSpacing", cs)
        t.set("StyledText", txt, expr=tl.typing(f"Txt{key}Src", start, per))
        stack = add(merge(f"Mrg{key}", stack, f"Txt{key}")).name

    shrink = add(transform("XfShrink", stack, pivot=fl.pt((CX, CY))))
    shrink.set("Size", 1.0, expr=tl.on(f"1 - 0.09*{e_fan}", "0.91"))
    _, out = tl.output(add, "XfShrink", ["AnimStart", "Speed", "Hold", "OutFrames"], intro_end=INTRO_END)
    fl.layout(tools)

    g = iter(range(1, 100))
    pubs = [Publish(f"Txt{k}Src", "StyledText", LABELS[k]) for k in LABELS]
    pubs += publish_color("BgCard", "TopLeft", "Карточка: фон", next(g))
    pubs += publish_color("BgWhite", "TopLeft", "Рамка", next(g))
    for k in LABELS:
        pubs += publish_color(f"Txt{k}", "", f"{LABELS[k]}: цвет", next(g), suffix="1")
    pubs += publish_color("BgTint1", "TopLeft", "Копии фото: тон", next(g))
    for k in LABELS:
        pubs += fl.publish_font(f"Txt{k}", f"{LABELS[k]}: шрифт", next(g))
        pubs.append(Publish(f"Txt{k}", "Size", f"{LABELS[k]}: размер"))
    pubs += [Publish("TxtName", "CharacterSpacing", "Имя: межбуквенный"),
             Publish("TxtRole", "CharacterSpacing", "Должность: межбуквенный")]
    pubs += tl.publish([("AnimOn", "Анимация вкл."), ("AnimStart", "Анимация: старт, кадр"),
                        ("Speed", "Анимация: скорость"), ("OutOn", "Затухание вкл."),
                        ("Hold", "Пауза перед затуханием, кадров"), ("OutFrames", "Затухание, кадров"),
                        ("Center", "Позиция"), ("Size", "Масштаб")])
    return tools, pubs, out.name

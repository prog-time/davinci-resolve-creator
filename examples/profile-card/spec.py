"""Profile Card — recreated from "animate card.mov" (60 fps, retimed to 30 fps).

Dark card pops from a point (590x590), white frame and photo grow inside, card
extends to 590x808 pushing the photo up, name / role / company type on letter by
letter, then the card shrinks to 91% while two tinted photo copies fan out.
"""
import os
import sys

sys.path.insert(0, os.path.expanduser("~/.claude/skills/davinci-resolve-templates/scripts"))
import fusion_lib as fl  # noqa: E402
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

FIT = [("TxtName", CARD_W - 40), ("TxtRole", CARD_W - 40), ("TxtCompany", CARD_W - 40)]

VARIANTS = {
    "Profile Card": dict(
        card="#201f20", white="#eaeaea", name_c="#eaeaea", role_c="#53acc0", company_c="#b6b5b6",
        tint="#53acc0", name="ИМЯ ФАМИЛИЯ", role="ДОЛЖНОСТЬ", company="Компания",
    ),
}

C = "XfBlock"
T = f"((time - {C}.AnimStart)*{C}.Speed)"


def clamp01(e):
    return f"min(1, max(0, {e}))"


def prog(a, b):
    return clamp01(f"({T} - {a})/{b - a}")


def ease_io4(x):
    return f"iif({x} < 0.5, 8*({x})^4, 1 - 8*(1-{x})^4)"


def ease_io3(x):
    return f"iif({x} < 0.5, 4*({x})^3, 1 - 4*(1-{x})^3)"


def ease_out3(x):
    return f"(1 - (1-{x})^3)"


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


def build(v, anim="expr"):
    tools = []

    def add(t):
        tools.append(t)
        return t

    def pt(x, y):
        return (fl.fx(x), fl.fy(y))

    e_ext = ease_io4(prog(57, 81))          # card extension 0..1
    e_fan = ease_io3(prog(105, 126))        # final shrink + fan 0..1

    # ---------- card ----------
    m = add(rect_mask("MaskCard", CX, CY, CARD_W, CARD_H1, round(30 / (CARD_W / 2), 4)))
    m.set("Height", m.inputs["Height"].value, expr=on(f"({CARD_H0} + {CARD_H1 - CARD_H0}*{e_ext})/{FH}",
                                                       f"{CARD_H1 / FH:.5f}"))
    add(background("BgCard", v["card"], mask="MaskCard"))
    pop = add(transform("XfCardPop", "BgCard", pivot=pt(CX, CY)))
    pop.set("Size", 1.0, expr=on(f"max(0.001, {ease_io4(prog(0, 33))})"))

    # ---------- inner group: white frame, photo copies, photo ----------
    add(background("BgInCanvas", "#000000", alpha=0.0))
    add(rect_mask("MaskWhite", WHITE[0], WHITE[1], WHITE[2], WHITE[2], round(20 / (WHITE[2] / 2), 4)))
    add(background("BgWhite", v["white"], mask="MaskWhite"))
    xw = add(transform("XfWhite", "BgWhite", pivot=pt(WHITE[0], WHITE[1])))
    xw.set("Size", 1.0, expr=on(f"max(0.001, {ease_out3(prog(20, 38))})"))
    stack = add(merge("MrgInWhite", "BgInCanvas", "XfWhite")).name

    add(rect_mask("MaskPhoto", PH[0], PH[1], PH[2], PH[3], round(22 / (PH[2] / 2), 4)))
    add(fl.loader("LdPhoto", PHOTO))

    def photo_layer(prefix):
        add(background(f"Bg{prefix}Canvas", "#000000", alpha=0.0))
        mp = add(merge(f"Mrg{prefix}", f"Bg{prefix}Canvas", "LdPhoto"))
        mp.set("Center", pt(PH[0], PH[1])).set("Size", round(PH[2] / IMG_W, 5))
        mp.link("EffectMask", "MaskPhoto", "Mask")
        return mp.name

    for i, angle in ((1, -9), (2, 6)):
        base = photo_layer(f"Copy{i}")
        tint = add(background(f"BgTint{i}", v["tint"], mask="MaskPhoto"))
        if i > 1:
            tint.follow_color("BgTint1", "TopLeft", "")
        add(merge(f"MrgTint{i}", base, f"BgTint{i}", blend=0.6))
        xc = add(transform(f"XfCopy{i}", f"MrgTint{i}", pivot=pt(PH[0], PH[1])))
        xc.set("Angle", float(angle), expr=on(f"{angle}*{e_fan}", str(float(angle))))
        mc = add(merge(f"MrgInCopy{i}", stack, f"XfCopy{i}"))
        mc.set("Blend", 1.0, expr=on(f"min(1, 6*{e_fan})"))
        stack = mc.name

    main = photo_layer("Photo")
    xp = add(transform("XfPhoto", main, pivot=pt(PH[0], PH[1])))
    xp.set("Size", 1.0, expr=on(f"max(0.001, {ease_out3(prog(36, 51))})"))
    stack = add(merge("MrgInPhoto", stack, "XfPhoto")).name
    inner = add(transform("XfInner", stack))
    inner.set("Center", (0.5, 0.5), expr=on(f"Point(0.5, 0.5 - {SHIFT / FH:.5f}*(1 - {e_ext}))", "Point(0.5, 0.5)"))

    # ---------- texts (source nodes hold the published text, display nodes type it) ----------
    texts = [("Name", v["name"], v["name_c"], "Bold", 84, 755.6, 0.938, 69, 1.5),
             ("Role", v["role"], v["role_c"], "Bold", 38, 833.2, 1.224, 81, 3),
             ("Company", v["company"], v["company_c"], "Light", 27, 892.2, None, 87, 1.8)]
    add(background("BgCanvas", "#000000", alpha=0.0))
    stack = add(merge("MrgCardPop", "BgCanvas", "XfCardPop")).name
    stack = add(merge("MrgInner", stack, "XfInner")).name
    for key, txt, col, style, size, y, cs, start, per in texts:
        add(text(f"Txt{key}Src", txt, CX, y, size, col, font="Oswald", style=style, h_anchor=0, v_anchor=0))
        t = add(text(f"Txt{key}", txt, CX, y, size, col, font="Oswald", style=style, h_anchor=0, v_anchor=0))
        if cs:
            t.set("CharacterSpacing", cs)
        t.set("StyledText", txt, expr=typing(f"Txt{key}Src", start, per))
        stack = add(merge(f"Mrg{key}", stack, f"Txt{key}")).name

    shrink = add(transform("XfShrink", stack, pivot=pt(CX, CY)))
    shrink.set("Size", 1.0, expr=on(f"1 - 0.09*{e_fan}", "0.91"))

    blk = add(transform(C, "XfShrink"))
    ctrls = [
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
    # fade starts after the intro is complete (source frame 126 at Speed 1) + Hold frames;
    # independent of clip length (no comp.RenderEnd)
    intro_end = f"({C}.AnimStart + {INTRO_END}/{C}.Speed)"
    out.set("Blend", 1.0, expr=(f"iif({C}.OutOn > 0.5, "
                                f"{clamp01(f'1 - (time - {intro_end} - {C}.Hold)/{C}.OutFrames')}, 1)"))
    fl.layout(tools)

    g = iter(range(1, 100))
    pubs = [Publish("TxtNameSrc", "StyledText", "Имя"),
            Publish("TxtRoleSrc", "StyledText", "Должность"),
            Publish("TxtCompanySrc", "StyledText", "Компания")]
    pubs += publish_color("BgCard", "TopLeft", "Карточка: фон", next(g))
    pubs += publish_color("BgWhite", "TopLeft", "Рамка", next(g))
    pubs += publish_color("TxtName", "", "Имя: цвет", next(g), suffix="1")
    pubs += publish_color("TxtRole", "", "Должность: цвет", next(g), suffix="1")
    pubs += publish_color("TxtCompany", "", "Компания: цвет", next(g), suffix="1")
    pubs += publish_color("BgTint1", "TopLeft", "Копии фото: тон", next(g))
    for key, label in (("Name", "Имя"), ("Role", "Должность"), ("Company", "Компания")):
        pubs += fl.publish_font(f"Txt{key}", f"{label}: шрифт", next(g))
        pubs.append(Publish(f"Txt{key}", "Size", f"{label}: размер"))
    pubs += [Publish("TxtName", "CharacterSpacing", "Имя: межбуквенный"),
             Publish("TxtRole", "CharacterSpacing", "Должность: межбуквенный"),
             Publish(C, "AnimOn", "Анимация вкл."),
             Publish(C, "AnimStart", "Анимация: старт, кадр"),
             Publish(C, "Speed", "Анимация: скорость"),
             Publish(C, "OutOn", "Затухание вкл."),
             Publish(C, "Hold", "Пауза перед затуханием, кадров"),
             Publish(C, "OutFrames", "Затухание, кадров"),
             Publish(C, "Center", "Позиция"),
             Publish(C, "Size", "Масштаб")]
    return tools, pubs, out.name

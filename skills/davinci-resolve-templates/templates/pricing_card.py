"""Pricing card title — example spec for scripts/generate.py.

Measured from a 1382x766 reference screenshot: card 313x730 px, scaled x1.38
to 432x1007 px and centered in a 1920x1080 frame. Two variants (regular and
accent) instead of a style switch, so every color field stays editable.

Build:
    python3 scripts/generate.py templates/pricing_card.py --out out --pack
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import fusion_lib as fl  # noqa: E402
from fusion_lib import Publish, background, merge, publish_color, rect_mask, text, transform  # noqa: E402

GROUP = "Pricing Cards"
PACK = "Pricing Cards"
CATEGORY = "Titles"
FRAME = (1920, 1080)
ANIM = "expr"           # expr | keys | static
fl.set_frame(*FRAME)    # pixel helpers below depend on the frame

S = 1.38                # reference px -> frame px
CARD_W, CARD_H = 432, 1007
FW, FH = FRAME
L = (FW - CARD_W) / 2   # card left
T = (FH - CARD_H) / 2   # card top


def X(r):
    return L + r * S


def Y(r):
    return T + r * S


# Font Awesome 6 Free (Solid) code points; user swaps them via Copy Glyph.
ICONS = {
    "sparkles": "", "image": "", "brain": "", "briefcase": "",
    "code": "", "search": "", "layers": "", "comment": "",
    "mic": "", "check": "",
}

VARIANTS = {
    "Pricing Card": dict(
        card_top="#242424", card_bottom="#242424", border="#363636",
        primary="#ececec", secondary="#b4b4b4", feature="#f0f0f0", icon="#d9d9d9",
        btn="#fafafa", btn_border="#fafafa", btn_text="#0d0d0d",
        badge_bg="#4f6c91", badge_text="#d6e4f5", badge_on=0.0,
        name="Базовый", heading="Всё для старта",
        desc="Основные функции сервиса\nи расширенные лимиты\nдля ежедневной работы.",
        price="€8", period="/ месяц", period_offset=63, button="Выбрать Базовый", badge="РЕКОМЕНДУЕМ",
        features=[("sparkles", "Базовая модель"), ("comment", "Больше сообщений"),
                  ("image", "Больше изображений"), ("brain", "Долгая память"),
                  ("mic", "Голосовой режим")],
        footer="Тариф может включать рекламу.",
    ),
    "Pricing Card Accent": dict(
        card_top="#355174", card_bottom="#252729", border="#34404f",
        primary="#f2f5f8", secondary="#b9c8d7", feature="#f4f8fc", icon="#c6cfda",
        btn="#6bb1f8", btn_border="#6bb1f8", btn_text="#ffffff",
        badge_bg="#4f6c91", badge_text="#d6e4f5", badge_on=1.0,
        name="Про", heading="Для профессионалов",
        desc="Расширенные возможности,\nкоторые подстраиваются\nпод ваши задачи.",
        price="€23", period="/ месяц", period_offset=86, button="Выбрать Про", badge="РЕКОМЕНДУЕМ",
        features=[("sparkles", "Продвинутые модели"), ("image", "Генерация изображений"),
                  ("brain", "Расширенная память"), ("briefcase", "Агент для сложных задач"),
                  ("code", "Агент для программирования"), ("search", "Глубокое исследование"),
                  ("layers", "Проекты и шаблоны")],
        footer="",
    ),
}

MAX_FEATURES = 8
LIST_TOP_REL = 337      # first row center, reference px
LIST_STEP_REL = 32.5
SCALE = "XfCard.TextScale"


def build(v, anim="expr"):
    tools, pubs = [], []

    def add(t):
        tools.append(t)
        return t

    cx, cy = FW / 2, FH / 2
    # --- card ---
    add(rect_mask("MaskCardBorder", cx, cy, CARD_W, CARD_H, 0.09))
    add(background("BgCardBorder", v["border"], mask="MaskCardBorder"))
    add(rect_mask("MaskCardFill", cx, cy, CARD_W - 3, CARD_H - 3, 0.09))
    add(background("BgCardFill", v["card_top"], bottom_hex=v["card_bottom"], mask="MaskCardFill"))
    stack = add(merge("MrgCard", "BgCardBorder", "BgCardFill")).name

    # --- button ---
    bx, by, bw, bh = cx, Y(283), 270 * S, 32 * S
    add(rect_mask("MaskBtnBorder", bx, by, bw, bh, 1.0))
    add(background("BgBtnBorder", v["btn_border"], mask="MaskBtnBorder"))
    stack = add(merge("MrgBtnBorder", stack, "BgBtnBorder")).name
    add(rect_mask("MaskBtnFill", bx, by, bw - 3, bh - 3, 1.0))
    add(background("BgBtnFill", v["btn"], mask="MaskBtnFill"))
    stack = add(merge("MrgBtnFill", stack, "BgBtnFill")).name
    add(text("TxtBtn", v["button"], bx, by, 16, v["btn_text"], style="Medium",
             h_anchor=0, v_anchor=0, scale_expr=SCALE))
    stack = add(merge("MrgBtnText", stack, "TxtBtn")).name

    # --- badge ---
    gx, gy = X(252), Y(31.5)
    add(rect_mask("MaskBadge", gx, gy, 84 * S, 21 * S, 1.0))
    add(background("BgBadge", v["badge_bg"], mask="MaskBadge"))
    add(text("TxtBadge", v["badge"], gx, gy, 12.5, v["badge_text"], style="Bold",
             h_anchor=0, v_anchor=0, scale_expr=SCALE))
    add(merge("MrgBadgeInner", "BgBadge", "TxtBadge"))
    stack = add(merge("MrgBadge", stack, "MrgBadgeInner", blend=v["badge_on"])).name

    # --- header texts (masters: TxtHeading = primary, TxtDesc = secondary) ---
    add(text("TxtPlan", v["name"], X(20), Y(24), 19, v["primary"], style="Bold", scale_expr=SCALE))
    add(text("TxtHeading", v["heading"], X(20), Y(69), 28, v["primary"], style="Bold", scale_expr=SCALE))
    add(text("TxtDesc", v["desc"], X(20), Y(106), 17, v["secondary"], line_spacing=1.35, scale_expr=SCALE))
    add(text("TxtPrice", v["price"], X(20), Y(205), 62, v["primary"], scale_expr=SCALE))
    per = add(text("TxtPeriod", v["period"], X(20 + v["period_offset"]), Y(224), 16.5, v["secondary"],
                   scale_expr=SCALE))
    per.set("Center", per.inputs["Center"].value,
            expr=f"Point(TxtPrice.Center.X + XfCard.PeriodOffset, {fl.fy(Y(224))})")
    add(text("TxtFooter", v["footer"], X(20), Y(694), 13, v["secondary"], scale_expr=SCALE))
    for t in tools:
        if t.name in ("TxtPlan", "TxtPrice"):
            t.follow_color("TxtHeading")
        if t.name in ("TxtPeriod", "TxtFooter"):
            t.follow_color("TxtDesc")
    for nm in ("TxtPlan", "TxtHeading", "TxtDesc", "TxtPrice", "TxtPeriod", "TxtFooter"):
        stack = add(merge("Mrg" + nm[3:], stack, nm)).name

    # --- feature list (rows follow XfCard.ListStep; colors follow row 1) ---
    list_top = fl.fy(Y(LIST_TOP_REL))
    feats = v["features"] + [("", "")] * (MAX_FEATURES - len(v["features"]))
    for i, (icon, label) in enumerate(feats, 1):
        k = i - 1
        ic = add(text(f"TxtIcon{i}", ICONS.get(icon, ""), X(27), Y(LIST_TOP_REL + k * LIST_STEP_REL), 18,
                      v["icon"], font="Font Awesome 6 Free", style="Solid", h_anchor=0, v_anchor=0,
                      scale_expr=SCALE))
        ic.set("Center", ic.inputs["Center"].value,
               expr=f"Point({fl.fx(X(27))}, {list_top} - {k}*XfCard.ListStep)")
        ft = add(text(f"TxtFeature{i}", label, X(47), Y(LIST_TOP_REL + k * LIST_STEP_REL), 17, v["feature"],
                      v_anchor=0, scale_expr=SCALE))
        ft.set("Center", ft.inputs["Center"].value,
               expr=f"Point({fl.fx(X(47))}, {list_top} - {k}*XfCard.ListStep)")
        if i > 1:
            ic.follow_color("TxtIcon1")
            ft.follow_color("TxtFeature1")
        stack = add(merge(f"MrgIcon{i}", stack, f"TxtIcon{i}")).name
        stack = add(merge(f"MrgFeature{i}", stack, f"TxtFeature{i}")).name

    # --- master transform with shared controls ---
    card = add(transform("XfCard", stack))
    step = round(LIST_STEP_REL * S / FH, 5)
    poff = round(v["period_offset"] * S / FW, 5)
    card.set("TextScale", 1.0).set("ListStep", step).set("PeriodOffset", poff)
    card.user_control("TextScale", LINKS_Name="Text Scale", LINKID_DataType="Number",
                      INPID_InputControl="SliderControl", INP_Default=1.0, INP_MinScale=0.3,
                      INP_MaxScale=3.0, ICS_ControlPage="Controls")
    card.user_control("ListStep", LINKS_Name="List Step", LINKID_DataType="Number",
                      INPID_InputControl="SliderControl", INP_Default=step,
                      INP_MinScale=0.0, INP_MaxScale=0.1, ICS_ControlPage="Controls")
    card.user_control("PeriodOffset", LINKS_Name="Period Offset", LINKID_DataType="Number",
                      INPID_InputControl="SliderControl", INP_Default=poff,
                      INP_MinScale=0.0, INP_MaxScale=0.2, ICS_ControlPage="Controls")
    if anim == "expr":
        fl.add_anim_controls(card, frames=12, slide=0.04)

    anim_tools, out = fl.animation("XfCard", "XfCard", mode=anim, frames=12, slide=0.04)
    tools += anim_tools
    fl.layout(tools)

    # --- published controls (order = Inspector order) ---
    g = iter(range(1, 100))
    pubs += [Publish("TxtPlan", "StyledText", "Тариф"),
             Publish("TxtHeading", "StyledText", "Заголовок"),
             Publish("TxtDesc", "StyledText", "Описание"),
             Publish("TxtPrice", "StyledText", "Цена"),
             Publish("TxtPeriod", "StyledText", "Период"),
             Publish("XfCard", "PeriodOffset", "Отступ периода от цены"),
             Publish("TxtBtn", "StyledText", "Кнопка"),
             Publish("TxtFooter", "StyledText", "Сноска внизу"),
             Publish("TxtBadge", "StyledText", "Бейдж"),
             Publish("MrgBadge", "Blend", "Бейдж: видимость (0/1)")]
    for i in range(1, MAX_FEATURES + 1):
        pubs += [Publish(f"TxtIcon{i}", "StyledText", f"Пункт {i}: иконка"),
                 Publish(f"TxtFeature{i}", "StyledText", f"Пункт {i}: текст")]
    pubs += publish_color("BgCardFill", "TopLeft", "Фон карточки сверху", next(g))
    pubs += publish_color("BgCardFill", "BottomLeft", "Фон карточки снизу", next(g))
    pubs += publish_color("BgCardBorder", "TopLeft", "Обводка карточки", next(g))
    pubs += publish_color("TxtHeading", "", "Цвет основного текста", next(g), suffix="1")
    pubs += publish_color("TxtDesc", "", "Цвет вторичного текста", next(g), suffix="1")
    pubs += publish_color("TxtFeature1", "", "Цвет текста пунктов", next(g), suffix="1")
    pubs += publish_color("TxtIcon1", "", "Цвет иконок", next(g), suffix="1")
    pubs += publish_color("BgBtnFill", "TopLeft", "Кнопка: фон", next(g))
    pubs += publish_color("BgBtnBorder", "TopLeft", "Кнопка: обводка", next(g))
    pubs += publish_color("TxtBtn", "", "Кнопка: текст", next(g), suffix="1")
    pubs += publish_color("BgBadge", "TopLeft", "Бейдж: фон", next(g))
    pubs += publish_color("TxtBadge", "", "Бейдж: текст", next(g), suffix="1")
    pubs += [Publish("XfCard", "Center", "Позиция"),
             Publish("XfCard", "Size", "Масштаб"),
             Publish("XfCard", "TextScale", "Масштаб текста"),
             Publish("XfCard", "ListStep", "Шаг списка")]
    if anim == "expr":
        pubs += [Publish("XfCard", "AnimOn", "Анимация вкл."),
                 Publish("XfCard", "AnimFrames", "Анимация: кадров"),
                 Publish("XfCard", "SlideDist", "Анимация: высота выезда")]
    return tools, pubs, out

# Что проверено в Resolve

Окружение проверок: DaVinci Resolve 21, macOS.

После каждой сверки с пользователем обновляй этот файл: переноси пункты из
«Требует проверки» в «Работает» или «Не работает» и записывай калибровочные
значения. Диагностический пакет: `scripts/make_test_pack.py`.

## Работает (проверено)

- Макрос `MacroOperator` + `InstanceInput` / `InstanceOutput`, загрузка из
  `Templates/Edit/Titles/<папка>/`.
- `TextPlus`: кириллица, цвет `Red1/Green1/Blue1/Alpha1`, `Center`, `Size`,
  якоря `HorizontalLeftCenterRight` / `VerticalTopCenterBottom`.
- `Background` со сплошным цветом и с `Type = FuID{"Vertical"}` (градиент
  `TopLeft*` → `BottomLeft*`).
- `RectangleMask` через `EffectMask` у Background, `CornerRadius`.
- `Merge` поверх прозрачного `Background` (`TopLeftAlpha = 0`): альфа
  сохраняется.
- Полная статичная карточка из 60+ нод, `Transform` с `UserControls`,
  публикация `Center` / `Size` и пользовательских слайдеров.
- **`RectangleMask`: Width — доля ширины кадра, Height — доля ВЫСОТЫ кадра**
  (`MASK_UNIT = "height"`). Маркер 35×35, собранный с Height = px/1920,
  отрисовался как 35×19.7 px (Typewriter Box, 21.2, 2026-11-11).
- **Масштаб `Text+ Size`** для Inter: `Size = px / 1920 × 1.51`
  (`TEXT_SIZE_K`). Без коэффициента ширина текста 386 px вместо 587,
  x-height 26 вместо 39 (Typewriter Box). Другие шрифты проверь тестом 11.
- **`EllipseMask`: Width и Height — обе доли ШИРИНЫ кадра** (в отличие от
  `RectangleMask`). Круг Ø210 с Height = px/1080 вышел в 1.78 раза выше
  (Icon Features, 2026-11-11). `fl.ellipse_mask()` это учитывает. Контур
  (`Solid = 0`, `BorderWidth` = px/1920) рисует тонкое кольцо, толщина
  на глаз верная.
- **`Transform.Center` — смещение, (0.5, 0.5) = на месте.** Если записать
  туда позицию элемента, он сдвинется ещё раз на столько же (колонки
  разъехались вдвое). Масштаб вокруг точки: `Pivot` = точка, `Center` = 0.5
  (`fl.transform(..., pivot=...)`).
- **`Text+ Size` считается от высоты строки шрифта** (hhea ascent + descent),
  а не от em: `Size = em_px / 1920 × (asc+desc)/upm / 0.8023`
  (`fl.text_size_k()`, метрики читаются из файла шрифта). Inter: 1.21 em,
  k = 1.51 (измерено). Phosphor-Thin: 1.0 em, k = 1.25. С коэффициентом
  Inter иконка вышла в 1.16–1.21 раза крупнее, что совпадает с расчётом.
- **Иконочные шрифты** Phosphor-Thin (Text+ c PUA-символом) рендерятся.
- **Выражения**: `time`, `iif`, `min`/`max`, ссылки на UserControls
  (`XfCard.BoxW`), `Point()` в Center, многострочное Lua-выражение с `:`,
  `string.gmatch`, `Text()` в `StyledText`, ссылка `Node.StyledText.Value`.
  Печать текста и мигание курсора работают (Typewriter Box).
- Resolve 21.2 из **App Store** (`DaVinciResolveLite`) читает шаблоны только
  из контейнера `~/Library/Containers/com.blackmagic-design.DaVinciResolveLite/Data/Library/Application Support/Fusion/Templates/`,
  `.drfx` лежит там целиком. Распаковка в `~/Library/Application Support/Blackmagic Design/…`
  для этой сборки не работает: шаблоны не появляются (проверено 2026-11-11).

## Требует проверки

| # | Что | Тест | Ожидаемый результат |
|---|---|---|---|
| 1 | ~~Высота `RectangleMask`~~ — проверено, см. выше. Test 05: должна быть ровно 4:1 полоса **B** (голубая) | Test 05 | контроль |
| 2 | `TEXT_SIZE_K` для шрифтов, кроме Inter | Test 11 | «H» при Size=100px примерно равна высоте планки × cap-height шрифта |
| 3 | `HorizontalJustificationNew = 0` выравнивает многострочный текст влево | Test 06 | 3 строки по левому краю |
| 4 | `comp.RenderEnd` (исчезновение в конце клипа); остальные выражения проверены | Test 07 | Выезд и фейд в начале и в конце клипа |
| 5 | Ключевые кадры: `BezierSpline`, `XYPath` | Test 08 | Выезд и фейд только в начале |
| 6 | Shapes: `sRectangle`, `sEllipse`, `sMerge`, `sRender` (имена входов, единицы) | Test 09 | Прямоугольник 400×200 и круг |
| 7 | `RectangleMask.SoftEdge` (тень), `SoftGlow` | Test 10 | Мягкая тень, свечение |
| 8 | `publish_font`: Font + Style в одной ControlGroup | Test 12 | Шрифт и стиль рядом |
| 9 | Ссылка на `Node.Center.X` в выражении (`TxtPeriod`) | Pricing Card | Период стоит справа от цены и двигается вместе с ней |
| 10 | Превью `.png` рядом с `.setting` показывается в Effects Library | любой шаблон | Миниатюра вместо стандартной иконки |
| 11 | Шаблоны типа Effect (`main_input`) и Generator | — | — |
| 13 | `Loader` в титре (`fl.loader`, still: Loop=1, GlobalStart −1000…100000), файл в `Fusion/Assets/<группа>/` контейнера App Store | Subscribe Bar | фото видно в круге на всех кадрах |
| 14 | `Merge` с `EffectMask` (обрезка фото кругом) и `Merge.Size` = px/ширина картинки (фото без масштабирования) | Subscribe Bar | фото Ø167, не больше и не меньше |
| 15 | `math.cos` / `math.sin` / `math.pi` и `abs` в выражениях | Subscribe Bar | спираль фото, нажатие кнопки |
| 16 | `EffectMask` на Text+ и `RectangleMask.SoftEdge` (письмо заголовка); 9 Loader в одном титре | Scrapbook Note | заголовок проявляется слева направо с мягким краем |
| 12 | Пути установки Windows / Linux; unzip-установка для сборки с сайта | — | — |

Если выражения (п. 4) не работают, переключай шаблоны на `ANIM = "keys"`
(только появление). Если не работают и ключевые кадры, ставь `"static"`.

## Не работает / ограничения

- Перетаскивание `.drfx` в окно Resolve кладёт пакет туда, откуда его
  читает установленная сборка. Это запасной способ, если скрипт не может
  писать в нужную папку.
- `osascript -e 'quit app "DaVinci Resolve"'` при несохранённом проекте
  возвращает ошибку `-128`. Пользователь должен сам сохранить проект (Cmd+S)
  и закрыть Resolve (Cmd+Q).
- Text+ не переносит строки сам.
- Картинка в Title: только «вшитая» через Loader с абсолютным путём (п. 13);
  поле выбора файла в Inspector не сделать, смена фото = пересборка.
- Переходы (Transitions) не поддерживаются.

## Калибровка

| Параметр | Значение | Дата, версия |
|---|---|---|
| `TEXT_SIZE_K` (Inter) | 1.51 | 2026-11-11, Resolve 21.2 App Store |
| `TEXT_LINE_K` (Size → высота строки) | 0.8023 | 2026-11-11, по Inter, подтверждено Phosphor |
| `MASK_UNIT` | height | 2026-11-11, Resolve 21.2 App Store |
| Text+ сетка «+» (Inter ExtraLight): шаг по X при Size=66px, CharacterSpacing=1.08, без K | 34.1 px | 2026-11-11 |
| то же, шаг по Y при LineSpacing=0.575, без K | 31.3 px | 2026-11-11 |

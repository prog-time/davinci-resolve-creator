# Формат .setting и .drfx

## .setting

Fusion-макрос — это Lua-таблица:

```lua
{
  Tools = ordered() {
    MyTitle = MacroOperator {
      CtrlWZoom = false,
      NameSet = true,
      Inputs = ordered() {          -- опубликованные параметры (Inspector)
        Input1 = InstanceInput { SourceOp = "TxtTitle", Source = "StyledText", Name = "Заголовок", },
        Input2 = InstanceInput { SourceOp = "TxtTitle", Source = "Red1", Name = "Цвет", ControlGroup = 1, },
        Input3 = InstanceInput { SourceOp = "TxtTitle", Source = "Green1", ControlGroup = 1, },
        -- Blue1, Alpha1 той же группы → одно цветовое поле
      },
      Outputs = {
        MainOutput1 = InstanceOutput { SourceOp = "MrgOut", Source = "Output", },
      },
      ViewInfo = GroupInfo { Pos = { 0, 0 } },
      Tools = ordered() {           -- ноды графа
        TxtTitle = TextPlus {
          Inputs = {
            StyledText = Input { Value = "Текст", },
            Center = Input { Value = { 0.5, 0.5 }, },
            Red1 = Input { Value = 1, Expression = "TxtMaster.Red1", },
            EffectMask = Input { SourceOp = "MaskX", Source = "Mask", },
          },
          ViewInfo = OperatorInfo { Pos = { 0, 0 } },
          UserControls = ordered() { TextScale = { LINKS_Name = "Text Scale", ... }, },
        },
      },
    },
  },
  ActiveTool = "MyTitle"
}
```

- Input может хранить значение (`Value`), выражение (`Expression`) или связь
  (`SourceOp` + `Source`).
- Ключи с точкой пишутся в скобках: `["Gamut.SLogVersion"] = ...`.
- Перечисления задаются как `FuID { "Vertical" }`.
- Эффекты (Effects) получают вход клипа через
  `MainInput1 = InstanceInput { SourceOp = "XfIn", Source = "Input" }`
  (`main_input` в `fl.macro`). Не проверено.

## Координаты

- `Center` — доли кадра, (0,0) внизу слева, Y вверх. Хелперы `fx(px)`,
  `fy(py)` переводят px (Y сверху) в эти доли.
- `RectangleMask.Width` — доля ширины кадра, `Height` — доля **высоты**
  кадра (проверено). `CornerRadius` 0..1.
- `TextPlus.Size` = `px / FRAME_W × TEXT_SIZE_K` (1.51 для Inter, проверено);
  для других шрифтов проверь тестом 11.
- Shapes (`sRectangle`, `sEllipse`): начало координат в центре кадра,
  единицы — ширина кадра, Y вверх. Не проверено.

## Выражения

Выражения пишутся в синтаксисе Fusion (простой Lua): `time`, `comp.RenderEnd`,
`iif(cond, a, b)`, `min`, `max`, `Point(x, y)`, ссылки `Node.Input`,
`Node.Center.X`. Всё это не проверено (тест 7).

## Ключевые кадры

```lua
MrgOutBlend = BezierSpline {
  SplineColor = { Red = 205, Green = 205, Blue = 16 },
  NameSet = true,
  KeyFrames = {
    [0] = { 0, RH = { 4, 0 } },
    [12] = { 1, LH = { 8, 1 } },
  }
},
-- в ноде: Blend = Input { SourceOp = "MrgOutBlend", Source = "Value", },
-- Point-вход: XYPath { Inputs = { X = Input{SourceOp=...}, Y = ... } }
```

Не проверено (тест 8).

## .drfx

`.drfx` — это zip, пути внутри повторяют структуру папки Templates:

```
Edit/Titles/<Группа>/<Имя>.setting
Edit/Titles/<Группа>/<Имя>.png      ← превью (опционально)
Edit/Generators/<Группа>/...
Edit/Effects/<Группа>/...
```

Группа — это папка. Под её именем шаблоны видны в Effects Library.

## Пути установки

| ОС | Папка Templates | Статус |
|---|---|---|
| macOS, App Store (в `.app` есть `Contents/_MASReceipt`) | `~/Library/Containers/<bundle id>/Data/Library/Application Support/Fusion/Templates` — `.drfx` кладётся целиком | проверено (21.2, `DaVinciResolveLite`) |
| macOS, сайт Blackmagic | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates` — unzip | не проверено |
| Windows | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates` | не проверено |
| Linux | `~/.local/share/DaVinciResolve/Fusion/Templates` | не проверено |

Какая сборка установлена, покажет `scripts/install_macos.sh --detect`.
Признак App Store-сборки — файл `Contents/_MASReceipt` внутри `.app`. Её
bundle id задаёт имя контейнера. После установки Resolve нужно перезапустить.

Где искать: Edit → Effects → Toolbox → Titles → Fusion Titles → группа.
Generators и Effects лежат в одноимённых разделах. Можно найти по поиску
по имени.

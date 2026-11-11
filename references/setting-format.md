# .setting and .drfx format

## .setting

A Fusion macro is a Lua table:

```lua
{
  Tools = ordered() {
    MyTitle = MacroOperator {
      CtrlWZoom = false,
      NameSet = true,
      Inputs = ordered() {          -- published controls (Inspector)
        Input1 = InstanceInput { SourceOp = "TxtTitle", Source = "StyledText", Name = "Title", },
        Input2 = InstanceInput { SourceOp = "TxtTitle", Source = "Red1", Name = "Color", ControlGroup = 1, },
        Input3 = InstanceInput { SourceOp = "TxtTitle", Source = "Green1", ControlGroup = 1, },
        -- Blue1, Alpha1 in the same group -> one color field
      },
      Outputs = {
        MainOutput1 = InstanceOutput { SourceOp = "MrgOut", Source = "Output", },
      },
      ViewInfo = GroupInfo { Pos = { 0, 0 } },
      Tools = ordered() {           -- graph nodes
        TxtTitle = TextPlus {
          Inputs = {
            StyledText = Input { Value = "Text", },
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

- An Input holds a value (`Value`), an expression (`Expression`) or a link
  (`SourceOp` + `Source`).
- Keys with a dot are bracketed: `["Gamut.SLogVersion"] = ...`.
- Enums are `FuID { "Vertical" }`.
- Effects get the clip input via
  `MainInput1 = InstanceInput { SourceOp = "XfIn", Source = "Input" }`
  (`main_input` in `fl.macro`). Not verified.
- A Loader keeps its file in a `Clips = { Clip { Filename = ..., ... } }`
  block (`fl.loader`). Not verified in titles.

## Coordinates

- `Center` is a fraction of the frame, (0,0) bottom left, Y up. Helpers
  `fx(px)`, `fy(py)` convert px (Y from the top).
- `RectangleMask.Width` is a fraction of frame width, `Height` of frame
  **height** (verified). `EllipseMask`: both of frame **width** (verified).
  `CornerRadius` 0..1.
- `TextPlus.Size` = `em_px / FRAME_W × (asc+desc)/upm / 0.8023` (verified for
  Inter and Phosphor; `fl.text_size_k()`).
- `Transform.Center` is an offset (0.5 = no move); scale/rotate around a
  point with `Pivot` (verified).
- Shapes (`sRectangle`, `sEllipse`): origin at the frame center, units of
  frame width, Y up. Not verified.

## Expressions

Fusion expressions are Lua: `time`, `iif(cond, a, b)`, `min`, `max`,
`Point(x, y)`, references `Node.Input`, `Node.Center.X`. A multi-line
expression starts with `:` and ends with `return ...`; `Text(s)` returns a
value for `StyledText`. Verified except `comp.RenderEnd` and `math.*`
(tests 7, 15).

## Keyframes

```lua
MrgOutBlend = BezierSpline {
  SplineColor = { Red = 205, Green = 205, Blue = 16 },
  NameSet = true,
  KeyFrames = {
    [0] = { 0, RH = { 4, 0 } },
    [12] = { 1, LH = { 8, 1 } },
  }
},
-- in the node: Blend = Input { SourceOp = "MrgOutBlend", Source = "Value", },
-- Point input: XYPath { Inputs = { X = Input{SourceOp=...}, Y = ... } }
```

Not verified (test 8).

## .drfx

A `.drfx` is a zip whose paths mirror the Templates folder:

```
Edit/Titles/<Group>/<Name>.setting
Edit/Titles/<Group>/<Name>.png      <- preview (optional)
Edit/Generators/<Group>/...
Edit/Effects/<Group>/...
```

The group is a folder; templates appear under its name in the Effects
Library.

## Install paths

| OS | Templates folder | Status |
|---|---|---|
| macOS, App Store (`.app` contains `Contents/_MASReceipt`) | `~/Library/Containers/<bundle id>/Data/Library/Application Support/Fusion/Templates` — the `.drfx` is kept whole | verified (21.2, `DaVinciResolveLite`) |
| macOS, Blackmagic website | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates` — unzip | not verified |
| Windows | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates` | not verified |
| Linux | `~/.local/share/DaVinciResolve/Fusion/Templates` | not verified |

`scripts/install_macos.sh --detect` shows the installed builds. An App Store
build has `Contents/_MASReceipt` inside the `.app`; its bundle id names the
container. Resolve must be restarted after installing.

Where to find templates: Edit → Effects → Toolbox → Titles → Fusion Titles →
group. Generators and Effects are in their own sections. Search by name also
works.

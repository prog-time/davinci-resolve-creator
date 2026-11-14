# What is verified in Resolve

Test environment: DaVinci Resolve 21.2, macOS (App Store build).

After every check with the user, update this file: move items from "Needs
verification" to "Works" or "Does not work" and record calibration values.
Diagnostic pack: `scripts/make_test_pack.py`.

## Works (verified)

- Macro `MacroOperator` + `InstanceInput` / `InstanceOutput`, loaded from
  `Templates/Edit/Titles/<folder>/`.
- `TextPlus`: Cyrillic, color `Red1/Green1/Blue1/Alpha1`, `Center`, `Size`,
  anchors `HorizontalLeftCenterRight` / `VerticalTopCenterBottom`.
- `Background` with a solid color and with `Type = FuID{"Vertical"}`
  (gradient `TopLeft*` → `BottomLeft*`).
- `RectangleMask` as `EffectMask` of a Background, `CornerRadius`.
- `Merge` over a transparent `Background` (`TopLeftAlpha = 0`): alpha is
  preserved.
- A full static card of 60+ nodes, `Transform` with `UserControls`,
  publishing `Center` / `Size` and custom sliders.
- **`RectangleMask`: Width is a fraction of frame width, Height of frame
  HEIGHT** (`MASK_UNIT = "height"`). A 35×35 handle built with
  Height = px/1920 rendered as 35×19.7 px (Typewriter Box, 2026-11-11).
- **`Text+ Size`** for Inter: `Size = px / 1920 × 1.51` (`TEXT_SIZE_K`).
  Without the factor the text was 386 px wide instead of 587, x-height 26
  instead of 39 (Typewriter Box).
- **`EllipseMask`: Width and Height are both fractions of frame WIDTH**
  (unlike `RectangleMask`). A Ø210 circle with Height = px/1080 came out
  1.78× taller (Icon Features, 2026-11-11). `fl.ellipse_mask()` handles it.
  Outline mode (`Solid = 0`, `BorderWidth` = px/1920) draws a thin ring;
  thickness looks right.
- **`Transform.Center` is an offset, (0.5, 0.5) = no move.** Putting the
  element's own position there moves it twice as far (columns spread 2×).
  Scale around a point: `Pivot` = the point, `Center` = 0.5
  (`fl.transform(..., pivot=...)`).
- **`Text+ Size` is relative to the font's line height** (hhea ascent +
  descent), not to the em: `Size = em_px / 1920 × (asc+desc)/upm / 0.8023`
  (`fl.text_size_k()`, metrics read from the font file). Inter: 1.21 em,
  k = 1.51 (measured). Phosphor-Thin: 1.0 em, k = 1.25. With Inter's k the
  icon came out 1.16–1.21× too big, matching the prediction.
- **Icon fonts**: Phosphor-Thin (Text+ with a PUA glyph) renders.
- **Expressions**: `time`, `iif`, `min`/`max`, references to UserControls
  (`XfCard.BoxW`), `Point()` in Center, multi-line Lua expressions starting
  with `:`, `string.gmatch`, `Text()` in `StyledText`, `Node.StyledText.Value`.
  Typing text and a blinking cursor work (Typewriter Box).
- Resolve 21.2 from the **App Store** (`DaVinciResolveLite`) reads templates
  only from its container
  `~/Library/Containers/com.blackmagic-design.DaVinciResolveLite/Data/Library/Application Support/Fusion/Templates/`,
  with the `.drfx` kept whole. Unzipping into
  `~/Library/Application Support/Blackmagic Design/…` does nothing for this
  build: templates never appear (verified 2026-11-11).

## Needs verification

| # | What | Test | Expected |
|---|---|---|---|
| 1 | ~~`RectangleMask` height~~ — verified above. Test 05: stripe **B** (cyan) must be exactly 4:1 | Test 05 | control |
| 2 | Text size factor for fonts other than Inter/Phosphor | Test 11 | "H" at Size=100px ≈ ruler height × the font's cap height |
| 3 | `HorizontalJustificationNew = 0` left-aligns multi-line text | Test 06 | 3 lines aligned left |
| 4 | `comp.RenderEnd` (exit at the clip end); other expressions are verified | Test 07, Test 18 | slide and fade at the start and at the end of the clip |
| 5 | Keyframes: `BezierSpline`, `XYPath` | Test 08 | slide and fade at the start only |
| 6 | Shapes: `sRectangle`, `sEllipse`, `sMerge`, `sRender` (input names, units) | Test 09 | 400×200 rectangle and a circle |
| 7 | `RectangleMask.SoftEdge` (shadow), `SoftGlow` | Test 10 | soft shadow, glow |
| 8 | `publish_font`: Font + Style in one ControlGroup | Test 12 | font and style side by side |
| 9 | Reference to `Node.Center.X` in an expression (`TxtPeriod`) | Pricing Card | the period sits right of the price and moves with it |
| 10 | Preview `.png` next to `.setting` shown in the Effects Library | any template | thumbnail instead of the default icon |
| 11 | Effect (`main_input`) and Generator templates | — | — |
| 12 | Windows / Linux install paths; unzip install for the website build | — | — |
| 13 | `Loader` in a title (`fl.loader`, still: Loop=1, GlobalStart −1000…100000), file in `Fusion/Assets/<group>/` of the App Store container | Test 14, Subscribe Bar | the photo is visible in the circle on every frame |
| 14 | `Merge` with `EffectMask` (round crop) and `Merge.Size` = px / image width (no rescaling of the foreground) | Test 14, Subscribe Bar | photo exactly Ø167 |
| 15 | `math.cos` / `math.sin` / `math.pi` and `abs` in expressions | Test 17, Subscribe Bar | photo spiral, button press |
| 16 | `EffectMask` on Text+ and `RectangleMask.SoftEdge` (title writing); 9 Loaders in one title | Test 16, Scrapbook Note | the title is revealed left to right with a soft edge |
| 17 | Text+ `CharacterSpacing` and `LineSpacing` units (assumed: spacing adds (cs−1)×Size×1920 px per character) | Test 19, Test 20, Profile Card | letter spacing matches the reference |
| 18 | Path map in a Loader path (`Fusion:Assets/<group>/<file>`) instead of an absolute path | Test 15 | the image shows like in test 14 → templates with images become portable |

If expressions (item 4) fail, switch templates to `ANIM = "keys"` (entrance
only). If keyframes fail too, use `"static"`.

## Does not work / limits

- Dragging a `.drfx` into the Resolve window puts the pack where the
  installed build reads it. Use it as a fallback when the script cannot
  write to the folder.
- `osascript -e 'quit app "DaVinci Resolve"'` with an unsaved project
  returns error `-128`. The user must save (Cmd+S) and quit (Cmd+Q) by hand.
- Text+ does not wrap lines.
- Pictures in a title: only baked in via Loader with an absolute path
  (item 13); no file picker in the Inspector; changing the photo = rebuild.
- Transitions are not supported.

## Calibration

| Parameter | Value | Date, version |
|---|---|---|
| `TEXT_SIZE_K` (Inter) | 1.51 | 2026-11-11, Resolve 21.2 App Store |
| `TEXT_LINE_K` (Size → line height) | 0.8023 | 2026-11-11, from Inter, confirmed by Phosphor |
| `MASK_UNIT` | height | 2026-11-11, Resolve 21.2 App Store |
| Text+ "+" grid (Inter ExtraLight): X step at Size=66px, CharacterSpacing=1.08, without K | 34.1 px | 2026-11-11 |
| same, Y step at LineSpacing=0.575, without K | 31.3 px | 2026-11-11 |

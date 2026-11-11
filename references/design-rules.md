# Template design rules

## Graph structure

- Every element is drawn full-frame and stacked with `Merge`:
  `stack = merge("MrgX", stack, "TxtX")`. Node order is layer order.
- A badge is two nodes: `RectangleMask` and `Background` with `EffectMask`.
  An outline is two badges: the outer one in the outline color, the inner
  one `2 × thickness` smaller.
- The graph ends with a master Transform (`XfCard` / `XfBlock`) and the
  output merge `MrgOut` over a transparent background. The macro output is
  `MrgOut`.
- Use `fl.layout(tools)` to lay the nodes out in the flow view.

## Fusion units (verified, see verified.md)

- `RectangleMask`: Width is a fraction of frame width, Height of frame
  **height**. `EllipseMask`: both are fractions of frame **width**. Use
  `fl.rect_mask` / `fl.ellipse_mask`; never set them by hand.
- `Transform.Center` is an offset (0.5 = no move). To scale or rotate around
  an element, keep Center at 0.5 and pass `pivot=`.
- `Text+ Size` depends on the font's line height. `fl.text()` converts from
  the font file itself. If the font file is not found, Inter's factor is
  used — warn about it.

## Variants instead of a switch

For "regular / highlighted" styles generate 2 files with different defaults
(`VARIANTS`). A switch built on expressions would lock the color fields: a
field driven by an expression cannot be edited in the Inspector.
Optional elements (e.g. a badge) use `Merge.Blend` 0/1, published as
"Badge: visibility (0/1)".

## Master nodes

- **Colors.** A color is published on one node (e.g. `TxtHeading`). Other
  nodes of the same color follow it with `t.follow_color("TxtHeading")`
  (expressions `TxtHeading.Red1` etc.). Only the master is published.
- **Shared parameters** (text scale, list step, animation) are UserControls
  on the master Transform and are published with `Publish`. Other nodes
  reference them: `XfCard.TextScale`, `XfCard.ListStep`.

## Text

- Text+ does not wrap lines. Line breaks are `\n` in the text. List items
  need a length limit (about 38 characters at 17 px on 345 px width).
  **Tell the user the limit.**
- Pass sizes in frame px (em); `fl.text()` applies the calibrated factor.
- Anchors: `h_anchor` -1/0/1 (left/center/right), `v_anchor` -1/0/1
  (top/center/bottom). For lists: `v_anchor=0`, position at the line center.
- Typing text: a source node `TxtXSrc` holds the published text (not
  rendered); the display node `TxtX` types it with a multi-line Lua
  expression that walks UTF-8 characters and returns `Text(...)` (see
  `examples/typewriter-box`).

## Icons

Pick the font by the image style: **line** icons — Phosphor (Thin/Light,
MIT, `@phosphor-icons/web` on jsDelivr, family `Phosphor-Thin`); **filled**
icons — Font Awesome 6 Free Solid. Before choosing, render the candidates
next to the reference and compare the stroke weight. Tabler Icons (2/24 em
stroke) is too heavy for thin icons. Write the code point in the spec as
`"\uXXXX"`, not the character itself.

The icon is a separate Text+ with the icon font, the text being the glyph
(e.g. `"\uf00c"` for Font Awesome). The user swaps it by copying the glyph on
the icon site (fontawesome.com → Copy Glyph) into the "Item N: icon" field.
Warn that only free icons of the installed style work.

## Logo and photos

A picture can be baked into the template: set
`ASSETS = {"name.png": "<source>"}` in the spec and use
`fl.loader("LdPhoto", fl.asset_path(GROUP, "name.png"))` in the graph.
`generate.py --install` copies the file into `Fusion/Assets/<group>/` of
the Resolve build it finds (the App Store build reads only its container).
The path is written into the `.setting`, so changing the photo means a
rebuild. Crop the photo beforehand (e.g. 512×512 around the face); round it
with an `EffectMask` on the Merge. Not verified (verified.md, items 13–14).

**Decor that cannot be built from nodes** (torn paper, textures, tape,
clips, sticky notes, pins, marker strokes): draw it as PNGs with a
`make_assets.py` script next to the spec (Pillow; rotation and shadow are
baked in; size in frame pixels). Put the shared layout into `geometry.py`,
read by both `make_assets.py` and `spec.py`. Place each part with
`place_image()` (Loader → Merge(Size=1, Center=position)) and animate it
with `Timeline.slide()` (`pivot` = position). Keep texts as live Text+. Example:
`examples/scrapbook-note/` (not verified in Resolve).

**Handwriting.** Text+ cannot draw a pen stroke. Imitation: a
`RectangleMask` with a soft edge as the Text+ `EffectMask`
(`Timeline.wipe_mask()`). The mask width grows left to right up to `C.TitleW` (Text+ does not know its
width, so add a "writing width" slider); a pen icon rides the edge (FA
`\uf304`, bottom-left anchor = the tip). Draw an underline as a marker
image revealed by the same kind of mask. Not verified.

Other options:

1. Put the logo PNG on a track above the title (most reliable).
2. Use an icon font glyph if the logo exists there (e.g. FA brands).
3. Make an Effect template applied to the logo clip (`main_input`); not
   verified.

## Node names

- Names are unique, ASCII, readable, with a type prefix: `Txt*` (Text+),
  `Bg*` (Background), `Mask*` (masks), `Mrg*` (Merge), `Xf*` (Transform),
  `Ld*` (Loader), `Shp*` (shapes), `Fx*` (effects).
- Reserved words (`Name`, `Input`, `Output`, `Text`, `Point`, `time`,
  `comp`, …) and node type names are forbidden. `fl.macro()` checks names,
  references and publishes and fails with a clear error.

## Inspector

- Labels are in the user's language, with prefixes for grouping:
  "Item 3: text", "Button: background" (in Russian: «Пункт 3: текст»,
  «Кнопка: фон»).
- The order of `pubs` is the order of fields in the Inspector: texts first,
  then fonts and sizes, colors, layout sliders, animation, position and
  scale.
- A color is published with `publish_color(..., group=N)`: 4 channels in one
  ControlGroup make one color field. Each color gets its own group number.

## Animation

Build animation from `scripts/fusion_anim.py` instead of hand-written
expressions: `Timeline(ctrl, speed)` gives `prog()`, `eased()`, `on()`,
`slide()` (fly in from a side with rotation/scale), `grow()` (scale from 0
around a pivot), `slide_y()`, `typing()`, `wipe_mask()` (handwriting reveal),
`hold_fade()` / `clip_end_fade()`, `controls()` and `output()` (master
Transform + MrgOut + exit fade), `publish()`; plus `place_image()` for
Loader-based images. `scripts/setting_diff.py A B` proves a refactor did not
change a template.

- `ANIM = "expr"`: entrance and exit on expressions, controls in the
  Inspector. Expressions are verified (time, iif, min/max, Point, multi-line
  Lua); `comp.RenderEnd` is not.
- `ANIM = "keys"`: entrance only, on keyframes. **Not verified** (test 8).
  A fallback if expressions fail.
- `ANIM = "static"`: no animation, for bisection.
- Standard master controls: `AnimOn`, `AnimStart`, `Speed` (all timings are
  `(time - AnimStart) * Speed`), `OutOn`, `Hold`, `OutFrames`.
- **Exit by default is a fade after a hold, not at the clip end.**
  `Hold` ("Hold before fade, frames", default 90) and `OutFrames` on the
  master Transform; expression on `MrgOut.Blend`:
  `iif(C.OutOn > 0.5, min(1, max(0, 1 - (time - (C.AnimStart + INTRO_END/C.Speed) - C.Hold)/C.OutFrames)), 1)`,
  where `INTRO_END` is the last frame of the entrance. The fade then does
  not depend on the clip length or on the unverified `comp.RenderEnd`. Build
  an "at clip end" exit only if the user asks for it.
- **Always warn:** the first and last frames of the clip are transparent.
  That is the animation, not a "black screen". Check with the playhead in
  the middle of the clip.

## Fonts

- **Always publish the font** of every visible text node:
  `fl.publish_font(node, "<Label>: font", group)` and next to it
  `Publish(node, "Size", "<Label>: size")`. Text+ sizes by the font's line
  height, so after a font change the text may get bigger or smaller. Say so
  and point to the size slider.
- If a text is typed through a source node (`TxtXSrc` → `TxtX`), publish the
  font on the display node `TxtX`, not on the source.

Use only fonts installed on the user's machine. Check before building:
`system_profiler SPFontsDataType | grep -i "<font>"` (macOS) or
`fc-list | grep -i "<font>"`. Missing font: offer a replacement or an install
(free fonts: `@expo-google-fonts/<family>` on jsDelivr ships static TTFs).
Not every font covers Cyrillic — check the cmap (e.g. Courier Prime does not;
Courier New does).

## Vertical frame

For 1080×1920 set `FRAME = (1080, 1920)` in the spec and call
`fl.set_frame(*FRAME)` before computing coordinates. All px helpers (`fx`,
`fy`, masks, text) follow it.

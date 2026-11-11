# Original brief: the `davinci-resolve-templates` skill

> The brief this skill was built from (translated from Russian). Some details
> were later corrected by testing in Resolve — see `references/verified.md`
> (mask units, Text+ size, install folder of the App Store build).

Create a Claude Code skill that generates DaVinci Resolve templates (titles,
badges, lower thirds, cards, generators, transitions) as Fusion `.setting`
macros packed into `.drfx`. The skill must NOT control Resolve: it only
generates files and installs them into the templates folder.

Main scenario: the user sends an image (screenshot of a badge, card or
title). The skill asks clarifying questions, then builds a template whose
texts, icons, colors, position and animation are editable in the Inspector.

The attached files are already proven in Resolve. Build on them, do not
start from scratch:
- `fusion_lib.py` — `.setting` builder: nodes, InstanceInput, UserControls,
  expressions, validation;
- `pricing_card.py` — a full template example (pricing card, 2 variants,
  81 published controls);
- `tests_build.py` — a pack of mini tests for diagnostics.

---

## 1. Skill structure

```
davinci-resolve-templates/
├── SKILL.md
├── references/
│   ├── setting-format.md      # .setting format: nodes, inputs, publishing, expressions
│   ├── verified.md            # what is verified in Resolve and what is not (section 5)
│   ├── questions.md           # questions to the user, with defaults
│   ├── design-rules.md        # template building rules
│   └── examples/              # working .setting files (generated from pricing_card.py and tests)
├── scripts/
│   ├── fusion_lib.py          # library (to be improved, section 6)
│   ├── analyze_image.py       # measurements from an image: HEX colors, bounds, gaps
│   ├── pack_drfx.py           # .setting → .drfx
│   ├── install_macos.sh       # install via unzip into the Templates folder
│   └── make_test_pack.py      # diagnostic tests (based on tests_build.py)
└── templates/
    └── pricing_card.py        # template spec example
```

SKILL.md description: "Generates DaVinci Resolve templates (Fusion
.setting/.drfx) from an image or description: titles, badges, lower thirds,
cards, generators with editable parameters in the Inspector". Keep the
description narrow so the skill does not trigger on regular editing.

## 2. Skill workflow (mandatory order)

1. **Image analysis.** Run `analyze_image.py`: colors (median, min and max
   per region), element bounds, gaps, radii. Convert sizes to a 1920×1080
   (or 1080×1920) frame with a scale factor.
2. **Questions in one batch** (section 3), each with a default. If
   AskUserQuestion is available, use it, max 4 questions at a time.
3. **Spec.** Show a layer table: element, position in px, size, HEX color,
   font; the list of Inspector controls; the animation. Wait for
   confirmation.
4. **Generation** with `fusion_lib.py`: a separate spec file in the style of
   `pricing_card.py`.
5. **Validation** with `validate()`: bracket balance, strings. If `luac` is
   available, also check the syntax with `luac -p`.
6. **Packing** into `.drfx` (a zip with `Edit/Titles/<Group>/<Name>.setting`).
7. **Install** with the script (section 7) and instructions where to find
   the template.
8. **Check:** ask for a screenshot from Resolve next to the original and fix
   differences. Record calibration values (text scale etc.) in
   `references/verified.md`.

## 3. Questions to the user

Don't ask what the image shows: position, colors, proportions, radii.

Required (they shape the template):
1. Structure: one element with copies on the timeline, or the whole block as
   one template. **Default: one element + variants.**
2. What is editable in the Inspector: texts, icons, colors, logo.
   **Default: all texts and colors.**
3. Text behaviour: fixed width or follows the text, how many lines.
   **Default: fixed, 1 line.**
4. Icons: icon font, PNG slot or vector. **Default: Font Awesome 6 Free.**
5. Animation. **Default: slide up + fade, 12 frames.**
6. Frame format, Resolve version, OS. **Default: 1920×1080, Resolve 21,
   macOS.**

Clarifying (only if the image does not tell): font and **Cyrillic
support**; own palette or the image's; shadow, outline, glass; one badge or
a series.

## 4. Template building rules (design-rules.md)

- **Variants instead of a switch.** If a "regular / highlighted" style is
  needed, generate 2 files with different defaults. A switch built on
  expressions would lock the color fields.
- **Master nodes for colors.** A color is published on one node (e.g.
  `Heading`); other nodes of the same color reference it with the expression
  `Heading.Red1` etc.
- **Shared parameters** (text scale, list step, animation) are UserControls
  on one Transform node (`Card`) and are published via InstanceInput.
- **Text+ does not wrap.** Line breaks are `\n` in the text. List items need
  a length limit (about 38 characters at 17px on a 345px width); warn the
  user about it.
- **Icons:** a separate Text+ with an icon font; the user swaps the glyph by
  copying it via Copy Glyph on fontawesome.com.
- **Node names:** unique, readable, with a suffix. No reserved words
  (`Name`, `Input`, `Output` etc.). Safe: `TxtName`, `BgCard`, `XfCard`.
- **Inspector labels** in Russian, with prefixes for grouping: "Item 3:
  text", "Button: background".
- **Animation** makes the first and last frames transparent. Tell the user
  explicitly, otherwise they take it for a black screen.
- **Fonts:** only installed ones. Ask or check before building (`fc-list` /
  `system_profiler SPFontsDataType`).

## 5. Verified in Resolve 21 (macOS) and not

**Works (verified):**
- `MacroOperator` + `InstanceInput` / `InstanceOutput`, loaded from
  `Templates/Edit/Titles/<folder>/`;
- `TextPlus` (Cyrillic, color `Red1/Green1/Blue1/Alpha1`, `Center`, `Size`,
  anchors `HorizontalLeftCenterRight` / `VerticalTopCenterBottom`);
- `Background` with a solid color and with `Type = FuID{"Vertical"}`
  (gradient `TopLeft*` → `BottomLeft*`);
- `RectangleMask` via `EffectMask` of a Background, `CornerRadius`;
- `Merge` over a transparent `Background` (`TopLeftAlpha = 0`): alpha is
  preserved;
- a full static card of 60+ nodes, `Transform` with `UserControls`,
  publishing `Center` / `Size` / custom sliders.

**Needs verification (mark in verified.md and ask the user):**
- **`RectangleMask` height.** A 600×300 px test (Height = 300/1080) was
  described by the user as a "square". Height may be relative to the frame
  **width** (then Height = px/1920). Check with a clearly elongated
  rectangle and fix the formula in `rect_mask()`.
- `Text+ Size` scale (currently `Size = px / 1920`, plus a "Text scale"
  slider for calibration).
- `HorizontalJustificationNew = 0` for left alignment in multi-line text.
- Animation expressions: `time`, `comp.RenderEnd`, `iif`, `min`/`max`,
  `Point()`, `Card.AnimFrames` references. If they fail, switch to keyframes
  or to entrance-only animation.
- Installing by dragging the `.drfx` into the Resolve window is unreliable.
  The main way is unzip (section 7).

## 6. `fusion_lib.py` improvements

- Fix `rect_mask()` after the height check (section 5).
- Add nodes: `sRectangle` / `sEllipse` (shape system), `Loader` (optional),
  `Transform` animated with keyframes (`BezierSpline`) as an alternative to
  expressions, `SoftGlow` / `DropShadow` for shadows.
- Add `publish_font(op)`: Font and Style in one ControlGroup.
- Generate a preview PNG for the Effects Library (same name next to the
  `.setting`), drawn with PIL from the spec.
- Check node names for reserved words and uniqueness.
- CLI: `python generate.py spec.py --variant all --pack --install`.

## 7. Install (macOS)

`~/Library/Application Support/Blackmagic Design/...` is closed to Claude's
remote access, so the install is a command the user runs in Terminal:

```bash
T="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates" && mkdir -p "$T" && unzip -o "<path to .drfx>" -d "$T"
```

Resolve must be restarted afterwards. Quitting it with
`osascript -e 'quit app "DaVinci Resolve"'` with an unsaved project returns
error `-128` (the user cancelled). The right way: ask the user to save
(Cmd+S) and quit by hand (Cmd+Q).

Where to look after installing: Edit page → Effects → Toolbox → Titles →
Fusion Titles section, group = folder name; or search by name.

Keep paths for other OSes in `references/setting-format.md` marked "not
verified":
- Windows: `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Templates`
- Linux: `~/.local/share/DaVinciResolve/Fusion/Templates`

## 8. Diagnostics ("black screen")

Order of checks, to be written into SKILL.md:
1. The playhead is in the middle of the clip, not on the first frame
   (animation).
2. The template was installed via unzip and Resolve restarted.
3. Mini test pack `make_test_pack.py`:
   - Test 1 Text — red text;
   - Test 2 Background — green frame;
   - Test 3 Rect Mask — blue 2:1 rectangle;
   - Test 4 Merge — white text on a transparent background.
4. Bisect the template: static version without expressions → without
   Transform → background only. The first broken step points to the
   culprit.
5. Ask for Workspace → Console and a screenshot of the node graph on the
   Fusion page.

## 9. Definition of done

- [ ] `SKILL.md` with workflow, questions, rules and diagnostics;
- [ ] `templates/pricing_card.py` produces two `.setting` and a `.drfx`,
      passing validation;
- [ ] `make_test_pack.py` creates tests 1–4 and a mask height test;
- [ ] `install_macos.sh <file.drfx>` installs the pack without touching
      Resolve;
- [ ] `references/verified.md` reflects section 5;
- [ ] `references/examples/` holds generated working `.setting` files.

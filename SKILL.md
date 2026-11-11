---
name: davinci-resolve-templates
description: |
  Generates DaVinci Resolve templates (Fusion .setting/.drfx) from an image,
  a reference video or a description: titles, lower thirds, cards, badges,
  generators with editable texts, fonts, colors and animation in the
  Inspector. Asks Grill Me questions, builds the template and installs it
  into its own group in Templates.
  Use ALWAYS when the user says "сделай шаблон для DaVinci", "шаблон для
  Resolve", "титр для давинчи", "плашка для Resolve", "lower third для
  DaVinci", "Fusion title", "сделай .drfx", "make a DaVinci Resolve
  template", "Resolve title template", "fusion macro", or sends a screenshot
  or reference video of a title/card/lower third and asks to recreate it in Resolve.
  Do NOT use for: regular editing, color grading, rendering or exporting
  video, controlling Resolve via scripts/API, Premiere/After Effects/CapCut
  templates, transitions.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
---

# davinci-resolve-templates

Turns an image, a video or a description into a DaVinci Resolve Fusion
template (`.setting` packed into `.drfx`). Texts, icons, fonts, colors,
position and animation of the result are editable in the Inspector. The skill
generates the files and installs them into a separate group in Templates.
**It never starts, stops or controls Resolve.**

**Language.** These instructions are in English, but talk to the user in the
language of their request: questions, the spec, warnings and Inspector labels
are in the user's language (Russian request → Russian answers and labels).
Placeholder texts in templates follow the language the user chose.

`SKILL_DIR` is the skill's base folder (shown when the skill loads). Shell
variables do not persist between Bash calls, so write the full path instead
of `$SKILL_DIR` in every command. Put working files into the current project:
`./resolve-templates/<slug>/` (spec `spec.py`, build in `out/`).

## Workflow

### Step 1 — Input and analysis

1. Get the image or description. If there is neither, the first question is
   "What element is it and where does it appear in the video?"
2. Look at the image (Read) and measure it:

   ```bash
   python3 "$SKILL_DIR/scripts/analyze_image.py" ref.png --frame 1920x1080
   python3 "$SKILL_DIR/scripts/analyze_image.py" ref.png --roi x,y,w,h      # elements inside a card
   python3 "$SKILL_DIR/scripts/analyze_image.py" ref.png --region x,y,w,h --sample x,y
   python3 "$SKILL_DIR/scripts/analyze_image.py" ref.png --crop x,y,w,h --zoom 4 --crop-out crop.png
   ```

   The script reports background, palette, element boxes, gaps and
   `scale.factor` with the formula to map into the frame. Take colors as the
   median of a region, not a single pixel. Without Pillow, tell the user:
   `python3 -m pip install --user pillow`. If they decline, measure by eye
   and warn about the precision.
3. **If the input is a video** (`.mov`, `.mp4`), split it into frames first:

   ```bash
   python3 "$SKILL_DIR/scripts/video_frames.py" ref.mov --out <scratch>/frames
   ```

   The script prints fps and a motion timeline and builds a contact sheet.
   Look at the sheet (Read), split the animation into stages, measure the
   layout on a frame where everything is in place with `analyze_image.py`,
   and track element sizes over frames (bbox by color) to get timings and
   curves. Convert source frames to timeline frames:
   `f_tl = (f_src − f_start) × fps_tl / fps_src` (ask for the timeline fps).
   Needs PyAV and Pillow. No ffmpeg needed; swift from Command Line Tools
   can be broken.
4. Write down what you saw (type, number of elements and variants, font,
   icons). These points do not become questions.

### Step 2 — Grill Me questions

Ask the questions from `references/questions.md`, **one per message**, each
with a recommendation. For simple templates or when the user wants speed,
use the **quick mode** from the same file: one message with all
recommendations, the user answers "OK" or corrects numbered items. Skip questions answered by the image or already
answered. "OK to all" / «ок на всё» means: take the recommendations.
Check fonts yourself:
`system_profiler SPFontsDataType | grep -i "<font>"` (macOS) /
`fc-list | grep -i "<font>"`.

### Step 3 — Spec

Show it and **wait for confirmation**:

- layer table: element · position (px) · size · HEX color · font/style;
- Inspector controls in the order they will appear;
- animation (mode, frames, exit);
- group, template and variant names, type (Titles/Generators/Effects);
- limits: characters per line, transparency on the first and last frame,
  unverified features from `references/verified.md` used in the template.

### Step 4 — Build

1. Read `references/design-rules.md` and the example
   `templates/pricing_card.py` (more in `examples/`).
2. Write `./resolve-templates/<slug>/spec.py` following the contract:
   `GROUP`, `CATEGORY`, `FRAME`, `ANIM`, `VARIANTS`,
   `build(v, anim) -> (tools, pubs, output_name)`. Import the library:

   ```python
   import sys, os
   sys.path.insert(0, os.path.expanduser("<SKILL_DIR>/scripts"))
   import fusion_lib as fl
   ```

3. Build and pack:

   ```bash
   python3 "$SKILL_DIR/scripts/generate.py" resolve-templates/<slug>/spec.py \
     --out resolve-templates/<slug>/out --pack
   ```

   `fl.macro()` checks node names, references and publishes. `validate()`
   checks brackets and strings and runs `luac -p` when installed. Fix errors
   in the spec, never in the `.setting`.
4. Open the preview `out/<Name>.png` (Read) and compare it with the
   reference. The preview is approximate: expressions and animation are not
   evaluated.

### Step 5 — Install into its own group

The group is the path inside the `.drfx`: `Edit/<Category>/<GROUP>/`.

**macOS has two Resolve builds and they read different folders.** A
template installed into the wrong folder silently never appears.

| Build | How to tell | Install into | How |
|---|---|---|---|
| **App Store** | `.app` contains `Contents/_MASReceipt`; bundle id e.g. `com.blackmagic-design.DaVinciResolveLite` | `~/Library/Containers/<bundle id>/Data/Library/Application Support/Fusion/Templates/` | `.drfx` copied as is |
| **Blackmagic website** | no `_MASReceipt` | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/` | `.drfx` unzipped (`Edit/…`) |

1. Detect the build (this also answers question 17):

   ```bash
   bash "$SKILL_DIR/scripts/install_macos.sh" --detect
   ```

2. Install. By default (`--target auto`) the script installs into every
   build it finds:

   ```bash
   bash "$SKILL_DIR/scripts/install_macos.sh" "resolve-templates/<slug>/out/<PACK>.drfx"
   ```

   If no build is found, ask the user: "Resolve from the App Store or from
   the Blackmagic website?", then pass `--target appstore`, `website` or
   `all`.
3. If the script cannot write to the folder, give the user the same command
   for Terminal with absolute paths. Fallback: drag the `.drfx` into the
   Resolve window; it then lands where this particular build reads it.

Then tell the user:

1. Save the project (Cmd+S), quit Resolve (Cmd+Q) and start it again. Never
   quit Resolve via `osascript`.
2. Where to find it: Edit → Effects → Toolbox → Titles → Fusion Titles →
   group `<GROUP>` (or search by name).
3. Put the playhead in the middle of the clip: the first and last frames
   are transparent because of the animation.

To remove a template and its images: `install_macos.sh --uninstall "<PACK>"`
prints the plan from the install manifest; run it with `--yes` only after the
user agrees.

Windows and Linux paths are in `references/setting-format.md`. They are not
verified; say so.

### Step 6 — Check

Ask for a screenshot from Resolve next to the reference. Fix differences in
the spec and rebuild. Record calibration values and confirmed points in
`references/verified.md`.

## "Black screen" diagnostics

Go in order:

1. The playhead is in the middle of the clip, not on the first frame.
2. The template is where **this** Resolve build reads it (App Store or
   website, see step 5) and Resolve was restarted. If older templates of the
   same group are visible and new ones are not, the template is almost
   certainly in the wrong folder.
3. Test pack:
   `python3 "$SKILL_DIR/scripts/make_test_pack.py" --out out/tests` →
   install `DRT Tests.drfx`. Tests: 01 Text (red text), 02 Background (green
   frame), 03 Rect Mask (blue 2:1 rectangle), 04 Merge (white text on a
   transparent background), 05 Mask Height, 06–13 (unverified features;
   expected results are printed at build time).
4. Bisect the template: `--anim static` (no expressions) → no Transform →
   background only. The first broken step points to the culprit.
5. Ask for Workspace → Console and a screenshot of the node graph on the
   Fusion page.

## Rules

- Do: one question at a time, each with a recommendation.
- Do: spec before building, confirmation before installing.
- Do: talk to the user in their language; Inspector labels in their language, with prefixes ("Button: background" / «Кнопка: фон»).
- Do: build style variants as separate files, not a switch.
- Do: publish a color on a master node; other nodes follow it (`follow_color`).
- Do: warn about unverified features, character limits and transparency at the clip edges.
- Do: detect the Resolve build before installing (`install_macos.sh --detect`) and install into its folder. The App Store build reads only its container `~/Library/Containers/<bundle id>/…`; the website build reads only `~/Library/Application Support/Blackmagic Design/…`.
- Do: name the `.drfx` after the template (`PACK`), not the group. In the App Store build all packs share one folder, and a pack named after the group overwrites its neighbour.
- Don't: say "installed" without naming the build and the folder.
- Don't: start, quit or script Resolve.
- Don't: edit `.setting` files by hand. The source of truth is `spec.py`.
- Don't: use fonts the user does not have.
- Don't: use reserved node names (`Name`, `Input`, `Text`…).
- Don't: promise transitions or a file picker in the Inspector. An image can only be baked in via `ASSETS` + `fl.loader` (see design-rules.md).

## Examples

### Example 1 — badge from a screenshot

**User:** *(lower third screenshot)* сделай такой шаблон для давинчи

**Assistant (in Russian):** runs `analyze_image.py` and writes what it saw:
lower third bottom left, 2 lines (name Bold, role Regular), background
#1e1e1e with radius, accent stripe #ff5a1f. Then asks one question at a
time («Вопрос 1/≈8. Варианты стиля? Рекомендую: один»). After the answers it
shows the spec, builds, installs into the group and explains where to find
the template.

### Example 2 — from a description, "use defaults"

**User:** need a card with a title and three items with icons, use defaults

**Assistant:** takes the recommendations (1920×1080, fixed 1 line, FA6,
slide-up and fade 12 frames), asks only for the group name and shows the
spec.

### Example 3 — "black screen"

**User:** поставил шаблон, а там пусто

**Assistant (in Russian):** asks where the playhead is, then follows the
diagnostics: test pack, bisection with `--anim static`.

## Edge Cases

- **Vertical video**: `FRAME = (1080, 1920)`, `fl.set_frame(*FRAME)` at the
  top of the spec.
- **Several elements in the image**: ask about the structure (question 3).
  A series of identical badges is one template plus copies on the timeline.
- **Font missing or without Cyrillic**: offer a replacement (Inter) or an
  install. Check Cyrillic coverage in the font's cmap, not by rendered width.
- **Expressions do not work in the user's Resolve**: rebuild with
  `--anim keys` and update verified.md.
- **A transition is requested**: say the skill does not do transitions;
  offer a title with in/out animation instead.
- **No Pillow**: no preview, measurements by eye. The template still builds.

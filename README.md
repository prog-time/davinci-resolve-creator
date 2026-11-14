# davinci-resolve-creator

Claude Code skill **`davinci-resolve-templates`**: turns a screenshot, a
reference video or a plain description into a DaVinci Resolve Fusion template
(`.setting`, packed into `.drfx`) — titles, lower thirds, cards, animated
badges — with texts, fonts, colors, position and animation editable in the
Inspector. It installs the template into a separate group of Resolve's
Templates folder. It never starts, stops or scripts Resolve.

## How it works

1. **Input** — image (`analyze_image.py`: colors, element boxes, scale to the
   frame) or video (`video_frames.py`: frames, motion timeline, contact sheet).
2. **Grill Me** — one question at a time, each with a recommended answer
   ([references/questions.md](skills/davinci-resolve-templates/references/questions.md)).
3. **Spec** — table of layers, Inspector controls, animation timing; waits
   for confirmation.
4. **Build** — `spec.py` → `scripts/generate.py` (node/expression checks,
   validation, preview PNG) → `.drfx`.
5. **Install** — `scripts/install_macos.sh` detects the Resolve build:
   the **App Store** build reads only its sandbox container, the **website**
   build reads `~/Library/Application Support/Blackmagic Design/…`.
6. **Check** — screenshot from Resolve next to the reference; calibration
   goes into [references/verified.md](skills/davinci-resolve-templates/references/verified.md).

## Install

### As a Claude Code plugin (recommended)

No clone and no symlink needed:

```bash
claude plugin marketplace add prog-time/davinci-resolve-creator
claude plugin install davinci-resolve-creator@prog-time
```

Inside Claude Code the same works as `/plugin marketplace add
prog-time/davinci-resolve-creator` and `/plugin install
davinci-resolve-creator@prog-time`.

### From a clone (try it or develop it)

```bash
git clone https://github.com/prog-time/davinci-resolve-creator.git
claude --plugin-dir ./davinci-resolve-creator     # load it for one session
claude plugin validate ./davinci-resolve-creator  # check the manifests
```

Alternative for local development, a plain skill via symlink (this is how the
author uses it; re-run the command after moving the repository):

```bash
ln -sfn "$PWD/davinci-resolve-creator/skills/davinci-resolve-templates" ~/.claude/skills/davinci-resolve-templates
```

Optional tools (the skill works without them, with less precision):

```bash
python3 -m pip install --user pillow==13.0.0 av==19.0.2   # image analysis, previews, video input
```

Then ask Claude Code, e.g. «сделай шаблон для DaVinci по этому скриншоту» or
"make a DaVinci Resolve title template from this video".

## What the plugin does on your machine

**Runs.** Python scripts from `skills/davinci-resolve-templates/scripts/`
(image and video analysis, building `.setting` and `.drfx`, previews) and the
shell script `install_macos.sh`. It never starts, stops or controls
DaVinci Resolve.

**Sends.** Nothing. No telemetry, no uploads of your images, videos or
templates anywhere.

**Downloads.** Only `fonts.py`, and only when it looks up or installs a font:
it asks `registry.npmjs.org` and `data.jsdelivr.com` for the package of a free
Google Font and fetches the font files from `cdn.jsdelivr.net`. Installing a
font into `~/Library/Fonts` (on Linux `~/.local/share/fonts`) happens only
with the `--yes` flag, which the skill passes after you agree; without it the
script prints a plan and writes nothing.

**Writes.** `install_macos.sh` writes into the Fusion user folder of your
Resolve (the App Store container or `~/Library/Application Support/Blackmagic
Design/DaVinci Resolve/Fusion`): the template pack in `Fusion/Templates`, images
of the template in `Fusion/Assets/<group>/`, and an install record in
`Fusion/Assets/.drt-manifests/` that `--uninstall` uses to remove exactly what
was installed. Working files go to `./resolve-templates/` in your project.
Windows and Linux installation is not automated.

**No Resolve on the machine** (claude.ai, Cowork, a cloud sandbox): the skill
builds the template and hands you the `.drfx` file to install by hand.

## Layout

```
.claude-plugin/
  plugin.json            plugin manifest
  marketplace.json       marketplace "prog-time" listing this plugin
skills/davinci-resolve-templates/
  SKILL.md               workflow, rules, diagnostics (loaded by Claude Code)
  references/
    questions.md         Grill Me questions with defaults
    design-rules.md      how templates are built (units, masters, fonts, decor)
    setting-format.md    .setting / .drfx format, install paths
    verified.md          what is confirmed in Resolve 21 and what is not
    examples/            reference .setting files
  scripts/
    fusion_lib.py        .setting builder: nodes, masks, Text+, Loader, checks
    fusion_anim.py       animation blocks: Timeline (slide, grow, typing, wipe,
                         hold fade, master controls), place_image
    setting_diff.py      semantic diff of two .setting files (refactor safety)
    generate.py          spec.py -> .setting + preview + .drfx [+ install]
    analyze_image.py     measurements from a reference image
    fonts.py             find / check (cmap) / compare / install fonts, icon glyph codes
    video_frames.py      frames + motion timeline from a reference video
    track.py             per-element bbox tracking, motion stages, easing fit
    preview_anim.py      animated preview without Resolve (Lua-evaluated, GIF + sheet)
    compare.py           Resolve screenshot vs reference: offsets, ratios, colors
    pack_drfx.py         .setting -> .drfx
    install_macos.sh     install into the right Resolve build (--detect)
    make_test_pack.py    diagnostic test pack (13 tests)
    ci_checks.py         CI checks: SKILL.md lint, build + Lua parse, secret scan
  templates/pricing_card.py  example spec
  examples/              specs of templates built with the skill
tests/                   pytest unit tests
docs/brief.md            original brief the skill was built from
```

## Development

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q tests
```

## CI

Every PR into `develop` runs independent jobs: SKILL.md lint, build of all
examples with a Lua parse of each `.setting` and every expression, unit
tests, and a scan for secrets and personal paths. Locally:

```bash
python3 skills/davinci-resolve-templates/scripts/ci_checks.py skill
python3 skills/davinci-resolve-templates/scripts/ci_checks.py settings   # needs: pip install lupa
python3 skills/davinci-resolve-templates/scripts/ci_checks.py scan
```

## Status

Verified in DaVinci Resolve 21.2 (macOS, App Store build): macro loading,
Text+ (incl. Cyrillic, calibrated size), masks (units differ between
Rectangle and Ellipse), Transform pivot semantics, expressions incl.
multi-line Lua and `Text()`. Not yet verified: `Loader` images inside titles,
`comp.RenderEnd`, shapes, Effects/Generators, Windows/Linux paths. Details in
[references/verified.md](skills/davinci-resolve-templates/references/verified.md).

## License

MIT, see [LICENSE](LICENSE).

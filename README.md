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
   ([references/questions.md](references/questions.md)).
3. **Spec** — table of layers, Inspector controls, animation timing; waits
   for confirmation.
4. **Build** — `spec.py` → `scripts/generate.py` (node/expression checks,
   validation, preview PNG) → `.drfx`.
5. **Install** — `scripts/install_macos.sh` detects the Resolve build:
   the **App Store** build reads only its sandbox container, the **website**
   build reads `~/Library/Application Support/Blackmagic Design/…`.
6. **Check** — screenshot from Resolve next to the reference; calibration
   goes into [references/verified.md](references/verified.md).

## Install

```bash
git clone https://github.com/prog-time/davinci-resolve-creator.git
ln -s "$PWD/davinci-resolve-creator" ~/.claude/skills/davinci-resolve-templates
```

Optional tools (the skill works without them, with less precision):

```bash
python3 -m pip install --user pillow av   # image analysis, previews, video input
```

Then ask Claude Code, e.g. «сделай шаблон для DaVinci по этому скриншоту» or
"make a DaVinci Resolve title template from this video".

## Layout

```
SKILL.md                 workflow, rules, diagnostics (loaded by Claude Code)
references/
  questions.md           Grill Me questions with defaults
  design-rules.md        how templates are built (units, masters, fonts, decor)
  setting-format.md      .setting / .drfx format, install paths
  verified.md            what is confirmed in Resolve 21 and what is not
  examples/              reference .setting files
scripts/
  fusion_lib.py          .setting builder: nodes, masks, Text+, Loader, checks
  fusion_anim.py         animation blocks: Timeline (slide, grow, typing, wipe,
                         hold fade, master controls), place_image
  setting_diff.py        semantic diff of two .setting files (refactor safety)
  generate.py            spec.py -> .setting + preview + .drfx [+ install]
  analyze_image.py       measurements from a reference image
  fonts.py               find / check (cmap) / compare / install fonts, icon glyph codes
  video_frames.py        frames + motion timeline from a reference video
  track.py               per-element bbox tracking, motion stages, easing fit
  preview_anim.py        animated preview without Resolve (Lua-evaluated, GIF + sheet)
  pack_drfx.py           .setting -> .drfx
  install_macos.sh       install into the right Resolve build (--detect)
  make_test_pack.py      diagnostic test pack (13 tests)
  ci_checks.py           CI checks: SKILL.md lint, build + Lua parse, secret scan
templates/pricing_card.py  example spec
examples/                specs of templates built with the skill
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
python3 scripts/ci_checks.py skill
python3 scripts/ci_checks.py settings   # needs: pip install lupa
python3 scripts/ci_checks.py scan
```

## Status

Verified in DaVinci Resolve 21.2 (macOS, App Store build): macro loading,
Text+ (incl. Cyrillic, calibrated size), masks (units differ between
Rectangle and Ellipse), Transform pivot semantics, expressions incl.
multi-line Lua and `Text()`. Not yet verified: `Loader` images inside titles,
`comp.RenderEnd`, shapes, Effects/Generators, Windows/Linux paths. Details in
[references/verified.md](references/verified.md).

## License

MIT, see [LICENSE](LICENSE).

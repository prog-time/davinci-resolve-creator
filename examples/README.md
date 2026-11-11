# Examples

Specs of templates built with the skill. Build one:

```bash
python3 ~/.claude/skills/davinci-resolve-templates/scripts/generate.py \
  examples/typewriter-box/spec.py --out out/typewriter-box --pack
```

`--install` instead of `--pack` also installs the `.drfx` (and copies the
`ASSETS` images) into the Resolve build found on this Mac.

| Example | What it shows | Needs |
|---|---|---|
| `typewriter-box` | selection box, typing text with UTF-8 safe expression, blinking cursor, Text+ cross grid | — |
| `icon-features` | 3 columns: thin ring (EllipseMask outline) + Phosphor icon + label, staggered pop | Phosphor-Thin font |
| `subscribe-bar` | photo spiral-in, slide-ups, press animation with state switch | `assets/subscribe-avatar.png` (square 512×512 photo) |
| `profile-card` | card retimed from a 60 fps video, typing labels, fanned photo copies, hold before fade | `assets/profile-photo.png` (772×814 photo), Oswald font |
| `scrapbook-note` | PNG decor drawn with Pillow (`make_assets.py`), parts fly in from all sides, hand-written title (wipe + pen), marker underline | run `make_assets.py <photo> assets`, Caveat font |

Photos and generated `assets/` are not in the repository — put your own.

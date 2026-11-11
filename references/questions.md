# Grill Me questions

Ask in the user's language. The wording below is the meaning, not a script.

## How to ask

- **One question per message.** If AskUserQuestion is available, use it: the
  recommended option goes first, marked "(recommended)" in the user's
  language (e.g. «(рекомендую)»). Otherwise write plain text.
- Question format (Russian example):

  > **Вопрос 3/≈12. Как ведёт себя текст?**
  > Рекомендую: фиксированная ширина, 1 строка (так на картинке).
  > Варианты: фикс 1 строка · многострочный (`\n`) · ширина под текст

- **Don't ask what the image shows** (position, colors, proportions, radii,
  number of items). Say what you saw instead: "Saw: 2 card variants, 5 and 7
  items, gradient at the top".
- Skip a question if it is already answered. Recount the "≈N".
- "Use defaults", "OK to all", "decide yourself" (or «давай дефолты»,
  «ок на всё», «дальше сам») mean: skip the remaining questions and take the
  recommendations.
- "Don't know": take the recommendation and list it under assumptions.
- Questions marked ↳ are asked only when their condition holds.

## Quick mode

Use it instead of one-by-one questions when the template is simple (one
style, up to ~3 texts, no photo or video reference, no ambiguity in the
image) or when the user asks for speed up front ("use defaults", «быстро»,
«давай дефолты»). Send ONE message in the user's language:

1. what you saw (type, elements, colors, fonts);
2. every remaining question from the list below as a numbered line with its
   recommendation already filled in;
3. "Reply OK, or correct the numbers you want to change".

Then go straight to the spec. Fall back to the full Grill Me when the answer
changes the structure (e.g. "make it a block of 3", "add a photo").

## A. Purpose

1. **Template type.** Title (title, badge, lower third, card), Generator
   (background without a clip), Effect (applied to a clip). The type decides
   the Templates folder. *Recommendation: infer from the image, usually Title.*
   The skill does not do transitions yet; say so plainly.
2. **Frame format.** 1920×1080 · 1080×1920 (Shorts/Reels) · 3840×2160.
   *Recommendation: 1920×1080.*
3. **Structure.** One element the user copies on the timeline, or the whole
   block as one template. *Recommendation: one element.*
4. **Style variants** ("regular / highlighted"). Each variant is a separate
   file. *Recommendation: as many as the image shows, otherwise 1.*

## B. Content

5. **What is editable in the Inspector.** Texts, icons, colors, position,
   scale. *Recommendation: all texts and main colors, plus position and scale.*
6. **Text behaviour.** Fixed width, 1 line · multi-line (the user adds line
   breaks with `\n`) · badge width follows the text.
   *Recommendation: fixed, 1 line.*
   - ↳ multi-line: **max lines?** *Recommendation: 3.* Warn about the
     characters-per-line limit (about 38 characters at 17 px on 345 px width).
   - ↳ width follows text: warn that Text+ cannot measure its width. There
     will be a "badge width" slider the user adjusts by hand.
7. **Font and Cyrillic.** "Detected font X. Do you need Cyrillic?" Check the
   font yourself (`system_profiler SPFontsDataType | grep -i <font>` or
   `fc-list | grep -i <font>`) and check Cyrillic in its cmap.
   *Recommendation: X if installed and covering the needed script,
   otherwise Inter.*
8. **Icons.** None · icon font · PNG slot · vector.
   *Recommendation: Font Awesome 6 Free (Solid) for filled icons, Phosphor
   Thin/Light for line icons. The user swaps an icon by copying the glyph
   from the icon site.*
   - ↳ list with icons: **max items?** *Recommendation: visible count + 2.*
9. **Logo or picture.** *Recommendation: none.* If needed, offer the options
   from design-rules.md ("Logo and photos"): a picture can only be baked in,
   and Loader in titles is not verified yet.

## C. Style

10. **Colors.** Palette from the image or brand HEX? Which colors go to the
    Inspector? *Recommendation: from the image; background, main text, accent.*
11. **Effects.** Shadow · outline · glass/blur · glow. *Recommendation: as in
    the image, no glass.* Shadow and glow are not verified (test 10).

## D. Animation

12. **Entrance.** Slide up with fade · fade only · scale · none.
    *Recommendation: slide up and fade, 12 frames.*
13. **Exit.** Fade after a hold · mirrored · none.
    *Recommendation: fade after a 90-frame hold (3 s at 30 fps) once the
    entrance is complete, 10 frames.* Hold and duration go to the Inspector.
14. **Animation controls in the Inspector.** *Recommendation: on/off, start,
    speed, hold, fade length.*

## E. Install

15. **Group name.** The folder in Templates; templates appear in Resolve
    under this name. *Recommendation: the project or channel name.*
16. **Template name** (and variants). *Recommendation: from the content,
    e.g. "Lower Third", "Lower Third Accent".*
17. **Resolve version, build and OS.** On macOS don't ask — detect:
    `install_macos.sh --detect`, and report it (e.g. "Resolve 21.2 from the
    App Store, installing into its container"). Ask "App Store or Blackmagic
    website?" only if nothing was found. Both found: install into both.
    *Recommendation: Resolve 21, macOS.* For Windows and Linux warn that the
    install path is not verified.

## After the questions

Show a summary: answers, assumptions and what you saw in the image. Then
show the spec (step 3 in SKILL.md) and wait for confirmation.

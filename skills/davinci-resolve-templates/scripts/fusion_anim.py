"""Animation building blocks on top of fusion_lib.

A Timeline holds the master controls (UserControls on one Transform, e.g.
"XfBlock") and produces the expressions every template needs: progress over
a frame range, easing, slide/grow/pop transforms, typing text, fade after a
hold. Using these keeps the rules of references/design-rules.md in one place
(Transform.Center is an offset, pivot for scale, hold-based exit).

    import fusion_lib as fl
    from fusion_anim import Timeline
    tl = Timeline("XfBlock")
    add(tl.slide("XfPaper", "MrgPaper", 0, 18, dy=800, angle=-3, pivot=fl.pt((940, 544))))
    ...
    blk, out = tl.output(add, stack, ["AnimStart", "Speed", "Hold", "OutFrames"], intro_end=140)
"""
import fusion_lib as fl


def clamp01(e):
    return f"min(1, max(0, {e}))"


EASE = {
    "linear": lambda x: x,
    "out3": lambda x: f"(1 - (1-{x})^3)",
    "io3": lambda x: f"iif({x} < 0.5, 4*({x})^3, 1 - 4*(1-{x})^3)",
    "io4": lambda x: f"iif({x} < 0.5, 8*({x})^4, 1 - 8*(1-{x})^4)",
    "back": lambda x: f"(1 + 2.70158*({x}-1)^3 + 1.70158*({x}-1)^2)",
}


def ease(name, x):
    return EASE[name](x)


# Standard master controls: cid -> (label, default, extra UserControl fields)
SLIDERS = {
    "AnimStart": ("Anim Start", 0, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=120)),
    "Speed": ("Speed", 1.0, dict(INP_MinScale=0.25, INP_MaxScale=4.0, INP_MinAllowed=0.05)),
    "Hold": ("Hold", 90, dict(INP_Integer=True, INP_MinScale=0, INP_MaxScale=600, INP_MinAllowed=0)),
    "OutFrames": ("Out Frames", 10, dict(INP_Integer=True, INP_MinScale=1, INP_MaxScale=60, INP_MinAllowed=1)),
}
CHECKBOXES = {"AnimOn": "Animation", "OutOn": "Fade Out"}


def slider(xf, cid, label, default, **extra):
    xf.set(cid, default)
    xf.user_control(cid, LINKS_Name=label, LINKID_DataType="Number", INPID_InputControl="SliderControl",
                    INP_Default=default, ICS_ControlPage="Controls", **extra)
    return xf


def checkbox(xf, cid, label, default=1):
    xf.set(cid, default)
    xf.user_control(cid, LINKS_Name=label, LINKID_DataType="Number", INPID_InputControl="CheckboxControl",
                    INP_Integer=False, INP_Default=default, CBC_TriState=False, ICS_ControlPage="Controls")
    return xf


class Timeline:
    """Expressions driven by the master Transform `ctrl`.

    speed=True: timings are (time - AnimStart) * Speed (Speed slider);
    speed=False: plain (time - AnimStart).
    """

    def __init__(self, ctrl="XfBlock", speed=True):
        self.C = ctrl
        self.speed = speed
        self.T = (f"((time - {ctrl}.AnimStart)*{ctrl}.Speed)" if speed
                  else f"(time - {ctrl}.AnimStart)")

    # ---- expressions ----
    def prog(self, a, b, t=None):
        """0..1 progress between timeline frames a and b."""
        return clamp01(f"({t or self.T} - {a})/{b - a}")

    def eased(self, a, b, name="out3"):
        return ease(name, self.prog(a, b))

    def on(self, e, off="1"):
        """Value e when animation is on, `off` when AnimOn is unchecked."""
        return f"iif({self.C}.AnimOn > 0.5, {e}, {off})"

    def typing(self, src, start, per_char):
        """Multi-line Lua: type src.StyledText letter by letter (UTF-8 safe)."""
        t = f"(time - {self.C}.AnimStart)*{self.C}.Speed" if self.speed else f"(time - {self.C}.AnimStart)"
        return (f''': local s = {src}.StyledText.Value or ""
local t = {t} - {start}
local n = -1
if t >= 0 then n = math.floor(t / {per_char}) + 1 end
if {self.C}.AnimOn < 0.5 then n = 100000 end
local out, i = "", 0
for ch in string.gmatch(s, "[^\\128-\\191][\\128-\\191]*") do
  if i < n then out = out .. ch end
  i = i + 1
end
return Text(out)''')

    def hold_fade(self, intro_end):
        """Blend for MrgOut: fade out OutFrames after intro_end + Hold (not tied to clip end)."""
        end = f"({self.C}.AnimStart + {intro_end}/{self.C}.Speed)" if self.speed else \
            f"({self.C}.AnimStart + {intro_end})"
        return f"iif({self.C}.OutOn > 0.5, {clamp01(f'1 - (time - {end} - {self.C}.Hold)/{self.C}.OutFrames')}, 1)"

    def clip_end_fade(self):
        """Blend for MrgOut: fade out over the last OutFrames of the clip (comp.RenderEnd)."""
        return f"iif({self.C}.OutOn > 0.5, {clamp01(f'(comp.RenderEnd - time)/{self.C}.OutFrames')}, 1)"

    # ---- transforms ----
    def slide(self, name, src, a, b, dx=0, dy=0, angle=0, size0=1.0, pivot=None, ease_name="out3"):
        """Transform that moves `src` in from (dx, dy) px (screen: +x right, +y down),
        rotating from `angle` and scaling from `size0`, over frames a..b."""
        W, H = fl.frame()
        e = ease(ease_name, self.prog(a, b))
        xf = fl.transform(name, src, pivot=pivot)
        if dx or dy:
            xf.set("Center", (0.5, 0.5), expr=self.on(
                f"Point(0.5 + {dx / W:.5f}*(1-{e}), 0.5 - {dy / H:.5f}*(1-{e}))", "Point(0.5, 0.5)"))
        if angle:
            xf.set("Angle", 0.0, expr=self.on(f"{angle}*(1-{e})", "0"))
        if size0 != 1.0:
            xf.set("Size", 1.0, expr=self.on(f"max(0.001, {size0} + {1 - size0}*{e})"))
        return xf

    def grow(self, name, src, a, b, pivot, ease_name="out3"):
        """Transform that scales `src` from 0 to 1 around `pivot` over frames a..b."""
        xf = fl.transform(name, src, pivot=pivot)
        xf.set("Size", 1.0, expr=self.on(f"max(0.001, {ease(ease_name, self.prog(a, b))})"))
        return xf

    def slide_y(self, name, src, progress, dist=0.04, direction=1):
        """Small vertical slide driven by an existing progress expression.
        direction +1 comes from below (slideUp), -1 from above (slideDown)."""
        xf = fl.transform(name, src)
        xf.set("Center", (0.5, 0.5), expr=(
            f"Point(0.5, 0.5 - {direction}*iif({self.C}.AnimOn > 0.5, {dist}*(1-{progress})^3, 0))"))
        return xf

    def wipe_mask(self, name, left, cy, width, height, width_expr, progress, soft=0.008):
        """Handwriting reveal: RectangleMask anchored at `left` (px) growing to
        width_expr * progress, with a soft edge. Use as EffectMask of a Text+ or Merge."""
        W, _ = fl.frame()
        m = fl.rect_mask(name, left + width / 2, cy, width, height, soft=soft)
        m.set("Width", width / W, expr=f"{width_expr}*{self.on(progress)}")
        m.set("Center", fl.pt((left + width / 2, cy)),
              expr=f"Point({fl.fx(left)} + {width_expr}*{self.on(progress)}/2, {fl.fy(cy)})")
        return m

    # ---- master controls and output ----
    def controls(self, xf, sliders, checkboxes=("AnimOn", "OutOn")):
        """sliders: standard names (see SLIDERS) or (cid, label, default, extra) tuples, in order."""
        for s in sliders:
            if isinstance(s, str):
                label, default, extra = SLIDERS[s]
                slider(xf, s, label, default, **extra)
            else:
                cid, label, default, extra = s
                slider(xf, cid, label, default, **extra)
        for cid in checkboxes:
            checkbox(xf, cid, CHECKBOXES[cid])
        return xf

    def output(self, add, stack, sliders, intro_end=None, fade="hold"):
        """Master Transform over `stack`, its controls, and MrgOut over a transparent
        background with the exit fade. fade: "hold" (needs intro_end) | "clip_end" | None.
        Returns (master, out)."""
        blk = add(fl.transform(self.C, stack))
        self.controls(blk, sliders)
        add(fl.background("BgOut", "#000000", alpha=0.0))
        out = add(fl.merge("MrgOut", "BgOut", self.C))
        if fade == "hold":
            out.set("Blend", 1.0, expr=self.hold_fade(intro_end))
        elif fade == "clip_end":
            out.set("Blend", 1.0, expr=self.clip_end_fade())
        return blk, out

    def publish(self, labels):
        """Publish master controls: labels = [(cid, label in the user's language), ...]."""
        return [fl.Publish(self.C, cid, label) for cid, label in labels]


# ---------- images ----------

def place_image(add, name, path, center, size=1.0, canvas="BgClear", mask=None, loader=None, merge_name=None):
    """Loader (unless `loader` names an existing one) merged onto `canvas` at
    `center` (px) with Merge.Size = size; optional EffectMask. Returns the Merge
    (named `merge_name` or MrgPlace<name>)."""
    if loader is None:
        loader = f"Ld{name}"
        add(fl.loader(loader, path))
    m = add(fl.merge(merge_name or f"MrgPlace{name}", canvas, loader))
    m.set("Center", fl.pt(center)).set("Size", size)
    if mask:
        m.link("EffectMask", mask, "Mask")
    return m

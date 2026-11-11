#!/usr/bin/env python3
"""Find, check, compare and install fonts for templates.

  fonts.py find <family>                       free static TTFs (Google Fonts via
                                               @expo-google-fonts on jsDelivr)
  fonts.py check <font.ttf|family> [--style S] [--script cyrillic|latin|greek]
                                               script coverage by the cmap table
  fonts.py compare --crop ref.png --text "..." <font> [<font> ...]
                                               sheet: reference crop next to each
                                               candidate rendered at the same height
  fonts.py install <family> [--styles Bold,Regular] [--yes]
                                               download into the user font folder
                                               (prints the plan without --yes)
  fonts.py glyph <phosphor|tabler> <icon-name> [--weight thin|light|regular|bold]
                                               code point of an icon by name

<font> is a path to a .ttf/.otf or "Family:Style" of an installed font.
Network: registry.npmjs.org and jsDelivr (find / install / glyph only).
Pick a package version at least 14 days old (supply-chain hygiene).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fusion_lib as fl  # noqa: E402

SCRIPTS = {
    "cyrillic": "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    "latin": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
    "greek": "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρστυφχψω",
}
MIN_AGE_DAYS = 14
ICON_PACKS = {
    "phosphor": ("@phosphor-icons/web", "src/{weight}/style.css",
                 r'\.ph-{weight}\.ph-{name}:before\s*\{{\s*content:\s*"\\([0-9a-f]+)"'),
    "tabler": ("@tabler/icons-webfont", "dist/tabler-icons.css",
               r'\.ti-{name}:before\s*\{{\s*content:\s*"\\([0-9a-f]+)"'),
}


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "davinci-resolve-templates"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def http_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "davinci-resolve-templates"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def slug(family):
    return re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-")


def stable_version(package):
    """Newest version published at least MIN_AGE_DAYS ago."""
    meta = http_json(f"https://registry.npmjs.org/{package}")
    now = dt.datetime.now(dt.timezone.utc)
    best = None
    for v in meta["versions"]:
        t = meta["time"].get(v)
        if not t or "-" in v.split("+")[0].split(".")[-1]:
            continue
        age = now - dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
        if age.days >= MIN_AGE_DAYS:
            best = v                       # registry lists versions in publish order
    if not best:
        raise SystemExit(f"no version of {package} older than {MIN_AGE_DAYS} days")
    return best


def package_files(package, version):
    tree = http_json(f"https://data.jsdelivr.com/v1/packages/npm/{package}@{version}?structure=flat")
    return [f["name"] for f in tree["files"]]


def ttf_styles(files):
    """{style: path} from expo-google-fonts names like /Oswald_700Bold.ttf."""
    out = {}
    for f in files:
        m = re.search(r"_(\d{3})([A-Za-z]+(?:_Italic)?)\.ttf$", f)
        if m:
            out[m.group(2).replace("_", "")] = f
    return out


def cmd_find(a):
    package = f"@expo-google-fonts/{slug(a.family)}"
    try:
        version = stable_version(package)
    except Exception as e:
        raise SystemExit(f"{package}: not found ({e}). Check the exact Google Fonts family name.")
    styles = ttf_styles(package_files(package, version))
    print(f"{package}@{version}")
    for style, path in sorted(styles.items()):
        print(f"  {style:20s} https://cdn.jsdelivr.net/npm/{package}@{version}{path}")


def resolve_font(spec, style="Regular"):
    if os.path.isfile(spec):
        return spec
    family, _, st = spec.partition(":")
    path = fl._find_font(family, st or style)
    if not path:
        raise SystemExit(f"font not found: {spec} (install it or pass a file path)")
    return path


def cmap_of(path):
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        raise SystemExit("needs fontTools: python3 -m pip install --user fonttools")
    font = TTFont(path, fontNumber=0)
    return set(font.getBestCmap() or {})


def cmd_check(a):
    path = resolve_font(a.font, a.style)
    cmap = cmap_of(path)
    chars = SCRIPTS[a.script]
    missing = [c for c in chars if ord(c) not in cmap]
    print(f"{path}: {a.script} {len(chars) - len(missing)}/{len(chars)}")
    if missing:
        print("  missing: " + "".join(missing))
        sys.exit(1)


def cmd_compare(a):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise SystemExit("needs Pillow: python3 -m pip install --user pillow")
    ref = Image.open(a.crop).convert("RGB")
    h = ref.height
    rows = [("reference", ref)]
    for spec in a.fonts:
        path = resolve_font(spec)
        size = h
        for _ in range(6):                                  # fit the ink height to the crop
            font = ImageFont.truetype(path, size)
            box = font.getbbox(a.text)
            ink = box[3] - box[1]
            if ink <= 0:
                break
            size = max(4, int(size * (h * 0.8) / ink))
        font = ImageFont.truetype(path, size)
        box = font.getbbox(a.text)
        img = Image.new("RGB", (max(1, box[2] - box[0]) + 20, h), "white")
        ImageDraw.Draw(img).text((10 - box[0], (h - (box[3] - box[1])) / 2 - box[1]), a.text, font=font, fill="black")
        rows.append((f"{os.path.basename(path)}  ({size}px)", img))
    W = max(r[1].width for r in rows) + 20
    sheet = Image.new("RGB", (W, sum(r[1].height + 26 for r in rows)), "white")
    d = ImageDraw.Draw(sheet)
    y = 0
    for label, img in rows:
        d.text((10, y + 4), label, fill="#c00000")
        sheet.paste(img, (10, y + 22))
        y += img.height + 26
    sheet.save(a.out)
    print(f"-> {a.out}")


def font_dir():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Fonts")
    if sys.platform.startswith("linux"):
        return os.path.expanduser("~/.local/share/fonts")
    raise SystemExit("install is supported on macOS and Linux only")


def cmd_install(a):
    package = f"@expo-google-fonts/{slug(a.family)}"
    version = stable_version(package)
    styles = ttf_styles(package_files(package, version))
    want = [s.strip() for s in a.styles.split(",")] if a.styles else sorted(styles)
    unknown = [s for s in want if s not in styles]
    if unknown:
        raise SystemExit(f"unknown styles {unknown}; available: {', '.join(sorted(styles))}")
    dest = font_dir()
    family_file = re.sub(r"[^A-Za-z0-9]", "", a.family)
    plan = [(f"https://cdn.jsdelivr.net/npm/{package}@{version}{styles[s]}",
             os.path.join(dest, f"{family_file}-{s}.ttf")) for s in want]
    for url, path in plan:
        print(f"{url}\n  -> {path}")
    if not a.yes:
        print("\nPlan only. Re-run with --yes to install (ask the user first).")
        return
    os.makedirs(dest, exist_ok=True)
    for url, path in plan:
        with open(path, "wb") as f:
            f.write(http_bytes(url))
    print(f"installed {len(plan)} file(s). Restart Resolve to see new fonts.")


def cmd_glyph(a):
    package, css_path, pattern = ICON_PACKS[a.pack]
    version = stable_version(package)
    css_url = f"https://cdn.jsdelivr.net/npm/{package}@{version}/{css_path.format(weight=a.weight)}"
    css = http_bytes(css_url).decode("utf-8")
    m = re.search(pattern.format(weight=a.weight, name=re.escape(a.name)), css)
    if not m:
        near = sorted(set(re.findall(r"-([a-z0-9-]*%s[a-z0-9-]*):before" % re.escape(a.name.split("-")[0]), css)))[:15]
        raise SystemExit(f"{a.name}: not in {package}@{version}" + (f"; similar: {', '.join(near)}" if near else ""))
    print(f"{a.pack} {a.name}: \\u{m.group(1)}   ({package}@{version})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find")
    p.add_argument("family")
    p = sub.add_parser("check")
    p.add_argument("font")
    p.add_argument("--style", default="Regular")
    p.add_argument("--script", default="cyrillic", choices=sorted(SCRIPTS))
    p = sub.add_parser("compare")
    p.add_argument("fonts", nargs="+")
    p.add_argument("--crop", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--out", default="font-compare.png")
    p = sub.add_parser("install")
    p.add_argument("family")
    p.add_argument("--styles")
    p.add_argument("--yes", action="store_true")
    p = sub.add_parser("glyph")
    p.add_argument("pack", choices=sorted(ICON_PACKS))
    p.add_argument("name")
    p.add_argument("--weight", default="thin", choices=["thin", "light", "regular", "bold", "fill", "duotone"])
    a = ap.parse_args()
    {"find": cmd_find, "check": cmd_check, "compare": cmd_compare, "install": cmd_install,
     "glyph": cmd_glyph}[a.cmd](a)


if __name__ == "__main__":
    main()

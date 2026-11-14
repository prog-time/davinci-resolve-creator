#!/usr/bin/env python3
"""Pack .setting files (and same-name preview .png) into a .drfx bundle.

A .drfx is a zip whose paths mirror Fusion/Templates:
    Edit/<Category>/<Group>/<Name>.setting

Usage:
    pack_drfx.py OUT.drfx --group "My Group" [--category Titles] FILE.setting [...]
"""
import argparse
import os
import sys
import zipfile

CATEGORIES = ("Titles", "Generators", "Effects", "Transitions")


def pack(out, files, group, category="Titles"):
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {CATEGORIES}")
    if not group or any(c in group for c in "/\\:"):
        raise ValueError(f"bad group name {group!r}")
    entries = []
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            if not f.endswith(".setting"):
                raise ValueError(f"not a .setting file: {f}")
            for p in (f, os.path.splitext(f)[0] + ".png"):
                if os.path.exists(p):
                    arc = f"Edit/{category}/{group}/{os.path.basename(p)}"
                    z.write(p, arc)
                    entries.append(arc)
    return entries


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--group", required=True)
    ap.add_argument("--category", default="Titles", choices=CATEGORIES)
    a = ap.parse_args()
    try:
        for e in pack(a.out, a.files, a.group, a.category):
            print(e)
    except ValueError as e:
        sys.exit(f"error: {e}")
    print(f"-> {a.out}")


if __name__ == "__main__":
    main()

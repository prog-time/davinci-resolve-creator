#!/usr/bin/env python3
"""Build Fusion templates from a spec file, pack them, optionally install.

Spec contract (see templates/pricing_card.py):
    GROUP = "My Group"                 # template group (folder) in Resolve
    PACK = "My Template"               # .drfx file name (default: first variant)
    PREVIEW_BG = "#ebe7e1"             # optional: preview background (dark text on light video)
    ASSETS = {"a.png": "src/a.png"}    # optional: images for fl.loader(), copied on --install
    FIT = [("TxtTitle", 700)]          # optional: warn when a text node is wider (px)
    CATEGORY = "Titles"                # Titles | Generators | Effects
    FRAME = (1920, 1080)
    VARIANTS = {"Template Name": {...}, ...}
    def build(v, anim) -> (tools, publishes, output_name[, main_input])

Usage:
    generate.py SPEC.py [--variant all|NAME] [--out DIR] [--anim expr|keys|static]
                [--pack] [--install] [--no-preview] [--preview-anim [FRAMES]]
"""
import argparse
import importlib.util
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fusion_lib as fl  # noqa: E402
from pack_drfx import pack  # noqa: E402


def load_spec(path):
    spec = importlib.util.spec_from_file_location("template_spec", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for attr in ("GROUP", "VARIANTS", "build"):
        if not hasattr(mod, attr):
            sys.exit(f"spec {path} has no {attr}")
    return mod


def macro_id(title):
    s = re.sub(r"[^A-Za-z0-9_]", "", title.replace(" ", ""))
    return s if s and not s[0].isdigit() else "T" + s


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--variant", default="all")
    ap.add_argument("--out", default="out")
    ap.add_argument("--anim", default=None, choices=("expr", "keys", "static"),
                    help="override the spec's ANIM (default: spec ANIM or expr)")
    ap.add_argument("--pack", action="store_true")
    ap.add_argument("--install", action="store_true", help="pack and run install_macos.sh")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--asset-paths", choices=("absolute", "pathmap"),
                    help="how Loader paths are written (default: spec ASSET_PATHS, env DRT_ASSET_PATHS, absolute)")
    ap.add_argument("--preview-anim", type=int, metavar="FRAMES", nargs="?", const=150,
                    help="also render an animated preview (GIF + frame sheet) of FRAMES frames")
    a = ap.parse_args()

    # frame must be set before the spec computes pixel positions
    if a.asset_paths:
        fl.ASSET_PATHS = a.asset_paths
    mod = load_spec(a.spec)
    fl.set_frame(*getattr(mod, "FRAME", (1920, 1080)))
    category = getattr(mod, "CATEGORY", "Titles")
    anim = a.anim or getattr(mod, "ANIM", "expr")

    names = list(mod.VARIANTS) if a.variant == "all" else [a.variant]
    for n in names:
        if n not in mod.VARIANTS:
            sys.exit(f"unknown variant {n!r}; have: {', '.join(mod.VARIANTS)}")

    os.makedirs(a.out, exist_ok=True)
    files = []
    for title in names:
        res = mod.build(mod.VARIANTS[title], anim)
        tools, pubs, out_name = res[:3]
        main_input = res[3] if len(res) > 3 else None
        src = fl.macro(macro_id(title), tools, pubs, out_name, main_input)
        fl.validate(src)
        path = os.path.join(a.out, f"{title}.setting")
        with open(path, "w", encoding="utf-8") as f:
            f.write(src)
        files.append(path)
        for warning in fl.check_fit(tools, getattr(mod, "FIT", [])):
            print(f"WARNING {title}: {warning}")
        prev = None if a.no_preview else fl.render_preview(tools, os.path.splitext(path)[0] + ".png", output=out_name,
                                                         bg=getattr(mod, "PREVIEW_BG", "#181818"))
        if a.preview_anim:
            try:
                import preview_anim
                shots = preview_anim.render_animation(tools, out_name, a.preview_anim, step=2,
                                                      bg=getattr(mod, "PREVIEW_BG", "#202020"))
                gif, sheet = preview_anim.save_outputs(shots, a.out, title)
                print(f"animated preview: {gif}, {sheet}")
            except SystemExit as e:
                print(f"animated preview skipped: {e}")
        print(f"{path}: {len(tools)} nodes, {len(pubs)} published, anim={anim}"
              + (", preview" if prev else ", no preview (pip install pillow)" if not a.no_preview else ""))
    lc = fl.luac_check("{}")
    print("luac: " + ("ok" if lc else "not installed — only the built-in structural check ran"))

    if a.pack or a.install:
        # one .drfx per spec, named after PACK or the first variant: App Store Resolve keeps
        # packs side by side in one folder, so a group-named pack would overwrite others
        drfx = os.path.join(a.out, f"{getattr(mod, 'PACK', names[0])}.drfx")
        pack(drfx, files, mod.GROUP, category)
        print(f"packed -> {drfx}  (Edit/{category}/{mod.GROUP}/)")
        if a.install:
            # ASSETS = {"name.png": "/source/path.png"} -> copied to fl.asset_path(GROUP, name)
            import shutil
            pack_name = getattr(mod, "PACK", names[0])
            copied = []
            for name, src_path in getattr(mod, "ASSETS", {}).items():
                dst = os.path.join(fl.asset_dir(mod.GROUP), name)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src_path, dst)
                copied.append(dst)
                print(f"asset -> {dst}")
            if copied:                         # read by install_macos.sh --uninstall
                man = fl.manifest_path(pack_name)
                os.makedirs(os.path.dirname(man), exist_ok=True)
                with open(man, "w", encoding="utf-8") as f:
                    f.write("".join(f"asset {p}\n" for p in copied))
            cmd = [os.path.join(HERE, "install_macos.sh"), drfx]
            r = subprocess.run(cmd)
            if r.returncode != 0:
                print("\nInstall failed here. Run it yourself in Terminal:")
                print(f'  bash "{cmd[0]}" "{os.path.abspath(drfx)}"')


if __name__ == "__main__":
    main()

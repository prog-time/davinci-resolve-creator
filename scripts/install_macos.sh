#!/usr/bin/env bash
# Install a .drfx where DaVinci Resolve (macOS) actually reads templates.
# There are TWO builds and they read DIFFERENT folders:
#
#   App Store build — sandboxed (Contents/_MASReceipt present). Reads only its container:
#     ~/Library/Containers/<bundle id>/Data/Library/Application Support/Fusion/Templates/
#     The .drfx is copied there as is.
#   Website build (blackmagicdesign.com installer) — reads:
#     ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/
#     The .drfx is unzipped there (Edit/<Category>/<Group>/...).
#
# Both builds installed -> installs into both. Does NOT start, stop, or script Resolve.
#
# Every install records what it put where in <Fusion>/Assets/.drt-manifests/<PACK>.txt
# (lines "template <path>"; generate.py --install adds "asset <path>").
#
# Usage:
#   install_macos.sh --detect                     # list Resolve builds and their Templates folders
#   install_macos.sh <file.drfx> [--target auto|appstore|website|all]
#   install_macos.sh --uninstall <PACK> [--yes]   # remove a pack and its images (plan without --yes)
set -euo pipefail

WEBSITE_T="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "macOS only. Paths for other OS: references/setting-format.md" >&2
  exit 1
fi

# Prints lines: <kind>|<bundle id>|<app path>|<templates dir>
detect() {
  local apps=() app id
  while IFS= read -r app; do [[ -n "$app" ]] && apps+=("$app"); done < <(
    { mdfind "kMDItemCFBundleIdentifier == 'com.blackmagic-design.DaVinciResolve*'" 2>/dev/null || true
      for app in "/Applications/DaVinci Resolve.app" "/Applications/DaVinci Resolve Studio.app" \
                 "/Applications/DaVinci Resolve/DaVinci Resolve.app" \
                 "/Applications/DaVinci Resolve Studio/DaVinci Resolve Studio.app"; do
        [[ -d "$app" ]] && echo "$app"
      done; } | grep -E '\.app$' | grep -v '/Contents/' | sort -u)
  for app in ${apps[@]+"${apps[@]}"}; do
    id="$(defaults read "$app/Contents/Info" CFBundleIdentifier 2>/dev/null || true)"
    [[ "$id" == com.blackmagic-design.DaVinciResolve* ]] || continue
    if [[ -e "$app/Contents/_MASReceipt" ]]; then
      echo "appstore|$id|$app|$HOME/Library/Containers/$id/Data/Library/Application Support/Fusion/Templates"
    else
      echo "website|$id|$app|$WEBSITE_T"
    fi
  done
}

fusion_dirs() {  # every Fusion user folder that exists (App Store containers + website)
  local d
  for d in "$HOME"/Library/Containers/com.blackmagic-design.DaVinciResolve*/Data/Library/"Application Support"/Fusion; do
    [[ -d "$d" ]] && echo "$d"
  done
  [[ -d "$(dirname "$WEBSITE_T")" ]] && dirname "$WEBSITE_T"
  return 0
}

record() {  # record <fusion dir> <template path>...   (replaces old template lines of this pack)
  local fdir="$1"; shift
  local man="$fdir/Assets/.drt-manifests/$PACK_NAME.txt"
  mkdir -p "$(dirname "$man")"
  { [[ -f "$man" ]] && grep -v '^template ' "$man" || true; for p in "$@"; do echo "template $p"; done; } > "$man.tmp"
  mv "$man.tmp" "$man"
}

if [[ "${1:-}" == "--uninstall" ]]; then
  PACK="${2:-}"
  [[ -z "$PACK" ]] && { echo "usage: $0 --uninstall <PACK> [--yes]" >&2; exit 1; }
  YES=""; [[ "${3:-}" == "--yes" ]] && YES=1
  plan=()
  while IFS= read -r fdir; do
    [[ -z "$fdir" ]] && continue
    man="$fdir/Assets/.drt-manifests/$PACK.txt"
    if [[ -f "$man" ]]; then
      while read -r _kind path; do
        case "$path" in "$fdir"/*) [[ -e "$path" ]] && plan+=("$path") ;; *) echo "skip (outside $fdir): $path" >&2 ;; esac
      done < "$man"
      plan+=("$man")
    elif [[ -f "$fdir/Templates/$PACK.drfx" ]]; then
      plan+=("$fdir/Templates/$PACK.drfx")
    fi
  done < <(fusion_dirs)
  if [[ ${#plan[@]} -eq 0 ]]; then
    echo "nothing installed for pack \"$PACK\""
    exit 1
  fi
  printf '  %s\n' "${plan[@]}"
  if [[ -z "$YES" ]]; then
    echo "Plan only. Re-run with --yes to delete these files (ask the user first)."
    exit 0
  fi
  for p in "${plan[@]}"; do rm -f "$p"; rmdir "$(dirname "$p")" 2>/dev/null || true; done
  echo "Removed ${#plan[@]} file(s). Restart Resolve."
  exit 0
fi

if [[ "${1:-}" == "--detect" ]]; then
  found="$(detect)"
  if [[ -z "$found" ]]; then
    echo "No DaVinci Resolve app found. Use --target appstore|website explicitly."
    exit 1
  fi
  echo "$found" | while IFS='|' read -r kind id app dir; do
    echo "$kind  $id"
    echo "  app:       $app"
    echo "  templates: $dir"
  done
  exit 0
fi

DRFX="${1:-}"
TARGET="auto"
if [[ "${2:-}" == "--target" ]]; then TARGET="${3:-auto}"; fi
if [[ -z "$DRFX" || ! -f "$DRFX" ]]; then
  echo "usage: $0 <file.drfx> [--target auto|appstore|website|all] | $0 --detect" >&2
  exit 1
fi

# Only accept archives whose entries are Edit/<Category>/<Group>/<file> (no .., no absolute paths).
BAD="$(unzip -Z1 "$DRFX" | grep -vE '^Edit/[^/]+/[^/]+/[^/]+$' | grep -vE '/$' || true)"
if [[ -n "$BAD" ]] || unzip -Z1 "$DRFX" | grep -q '\.\.'; then
  echo "refusing: unexpected entries in $DRFX:" >&2
  echo "$BAD" >&2
  exit 1
fi

PACK_NAME="$(basename "$DRFX" .drfx)"
install_appstore() {  # $1 = templates dir
  mkdir -p "$1"
  cp -f "$DRFX" "$1/$(basename "$DRFX")"
  record "$(dirname "$1")" "$1/$(basename "$DRFX")"
  echo "Installed [App Store build] -> $1/$(basename "$DRFX")"
}
install_website() {
  mkdir -p "$WEBSITE_T"
  unzip -o -q "$DRFX" -d "$WEBSITE_T"
  local entries=()
  while IFS= read -r e; do [[ "$e" == */ ]] || entries+=("$WEBSITE_T/$e"); done < <(unzip -Z1 "$DRFX")
  record "$(dirname "$WEBSITE_T")" "${entries[@]}"
  echo "Installed [website build]   -> $WEBSITE_T (unzipped)"
}

FOUND="$(detect)"
DEFAULT_APPSTORE="$HOME/Library/Containers/com.blackmagic-design.DaVinciResolveLite/Data/Library/Application Support/Fusion/Templates"
n=0
case "$TARGET" in
  auto|all)
    if [[ -z "$FOUND" && "$TARGET" == "auto" ]]; then
      echo "No DaVinci Resolve app found. Re-run with --target appstore|website|all." >&2
      exit 1
    fi
    if [[ "$TARGET" == "all" ]]; then
      install_appstore "$DEFAULT_APPSTORE"; install_website; n=2
    else
      while IFS='|' read -r kind id app dir; do
        if [[ "$kind" == "appstore" ]]; then install_appstore "$dir"; else install_website; fi
        n=$((n + 1))
      done <<< "$FOUND"
    fi
    ;;
  appstore)
    dir="$(echo "$FOUND" | awk -F'|' '$1=="appstore"{print $4; exit}')"
    install_appstore "${dir:-$DEFAULT_APPSTORE}"; n=1
    ;;
  website)
    install_website; n=1
    ;;
  *)
    echo "unknown --target $TARGET" >&2
    exit 1
    ;;
esac

GROUP="$(unzip -Z1 "$DRFX" | head -n1 | cut -d/ -f3)"
CATEGORY="$(unzip -Z1 "$DRFX" | head -n1 | cut -d/ -f2)"
unzip -Z1 "$DRFX" | sed 's/^/  /'
echo
echo "Installed into $n location(s)."
echo "Next: save the project (Cmd+S), quit Resolve (Cmd+Q), start it again."
echo "Find it: Edit page -> Effects -> Toolbox -> $CATEGORY -> Fusion $CATEGORY -> group \"$GROUP\" (or search by name)."

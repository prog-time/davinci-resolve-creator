#!/usr/bin/env python3
"""Semantic diff of two Fusion .setting files (needs lupa).

Parses both with a real Lua parser and compares nodes, inputs, values, links,
expressions, user controls and published inputs. Ignores key order and node
positions in the flow view (ViewInfo). Use it to prove a refactor did not
change a template.

Usage: setting_diff.py A.setting B.setting      (exit 1 when they differ)
       setting_diff.py DIR_A DIR_B              (pairs files by relative path)
"""
import os
import sys

try:
    import lupa
except ImportError:
    sys.exit("needs lupa: python3 -m pip install lupa")

LUA = """
local function ctor(name)
  return function(t)
    if type(t) ~= "table" then return { __type = name, __value = t } end
    t.__type = name
    return t
  end
end
ordered = function() return function(t) return t end end
setmetatable(_G, { __index = function(_, k) return ctor(k) end })
return function(src) return load("return " .. src)() end
"""
IGNORE = {"ViewInfo", "CtrlWZoom"}


def to_py(v):
    if lupa.lua_type(v) == "table":
        keys = list(v.keys())
        if keys and all(isinstance(k, int) for k in keys) and "__type" not in keys:
            return [to_py(v[k]) for k in sorted(keys)]
        return {str(k): to_py(v[k]) for k in keys if str(k) not in IGNORE}
    if isinstance(v, float):
        return round(v, 6)
    return v


def load(path, parse):
    return to_py(parse(open(path, encoding="utf-8").read()))


def diff(a, b, path="", out=None):
    out = [] if out is None else out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}/{k}: only in B = {str(b[k])[:120]}")
            elif k not in b:
                out.append(f"{path}/{k}: only in A = {str(a[k])[:120]}")
            else:
                diff(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append(f"{path}: {str(a)[:120]}  !=  {str(b)[:120]}")
    return out


def pairs(a, b):
    if os.path.isfile(a):
        return [(a, b)]
    res = []
    for root, _, files in os.walk(a):
        for f in files:
            if f.endswith(".setting"):
                pa = os.path.join(root, f)
                res.append((pa, os.path.join(b, os.path.relpath(pa, a))))
    return sorted(res)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    parse = lupa.LuaRuntime().execute(LUA)
    failed = False
    for pa, pb in pairs(sys.argv[1], sys.argv[2]):
        if not os.path.exists(pb):
            print(f"MISSING {pb}")
            failed = True
            continue
        d = diff(load(pa, parse), load(pb, parse))
        print(f"{'SAME' if not d else 'DIFF'} {os.path.basename(pa)}" + (f" ({len(d)})" if d else ""))
        for line in d[:40]:
            print("   ", line)
        failed |= bool(d)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

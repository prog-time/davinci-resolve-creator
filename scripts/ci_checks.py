#!/usr/bin/env python3
"""Repository checks used by CI (and runnable locally).

  ci_checks.py skill      SKILL.md frontmatter: name, description length, allowed-tools
  ci_checks.py settings   build every examples/*/spec.py and templates/*.py, then parse each
                          .setting (plus references/examples/*.setting) and every Fusion
                          expression with a real Lua parser (lupa)
  ci_checks.py scan       secrets and personal absolute paths in tracked files

Exit code 1 on any failure; each problem is printed as path: message.
"""
import glob
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
MAX_DESCRIPTION = 1024


def check_skill():
    errs = []
    text = open(os.path.join(ROOT, "SKILL.md"), encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ["SKILL.md: no YAML frontmatter"]
    fm = m.group(1)
    name = re.search(r"^name:\s*(\S+)", fm, re.M)
    if not name or name.group(1) != "davinci-resolve-templates":
        errs.append("SKILL.md: name must be davinci-resolve-templates")
    desc = re.search(r"^description:\s*\|\n((?:  .*\n?)+)", fm + "\n", re.M)
    if not desc:
        errs.append("SKILL.md: description must be a literal block (|)")
    elif len(desc.group(1)) > MAX_DESCRIPTION:
        errs.append(f"SKILL.md: description is {len(desc.group(1))} chars (max {MAX_DESCRIPTION})")
    if not re.search(r"^allowed-tools:\n(  - \S+\n?)+", fm + "\n", re.M):
        errs.append("SKILL.md: allowed-tools list is missing")
    for ref in re.findall(r"`((?:references|scripts|templates|examples)/[^`*<>]+?)`", text):
        if not os.path.exists(os.path.join(ROOT, ref.rstrip("/"))):
            errs.append(f"SKILL.md: referenced path does not exist: {ref}")
    return errs


LUA_COLLECT = """
local exprs = {}
local function grab(t)
  if type(t) == "table" and t.Expression then table.insert(exprs, t.Expression) end
  return t
end
ordered = function() return function(t) return t end end
setmetatable(_G, { __index = function(_, k) return grab end })
return function(src)
  exprs = {}
  local f, err = load("return " .. src)
  if not f then return nil, err end
  local ok, e2 = pcall(f)
  if not ok then return nil, e2 end
  return exprs
end
"""
LUA_CHECK = """function(e)
  local code = e:sub(1, 1) == ":" and e:sub(2) or ("return " .. e)
  local f, err = load(code)
  return err
end"""


def check_settings():
    try:
        import lupa
    except ImportError:
        return ["lupa is not installed: python3 -m pip install lupa"]
    errs = []
    out = tempfile.mkdtemp(prefix="drc-ci-")
    specs = sorted(glob.glob(os.path.join(ROOT, "examples", "*", "spec.py")) +
                   glob.glob(os.path.join(ROOT, "templates", "*.py")))
    for spec in specs:
        rel = os.path.relpath(spec, ROOT)
        dst = os.path.join(out, os.path.basename(os.path.dirname(spec)) if spec.endswith("spec.py")
                           else os.path.splitext(os.path.basename(spec))[0])
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "generate.py"), spec, "--out", dst,
                            "--no-preview"], capture_output=True, text=True, cwd=os.path.dirname(spec))
        if r.returncode:
            errs.append(f"{rel}: build failed: {(r.stderr or r.stdout).strip().splitlines()[-1]}")
        else:
            print(f"built {rel}")
    lua = lupa.LuaRuntime()
    collect = lua.execute(LUA_COLLECT)
    check = lua.eval(LUA_CHECK)
    files = sorted(glob.glob(os.path.join(out, "**", "*.setting"), recursive=True) +
                   glob.glob(os.path.join(ROOT, "references", "examples", "*.setting")))
    for f in files:
        name = os.path.relpath(f, out) if f.startswith(out) else os.path.relpath(f, ROOT)
        res = collect(open(f, encoding="utf-8").read())
        if isinstance(res, tuple) or res is None:
            errs.append(f"{name}: Lua parse error: {res[1] if isinstance(res, tuple) else '?'}")
            continue
        exprs = list(res.values())
        bad = [(e, check(e)) for e in exprs if check(e)]
        for e, err in bad:
            errs.append(f"{name}: bad expression {e[:80]!r}: {err}")
        print(f"parsed {name}: {len(exprs)} expressions")
    if not files:
        errs.append("no .setting files were produced")
    return errs


SECRET_PATTERNS = [
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("Anthropic/OpenAI key", re.compile(r"sk-(ant-)?[A-Za-z0-9_-]{20,}")),
    ("AWS key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Slack token", re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"BEGIN [A-Z ]*PRIVATE KEY")),
    ("personal absolute path", re.compile(r"/(Users|home)/[a-z][a-z0-9_.-]+/")),
]
SCAN_SKIP = ("scripts/ci_checks.py",)


def check_scan():
    errs = []
    files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    for rel in files:
        if rel in SCAN_SKIP:
            continue
        try:
            text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pat in SECRET_PATTERNS:
                if pat.search(line):
                    errs.append(f"{rel}:{lineno}: possible {label}")
    return errs


def main():
    cmds = {"skill": check_skill, "settings": check_settings, "scan": check_scan}
    if len(sys.argv) != 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: {sys.argv[0]} {{{'|'.join(cmds)}}}")
    errs = cmds[sys.argv[1]]()
    for e in errs:
        print(f"ERROR {e}")
    print(f"{sys.argv[1]}: {'FAILED' if errs else 'OK'} ({len(errs)} problem(s))")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()

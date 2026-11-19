#!/usr/bin/env python3
"""Check the rule files in .claude/rules/ of the current repository.

Reports, for each rule file:
  - frontmatter that does not parse, or keys other than `paths`;
  - globs that match no file in the repository, so the file never loads;
  - no rules written as list items;
  - a file longer than the limit (40 lines).

Exit status is 1 when a problem was found. Standard library only.
"""
import argparse
import pathlib
import re
import subprocess
import sys

SKIP_DIRS = {".git", "node_modules", "vendor", "target", "dist", "build", ".venv", "venv", "__pycache__"}


def repo_files(root):
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
                             capture_output=True, text=True, timeout=120)
        if out.returncode == 0:
            return [f for f in out.stdout.splitlines() if f]
    except (OSError, subprocess.TimeoutExpired):
        pass
    found = []
    for p in root.rglob("*"):
        if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_DIRS):
            found.append(p.relative_to(root).as_posix())
    return found


def glob_to_regex(glob):
    """`**/` spans folders, `*` and `?` stay inside one path part, `{a,b}` is a choice."""
    out, i = "", 0
    while i < len(glob):
        c = glob[i]
        if glob.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif glob.startswith("**", i):
            out, i = out + ".*", i + 2
        elif c == "*":
            out, i = out + "[^/]*", i + 1
        elif c == "?":
            out, i = out + "[^/]", i + 1
        elif c == "{" and "}" in glob[i:]:
            end = glob.index("}", i)
            out += "(?:" + "|".join(re.escape(x) for x in glob[i + 1:end].split(",")) + ")"
            i = end + 1
        else:
            out, i = out + re.escape(c), i + 1
    return re.compile("^" + out + "$")


def parse(text):
    """Return (globs or None, body, problems). Reads only the `paths` key."""
    if not text.startswith("---"):
        return None, text, []
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*(?:\n|$)", text, re.S)
    if not m:
        return None, text, ["frontmatter starts with --- but has no closing ---"]
    problems, globs, in_paths = [], [], False
    for raw in m.group(1).splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s*(.+)$", line)
        if item and in_paths:
            globs.append(item.group(1).strip().strip("'\""))
            continue
        key = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not key:
            problems.append(f"cannot read frontmatter line: {line.strip()!r}")
            continue
        in_paths = key.group(1) == "paths"
        if not in_paths:
            problems.append(f"unknown frontmatter key {key.group(1)!r} (only `paths` is used)")
        elif key.group(2).strip():
            value = key.group(2).strip()
            if value.startswith("["):
                value = value.strip("[]")
            # split on commas, but not on the commas inside {a,b}
            globs += [g.strip().strip("'\"") for g in re.split(r",(?![^{]*\})", value) if g.strip()]
    if not globs:
        problems.append("frontmatter has no `paths` entries; remove it to load the file always")
    return globs, text[m.end():], problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--max-lines", type=int, default=40)
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()
    rules_dir = root / ".claude" / "rules"
    rule_files = sorted(rules_dir.rglob("*.md")) if rules_dir.is_dir() else []
    if not rule_files:
        print(f"no rule files in {rules_dir}")
        return 1
    files = [f for f in repo_files(root) if not f.startswith(".claude/")]
    failed = False
    for rf in rule_files:
        text = rf.read_text(encoding="utf-8")
        globs, body, problems = parse(text)
        lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        rules = sum(1 for l in body.splitlines() if re.match(r"^\s*[-*]\s+\S", l))
        scope = "always loaded"
        if globs:
            counts = []
            for g in globs:
                n = sum(1 for f in files if glob_to_regex(g).match(f))
                counts.append((g, n))
            scope = ", ".join(f"{g} ({n} files)" for g, n in counts)
            if not any(n for _, n in counts):
                problems.append("no glob matches a file in the repository, so the file never loads")
        if lines > args.max_lines:
            problems.append(f"{lines} lines, over the limit of {args.max_lines}")
        if rules == 0:
            problems.append("no rules (no list items) in the file")
        print(f"{rf.relative_to(root).as_posix()}: {rules} rules, {lines} lines, {scope}")
        for p in problems:
            failed = True
            print(f"  PROBLEM: {p}")
    print("problems found" if failed else "all rule files are fine")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

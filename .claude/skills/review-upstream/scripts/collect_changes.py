#!/usr/bin/env python3
"""Collect what changed in the watched skill repositories over a period.

Reads upstream.json, fetches each watched repository (history and trees only,
file contents on demand, nothing is checked out or executed) and writes:

  <out>/summary.json          everything below, machine readable
  <out>/diffs/<name>.diff     upstream diff for each copied or related skill
  <out>/repos/<owner>__<repo> the clones, for `git show <head>:<path>`

Period:
  --days N              the last N days
  --since YYYY-MM-DD    from that day (UTC) until now, or until --until
  (neither)             since the commit recorded for each repository in
                        upstream.json "watch", that is, since the last review

Only the Python standard library and git are needed.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SKILL_FILE = "SKILL.md"


def git(repo_dir, *args, check=True, timeout=600):
    r = subprocess.run(["git", "-C", str(repo_dir), *args], capture_output=True, text=True,
                       timeout=timeout, errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()[:400]}")
    return r.stdout


def fetch_repo(repo, root):
    d = root / repo.replace("/", "__")
    url = f"https://github.com/{repo}.git"
    if (d / ".git").exists():
        git(d, "fetch", "--quiet", "--filter=blob:none", "origin", timeout=1800)
        head = git(d, "rev-parse", "origin/HEAD").strip()
    else:
        d.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                            "--single-branch", url, str(d)], capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            raise RuntimeError(f"clone of {repo} failed: {r.stderr.strip()[:400]}")
        head = git(d, "rev-parse", "HEAD").strip()
    return d, head


def is_commit(d, sha):
    return subprocess.run(["git", "-C", str(d), "cat-file", "-e", f"{sha}^{{commit}}"],
                          capture_output=True).returncode == 0


def is_ancestor(d, a, b):
    return subprocess.run(["git", "-C", str(d), "merge-base", "--is-ancestor", a, b],
                          capture_output=True).returncode == 0


def skill_dirs(d, rev):
    """Folders that hold a SKILL.md at this revision ('' for the repo root)."""
    if rev == EMPTY_TREE:
        return set()
    out = git(d, "ls-tree", "-r", "--name-only", rev)
    return {os.path.dirname(p) for p in out.splitlines() if os.path.basename(p) == SKILL_FILE}


def canonical(dirs):
    """Group mirror copies of a skill (same folder name) and keep the shortest path."""
    groups = {}
    for p in dirs:
        groups.setdefault(os.path.basename(p) or p, []).append(p)
    return {name: sorted(ps, key=lambda p: (len(p), p)) for name, ps in groups.items()}


def log(d, rng, paths):
    fmt = "%H%x1f%cs%x1f%s"
    args = ["log", f"--format={fmt}", rng if isinstance(rng, str) else rng[0]]
    out = git(d, *args, "--", *paths)
    rows = []
    for line in out.splitlines():
        sha, date, subject = line.split("\x1f", 2)
        rows.append({"sha": sha[:12], "date": date, "subject": subject[:160]})
    return rows


def frontmatter_description(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*(\n|$)", text, re.S)
    if not m:
        return ""
    lines = m.group(1).splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        value = line[len("description:"):].strip()
        if value in (">", "|", ">-", "|-", ">+", "|+", ""):
            block = []
            for nxt in lines[i + 1:]:
                if nxt.strip() and not nxt.startswith((" ", "\t")):
                    break
                block.append(nxt.strip())
            value = " ".join(b for b in block if b)
        return " ".join(value.strip("'\"").split())[:600]
    return ""


def describe_skill(d, rev, path):
    rel = f"{path}/{SKILL_FILE}" if path else SKILL_FILE
    text = git(d, "show", f"{rev}:{rel}", check=False)
    files = git(d, "ls-tree", "-r", "--name-only", rev, "--", path or ".").splitlines()
    return {"description": frontmatter_description(text), "lines": text.count("\n"), "files": len(files)}


def diff_to_file(d, base, head, paths, target):
    out = git(d, "diff", base, head, "--", *paths)
    if not out.strip():
        return None, []
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(out, encoding="utf-8")
    status = git(d, "diff", "--name-status", base, head, "--", *paths).splitlines()
    return str(target), status


def review_repo(watch, skills, related, args, out):
    repo = watch["repo"]
    if not REPO_RE.match(repo):
        raise RuntimeError(f"bad repository name: {repo!r}")
    d, head = fetch_repo(repo, out / "repos")
    info = {"repo": repo, "license": watch.get("license"), "recorded_commit": watch.get("commit")}

    # Period edges are found on the main line of the default branch, so that a
    # side branch merged later cannot move them.
    if args.until:
        head = git(d, "rev-list", "-1", "--first-parent", f"--before={args.until}T23:59:59Z", head).strip() or head
    if args.since:
        base = git(d, "rev-list", "-1", "--first-parent", f"--before={args.since}", head).strip() or EMPTY_TREE
        info["mode"] = f"since {args.since}"
    else:
        base = watch.get("commit") or ""
        if base and is_commit(d, base) and is_ancestor(d, base, head):
            info["mode"] = "since the recorded commit"
        else:
            info["mode"] = "recorded commit not in history, last 30 days used"
            info["warning"] = "The commit recorded in upstream.json is not an ancestor of the current head."
            cut = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
            base = git(d, "rev-list", "-1", "--first-parent", f"--before={cut}", head).strip() or EMPTY_TREE

    rng = head if base == EMPTY_TREE else f"{base}..{head}"
    info.update({"base": base, "head": head, "head_date": git(d, "log", "-1", "--format=%cs", head).strip(),
                 "commits_in_period": int(git(d, "rev-list", "--count", rng).strip())})

    at_head, at_base = skill_dirs(d, head), skill_dirs(d, base)
    head_groups, base_groups = canonical(at_head), canonical(at_base)

    # 1. Skills copied into this marketplace.
    copied, copied_paths = [], set()
    for s in skills:
        paths = [s["path"], *s.get("extra_paths", [])]
        copied_paths.add(s["path"])
        name = f'{s["plugin"]}__{s["skill"]}'
        entry = {"plugin": s["plugin"], "skill": s["skill"], "path": s["path"], "copied_at": s["commit"],
                 "local_changes": s.get("changes", []), "exists_at_head": s["path"] in at_head}
        # Changes that are already in the copy are not news: when the copy was
        # taken inside the period, start from the copy instead.
        start = base
        if is_commit(d, s["commit"]) and is_ancestor(d, s["commit"], head) and (
                base == EMPTY_TREE or is_ancestor(d, base, s["commit"])):
            start = s["commit"]
        entry["period_starts_at_copy"] = start != base
        skill_rng = head if start == EMPTY_TREE else f"{start}..{head}"
        entry["commits_in_period"] = log(d, skill_rng, paths) if info["commits_in_period"] else []
        entry["diff"], entry["files_in_period"] = diff_to_file(d, start, head, paths, out / "diffs" / f"{name}.diff")
        if is_commit(d, s["commit"]):
            pending = git(d, "diff", "--name-status", s["commit"], head, "--", *paths).splitlines()
            entry["not_taken_yet"] = {"files": pending,
                                      "commits": int(git(d, "rev-list", "--count", f'{s["commit"]}..{head}', "--", *paths).strip())}
            if pending:
                target = out / "diffs" / f"{name}.since-copy.diff"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(git(d, "diff", s["commit"], head, "--", *paths), encoding="utf-8")
                entry["not_taken_yet"]["diff"] = str(target)
        copied.append(entry)

    # 2. Upstream skills that cover the same ground as a skill here.
    rel = []
    for r in related:
        entry = {"for_skill": r["for_skill"], "path": r["path"], "exists_at_head": r["path"] in at_head}
        entry["commits_in_period"] = log(d, rng, [r["path"]]) if info["commits_in_period"] else []
        name = f'related__{r["for_skill"]}__{os.path.basename(r["path"])}'
        entry["diff"], entry["files_in_period"] = diff_to_file(d, base, head, [r["path"]], out / "diffs" / f"{name}.diff")
        rel.append(entry)
    related_paths = {r["path"] for r in related}

    # 3. Skills that did not exist at the start of the period.
    new = []
    for name, paths in sorted(head_groups.items()):
        if name in base_groups:
            continue
        new.append({"name": name, "path": paths[0], "copies": len(paths), **describe_skill(d, head, paths[0])})

    # 4. Other skills that changed: what the repository is working on.
    counts = {}
    if info["commits_in_period"] and base != EMPTY_TREE:
        tracked = {ps[0]: n for n, ps in head_groups.items() if n in base_groups}
        prefixes = sorted(tracked, key=len, reverse=True)
        seen = set()  # skill folders already counted for the current commit
        for line in git(d, "log", "--name-only", "--format=%x1e%H", rng).splitlines():
            if line.startswith("\x1e"):
                seen = set()
                continue
            if not line:
                continue
            for p in prefixes:
                inside = (line == p or line.startswith(p + "/")) if p else "/" not in line
                if inside:
                    if p not in seen:
                        seen.add(p)
                        counts[p] = counts.get(p, 0) + 1
                    break
    other = [{"name": os.path.basename(p) or p, "path": p, "commits": c}
             for p, c in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
             if p not in copied_paths and p not in related_paths]

    info.update({"copied": copied, "related": rel, "new_skills": new,
                 "removed_skill_names": sorted(set(base_groups) - set(head_groups)),
                 "other_changed_skills": other[:40], "other_changed_skills_total": len(other),
                 "clone": str(d)})
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int)
    ap.add_argument("--since", help="YYYY-MM-DD")
    ap.add_argument("--until", help="YYYY-MM-DD")
    ap.add_argument("--upstream", default="upstream.json")
    ap.add_argument("--out", default="/tmp/upstream-review")
    args = ap.parse_args()
    if args.days is not None and args.since:
        ap.error("use --days or --since, not both")
    for value in (args.since, args.until):
        if value and not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            ap.error(f"dates are YYYY-MM-DD, got {value!r}")
    if args.days is not None:
        if args.days < 1:
            ap.error("--days must be 1 or more")
        args.since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    elif args.since:
        args.since += "T00:00:00Z"

    up = json.loads(pathlib.Path(args.upstream).read_text(encoding="utf-8"))
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in (out / "diffs").glob("*.diff") if (out / "diffs").exists() else []:
        old.unlink()

    related = [{"for_skill": s["skill"], **r} for s in up["skills"] for r in s.get("related", [])]
    repos, errors = [], []
    watched = {w["repo"] for w in up["watch"]}
    for w in up["watch"]:
        try:
            repos.append(review_repo(w, [s for s in up["skills"] if s["repo"] == w["repo"]],
                                     [r for r in related if r["repo"] == w["repo"]], args, out))
        except Exception as e:  # one broken repository must not stop the review
            errors.append({"repo": w["repo"], "error": str(e)})
    for s in up["skills"]:
        if s["repo"] not in watched:
            errors.append({"repo": s["repo"], "error": f'skill {s["skill"]} comes from a repository that is not in "watch"'})

    summary = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "period": {"since": args.since, "until": args.until,
                          "mode": "period" if args.since else "since last review"},
               "focus": up.get("focus", []), "declined": up.get("declined", []),
               "repos": repos, "errors": errors}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"period: {args.since or 'since last review'}" + (f" until {args.until}" if args.until else ""))
    for r in repos:
        changed = [c for c in r["copied"] if c["diff"]]
        gone = [c["skill"] for c in r["copied"] if not c["exists_at_head"]]
        line = (f'{r["repo"]}: {r["commits_in_period"]} commits, copied skills changed {len(changed)}/{len(r["copied"])}, '
                f'related changed {sum(1 for x in r["related"] if x["diff"])}, new skills {len(r["new_skills"])}, '
                f'other changed {r["other_changed_skills_total"]}')
        print(line + (f', MISSING upstream: {", ".join(gone)}' if gone else "") + (f' [{r["warning"]}]' if r.get("warning") else ""))
        for c in changed:
            print(f'    {c["plugin"]}/{c["skill"]}: {len(c["commits_in_period"])} commits, {len(c["files_in_period"])} files')
    for e in errors:
        print(f'ERROR {e["repo"]}: {e["error"]}')
    print(f"summary: {out / 'summary.json'}")
    return 1 if errors and not repos else 0


if __name__ == "__main__":
    sys.exit(main())

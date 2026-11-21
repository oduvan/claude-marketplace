#!/usr/bin/env python3
"""Collect how skills were used in the Claude Code sessions of this machine.

Reads the session transcripts Claude Code keeps under ~/.claude/projects and
writes, for the sessions that fall in the period:

  <out>/sessions.json     totals, use per skill, one row per session
  <out>/digests/*.md      one readable digest per session: the user's prompts
                          in order, with a mark where each skill started

Nothing is uploaded and nothing outside <out> is written. The digests hold
the user's own prompts, so they stay on this machine: keep <out> outside any
repository. Obvious secrets are masked, which is a safety net, not a
guarantee.

Period:
  --days N              the last N days (default 7)
  --since YYYY-MM-DD    from that day (UTC) until now, or until --until

Only the Python standard library is needed.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys

UTC = dt.timezone.utc
COMMAND_RE = re.compile(r"<command-name>\s*/?([\w:.-]+)\s*</command-name>")
ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.S)
SKILL_FILE_RE = re.compile(r"/skills/([\w.-]+)/SKILL\.md$")
INTERRUPT = "[Request interrupted by user"
NOISE_PREFIXES = ("<local-command-", "<system-reminder>", "<task-notification>", "Caveat: The messages below",
                  "<bash-input>", "<bash-stdout>", "<bash-stderr>", "<user-prompt-submit-hook>")
SECRET_RES = [
    re.compile(r"\b(sk|pk|rk|ghp|gho|ghs|ghu|github_pat|xox[abprs]|AKIA|glpat)[-_A-Za-z0-9]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}"),
    re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b(\s*[:=]\s*)(\S+)"),
]


def mask(text):
    for i, rx in enumerate(SECRET_RES):
        text = rx.sub((lambda m: f"{m.group(1)}{m.group(2)}[masked]") if i == 3 else "[masked]", text)
    return text


def clip(text, limit):
    text = mask(" ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def parse_time(value):
    if not isinstance(value, str):
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def marketplace_skills(root):
    """Skills this marketplace ships: {bare name: plugin or 'project'}."""
    found = {}
    for f in sorted(root.glob("plugins/*/skills/*/SKILL.md")):
        found[f.parent.name] = f.parents[2].name
    for f in sorted(root.glob(".claude/skills/*/SKILL.md")):
        found[f.parent.name] = "project"
    return found


def user_text(content):
    """(prompt text, tool results) from a user entry's content."""
    if isinstance(content, str):
        return content, []
    texts, results = [], []
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            texts.append(block.get("text", ""))
        elif block.get("type") == "tool_result":
            results.append(bool(block.get("is_error")))
    return "\n".join(texts), results


def read_session(files):
    """Turn the transcript files of one session into an ordered list of events."""
    rows = []
    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    rows.sort(key=lambda r: r.get("timestamp") or "")

    info = {"cwd": None, "entrypoint": None, "branch": None, "first": None, "last": None, "available": set(),
            "tools": {}, "tool_errors": 0, "interrupts": 0, "assistant_turns": 0}
    events = []  # ("prompt", text) | ("skill", name, how, args) | ("error",) | ("interrupt",)
    for row in rows:
        kind = row.get("type")
        when = parse_time(row.get("timestamp"))
        if when:
            info["first"] = info["first"] or when
            info["last"] = when
        if kind == "attachment":
            att = row.get("attachment") or {}
            if att.get("type") == "skill_listing":
                info["available"].update(n for n in att.get("names") or [] if isinstance(n, str))
            continue
        if kind not in ("user", "assistant"):
            continue
        side = bool(row.get("isSidechain"))
        if not side:
            info["cwd"] = info["cwd"] or row.get("cwd")
            info["entrypoint"] = info["entrypoint"] or row.get("entrypoint")
            info["branch"] = row.get("gitBranch") or info["branch"]
        message = row.get("message") or {}
        content = message.get("content")
        if kind == "assistant":
            if not side:
                info["assistant_turns"] += 1
            for block in content if isinstance(content, list) else []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name") or "?"
                info["tools"][name] = info["tools"].get(name, 0) + 1
                args = block.get("input") if isinstance(block.get("input"), dict) else {}
                if name == "Skill" and args.get("skill"):
                    events.append(("skill", str(args["skill"]), "model", clip(str(args.get("args") or ""), 120)))
                elif name == "Read":
                    m = SKILL_FILE_RE.search(str(args.get("file_path") or ""))
                    if m:
                        events.append(("skill", m.group(1), "read", ""))
            continue
        text, results = user_text(content)
        for is_error in results:
            if is_error:
                info["tool_errors"] += 1
                events.append(("error",))
        if INTERRUPT in text:
            info["interrupts"] += 1
            events.append(("interrupt",))
            continue
        if side or row.get("isMeta") or row.get("isCompactSummary"):
            continue
        command = COMMAND_RE.search(text)
        if command:
            args = ARGS_RE.search(text)
            events.append(("skill", command.group(1), "user", clip(args.group(1) if args else "", 120)))
            continue
        text = text.strip()
        if text and not text.startswith(NOISE_PREFIXES):
            events.append(("prompt", text))
    return info, events


def split_name(name):
    plugin, _, bare = name.rpartition(":")
    return plugin, bare


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int)
    ap.add_argument("--since", help="YYYY-MM-DD")
    ap.add_argument("--until", help="YYYY-MM-DD")
    ap.add_argument("--projects-dir", default=str(pathlib.Path.home() / ".claude" / "projects"))
    ap.add_argument("--marketplace", default=".", help="root of the marketplace repository")
    ap.add_argument("--out", default="/tmp/marketplace-review/sessions")
    args = ap.parse_args()
    if args.days is not None and args.since:
        ap.error("use --days or --since, not both")
    for value in (args.since, args.until):
        if value and not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            ap.error(f"dates are YYYY-MM-DD, got {value!r}")
    now = dt.datetime.now(UTC)
    since = (dt.datetime.fromisoformat(args.since).replace(tzinfo=UTC) if args.since
             else now - dt.timedelta(days=args.days if args.days is not None else 7))
    until = dt.datetime.fromisoformat(args.until).replace(tzinfo=UTC) + dt.timedelta(days=1) if args.until else now

    projects = pathlib.Path(args.projects_dir).expanduser()
    out = pathlib.Path(args.out).expanduser()
    digests = out / "digests"
    digests.mkdir(parents=True, exist_ok=True)
    for old in digests.glob("*.md"):
        old.unlink()
    ours = marketplace_skills(pathlib.Path(args.marketplace).resolve())

    if not projects.is_dir():
        summary = {"error": f"no session folder at {projects}", "sessions": []}
        (out / "sessions.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(summary["error"])
        return 1

    # A session can span several files (subagents); group them by session id.
    groups = {}
    floor = since.timestamp() - 86400
    for f in projects.rglob("*.jsonl"):
        try:
            if f.stat().st_mtime < floor:
                continue
        except OSError:
            continue
        rel = f.relative_to(projects).parts
        sid = rel[1] if len(rel) > 2 else f.stem  # <project>/<session>/subagents/x.jsonl or <project>/<session>.jsonl
        groups.setdefault((rel[0], sid), []).append(f)

    sessions, per_skill, available_anywhere = [], {}, set()
    for (folder, sid), files in sorted(groups.items()):
        info, events = read_session(sorted(files))
        if not info["first"] or info["last"] < since or info["first"] > until:
            continue
        prompts = [e[1] for e in events if e[0] == "prompt"]
        if not prompts and not any(e[0] == "skill" for e in events):
            continue
        project = pathlib.PurePath(info["cwd"]).name if info["cwd"] else folder.strip("-").split("-")[-1]
        available = {split_name(n)[1] for n in info["available"]}
        available_anywhere |= available
        uses, lines = [], []
        for i, event in enumerate(events):
            if event[0] == "prompt":
                lines.append(f"- USER: {clip(event[1], 400)}")
            elif event[0] == "interrupt":
                lines.append("- (the user interrupted Claude)")
            elif event[0] == "skill":
                plugin, bare = split_name(event[1])
                before = next((e[1] for e in reversed(events[:i]) if e[0] == "prompt"), "")
                after, errors, interrupted = [], 0, False
                for later in events[i + 1:]:
                    if later[0] == "skill":
                        break
                    if later[0] == "prompt" and len(after) < 3:
                        after.append(clip(later[1], 300))
                    elif later[0] == "error" and not after:
                        errors += 1
                    elif later[0] == "interrupt" and not after:
                        interrupted = True
                use = {"skill": bare, "plugin": plugin or ours.get(bare, ""), "ours": bare in ours, "started_by": event[2],
                       "args": event[3], "prompt_before": clip(before, 400), "prompts_after": after,
                       "tool_errors_before_next_prompt": errors, "interrupted_before_next_prompt": interrupted}
                uses.append(use)
                agg = per_skill.setdefault(bare, {"skill": bare, "plugin": use["plugin"], "ours": use["ours"], "uses": 0,
                                                  "by_model": 0, "by_user": 0, "by_read": 0, "sessions": set(), "projects": set(),
                                                  "interrupted": 0})
                agg["uses"] += 1
                agg["by_" + event[2]] += 1
                agg["sessions"].add(sid)
                agg["projects"].add(project)
                agg["interrupted"] += int(interrupted)
                how = {"user": "started by the user", "model": "started by the model", "read": "loaded by reading its file"}[event[2]]
                lines.append(f"- >>> SKILL {event[1]} {how}"
                             + (f" with: {event[3]}" if event[3] else ""))
        name = f"{info['first'].strftime('%Y%m%d-%H%M')}-{re.sub(r'[^A-Za-z0-9_.-]', '_', project)[:40]}-{sid[:8]}.md"
        minutes = int((info["last"] - info["first"]).total_seconds() // 60)
        head = [f"# {project} · {info['first'].strftime('%Y-%m-%d %H:%M')} UTC · {minutes} min",
                f"prompts: {len(prompts)} · skill uses: {len(uses)} · tool errors: {info['tool_errors']} · "
                f"interrupts: {info['interrupts']} · started from: {info['entrypoint'] or 'unknown'}",
                "our skills available: " + (", ".join(sorted(available & set(ours))) or "none listed"), ""]
        (digests / name).write_text("\n".join(head + lines) + "\n", encoding="utf-8")
        sessions.append({"digest": f"digests/{name}", "project": project, "started": info["first"].isoformat(),
                         "minutes": minutes, "prompts": len(prompts), "assistant_turns": info["assistant_turns"],
                         "tool_errors": info["tool_errors"], "interrupts": info["interrupts"], "entrypoint": info["entrypoint"],
                         "skills_used": [u["skill"] for u in uses], "our_skills_available": sorted(available & set(ours)),
                         "first_prompt": clip(prompts[0], 200) if prompts else "", "uses": uses})

    skills = []
    for agg in sorted(per_skill.values(), key=lambda a: (-a["uses"], a["skill"])):
        skills.append({**agg, "sessions": len(agg["sessions"]), "projects": len(agg["projects"])})
    used = {s["skill"] for s in skills}
    summary = {
        "period": {"since": since.isoformat(), "until": until.isoformat()},
        "projects_dir": str(projects),
        "totals": {"sessions": len(sessions), "with_a_skill": sum(1 for s in sessions if s["skills_used"]),
                   "projects": len({s["project"] for s in sessions}), "prompts": sum(s["prompts"] for s in sessions),
                   "interrupts": sum(s["interrupts"] for s in sessions)},
        "skills": skills,
        "our_skills_not_used": sorted(n for n in ours if n not in used and n in available_anywhere),
        "our_skills_never_available": sorted(n for n in ours if n not in used and n not in available_anywhere),
        "sessions": sorted(sessions, key=lambda s: s["started"]),
    }
    (out / "sessions.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    t = summary["totals"]
    print(f"period: {since:%Y-%m-%d} to {until:%Y-%m-%d} · sessions: {t['sessions']} in {t['projects']} projects · "
          f"with a skill: {t['with_a_skill']} · prompts: {t['prompts']} · interrupts: {t['interrupts']}")
    for s in skills:
        print(f"  {s['skill']}{'' if s['ours'] else ' (not ours)'}: {s['uses']} uses in {s['sessions']} sessions "
              f"(model {s['by_model']}, user {s['by_user']}, read {s['by_read']}), interrupted {s['interrupted']}")
    print("ours, available but not used: " + (", ".join(summary["our_skills_not_used"]) or "none"))
    print("ours, never available in these sessions: " + (", ".join(summary["our_skills_never_available"]) or "none"))
    print(f"summary: {out / 'sessions.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

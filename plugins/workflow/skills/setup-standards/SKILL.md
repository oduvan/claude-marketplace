---
name: setup-standards
description: Set up coding standards for a repository as one rule file per language in .claude/rules/, each loaded only when Claude works on files of that language, plus a general file for the whole project. Use when the user wants to set up, define, add or update coding standards, conventions or rules for a project, or for one language or framework in it.
argument-hint: "[language or framework ...]"
---

# Set up standards

Writes the project's coding standards where Claude Code loads them by itself:

```
.claude/rules/
  general.md       no paths: loaded in every session
  go.md            loaded when a .go file is read
  python.md        loaded when a .py file is read
  django.md        a framework gets its own file, scoped to its folders
```

The `code-review` skill reads the same files as the project's standards.

Arguments: `$ARGUMENTS`. With arguments, do only those languages or
frameworks. With none, do every one the project uses.

## 1. Survey the project

Find out, from the files and not from the user:

- **Languages and frameworks in use.** Manifests (`go.mod`, `pyproject.toml`,
  `package.json`, `tsconfig.json`, `Cargo.toml`, …) and where the source
  files of each one live. Ignore vendored and generated code.
- **What tooling already enforces.** Formatter, linter and type-checker
  configuration, pre-commit hooks, CI steps. Read the configuration, not only
  its presence: which rule sets are on, how strict the type checker is. A
  tool enforces something only when something runs it: CI, a pre-commit
  hook, or the project's own test command. Note each tool that is
  configured but never run.
- **What is already written down.** `CLAUDE.md`, existing `.claude/rules/`,
  `CONTRIBUTING.md`, `CODING_STANDARDS.md`, style notes under `docs/`.
- **What the code actually does.** For each language read several real
  files, including tests: the largest, the most recently changed, and one
  typical small one. When the project has fewer than about 30 source files,
  read all of them. Look for places where more than one way is valid and
  the project keeps to one: error handling, naming, file and package layout,
  where tests live and how they are named, logging, configuration,
  dependency choices, how public API is documented.

Note where the code is inconsistent with itself. Those are questions for
step 3, not rules.

## 2. Decide what counts as a rule

A line earns its place only when all of these hold:

- **It is a choice.** Several ways are valid and this project takes one.
  "Handle errors" is not a rule. "Wrap errors with `%w` and the operation
  name; never log and return the same error" is.
- **No tool covers it.** If a configured formatter, linter or type checker
  would fail on it, leave it out. This holds for a tool that is configured
  but never run too: the fix there is to run the tool, not to repeat its
  rules.
- **A capable model would not do it anyway.** General good practice and
  textbook idiom stay out. The file holds what cannot be guessed.
- **A reviewer can check it** against a diff.

Aim for 5 to 15 rules per language and keep each file to 40 lines at most.
A short file that is followed beats a long one that is skimmed. Put the
reason after a rule when it is not obvious, in a few words.

## 3. Ask about the open decisions

Ask one round of numbered questions, only about decisions: an inconsistency
found in step 1, or a gap in a place where the choice matters. Give a
recommended answer with each and word the question so that "yes" accepts
it. Take the recommendation from the first of these that settles it:

1. what a document or a code comment in the repository already says;
2. what the other side depends on, when two parts must agree (the caller of
   an API, the reader of a file format);
3. what most of the code does;
4. what the newest code does.

Do not ask for facts that the repository can answer.

If nobody can answer, for example in a scheduled or headless run, take the
recommended answers and list them under "Assumed" in the summary. When the
sources disagree with equal weight, or none applies, write no rule and list
the question under "Open". A question whose answer is "no rule is needed"
is not reported.

## 4. Write the files

One file per language or framework, named after it in lower case.

```markdown
---
paths:
  - "**/*.go"
---

# Go

Enforced by tooling, not repeated here: gofmt, go vet (`make test`).
Configured, but nothing runs it: golangci-lint (`.golangci.yml`).

## Errors
- Wrap with `fmt.Errorf("<operation>: %w", err)`; the caller logs, once.

## Tests
- Table-driven, in the same package, file `<name>_test.go` next to the code.
```

The example shows the format only; the rules come from this project. The
first line names the tools that something runs. The second line appears only
when a tool is configured but never run, so that a reader of the file does
not take its checks for granted.

- `paths` is a YAML list of quoted globs, one entry per extension, and only
  for extensions the repository has now (`"**/*.ts"`, and `"**/*.tsx"` once
  there is a `.tsx` file). A language file uses `**/*.<ext>` also when the
  language lives in one folder today. Scope a framework file to its folders
  (`"backend/**/*.py"`), not to the whole language.
- `general.md` has no frontmatter. It holds coding rules that cross
  languages: a contract two parts share, a unit or naming scheme used
  everywhere. Project instructions that `CLAUDE.md` already gives (how to
  run tests, what never to commit) stay in `CLAUDE.md` and are not repeated.
  When there is no cross-language rule, do not create the file.
- Group rules under short headings. One rule per line, imperative, concrete,
  with an identifier, path or example from this project where it helps.

When a rule file already exists, change it in place: keep the rules a person
wrote, add what is missing, and remove a rule only when the code or the user
contradicts it. Say what changed.

A rule lives in one place. Move a rule about one language out of
`CLAUDE.md` into that language's file, and leave everything else in
`CLAUDE.md` as it is.

Do not change source code in this run, also where it breaks a new rule.

## 5. Check

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/check_rules.py"
```

It reports a rule file whose frontmatter does not parse or has a key other
than `paths`, a file whose globs match nothing in the repository, a file
with no rules written as list items, and a file over 40 lines. Fix what it
reports.

## 6. Summarise

Tell the user, briefly:

- which rule files were written or changed, with the number of rules in
  each, and every line moved out of `CLAUDE.md` or another document;
- what was left out because tooling covers it, and which of those tools are
  configured but never run;
- "Assumed" and "Open" from step 3;
- existing code that does not follow the new rules yet, as `file:line` with
  the rule it breaks, and any real defect found on the way, marked as a bug;
- that `/memory` in Claude Code shows which rule files a session has loaded.

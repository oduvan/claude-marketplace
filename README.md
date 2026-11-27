# lyabah Claude Code marketplace

Claude Code plugins for the lyabah projects, and a reviewed set of community
skills in six more plugins: `workflow`, `go`, `web`, `threejs`, `game-design`
and `docker`.

## Install

In Claude Code:

```
/plugin marketplace add oduvan/claude-marketplace
/plugin install lyabah-docs@lyabah
```

Or from a terminal:

```bash
claude plugin marketplace add oduvan/claude-marketplace
claude plugin install lyabah-docs@lyabah
```

The other plugins install the same way, for example `workflow@lyabah` or
`go@lyabah`. A plugin holds skills that a project turns on together, so each
project installs only the ones it needs.

## lyabah-docs

[lyabah-service](https://service.lyabah.com/help.md) copies the `docs/` folder
of each repository. Agents read two kinds of files from there. This plugin has
one skill for each, and one for building the endpoints those articles describe.

| Skill | The file | What the skill makes sure of |
|---|---|---|
| `db-schema-doc` | `docs/db_schema.md` and `docs/db_schema/*.md` | `db_schema.md` is a small map, read together with every other repository's: what the service is, its database, and one line per article. The articles in `docs/db_schema/` explain what each topic's data means, where queries go wrong, and give queries to copy. Data is changed through the API (`find_api_endpoints`), not SQL. They leave out what `describe_database` already shows (column types, nullability, indexes). They are updated in the same commit as each migration, together with the `writes` lists of the API docs that name what the migration changed. |
| `api-endpoint` | The endpoint itself, in any language | The endpoint checks `Authorization: Bearer <LYABAH_KEY>`: an unset key gets 503, and a missing or wrong one gets 401. It has `GET /api/ping`, and answers every error as `{"error": …}`. An action that needs approval takes `draft`: a draft does all the work in one transaction, rolls it back and answers as the real call would, with `X-Draft-Checksum`. The real call answers `412` and applies nothing when the checksum no longer matches. There are tested examples in Go (net/http, pgx) and Python (FastAPI, psycopg). |
| `api-doc` | `docs/api/<name>.yaml.md` | The article is about one subject of the API: one call, or several named actions over shared parameters and a shared `base`; a call names its action. Values put parameters where they go with `{$param: name}` and `{$name}`. Each action says whether it needs approval (`approve_required`), so reads can go through `call_api` at once. `writes` lists the fields the article is about changing, so `find_api_endpoints` and `describe_database` can find it. The Markdown says what the calls change, how to turn a request into an action and its parameters, and how to explain every answer to the person. |

The skills start on their own when an agent writes or changes one of these
files, or adds a migration. You can also ask for them by name, for example
"use api-doc to describe POST /api/posts".

## Reviewed community skills

These skills come from other repositories. Each one is a full copy taken at a
fixed commit, after reading it. Nothing here updates on its own.

### workflow

| Skill | Source | What it does |
|---|---|---|
| `diagnosing-bugs` | mattpocock/skills | Builds a fast pass/fail check for the bug first, then looks for the cause. |
| `verification-before-completion` | obra/superpowers | No "done" without running the check and showing its output. |
| `tdd` | mattpocock/skills | Red, then green, with tests at agreed public interfaces. |
| `grilling` | mattpocock/skills | Asks questions in rounds, each with a suggested answer, before building. |
| `brainstorming` | obra/superpowers | Finds out what the person wants and why, agrees on an approach, and writes a design doc before anything is built. |
| `writing-plans` | obra/superpowers | Turns a design or spec into a plan of small tasks, each with its files, interfaces and tests. |
| `code-review` | mattpocock/skills | Reviews a diff twice: against the repo's standards and against the spec. |
| `code-simplification` | addyosmani/agent-skills | Makes code simpler without changing what it does. |
| `security-and-hardening` | addyosmani/agent-skills | Threat model and checklist for web services. |
| `git-guardrails-claude-code` | mattpocock/skills | Sets up a hook that blocks force push, `reset --hard`, `clean` and `branch -D`. |
| `setup-standards` | this repository | Writes the project's coding standards as one rule file per language in `.claude/rules/`. `code-review` checks against them. |
| `pull-request` | this repository | Branch names, pull request titles and descriptions, and merging, the way this owner does them. |

### go

| Skill | Source | What it does |
|---|---|---|
| `go` | spf13/go-skills | Idiomatic Go. Reads the `go` version in `go.mod` before it suggests a feature. |

### web

| Skill | Source | What it does |
|---|---|---|
| `frontend-design` | anthropics/skills | Pages with their own look, not a template. |
| `webapp-testing` | anthropics/skills | Playwright tests against a local web app. |

### threejs

| Skill | Source | What it does |
|---|---|---|
| `threejs-scene-setup` | gamedev-skills/awesome-gamedev-agent-skills | Scene, camera, renderer, render loop and resize in three.js. |
| `threejs-gltf-loading` | gamedev-skills/awesome-gamedev-agent-skills | Loads glTF/GLB models and plays their animations. |
| `threejs-materials-lighting` | gamedev-skills/awesome-gamedev-agent-skills | Materials, lights, shadows and environment lighting. |

### game-design

| Skill | Source | What it does |
|---|---|---|
| `game-feel` | gamedev-skills/awesome-gamedev-agent-skills | Screen shake, hit-stop, easing, squash and stretch. |
| `game-ui-ux` | gamedev-skills/awesome-gamedev-agent-skills | HUDs and menus that scale, with safe areas for phones. |

### docker

| Skill | Source | What it does |
|---|---|---|
| `docker-patterns` | affaan-m/ECC | Dockerfiles and Compose: networks, volumes, security, debugging. |

### Where each copy came from

[`upstream.json`](upstream.json) has two lists:

- `watch`: the repositories this marketplace follows, each with the last
  commit that was reviewed.
- `skills`: one entry per copied skill, with its source repository, path and
  commit, and every local change made to it.

A skill folder is the same as its source at that commit, apart from the
changes listed for it in `upstream.json`.

`upstream.json` also holds:

- `focus`: what this marketplace is for. A new upstream skill is suggested
  only when it fits.
- `declined`: skills that were looked at and not taken, with the reason, so
  they are not suggested again.
- `related`, on a skill: upstream skills that are not copied but cover the
  same ground. Their changes are read for ideas.
- `extra_paths`, on a skill: upstream files outside the skill's folder that
  the copy includes.

### Updates

The `marketplace-review` skill in `.claude/skills/` is the periodic review. It
runs inside this repository, on the machine where the owner works:

```
/marketplace-review days=7
/marketplace-review since=2026-11-01 until=2026-11-15
/marketplace-review
```

With no arguments the period is "since the last review". Each run reads two
things:

- **The watched repositories:** what they changed in the period.
- **The Claude Code sessions on this machine:** which skills were used and
  how each use went. It also reads the pipeline run summaries on Lyabah
  Service when that connector is available.

It writes `reviews/YYYY-MM-DD.md` and opens a pull request with it:

- updates to copied skills, each marked Take, Adapt or Skip with the reason;
- ideas from related skills, and new upstream skills that fit `focus`;
- how often each skill was used and how it went;
- edits the skills here need, as exact text;
- new skills, rules or hooks worth building, from work that was repeated.

The report in this public repository names skills and kinds of work only. It
holds no project names, file paths, code or prompts. The details that name
projects go to `~/.claude/marketplace-review/` on the owner's machine.

The run changes no skill. It moves `watch[].commit` to the commits it read,
so merging the pull request marks the review as read. A skill's own `commit`
moves only when its update is taken, by hand, in a separate change.

### Licenses

The copied skills keep their own licenses. The license texts are in
[`THIRD_PARTY_LICENSES/`](THIRD_PARTY_LICENSES); the two skills from
anthropics/skills carry their own `LICENSE.txt`. The MIT license in `LICENSE`
covers the rest of this repository.

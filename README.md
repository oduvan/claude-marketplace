# lyabah Claude Code marketplace

Claude Code plugins for the lyabah projects.

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

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
one skill for each.

| Skill | The file | What the skill makes sure of |
|---|---|---|
| `db-schema-doc` | `docs/db_schema.md` | The doc explains what the data means and where queries go wrong. It leaves out what `describe_database` already shows (column types, nullability, indexes), and it is updated in the same commit as each migration. |
| `api-doc` | `docs/api/<name>.yaml.md` | The front matter declares every input the endpoint reads and passes lyabah-service's parser. A `draft` is declared only when the API really has a check-only mode. The Markdown says what the call changes, how to turn a request into parameters, and how to read every answer. |

The skills start on their own when an agent writes or changes one of these
files, or adds a migration. You can also ask for them by name, for example
"use api-doc to describe POST /api/posts".

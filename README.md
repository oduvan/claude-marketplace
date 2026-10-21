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
| `db-schema-doc` | `docs/db_schema.md` | The doc explains what the data means and where queries go wrong, and says that data is changed through the API (`find_api_endpoints`), not SQL. It leaves out what `describe_database` already shows (column types, nullability, indexes). It is updated in the same commit as each migration, together with the `writes` lists of the API docs that name what the migration changed. |
| `api-doc` | `docs/api/<name>.yaml.md` | The article is about one subject of the API: one call, or several named actions over shared parameters and a shared `base`; a call names its action. Values put parameters where they go with `{$param: name}` and `{$name}`. Each action says whether it needs approval (`approve_required`), so reads can go through `call_api` at once. `writes` lists the fields the article is about changing, so `find_api_endpoints` and `describe_database` can find it. The Markdown says what the calls change, how to turn a request into an action and its parameters, and how to explain every answer to the person. |

The skills start on their own when an agent writes or changes one of these
files, or adds a migration. You can also ask for them by name, for example
"use api-doc to describe POST /api/posts".

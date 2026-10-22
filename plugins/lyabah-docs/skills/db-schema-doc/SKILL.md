---
name: db-schema-doc
description: Use when writing, reviewing or updating a repository's docs/db_schema.md or the articles under docs/db_schema/, or when a change adds, renames or drops a table or column (a database migration) in a repository whose database lyabah-service's SQL tools read (query_database, describe_database).
---

# Writing docs/db_schema.md and docs/db_schema/

## What the files are for

lyabah-service copies each repository's `docs/` folder. An agent with a
question about data first reads **every** repository's `docs/db_schema.md`
at once (`read_doc` with the path `db_schema.md` and no repo). From those it
decides which service holds the answer. Then it reads only the articles it
needs, and only then writes SQL with `query_database`.

So the schema docs come in two layers:

- **`docs/db_schema.md` is a map.** It is small: what the service is, which
  database it uses, and a link to each article with one line on what is
  there. It holds no tables, columns or queries. Many maps are read
  together, so every word in one costs every agent that asks anything.
- **`docs/db_schema/<topic>.md` are the articles.** Each covers one topic
  (e.g. orders, readers): its tables, what the data means, the traps, and
  queries to copy. An agent reads only the ones its question needs.

`describe_database` already shows every table's columns, types,
nullability, constraints, indexes and foreign keys. So the articles hold
only what the database cannot tell: what the data **means**, and the traps
that make a query give a wrong answer.

## The map: docs/db_schema.md

Exactly these parts, and nothing else. Keep it under 150 words.

1. **`# <repo>: database`**, then one or two sentences: what the service is
   and does, for someone who has never heard of it. Then the database's name
   on the shared Postgres, in backticks, e.g. `lyabah_news`.
2. **`## Articles`**: one bullet per article,
   `- [<Topic>](db_schema/<topic>.md): <tables> - <the questions it answers>.`
   Name the tables, and say what someone would come to ask in their words
   ("what is watched, what failed"), so an agent can pick the article from
   the map alone. The first bullet is always
   `[Before you query](db_schema/before-you-query.md)`.
3. **One line on changing data**: through the repository's API, never SQL
   (`find_api_endpoints` with `<database>.<table>.<column>`). If the
   repository has no `docs/api/`, say that its data cannot be changed
   through lyabah-service.

## The articles: docs/db_schema/<topic>.md

**`before-you-query.md`** always exists. It lists in short bullets the rules
that apply across topics: empty text stored as `''` instead of NULL, time
zones and units, soft deletes or expiry that every query must filter on,
very large columns not to select with `*`, links between tables that are not
foreign keys, columns that hold secrets or hashes. If there are none, say so
in one line.

**One article per topic.** Group tables the way questions come: what a
person asks together goes together. A small database may have one topic
article. Each article has these parts:

1. **`# <repo>: <topic>`**, then one line linking back:
   `Part of [the database map](../db_schema.md); read [Before you query](before-you-query.md) first.`
2. **One paragraph per table**: start with **`table_name`**, then say what one
   row is. Then a bullet only for each column whose meaning is not obvious
   from its name: allowed values and what each means, status flows, how a
   value is derived, what NULL or `''` means here, when it changes, and the
   API's name for it when that differs from the column's. A table whose
   columns all mean what their names say gets its one sentence.
3. **How this data changes**: the API article that writes it, as a link
   (`[resources](../api/resources.yaml.md)`), or "only the service itself
   writes it", or "nothing through lyabah-service".
4. **`## Useful questions`**: two to six queries in one `sql` block, each
   with a `--` comment saying the question it answers. Agents read data only
   this way: no API article has an action that just returns rows (see the
   `api-doc` skill, "Which calls get an action"). So when the API has a plain
   read for this topic, such as a list or a get by id, give the query that
   answers the same question, with the columns that read returned. Mark the
   long columns, to be selected only when needed. Run each query before you
   keep it: with `query_database` if the MCP tools are connected, otherwise
   against a throwaway Postgres built from the repository's migrations.

Every table that is used is in exactly one article. A table the code creates
outside the migrations (such as a migration runner's `schema_migrations`)
gets one sentence in the article it fits best.

## How to write them

1. Find the database's name: the service's `DB_NAME` (often the service name
   with `-` changed to `_`). Read every migration, then the code that writes
   each table: the meaning lives there, not in the SQL.
2. If the MCP tools are connected, call `describe_database` on the database
   and check that every table you describe exists, and that you missed none
   that is still used.
3. Choose the topics, write the articles, then write the map from them.
4. When an older `docs/db_schema.md` holds everything in one file, split it:
   keep every fact and query, move each to its article, and cut the map down
   to its three parts. Fix every link to the old sections, in `docs/api/`
   articles too.
5. In a new repository, the database must also be listed in lyabah-service's
   `internal/registry/registry.yaml`, and the repository needs its docs
   webhook (see lyabah-service's help, "Repository docs"). Say so to the user
   if either is missing; do not change lyabah-service yourself.

## When a migration changes the schema

Update the article of each table the migration adds, changes or drops, in
the same commit as the migration. A dropped table leaves its article. A new
topic gets a new article and a line in the map; otherwise the map changes
only when the tables an article covers, or the questions it answers, change.

In the same commit, fix the `writes` lists in `docs/api/*.yaml.md` that name
what the migration renames or drops (search them for `<database>.<table>`),
and add the new columns to the `writes` of the articles whose calls set
them. Use the `api-doc` skill for those files. Run every example query again
on the new schema.

## Check before you finish

- The map has its three parts, no tables, columns or queries, and is under
  150 words.
- Every link in the map and the articles opens a file that exists.
- Every table that exists and is used is in exactly one article; none that
  is dropped.
- No column is listed only to give its type or its nullability.
- No migration number or date is quoted as "the doc's version": git keeps that.
- Every example query ran.
- No `docs/api/*.yaml.md` `writes` names a table or column that is gone.

An example of both layers: `reference/example/db_schema.md` and the articles
in `reference/example/db_schema/`.

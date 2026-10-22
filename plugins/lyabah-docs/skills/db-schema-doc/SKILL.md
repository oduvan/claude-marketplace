---
name: db-schema-doc
description: Use when writing, reviewing or updating a repository's docs/db_schema.md, or when a change adds, renames or drops a table or column (a database migration) in a repository whose database lyabah-service's SQL tools read (query_database, describe_database).
---

# Writing docs/db_schema.md

## What the file is for

lyabah-service copies each repository's `docs/` folder. Before an agent writes
SQL with `query_database`, it reads `docs/db_schema.md`. The agent also has
`describe_database`, which already shows every table's columns, types,
nullability, constraints, indexes and foreign keys.

So the doc holds only what the database cannot tell: what the data **means**,
and the traps that make a query give a wrong answer.

## The shape of the doc

Write the doc in exactly these parts, in this order:

1. **Title and one paragraph.** `# <repo>: database schema`. Then: the
   database's name on the shared Postgres (in backticks, e.g. `lyabah_news`),
   what the service is, and that the migrations in `<path>` create it.
2. **`## Before you write a query`.** Short bullets with the rules that apply
   to many tables: empty text stored as `''` instead of NULL, time zones and
   units, soft deletes or expiry that every query must filter on, very large
   columns not to select with `*`, links between tables that are not foreign
   keys, columns that hold secrets or hashes. End with how data is
   changed: through the repository's API calls, never SQL, found with
   `find_api_endpoints` by the column or table (`<database>.<table>.<column>`);
   `describe_database` on a table lists them too. When the repository has no
   `docs/api/` yet, say that its data cannot be changed through lyabah-service.
3. **One `##` section per topic** (e.g. "Articles", "Readers"). In it, one
   paragraph per table: start with **`table_name`**, then say what one row is.
   Then a bullet only for each column whose meaning is not obvious from its
   name: allowed values and what each means, status flows, how a value is
   derived, what NULL or `''` means here, when it changes, and the API's
   name for it when that differs from the column's. A table whose columns all
   mean what their names say gets its one sentence and nothing more.
4. **`## Useful questions`.** Two to five example queries in one `sql` block,
   each with a `--` comment saying the question it answers. Agents read data
   only this way: no API article has an action that just returns rows (see
   the `api-doc` skill, "Which calls get an action"). So when the API has a
   plain read, such as a list or a get by id, give the query that answers
   the same question, with the columns that read returned. Mark the long
   columns, which should be selected only when needed. Run each one
   before you keep it: with `query_database` if the MCP tools are connected,
   otherwise against a throwaway Postgres built from the repository's
   migrations.

Keep the doc short: a few lines per table. A 20-table database fits in about
1,000 words of prose, not counting the SQL block.

## How to write it

1. Find the database's name: the service's `DB_NAME` (often the service name
   with `-` changed to `_`). Read every migration, then the code that writes
   each table: the meaning lives there, not in the SQL. A table the code
   creates outside the migrations (such as a migration runner's
   `schema_migrations`) gets one sentence.
2. If the MCP tools are connected, call `describe_database` on the database
   and check that every table you describe exists, and that you missed none
   that is still used.
3. Write the doc in the shape above.
4. In a new repository, the database must also be listed in lyabah-service's
   `internal/registry/registry.yaml`, and the repository needs its docs
   webhook (see lyabah-service's help, "Repository docs"). Say so to the user
   if either is missing; do not change lyabah-service yourself.

## When a migration changes the schema

Update the doc in the same commit as the migration: the paragraph of each
table the migration adds, changes or drops. A dropped table leaves the doc.

In the same commit, fix the `writes` lists in `docs/api/*.yaml.md` that name
what the migration renames or drops (search them for `<database>.<table>`),
and add the new columns to the `writes` of the articles whose calls set
them. Use the `api-doc` skill for those files. Run every example query again on the new
schema.

## Check before you finish

- Every table that exists and is used is described; none that is dropped.
- No column is listed only to give its type or its nullability.
- No migration number or date is quoted as "the doc's version": git keeps that.
- Every example query ran.
- No `docs/api/*.yaml.md` `writes` names a table or column that is gone.

A good example of the shape: `reference/example.md`.

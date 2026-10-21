---
name: api-doc
description: Use when writing, reviewing or updating a docs/api/<name>.yaml.md file, or when an agent should be able to call one of a repository's HTTP endpoints through lyabah-service (prepare_api_call, find_api_endpoints), or when an endpoint that already has such a file changes its path, parameters, answers or the data it writes.
---

# Writing docs/api/<name>.yaml.md

## What the file is for

lyabah-service copies each repository's `docs/` folder. One file
`docs/api/<name>.yaml.md` describes one endpoint. An agent reads it, then calls
`prepare_api_call` with parameters; the service builds the request from the
file, a person reviews it, and only then is it sent.

The file has two parts, and both must be complete:

- **YAML front matter** between two `---` lines. The service parses it
  strictly: an unknown key, an undeclared parameter or a wrong type makes the
  endpoint unusable. The full rules are in `reference/format.md`. Read it
  before you write the front matter.
- **Markdown** for the agent that prepares calls. It is the only explanation
  that agent gets.

The endpoint's name is the path under `docs/api/` without `.yaml.md`:
`docs/api/resources/create.yaml.md` is `resources/create`. Use
`<thing>/<action>` names, one file per endpoint.

## How to write it

1. **Read the handler,** not only the route: the type it decodes the body
   into, every field, the checks it makes (lengths, patterns, allowed values),
   whether it refuses unknown fields, every status code it answers with, and
   what it changes.
2. **Declare every input as a parameter** in `params`, with the server's own
   limits (`maxLength`, `pattern`, `enum`, `minimum`…) and a `description`
   that names the column it lands in when the names differ.
   Mark the ones the server needs `required: true`. Then map each parameter
   into `path`, `query`, `headers` or `body` with a quoted template,
   `"{{name}}"`. A rule the schema cannot hold, such as "send at least one of
   these", goes in the Markdown.
3. **Leave authentication out.** The lyabah-service registry sets the
   `Authorization` header and the base URL. The file never names a secret.
4. **List what it writes** in `writes`, with the rule below.
5. **Decide on `draft`** with the rule below.
6. **Write the `summary` and the Markdown** in the shape below.
7. **Check** with the list at the end.

## The writes rule

Agents find an endpoint with `find_api_endpoints` by the column or table it
changes, and `describe_database` shows a table's endpoints. Both read
`writes`, so every endpoint that changes data has it:

```yaml
writes:
  updates: [lyabah_news.resources.url, lyabah_news.resources.pending]  # database.table.column
  creates: [lyabah_news.applied_changes]                               # database.table
  deletes: [lyabah_news.resources]
```

Follow the handler down to every SQL statement it runs, helpers included:

- every column an `UPDATE` sets, including the ones set as a side effect
  (a cleared `pending`, an `updated_at`);
- every table it `INSERT`s into (`creates`), and every table it deletes rows
  from (`deletes`), including tables whose rows go with them through
  `ON DELETE CASCADE`.

Use the database's name on the shared Postgres, as `docs/db_schema.md` gives
it (or the service's `DB_NAME` when there is no such doc yet), and the
tables' and columns' real names. Leave out only counters and logs that record
the call itself (daily stats, audit rows). A row that other parts of the
service read later, such as a cache or a list of known hosts, is data: list
it. An endpoint that changes data but no database gets `writes: {}`. A `GET`
has no `writes`.

## The draft rule

Add `draft` only if the same endpoint has a mode that checks the call and
changes nothing (e.g. a `dry_run=1` query parameter), **and** that mode
accepts exactly the same input. Draft calls are sent to the real API while
the call is prepared, before anyone reviews it, and a call whose draft fails
is not kept.

A different endpoint that looks like a preview is not a draft when it decodes
a different type: if it refuses unknown fields, every full call would fail its
draft. Without `draft`, preparing a call only checks the parameters. Say which
case it is in the Markdown.

## The shape of the summary and the Markdown

`find_api_endpoints` also searches the words of the endpoint's name, its
`summary` and its Markdown. Write the `summary` as one line in the words a
request would use ("Stop watching a feed or page"), not the handler's name.

1. `# <What the call does>`, then a paragraph: what the call changes, what is
   kept, whether it can be undone, and what happens right after it is sent.
2. `## Turning a request into parameters`: bullets that map typical requests
   ("follow this blog") to parameter values, and say what this endpoint cannot
   do and which one to use instead.
3. `## Reading the answer`: how to treat the response and explain it to the
   person who asked. The agent passes this on to them, and records it with
   `interpret_api_result`, so write it for that:
   - The success status, and a short JSON example of the body, copied from
     what the handler really writes.
   - A list of the fields that matter: what each one means, in which units,
     and how to say it in plain words ("`changed_at` is when the page's text
     last changed, not when it was checked"). Say which field shows that the
     call did what was asked, and which ones the person should hear about.
   - Every other status the handler can return (400, 401, 404, 409, 413,
     422, 500…), each with what it means for the person ("no resource has this
     id: it may have been deleted already") and what to do next: fix the
     parameters and prepare again, read the data first, or tell the owner.
   - What a body that is not JSON, or is empty, means, if the endpoint can
     send one.

## Check before you finish

- Every field the handler reads is a parameter; no parameter is unused.
- Every template is quoted; every path parameter is required or has a default.
- `writes` follows the writes rule, and each name in it exists in the
  repository's migrations.
- No `Authorization`, `Cookie` or `Content-Type` header (the body's type is
  `content_type`).
- `draft` follows the draft rule.
- The Markdown has the three parts, its JSON matches what the handler
  writes, and every status the handler can return is explained.
- After the file is merged and synced:
  - `find_api_endpoints` with one of its `writes` names finds it, and its
    `problems` do not name it;
  - prepare one call with real-looking parameters in a group named
    `doc-check-<name>`, read back the request it built (`get_api_group`), then
    `discard_api_call` it. If the service says the file "cannot be used", fix
    what the message names.

A full example: `reference/example.yaml.md`.

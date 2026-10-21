---
name: api-doc
description: Use when writing, reviewing or updating a docs/api/<name>.yaml.md article, or when an agent should be able to call one of a repository's HTTP endpoints through lyabah-service (find_api_endpoints, call_api, prepare_api_call), or when an endpoint that already has an article changes its path, parameters, answers or the data it writes.
---

# Writing docs/api/<name>.yaml.md articles

## What the file is for

lyabah-service copies each repository's `docs/` folder. A file
`docs/api/<name>.yaml.md` is an **article** about one subject of the API, for
example the watched resources. An agent finds it with `find_api_endpoints`,
reads it, picks the action that fits and calls it: at once with `call_api`
when the action needs no approval, otherwise with `prepare_api_call`, which a
person approves before anything is sent.

The file has two parts, and both must be complete:

- **YAML front matter** between two `---` lines. The service parses it
  strictly: an unknown field, an unused parameter or an old-style template
  makes the article unusable. The full rules are in `reference/format.md`.
  Read it before you write the front matter.
- **Markdown** for the agent that calls it. It is the only explanation that
  agent gets.

The article's name is the path under `docs/api/` without `.yaml.md`:
`docs/api/resources.yaml.md` is `resources`.

## One call or several actions

- Several endpoints on the same subject that share parameters and
  explanation (create, update, delete a resource) go in **one article**,
  under `actions`. Shared parts go in `actions.base`; `default` is the action
  a call gets when it names none.
- A lone endpoint keeps its own **simple article**: its `method`, `path` and
  the rest sit at the top, next to `params`.

## How to write it

1. **Read each handler,** not only the route: the type it decodes the body
   into, every field, the checks it makes (lengths, patterns, allowed values),
   whether it refuses unknown fields, every status code it answers with, and
   what it changes.
2. **Declare every input once** in the article's `params`, with the server's
   own limits (`maxLength`, `pattern`, `enum`, `minimum`…) and a `description`
   that names the column it lands in when the names differ.
3. **Write each call:** `method`, `path` (`{$id}` for a path segment),
   `required` (the params this call needs), and `query`, `headers` and `body`
   with `{$param: name}` where a parameter goes and constants as they are. A
   rule the schema cannot hold, such as "send at least one of these", goes in
   the Markdown.
4. **Leave authentication out.** The lyabah-service registry sets the
   `Authorization` header and the base URL. The file never names a secret.
5. **Set `approve_required`** with the rule below.
6. **Decide on `draft`** with the rule below.
7. **List what it writes** in `writes`, with the rule below.
8. **Write the `summary` and the Markdown** in the shape below.
9. **Check** with the list at the end.

## The approve_required rule

A call needs a person's approval unless it says `approve_required: false`.
The default is `true`, and `false` for `GET`. Set it on each action, never in
`base`:

- `false` only for a call that changes nothing: a read, a preview, a check.
  Then agents can `call_api` it and get the answer at once.
- `true` on a `GET` that does change something (it marks a message read, it
  starts a job). Never leave such a `GET` on its default.

## The draft rule

Add `draft` only if the same endpoint has a mode that checks the call and
changes nothing (e.g. a `dry_run=1` query parameter), **and** that mode
accepts exactly the same input. Draft calls are sent to the real API while
the call is prepared, before anyone reviews it, and a call whose draft fails
is not kept.

A different endpoint that looks like a preview is not a draft when it decodes
a different type: if it refuses unknown fields, every full call would fail its
draft. Make it an action of its own instead, often with
`approve_required: false`.

## The writes rule

`writes` lists the fields the article is about changing, as
`database.table.field`. `find_api_endpoints` and `describe_database` use it to
send an agent who wants to change a field to this article. Follow each
handler down to every SQL statement it runs, helpers included, and list every
column it sets: the ones a request names and the ones set as a side effect (a
cleared `pending`, an `updated_at`). Columns only the database fills (`id`, a
`created_at` default) are not listed, and a `DELETE` adds no fields of its
own: the fields of the rows it removes are already listed by the calls that
set them.

Use the database's name on the shared Postgres, as `docs/db_schema.md` gives
it (or the service's `DB_NAME` when there is no such doc yet), and the real
table and column names. Leave out only counters and logs that record the call
itself (daily stats, audit rows); a row that other parts of the service read
later, such as a cache, is data. An article that changes no database has no
`writes`.

## The shape of the summary and the Markdown

`find_api_endpoints` searches the words of the article's name, its `summary`,
its action names and its Markdown. Write the `summary` as one line in the
words a request would use ("Watched pages and feeds - start, change or stop
watching one").

1. `# <The subject>`, then a paragraph: what the calls change, what is kept,
   whether a change can be undone, and what happens right after a call.
2. Only when an action's name does not say enough (a side effect, an order to
   call them in), a line about that action. Names like `update` or `delete`
   need none.
3. `## Turning a request into parameters`: bullets that map typical requests
   ("follow this blog") to an action and its parameter values, and say what
   the article cannot do and where to go instead.
4. `## Reading the answer`: how to treat each response and explain it to the
   person who asked. The agent passes this on to them, and records it with
   `interpret_api_result`, so write it for that:
   - The success status of each action, and a short JSON example of the body,
     copied from what the handler really writes.
   - A list of the fields that matter: what each one means, in which units,
     and how to say it in plain words ("`changed_at` is when the page's text
     last changed, not when it was checked"). Say which field shows that the
     call did what was asked, and which ones the person should hear about.
   - Every other status the handlers can return (400, 401, 404, 409, 413,
     422, 500…), each with what it means for the person ("no resource has this
     id: it may have been deleted already") and what to do next: fix the
     parameters and call again, read the data first, or tell the owner.
   - What a body that is not JSON, or is empty, means, if an endpoint can
     send one.

## Check before you finish

- Every field a handler reads is a parameter of its action; every parameter
  is used by some call.
- Every placeholder is `{$param: name}` or `{$name}`; no `{{name}}` is left.
- Every path parameter is in that call's `required`, or has a default.
- `approve_required`, `draft` and `writes` follow their rules.
- No `Authorization`, `Cookie` or `Content-Type` header (the body's type is
  `content_type`).
- The Markdown has its parts, its JSON matches what the handlers write, and
  every status the handlers can return is explained.
- Check the file with lyabah-service, not a generic YAML tool: a YAML parser
  reads `$param` as plain data and knows none of the rules. After the file is
  merged and synced:
  - `find_api_endpoints` with one of its `writes` finds it, and its `problems`
    do not name it;
  - an action with `approve_required: false`: `call_api` it once with real
    parameters and check the answer against the Markdown;
  - every other action: prepare one call in a group named `doc-check-<name>`,
    read back the request it built (`get_api_group`), then `discard_api_call`
    it.

A full example: `reference/example.yaml.md`.

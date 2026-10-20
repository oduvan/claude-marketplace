---
name: api-doc
description: Use when writing, reviewing or updating a docs/api/<name>.yaml.md file, or when an agent should be able to call one of a repository's HTTP endpoints through lyabah-service (prepare_api_call), or when an endpoint that already has such a file changes its path, parameters or answers.
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
   limits (`maxLength`, `pattern`, `enum`, `minimum`…) and a `description`.
   Mark the ones the server needs `required: true`. Then map each parameter
   into `path`, `query`, `headers` or `body` with a quoted template,
   `"{{name}}"`.
3. **Leave authentication out.** The lyabah-service registry sets the
   `Authorization` header and the base URL. The file never names a secret.
4. **Decide on `draft`** with the rule below.
5. **Write the Markdown** in the shape below.
6. **Check** with the list at the end.

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

## The shape of the Markdown

1. `# <What the call does>`, then a paragraph: what the call changes, what is
   kept, whether it can be undone, and what happens right after it is sent.
2. `## Turning a request into parameters`: bullets that map typical requests
   ("follow this blog") to parameter values, and say what this endpoint cannot
   do and which one to use instead.
3. `## Reading the answer`: the success status with a short JSON example, what
   to check in it, then each error status the handler can return with what it
   means and what to do.

## Check before you finish

- Every field the handler reads is a parameter; no parameter is unused.
- Every template is quoted; every path parameter is required or has a default.
- No `Authorization`, `Cookie` or `Content-Type` header (the body's type is
  `content_type`).
- `draft` follows the draft rule.
- The Markdown has the three parts, and its JSON matches what the handler
  writes.
- After the file is merged and synced, prepare one call with real-looking
  parameters in a group named `doc-check-<name>`, read back the request it
  built (`get_api_group`), then `discard_api_call` it. If the service says the
  file "cannot be used", fix what the message names.

A full example: `reference/example.yaml.md`.

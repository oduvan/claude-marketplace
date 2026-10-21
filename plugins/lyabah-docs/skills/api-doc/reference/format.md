# The front matter of docs/api/<name>.yaml.md

These are the rules lyabah-service's parser enforces. A file that breaks one is
refused when an agent calls it, and `find_api_endpoints` lists it under
`problems`, with the message naming what is wrong.

The file must start with a `---` line, then the YAML, then another `---` line
(`...` also closes it). Everything after is the Markdown.

## The article's fields

| Field | Meaning |
|---|---|
| `summary` | One line. When left out, the first paragraph of the Markdown is used. |
| `writes` | A list of `database.table.field`, in lowercase letters, digits and `_`. None listed twice. |
| `params` | One JSON Schema per parameter. Every parameter must be used by some call. |
| `actions` | The calls by name, when there is more than one. |

An article has either one call at the top level, its fields next to
`params`, or `actions`. A file with both is refused.

## A call's fields

| Field | Required | Meaning |
|---|---|---|
| `method` | yes | `GET`, `POST`, `PUT`, `PATCH` or `DELETE`. |
| `path` | yes | Starts with one `/`, goes after the API's base URL, and has no `?` or `#`: query parameters go under `query`. `{$name}` fills a path segment. |
| `required` | no | The parameters the call needs. Each must be one it uses. |
| `query` | no | The query string, as an object. A list value repeats the key. |
| `headers` | no | Extra headers, as an object. A value is one line. |
| `body` | no | Any JSON. An object or a list is sent as JSON; a string is sent as text. |
| `content_type` | no | `application/json` by default (`text/plain` for a string body). `application/x-www-form-urlencoded` sends an object body as a form. With any other type, a string body is sent as it is and an object or list as JSON, under that type. |
| `draft` | no | How to send the same call so that the API only checks it. See below. |
| `approve_required` | no | `true` by default, `false` by default for `GET`. |

An unknown field is an error, so a misspelt one does not pass unnoticed.
`summary`, `writes` and `params` inside an action are errors too: they belong
to the article.

## actions

- Names are lowercase letters, digits and `_`. `default` must be there.
- `base` holds what the other actions share. It is never called, and it may
  not set `approve_required`.
- Each other action starts from `base`: a field replaces `base`'s; `query`,
  `headers` and an object `body` are merged into `base`'s key by key, all the
  way down; `null` removes a field or a key.
- An action accepts only the parameters it uses. A call that passes another
  one is refused with the list of those it takes.

## params

- A parameter's name is letters, digits and `_`.
- Each one is a JSON Schema: `type`, `enum`, `pattern`, `minLength`,
  `maxLength`, `minimum`, `maximum`, `items`, `default`, `description`…
- `type` is one of `string`, `number`, `integer`, `boolean`, `array`,
  `object`, `null`. A misspelt type is an error.
- `required: true` is an error here: list the parameter in the call's
  `required`.
- `pattern` is Go's RE2 syntax (no lookahead or backreferences) and is not
  anchored: write `^…$` to match the whole value.
- `minLength` and `maxLength` count characters, not bytes. When the server
  limits bytes, use its number and say so in the `description`: text with
  non-Latin letters can pass the doc and still be refused.
- A `default` must itself match the schema.
- Numbers of 2^53 or more cannot be sent exactly: make such ids strings.

## Parameters in values

In `path`, `query`, `headers`, `body` and everything under `draft`:

- `{$param: name}` as a whole value becomes the parameter's value with its
  type: a number stays a number, a list a list, an object an object. It holds
  only the name; any other key next to `$param` is an error.
- Inside a string, `{$name}` writes the value out (`"Watching {$name}"`), and
  an object or list as JSON.
- `{{$name}}` inside a string is the plain text `{$name}`.
- `{$literal: value}` sends `value` exactly as written, even if it looks like
  a marker.
- A key or list item whose parameter was not given, and that has no default,
  is left out. An empty string, `0` or `false` counts as given and is sent.
- Every other value is sent as written: `{{x}}`, `$x` and `{x}` in a string
  included.
- `{{name}}` or a path's `{name}` naming a declared parameter is refused as
  the old form, with the new one in the message.
- Every parameter a value names must be declared in `params`.

These markers are plain YAML, so every YAML library reads them the same way.
Only lyabah-service knows what they mean: check an article with it.

## Headers

- Never `Authorization`, `Cookie`, `Host`, `Content-Length`, `Connection`,
  `Transfer-Encoding` or `Proxy-Authorization`: the service or the registry
  sets them.
- Never `Content-Type`: use `content_type`.
- Never a header the registry already sets for this API.
- Names are case-insensitive, so one name given twice in two cases is an
  error.

## draft

`draft` changes the call so that the API only checks it:

- `method` and `path`: another method or path.
- `query` and `headers`: added to the call's.
- `body`: fields merged into the call's body, which must then be an object.

A `draft` that changes nothing is an error. The service sends the draft while
the call is prepared, before anyone reviews it, and keeps the call only if the
draft answers with a 2xx status. `call_api` does not run drafts.

## Where the API lives

The base URL and the credentials come from lyabah-service's
`internal/registry/registry.yaml`, never from the API's own repository. A
repository whose API agents should call needs an `api:` entry there, and a
database named in `writes` must be one the registry lists for that
repository; tell the user if either is missing.

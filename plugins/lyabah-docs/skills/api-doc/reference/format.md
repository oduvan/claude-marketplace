# The front matter of docs/api/<name>.yaml.md

These are the rules lyabah-service's parser enforces. A file that breaks one is
refused when an agent prepares a call, with a message that names the problem.

The file must start with a `---` line, then the YAML, then another `---` line
(`...` also closes it). Everything after is the Markdown.

## Fields

An unknown field is an error, so a misspelt one does not pass unnoticed.

| Field | Required | Meaning |
|---|---|---|
| `method` | yes | `GET`, `POST`, `PUT`, `PATCH` or `DELETE`. |
| `path` | yes | Starts with one `/`, goes after the API's base URL, and has no `?` or `#`: query parameters go under `query`. `{{name}}` (or `{name}`, as OpenAPI writes it) fills a path segment. |
| `summary` | no | One line. When left out, the first paragraph of the Markdown is used. |
| `params` | no | One JSON Schema per parameter. Parameters not declared here are refused. |
| `query` | no | The query string, as a map. A list value repeats the key. |
| `headers` | no | Extra headers, as a map. A value is one line. |
| `body` | no | An object or a list is sent as JSON; a string is sent as text. |
| `content_type` | no | `application/json` by default (`text/plain` for a string body). `application/x-www-form-urlencoded` sends an object body as a form. With any other type, a string body is sent as it is and an object or list as JSON, under that type. |
| `draft` | no | How to send the same call so that the API only checks it. |

## params

- A parameter's name is letters, digits and `_`.
- Each one is a JSON Schema: `type`, `enum`, `pattern`, `minLength`,
  `maxLength`, `minimum`, `maximum`, `items`, `default`, `description`…
- `type` is one of `string`, `number`, `integer`, `boolean`, `array`,
  `object`, `null`. A misspelt type is an error.
- `required: true` marks a parameter that must be given. It is not part of
  JSON Schema; the service reads it and removes it.
- `pattern` is Go's RE2 syntax (no lookahead or backreferences) and is not
  anchored: write `^…$` to match the whole value.
- `minLength` and `maxLength` count characters, not bytes. When the server
  limits bytes, use its number and say so in the `description`: text with
  non-Latin letters can pass the doc and still be refused.
- A `default` must itself match the schema.
- Numbers of 2^53 or more cannot be sent exactly: make such ids strings.

## Templates

`path`, `query`, `headers`, `body` and everything under `draft` are templates.

- `"{{name}}"` as a whole value becomes the parameter's value with its type:
  a boolean stays a boolean, an object stays an object.
- Inside other text (`"/posts/{{slug}}/view"`, `"lang-{{lang}}"`), the value
  is written out, and an object or list as JSON.
- A key whose template names a parameter that was not given, and that has no
  default, is left out of the call. That is how optional fields work. An
  empty string, `0` or `false` counts as given and is sent, so an API that
  clears a field on `""` can be told to.
- Every parameter a template names must be declared in `params`.
- A path parameter must be `required: true` or have a `default`.
- **Quote every template.** YAML reads a bare `{{name}}` as a map, and the
  file is refused.

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
draft answers with a 2xx status.

## Where the API lives

The base URL and the credentials come from lyabah-service's
`internal/registry/registry.yaml`, never from the API's own repository. A
repository whose API agents should call needs an `api:` entry there; tell the
user if it is missing.

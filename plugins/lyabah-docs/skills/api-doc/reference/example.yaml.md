---
summary: The shop's posts - read one, replace its text, or publish and hide it.
writes:
  - lyabah_shop.posts.title_en
  - lyabah_shop.posts.title_uk
  - lyabah_shop.posts.html_en
  - lyabah_shop.posts.html_uk
  - lyabah_shop.posts.published
  - lyabah_shop.posts.updated_at
params:
  slug:
    type: string
    pattern: "^[a-z0-9-]{1,100}$"
    description: The post's slug, as in its URL, e.g. spring-sale.
  lang:
    type: string
    enum: [en, uk]
    default: en
    description: Which language's text to read or replace (title_en or title_uk, html_en or html_uk).
  title:
    type: string
    minLength: 1
    maxLength: 300
    description: The post's whole new title. One line.
  html:
    type: string
    maxLength: 500000
    description: The post's whole new HTML body.
  published:
    type: boolean
    description: true shows the post to readers, false hides it.
actions:
  base:
    path: /api/posts/{$slug}
    required:
      - slug
  replace:
    method: PUT
    required:
      - slug
      - title
      - html
    query:
      lang:
        $param: lang
    body:
      title:
        $param: title
      html:
        $param: html
      source: agent
    draft:
      query:
        dry_run: "1"
  get:
    method: GET
    query:
      lang:
        $param: lang
  publish:
    method: PATCH
    required:
      - slug
      - published
    body:
      published:
        $param: published
---

# The shop's posts

A post has a title and an HTML body in English and in Ukrainian. Replacing
the text of one language leaves the other as it is. The old text is kept in
the post's history, so the owner can bring it back on the site's admin page.

`replace` has a draft mode: with `dry_run=1` the site checks the
call (the post exists, the HTML is allowed) and changes nothing. Preparing a
call runs it. `get` changes nothing, so it can be called at once.

## Turning a request into parameters

- "Fix the typo in the spring sale post": `get` it first (`slug:
  spring-sale`), fix the text, then `replace` with the whole title
  and HTML: it replaces, it does not patch.
- "Translate it into Ukrainian": `replace` with `lang: uk` and the
  Ukrainian title and HTML.
- "Hide the spring sale post": `publish` with `published: false`.
- A new post is not made here: use the `posts/create` article.

## Reading the answer

`replace` and `publish` answer `200` with the post as it is now;
`get` answers the same for the language asked:

```json
{"slug": "spring-sale", "lang": "en", "title": "Spring sale", "html": "<p>…</p>", "published": true, "updated_at": "2026-10-20T10:00:00Z"}
```

- `title` and `html` are the text now. If they are what you sent, the change
  worked: tell the person the post's new title.
- `published`: `true` means readers see the post now, `false` that it is
  hidden. Mention it after `publish`, or when it is not what they would
  expect.
- `updated_at` is when the post last changed, in UTC. Give it in the person's
  time if you mention it.

Other answers:

- `400`: the HTML has a tag the site does not allow; the message names it.
  Tell the person which tag was refused, remove it and try again.
- `404`: no post has that slug. It may be misspelt, or deleted. Say so.
- `409`: someone changed the post after you read it, so nothing was saved.
  `get` it again, redo the change and prepare a new call.
- `401` or `500`: a problem on the site's side, not in the request. Tell the
  owner; do not retry in a loop.

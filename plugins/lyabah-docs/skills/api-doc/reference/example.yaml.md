---
summary: Replace a post's title and HTML, in one language.
method: PUT
path: /api/posts/{{slug}}
params:
  slug:
    type: string
    required: true
    pattern: "^[a-z0-9-]{1,100}$"
    description: The post's slug, as in its URL, e.g. spring-sale.
  lang:
    type: string
    enum: [en, uk]
    default: en
    description: Which language's text to replace.
  title:
    type: string
    required: true
    minLength: 1
    maxLength: 300
    description: The post's whole new title. One line.
  html:
    type: string
    required: true
    maxLength: 500000
    description: The post's whole new HTML body.
  publish:
    type: boolean
    description: true publishes the post, false hides it. Left as it is when not given.
query:
  lang: "{{lang}}"
body:
  title: "{{title}}"
  html: "{{html}}"
  published: "{{publish}}"
draft:
  query: {dry_run: "1"}
---

# Replace a post's text

Replaces the title and the HTML of one post in one language. The other
language's text stays as it is. The old text is kept in the post's history,
so the owner can bring it back on the site's admin page.

The API has a draft mode: with `dry_run=1` it checks the call (the post
exists, the HTML is allowed) and changes nothing. Preparing a call runs it.

## Turning a request into parameters

- "Fix the typo in the spring sale post" → `slug: spring-sale`. Read the post
  first (`GET /api/posts/spring-sale`), fix the text, and send the whole
  title and HTML back: this call replaces, it does not patch.
- "Translate it into Ukrainian" → `lang: uk`, with the Ukrainian title and
  HTML.
- Leave `publish` out unless the request is to publish or to hide the post.
- A new post is not made with this call: use `posts/create`.

## Reading the answer

`200` with the post as it is now:

```json
{"slug": "spring-sale", "lang": "en", "title": "Spring sale", "published": true, "updated_at": "2026-10-20T10:00:00Z"}
```

Check that `title` is the one you sent.

- `400`: the HTML has a tag the site does not allow; the message names it.
  Remove it and prepare the call again.
- `404`: no post has that slug. List posts with `GET /api/posts`.
- `409`: someone changed the post after you read it. Read it again and redo
  the change.

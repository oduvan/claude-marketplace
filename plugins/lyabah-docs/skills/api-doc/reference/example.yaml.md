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
writes:
  updates:
    - lyabah_shop.posts.title_en
    - lyabah_shop.posts.title_uk
    - lyabah_shop.posts.html_en
    - lyabah_shop.posts.html_uk
    - lyabah_shop.posts.published
    - lyabah_shop.posts.updated_at
  creates: [lyabah_shop.post_history]
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

- `title` is the title now. If it is the one you sent, the call worked: tell
  the person the post's new title.
- `published`: `true` means readers see the post now, `false` that it is
  hidden. Mention it when the request was to publish or hide it, or when it
  is not what they would expect.
- `updated_at` is when this change was saved, in UTC. Give it in the
  person's time if you mention it.

Other answers:

- `400`: the HTML has a tag the site does not allow; the message names it.
  Tell the person which tag was refused, remove it and prepare the call again.
- `404`: no post has that slug. It may be misspelt, or deleted. Say so, and
  list the posts with `GET /api/posts` to find the right one.
- `409`: someone changed the post after you read it, so nothing was saved.
  Read it again, redo the change and prepare a new call.
- `401` or `500`: a problem on the site's side, not in the request. Tell the
  owner; do not retry in a loop.

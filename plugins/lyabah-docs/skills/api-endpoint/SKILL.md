---
name: api-endpoint
description: Use when adding or changing an HTTP endpoint of a lyabah service that lyabah-service calls (an action agents send with call_api or prepare for approval with prepare_api_call), or when adding the LYABAH_KEY check, GET /api/ping, a draft mode or a draft checksum to a service's API, in any language or framework.
---

# Building endpoints lyabah-service calls

lyabah-service (service.lyabah.com) sends agents' calls to the owner's
services. It finds each service's base URL in its registry, adds
`Authorization: Bearer <LYABAH_KEY>`, and for a call that needs approval it
first sends the call as a **draft**. The owner reviews the draft's answer,
then approves. The contract below is the same in every language: only how it
is written changes. The examples are `reference/go.md` (net/http, pgx) and
`reference/python.md` (FastAPI, psycopg). For another stack, port one of
them, and keep every rule below.

## The contract

**The key**
1. Every endpoint that changes data, or shows what is not public, checks
   `Authorization: Bearer <LYABAH_KEY>`. The key comes from the environment
   variable `LYABAH_KEY`, the same key every lyabah service checks. Public
   pages and public reads stay open.
2. The header must be exactly `Bearer ` followed by the key. Compare in
   constant time.
3. A missing or wrong key answers `401` with `WWW-Authenticate: Bearer`.
4. `LYABAH_KEY` empty, or shorter than 12 characters: the protected endpoints
   answer `503` with `{"error": "LYABAH_KEY is not set"}`, and the app logs a
   warning at start. The API is never open because a secret is missing.
5. `GET /api/ping`, behind the key, answers
   `{"ok": true, "service": "<SERVICE_NAME>"}`.

**Errors**
6. Every error is JSON, `{"error": "<one plain sentence>"}`, with the right
   status: `400` for a bad value, `404` for a missing thing, `409` for a
   conflict, `412` for a stale checksum, `422` for input that fails
   validation. Frameworks have their own error shapes (FastAPI's `detail`,
   Flask's HTML pages): replace them, including validation errors.

**The draft** (every action that needs approval: anything that changes data)
7. It takes `draft` as a query parameter: `1` checks the call, and `0` or
   none applies it. Any other value gets `400`.
8. With `draft=1` the endpoint does everything the real call does (the
   checks, the reads, the database writes) inside one transaction. Then it
   rolls back, and answers exactly as the real call would: same status, same
   body, plus the header `X-Draft: 1`. Values the database makes up (a new
   id, a timestamp) will differ in the real call; say so in the article.
9. Work outside the database (sending mail, calling another API, writing a
   file, publishing) is not done in a draft. The draft answers as if it had
   been done, and does it only when `draft=0`.

**The checksum** (same actions)
10. The draft also answers with `X-Draft-Checksum`: a hex SHA-256 of the
    state the change depends on. That is the row it updates or deletes, or,
    for a create, the fact that the row is not there yet. Leave out what
    changes on its own: counters, timestamps, results that a job refreshes.
    Otherwise every call looks changed.
11. The real call (`draft=0`) brings the checksum back in the same header.
    Inside its transaction, before writing anything, the endpoint locks the
    rows (`SELECT … FOR UPDATE`) and works the checksum out again. If the
    two differ, it answers `412` and applies nothing. A real call without
    the header is not checked, so the service's other callers keep working.
12. The order inside a call: key, then `draft` value, then input, then lock
    and read, then `404`, then checksum (`412`), then the change, then
    commit or roll back.

**Tests** (always, for every endpoint)
13. No key gets 401, a wrong key gets 401, an unset key gets 503, the right
    key passes, and `/api/ping` works. A bad `draft` gets 400. A draft
    answers like the real call, with `X-Draft: 1` and `X-Draft-Checksum`,
    and changes nothing. A real call with the draft's checksum applies. A
    real call with a stale checksum gets 412 and changes nothing. A real
    call without the header applies. The checksum stays the same when only
    the left-out fields change. Run against the real database, not mocks.

## After the endpoint

- **Describe it** in `docs/api/<name>.yaml.md`, in the same change.
  REQUIRED: use the `api-doc` skill. It covers `approve_required`, where
  `draft` goes, and `writes`.
- **Register the service** if lyabah-service's registry
  (`internal/registry/registry.yaml` in oduvan/lyabah-service) has no `api`
  entry for the repository. The entry is the `base_url` and the header
  `Authorization: Bearer ${LYABAH_KEY}`. That is a pull request to
  lyabah-service; say so rather than skipping it.
- **The deploy** passes `LYABAH_KEY` into the app. A repository made from
  lyabah-template already does. Never print the key, and never commit it.

## Common mistakes

| Mistake | Fix |
|---|---|
| An unset key is refused with 401, or lets everything through | 503 and a warning at start (rule 4) |
| `removeprefix("Bearer ")` or `TrimPrefix`, which accepts the bare key | Require the prefix: no prefix gets 401 |
| The framework's own error body (`{"detail": …}`) | Error handlers that write `{"error": …}` (rule 6) |
| The draft sends the email, or calls the other API | Do it only when `draft=0` (rule 9) |
| `updated_at` or a counter in the checksum | Only the fields the change depends on (rule 10) |
| The checksum is compared after the write, or without a lock | Lock, compare, then write (rule 11) |
| The draft answers 200 where the real call answers 201 | Same status and body; only `X-Draft` differs (rule 8) |
| A different endpoint that "previews" stands in for the draft | Preview is a separate action with `approve_required: false`; the action itself still takes `draft` |

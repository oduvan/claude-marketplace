# The contract in Python (FastAPI, psycopg 3)

The same service as `go.md`: books that can be renamed and deleted through
lyabah-service. The code runs as it is on Python 3.10 or newer, and its
tests pass against Postgres 18. Adapt the names; keep every rule of the
contract.

- `require_key` covers rules 1 to 4: 503 when the key is unset, 401 with
  `WWW-Authenticate` otherwise, and the `Bearer` scheme is required (a bare
  key is refused).
- The two exception handlers cover rule 6. FastAPI answers
  `{"detail": …}` by default, and validation errors as a list: both become
  `{"error": "<sentence>"}`.
- `is_draft` covers rule 7, and `change` covers rules 8, 10, 11 and 12: one
  connection with one transaction, the row locked, the checksum compared
  before the write, and `rollback()` for a draft. psycopg commits when the
  `with` block ends without an error.
- `book_sum` leaves `updated_at` out (rule 10).
- Work outside the database goes after the `with` block, under
  `if not draft` (rule 9). This example has none.

With Flask or Django, keep the same pieces: a decorator or middleware for
the key, error handlers that write `{"error": …}`, and a helper like
`change` that runs the change in one transaction and rolls a draft back.

`api.py`:

```python
import hashlib
import hmac
import logging
import os

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

CHECKSUM_HEADER = "X-Draft-Checksum"
KEY = os.environ.get("LYABAH_KEY", "")
SERVICE = os.environ.get("SERVICE_NAME", "books")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

app = FastAPI()
if len(KEY) < 12:
    logging.warning("LYABAH_KEY is not set: the API answers 503 until it is")


# Every error is {"error": "..."}, the framework's own ones too.
@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    first = exc.errors()[0]
    where = ".".join(str(p) for p in first["loc"][1:]) or "the request"
    return JSONResponse({"error": f"{where}: {first['msg']}"}, status_code=422)


def require_key(authorization: str = Header(default="")):
    """Lets a request through only with Authorization: Bearer <LYABAH_KEY>."""
    if len(KEY) < 12:
        raise HTTPException(503, "LYABAH_KEY is not set")
    scheme, _, got = authorization.partition(" ")
    if scheme != "Bearer" or not hmac.compare_digest(got.encode(), KEY.encode()):
        raise HTTPException(401, "send Authorization: Bearer <LYABAH_KEY>", headers={"WWW-Authenticate": "Bearer"})


def is_draft(draft: str | None, response: Response) -> bool:
    """1 checks the call, 0 or none applies it; anything else is a 400."""
    if draft in (None, "", "0"):
        return False
    if draft == "1":
        return True
    raise HTTPException(400, f"draft must be 0 or 1, not {draft!r}")


def book_sum(book: dict) -> str:
    """What a change to the book depends on: id, title, author. Not updated_at."""
    return hashlib.sha256(f"{book['id']}\n{book['title']}\n{book['author']}".encode()).hexdigest()


def change(book_id: int, draft: bool, want: str | None, response: Response, fn):
    """Runs fn on the locked book in one transaction. A draft rolls it back and
    answers with the checksum; a real call with a stale checksum gets 412."""
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        book = conn.execute("SELECT id, title, author FROM books WHERE id = %s FOR UPDATE", (book_id,)).fetchone()
        if book is None:
            raise HTTPException(404, "no such book")
        current = book_sum(book)
        if not draft and want and want.strip() != current:
            raise HTTPException(412, "the book changed since the draft that was approved; nothing was done")
        result = fn(conn, book)
        if draft:
            conn.rollback()
            response.headers[CHECKSUM_HEADER] = current
        return result  # leaving the block commits a real call


@app.get("/api/ping", dependencies=[Depends(require_key)])
def ping():
    return {"ok": True, "service": SERVICE}


class Rename(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)


@app.patch("/api/books/{book_id}", dependencies=[Depends(require_key)])
def rename_book(book_id: int, body: Rename, response: Response, draft: str | None = None,
                x_draft_checksum: str | None = Header(default=None)):
    d = is_draft(draft, response)

    def fn(conn, book):
        conn.execute("UPDATE books SET title = %s, updated_at = now() WHERE id = %s", (body.title, book_id))
        return {**book, "title": body.title}

    return change(book_id, d, x_draft_checksum, response, fn)


@app.delete("/api/books/{book_id}", dependencies=[Depends(require_key)])
def delete_book(book_id: int, response: Response, draft: str | None = None,
                x_draft_checksum: str | None = Header(default=None)):
    d = is_draft(draft, response)

    def fn(conn, book):
        conn.execute("DELETE FROM books WHERE id = %s", (book_id,))
        return {"deleted": book}

    return change(book_id, d, x_draft_checksum, response, fn)
```

`test_api.py` (pytest). It needs `TEST_DATABASE_URL`, and skips without it:

```python
import importlib
import os

import psycopg
import pytest
from fastapi.testclient import TestClient

KEY = "test-key-of-24-characters"
AUTH = {"Authorization": f"Bearer {KEY}"}


def client(key):
    os.environ["LYABAH_KEY"] = key
    import api
    return TestClient(importlib.reload(api).app)


@pytest.fixture
def db():
    url = os.environ.get("TEST_DATABASE_URL") or pytest.skip("TEST_DATABASE_URL is not set")
    os.environ["DATABASE_URL"] = url
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS books")
        conn.execute("CREATE TABLE books (id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL,"
                     " updated_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        conn.execute("INSERT INTO books (title, author) VALUES ('Kobzar', 'Shevchenko')")
        yield conn


def title(db):
    row = db.execute("SELECT title FROM books WHERE id = 1").fetchone()
    return row[0] if row else None


def test_key(db):
    c = client(KEY)
    r = c.get("/api/ping")
    assert r.status_code == 401 and r.headers["WWW-Authenticate"] == "Bearer" and "error" in r.json()
    assert c.get("/api/ping", headers={"Authorization": "Bearer wrong-key-of-many"}).status_code == 401
    assert c.get("/api/ping", headers={"Authorization": KEY}).status_code == 401  # no "Bearer "
    assert c.get("/api/ping", headers=AUTH).json() == {"ok": True, "service": "books"}
    assert client("").get("/api/ping", headers=AUTH).status_code == 503


def test_errors_are_json(db):
    c = client(KEY)
    r = c.patch("/api/books/1", json={"title": ""}, headers=AUTH)
    assert r.status_code == 422 and list(r.json()) == ["error"]
    assert c.delete("/api/books/9", headers=AUTH).json() == {"error": "no such book"}


def test_draft_and_checksum(db):
    c = client(KEY)
    assert c.patch("/api/books/1?draft=yes", json={"title": "X"}, headers=AUTH).status_code == 400
    d = c.patch("/api/books/1?draft=1", json={"title": "Kobzar, 1840"}, headers=AUTH)
    s = d.headers["X-Draft-Checksum"]
    assert d.status_code == 200 and len(s) == 64 and title(db) == "Kobzar"
    db.execute("UPDATE books SET updated_at = now() + interval '1 hour'")
    again = c.patch("/api/books/1?draft=1", json={"title": "Kobzar, 1840"}, headers=AUTH).headers["X-Draft-Checksum"]
    assert again == s, "updated_at must not change the checksum"
    db.execute("UPDATE books SET title = 'Kobzar (edited)'")
    r = c.patch("/api/books/1?draft=0", json={"title": "Kobzar, 1840"}, headers={**AUTH, "X-Draft-Checksum": s})
    assert r.status_code == 412 and title(db) == "Kobzar (edited)"
    fresh = c.delete("/api/books/1?draft=1", headers=AUTH).headers["X-Draft-Checksum"]
    assert c.delete("/api/books/1?draft=0", headers={**AUTH, "X-Draft-Checksum": fresh}).status_code == 200
    assert title(db) is None
    assert c.delete("/api/books/1", headers=AUTH).status_code == 404
```

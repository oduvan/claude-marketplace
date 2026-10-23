# The contract in Go (net/http, pgx)

A complete example: a service whose books can be renamed and deleted through
lyabah-service. The code runs as it is, and its tests pass against Postgres 18.
Adapt the names; keep every rule of the contract.

- `requireKey` covers rules 1 to 4: 503 when the key is unset, 401 with
  `WWW-Authenticate` otherwise, and the `Bearer ` prefix is required.
- `isDraft` covers rule 7, and `change` covers rules 8, 10, 11 and 12: one
  transaction, the row locked, the checksum compared before the write, and
  a rollback for a draft through the deferred `Rollback`.
- `bookSum` leaves `updated_at` out (rule 10).
- Work outside the database goes after `tx.Commit`, under `if !draft`
  (rule 9). This example has none.

`api.go`:

```go
package books

import (
	"context"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"strconv"
	"strings"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

// checksumHeader carries the draft's checksum, both ways.
const checksumHeader = "X-Draft-Checksum"

type Server struct {
	DB      *pgxpool.Pool
	Key     string // LYABAH_KEY
	Service string // SERVICE_NAME
}

func (s *Server) Routes() http.Handler {
	if len(s.Key) < 12 {
		slog.Warn("LYABAH_KEY is not set: the API answers 503 until it is")
	}
	mux := http.NewServeMux()
	mux.Handle("GET /api/ping", s.requireKey(http.HandlerFunc(s.ping)))
	mux.Handle("PATCH /api/books/{id}", s.requireKey(http.HandlerFunc(s.renameBook)))
	mux.Handle("DELETE /api/books/{id}", s.requireKey(http.HandlerFunc(s.deleteBook)))
	return mux
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// requireKey lets a request through only with Authorization: Bearer <key>.
func (s *Server) requireKey(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if len(s.Key) < 12 {
			writeError(w, http.StatusServiceUnavailable, "LYABAH_KEY is not set")
			return
		}
		got, ok := strings.CutPrefix(r.Header.Get("Authorization"), "Bearer ")
		if !ok || subtle.ConstantTimeCompare([]byte(got), []byte(s.Key)) != 1 {
			w.Header().Set("WWW-Authenticate", "Bearer")
			writeError(w, http.StatusUnauthorized, "send Authorization: Bearer <LYABAH_KEY>")
			return
		}
		next.ServeHTTP(w, r)
	})
}

func (s *Server) ping(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "service": s.Service})
}

// isDraft reads ?draft=: 1 checks the call, 0 or none applies it. It answers
// 400 itself for anything else.
func isDraft(w http.ResponseWriter, r *http.Request) (draft, ok bool) {
	switch v := r.URL.Query().Get("draft"); v {
	case "", "0":
		return false, true
	case "1":
		return true, true
	default:
		writeError(w, http.StatusBadRequest, fmt.Sprintf("draft must be 0 or 1, not %q", v))
		return false, false
	}
}

type book struct {
	ID     int64  `json:"id"`
	Title  string `json:"title"`
	Author string `json:"author"`
}

// bookSum is the checksum of what a change to the book depends on: its id,
// title and author. updated_at is left out: it moves on its own.
func bookSum(b book) string {
	h := sha256.Sum256([]byte(fmt.Sprintf("%d\n%s\n%s", b.ID, b.Title, b.Author)))
	return hex.EncodeToString(h[:])
}

var errStale = errors.New("the book changed since the draft that was approved; nothing was done")

// change runs fn on the locked book inside one transaction. A draft rolls it
// back and answers with the checksum; a real call with a checksum is refused
// when the book no longer matches it.
func (s *Server) change(w http.ResponseWriter, r *http.Request, fn func(ctx context.Context, tx pgx.Tx, b book) (int, any, error)) {
	draft, ok := isDraft(w, r)
	if !ok {
		return
	}
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		writeError(w, http.StatusNotFound, "no such book")
		return
	}
	ctx := r.Context()
	tx, err := s.DB.Begin(ctx)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "the database is not answering")
		return
	}
	defer tx.Rollback(ctx) // a draft, or any error, keeps nothing

	var b book
	err = tx.QueryRow(ctx, `SELECT id, title, author FROM books WHERE id = $1 FOR UPDATE`, id).Scan(&b.ID, &b.Title, &b.Author)
	if errors.Is(err, pgx.ErrNoRows) {
		writeError(w, http.StatusNotFound, "no such book")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "reading the book failed")
		return
	}
	sum := bookSum(b)
	if want := strings.TrimSpace(r.Header.Get(checksumHeader)); !draft && want != "" && want != sum {
		writeError(w, http.StatusPreconditionFailed, errStale.Error())
		return
	}
	status, body, err := fn(ctx, tx, b)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "the change failed")
		return
	}
	if draft {
		w.Header().Set(checksumHeader, sum)
	} else if err := tx.Commit(ctx); err != nil {
		writeError(w, http.StatusInternalServerError, "saving the change failed")
		return
	}
	writeJSON(w, status, body)
}

func (s *Server) renameBook(w http.ResponseWriter, r *http.Request) {
	var in struct {
		Title string `json:"title"`
	}
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 64<<10))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "the body must be {\"title\": \"…\"}")
		return
	}
	title := strings.TrimSpace(in.Title)
	if title == "" || len(title) > 255 {
		writeError(w, http.StatusUnprocessableEntity, "title must be 1 to 255 characters")
		return
	}
	s.change(w, r, func(ctx context.Context, tx pgx.Tx, b book) (int, any, error) {
		_, err := tx.Exec(ctx, `UPDATE books SET title = $2, updated_at = now() WHERE id = $1`, b.ID, title)
		b.Title = title
		return http.StatusOK, b, err
	})
}

func (s *Server) deleteBook(w http.ResponseWriter, r *http.Request) {
	s.change(w, r, func(ctx context.Context, tx pgx.Tx, b book) (int, any, error) {
		_, err := tx.Exec(ctx, `DELETE FROM books WHERE id = $1`, b.ID)
		return http.StatusOK, map[string]any{"deleted": b}, err
	})
}
```

`api_test.go`. It needs `TEST_DATABASE_URL`, and skips without it:

```go
package books

import (
	"context"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5/pgxpool"
)

const testKey = "test-key-of-24-characters"

func setup(t *testing.T, key string) (*httptest.Server, *pgxpool.Pool) {
	url := os.Getenv("TEST_DATABASE_URL")
	if url == "" {
		t.Skip("TEST_DATABASE_URL is not set")
	}
	ctx := context.Background()
	db, err := pgxpool.New(ctx, url)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(db.Close)
	_, err = db.Exec(ctx, `DROP TABLE IF EXISTS books;
		CREATE TABLE books (id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
		INSERT INTO books (title, author) VALUES ('Kobzar', 'Shevchenko')`)
	if err != nil {
		t.Fatal(err)
	}
	ts := httptest.NewServer((&Server{DB: db, Key: key, Service: "books"}).Routes())
	t.Cleanup(ts.Close)
	return ts, db
}

func call(t *testing.T, ts *httptest.Server, method, path, body string, headers ...string) *http.Response {
	req, _ := http.NewRequest(method, ts.URL+path, strings.NewReader(body))
	for i := 0; i+1 < len(headers); i += 2 {
		req.Header.Set(headers[i], headers[i+1])
	}
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	res.Body.Close()
	return res
}

func title(t *testing.T, db *pgxpool.Pool) string {
	var s string
	db.QueryRow(context.Background(), `SELECT coalesce(max(title), '') FROM books WHERE id = 1`).Scan(&s)
	return s
}

func TestKey(t *testing.T) {
	ts, _ := setup(t, testKey)
	if r := call(t, ts, "GET", "/api/ping", ""); r.StatusCode != 401 || r.Header.Get("WWW-Authenticate") != "Bearer" {
		t.Fatalf("no key: %d", r.StatusCode)
	}
	for _, h := range []string{"Bearer wrong-key-of-many-chars", testKey} {
		if r := call(t, ts, "GET", "/api/ping", "", "Authorization", h); r.StatusCode != 401 {
			t.Fatalf("%q: %d", h, r.StatusCode)
		}
	}
	if r := call(t, ts, "GET", "/api/ping", "", "Authorization", "Bearer "+testKey); r.StatusCode != 200 {
		t.Fatalf("right key: %d", r.StatusCode)
	}
	unset, _ := setup(t, "")
	if r := call(t, unset, "GET", "/api/ping", "", "Authorization", "Bearer "); r.StatusCode != 503 {
		t.Fatalf("unset key: %d", r.StatusCode)
	}
}

func TestDraftAndChecksum(t *testing.T) {
	ts, db := setup(t, testKey)
	auth := []string{"Authorization", "Bearer " + testKey}
	if r := call(t, ts, "PATCH", "/api/books/1?draft=yes", `{"title":"X"}`, auth...); r.StatusCode != 400 {
		t.Fatalf("bad draft: %d", r.StatusCode)
	}
	d := call(t, ts, "PATCH", "/api/books/1?draft=1", `{"title":"Kobzar, 1840"}`, auth...)
	sum := d.Header.Get("X-Draft-Checksum")
	if d.StatusCode != 200 || len(sum) != 64 || title(t, db) != "Kobzar" {
		t.Fatalf("a draft answers as the real call and changes nothing: %d %v", d.StatusCode, d.Header)
	}
	db.Exec(context.Background(), `UPDATE books SET updated_at = now() + interval '1 hour'`)
	if again := call(t, ts, "PATCH", "/api/books/1?draft=1", `{"title":"Kobzar, 1840"}`, auth...).Header.Get("X-Draft-Checksum"); again != sum {
		t.Fatal("updated_at must not change the checksum")
	}
	db.Exec(context.Background(), `UPDATE books SET title = 'Kobzar (edited)'`)
	if r := call(t, ts, "PATCH", "/api/books/1?draft=0", `{"title":"Kobzar, 1840"}`, append(auth, "X-Draft-Checksum", sum)...); r.StatusCode != 412 || title(t, db) != "Kobzar (edited)" {
		t.Fatalf("a stale checksum: %d", r.StatusCode)
	}
	fresh := call(t, ts, "DELETE", "/api/books/1?draft=1", "", auth...).Header.Get("X-Draft-Checksum")
	if r := call(t, ts, "DELETE", "/api/books/1?draft=0", "", append(auth, "X-Draft-Checksum", fresh)...); r.StatusCode != 200 || title(t, db) != "" {
		t.Fatalf("a fresh checksum applies: %d", r.StatusCode)
	}
	if r := call(t, ts, "DELETE", "/api/books/1", "", auth...); r.StatusCode != 404 {
		t.Fatalf("gone: %d", r.StatusCode)
	}
}
```

To wire it up, call `Routes()` from `main`, with `Key: os.Getenv("LYABAH_KEY")`
and `Service: os.Getenv("SERVICE_NAME")`. In a service that already has a
router and a database layer, keep `requireKey`, `isDraft` and the shape of
`change`, and use the service's own helpers for the rest.

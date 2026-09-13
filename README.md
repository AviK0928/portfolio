# Portfolio

A database-driven personal site. Every section renders from Postgres — nothing is
hardcoded — and sections degrade independently when content is missing or the
database is unreachable.

FastAPI, Jinja2 and SQLAlchemy on Neon Postgres, deployed as a Python function on
Vercel.

## Why it's built this way

**Three section states, not two.** Each section is `ready`, `empty`, or
`unavailable`. "Nothing published yet" and "the query failed" are different
things: if the database is down, a section that *does* have content must not
render an empty state and quietly lie about it. Each section catches its own
errors, so one failing table degrades alone rather than taking down the page.

**Cache headers are the availability mechanism.** Public responses carry
`s-maxage=300, stale-while-revalidate=86400`. Within five minutes the edge serves
cached HTML with no function invocation; for 24 hours after that it serves stale
content immediately while revalidating behind it. A cold Neon compute or a brief
outage is invisible to visitors.

**`NullPool`, not a connection pool.** Each serverless invocation is a fresh
process, so a retained pool would hold connections that are never reused and
never cleanly closed. One connection per request, closed after, through Neon's
PgBouncer endpoint.

**Functions co-located with the database.** Both run in `ap-southeast-1`
(`sin1` on Vercel). Cross-region was measured at ~240ms per round trip and about
ten round trips per request; co-location removes essentially all of it.

## Stack

| Layer | Choice |
|---|---|
| Web | FastAPI, Jinja2 server-side rendering |
| Data | SQLAlchemy 2.0, Postgres via psycopg 3 |
| Database | Neon (free tier, scale-to-zero) |
| Hosting | Vercel Python runtime, region `sin1` |
| Styling | Plain CSS with custom properties — no build step |
| Tests | pytest against in-memory SQLite |

## Layout

```text
.
├── api/
│   └── index.py           Vercel entrypoint — imports the FastAPI app
├── app/
│   ├── config.py          Settings via pydantic-settings
│   ├── db.py              Engine, session factory, NullPool
│   ├── models.py          Nine SQLAlchemy models
│   ├── repository.py      Read side: section states, per-section error containment
│   ├── schemas.py         Response and input schemas, deliberately separate
│   ├── api.py             Public read-only JSON API
│   ├── admin.py           Token-protected write API
│   ├── pages.py           Server-rendered page route
│   ├── security.py        Bearer auth, fails closed
│   └── templates/
│       ├── base.html      Masthead, footer, colophon
│       ├── index.html     Hero and all nine sections
│       └── partials/
│           └── section.html   Section macro: ready / empty / unavailable
├── public/
│   └── styles.css         Design system — served by the CDN, not the function
├── scripts/
│   └── init_db.py         Idempotent schema creation
├── tests/                 53 tests
├── engineering.md         Decisions, failed approaches, debugging findings
├── requirements.txt       Runtime deps — what Vercel bundles
├── requirements-dev.txt   Adds uvicorn, pytest, httpx
├── vercel.json            Region pin (sin1) and rewrites
└── .python-version        3.13
```

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env      # add your Neon pooled URL and an admin token
python -m scripts.init_db
uvicorn app.main:app --reload
```

`DATABASE_URL` must use the `postgresql+psycopg://` scheme and Neon's **pooled**
host — the one containing `-pooler`. Neon's pooler rejects `statement_timeout` in
the connection startup packet, so it is set as a statement after connect instead.

```bash
python -m pytest -q
```

Tests run against in-memory SQLite with no database required. List columns use
`JSON` rather than Postgres `ARRAY` specifically to keep the models
dialect-portable.

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | Neon pooled connection string |
| `ADMIN_API_TOKEN` | for writes | Bearer token for the admin API |
| `DEBUG` | no | Serves `/styles.css` locally; Vercel's CDN handles it in production |
| `PUBLIC_CACHE_SECONDS` | no | Edge cache TTL, default 300 |

## Data model

Nine tables. Every content table carries `display_order` (ascending sort) and
`is_published` (hide without deleting).

| Table | Drives |
|---|---|
| `site_profile` | Name, headline, bio, location, email, resume link |
| `projects` | Title, summary, stack, notes, repo and live links |
| `experience` | Roles and open-source work with dated bullets |
| `dsa_profiles` | Platform, handle, link, solved count, rating |
| `blogs` | Title, link, summary, date, tags |
| `skills` | Name plus a grouping category |
| `certifications` | Name, issuer, date, credential link |
| `education` | Institute, degree, dates, score |
| `social_links` | Footer links |

## API

Public, no auth, cached at the edge:

```text
GET /api/v1/profile
GET /api/v1/sections/{resource}
GET /healthz
```

Admin, bearer token, never cached:

```text
GET    /api/v1/admin/{resource}
POST   /api/v1/admin/{resource}
PUT    /api/v1/admin/{resource}/{id}
DELETE /api/v1/admin/{resource}/{id}
PUT    /api/v1/admin/profile
```

Resources: `projects`, `experience`, `dsa-profiles`, `blogs`, `skills`,
`certifications`, `education`, `social-links`.

`/healthz` returns 200 with `{"db": "unavailable"}` rather than 500 when the
database is unreachable — app liveness and database reachability are separate
signals, and a 500 would alarm monitors for a site still serving cached content.

### Auth

**Fails closed.** An unset `ADMIN_API_TOKEN` returns 503 for every admin request
rather than accepting them. With a single equality check an unset token would be
the empty string, and a request with an empty bearer header would authenticate.

Token comparison uses `secrets.compare_digest`; `==` short-circuits on the first
differing byte and leaks token content through response timing.

Input schemas use `extra="forbid"`, so a misspelled field returns 422 naming the
field rather than silently doing nothing.

## Content

All content is managed through the admin API — there is no seed script and no
admin UI. `PUT` replaces the entire row, so edits should read the current row,
change what's needed, and send the whole thing back. Omitted fields reset to
their defaults.

## Engineering log

`engineering.md` records decisions, failed approaches and debugging findings from
development: the latency investigation that traced 2.5s responses to round-trip
count rather than database speed, Neon's pooler rejecting `statement_timeout` in
the startup packet, in-memory SQLite being per-connection and invisible across
TestClient's thread, and the runtime-validation gap that turned 422s into 500s.

## Licence

No licence granted. Personal project.

# Engineering Log — Portfolio

## Phase 1 — Skeleton, schema, DB connectivity

**Hosting choice.** Render's free tier was rejected: web services spin down after
15 min idle with 30–60s cold starts, and free Postgres expires 30 days after
creation. Chose Vercel (Python runtime, serverless — no spin-down concept) plus
Neon free Postgres (scale-to-zero after 5 min, resumes in a few hundred ms, no
expiry).

**Serverless connection handling.** Each Vercel invocation is a fresh process, so
a retained SQLAlchemy pool would hold connections that are never reused and never
cleanly closed, exhausting Neon's connection budget. Using `NullPool` + Neon's
`-pooler` (PgBouncer) host: one connection per request, closed after.

**Fail-fast over hang.** `connect_timeout=5` and `statement_timeout=4000ms`. An
unreachable DB must fail in seconds, not hang until the platform kills the
function — a hang burns both Neon CU-hours and function duration.

**Degradation contract.** `/healthz` returns 200 with `{"db": "unavailable"}`
rather than 500 when the DB is unreachable. App liveness and DB reachability are
separate signals; a 500 would alarm monitors for a site still serving cached
content fine. Pinned by a test before any feature was built on it.

**JSON over Postgres ARRAY.** List columns (`tech_stack`, `highlights`, `bullets`,
`tags`) use `JSON` so models stay dialect-portable and the test suite runs on
SQLite with no database. Array operators are not needed here.

**Dependency pinning process.** Installed with version ranges first, then froze
the resolved set (Python 3.13.15 / linux-x86_64, matching Vercel's build target)
rather than guessing which patch releases ship cp313 wheels. `psycopg-binary` is
pinned by name, not via the `[binary]` extra, so the build cannot silently fall
back to the pure-Python implementation — safe only because Colab and Vercel share
linux-x86_64.

**Split requirements.** `requirements.txt` is runtime-only (what Vercel bundles);
`requirements-dev.txt` layers on uvicorn/pytest/httpx. Test tooling in the
function bundle is dead weight against the size limit.

**Python version pinned to 3.13** via `.python-version`. Vercel defaults to 3.12
when the repo declares nothing — a mismatch that produces build failures which
cannot be reproduced locally.

### Latency investigation (root-caused)

Warm `/healthz` measured 2.5s locally, against an expectation of tens of ms.
Decomposing a single request showed every figure was a multiple of one number:

    dns          0.038s
    tcp          0.260s        <- one RTT
    connect      1.526s        ~6 RTTs (TCP + TLS + startup + pooler auth)
    query        0.239s        <- one RTT, on an open connection
    sqlalchemy   2.467s        ~10 RTTs total

Root cause: 240ms RTT from a US Colab VM to Neon in ap-southeast-1, paid ~10
times per request. Not Neon, not psycopg, not `NullPool`. The fix is
co-location, not code: `vercel.json` pins functions to `sin1`, matching the
Neon region, which takes the RTT to ~1ms. The local 2.5s is a development
artifact and is expected to stay that way.

**Failed optimization: `statement_timeout` in the startup packet.** Attempted to
save one RTT by moving the setting from a post-connect `SET` into
`connect_args={"options": "-c statement_timeout=..."}`. Neon's pooler rejects it:
`unsupported startup parameter in options` — PgBouncer only forwards a whitelist
of startup parameters. Reverted to the `connect` event listener. Dropping the
pooler to allow `options` would have been backwards: PgBouncer is what makes
`NullPool` affordable, and the round trip costs ~1ms in-region.

Incidental: Colab has no IPv6 route, so psycopg's per-address failure list is
padded with `Network is unreachable` for every AAAA record. Read only the IPv4
attempts when diagnosing Neon connection errors from Colab.

### Colab workflow

- **Secrets cannot hold empty values.** `userdata.get()` raises
  `SecretNotFoundError` for a secret created blank, so `get(...) or ""` never
  reaches its fallback. Optional secrets need try/except; required ones
  (`DATABASE_URL`) still raise loudly.
- **Config caching order.** `get_settings()` is `lru_cache`d at import, so
  environment injection must run before anything imports `app`. Otherwise a
  runtime restart is the only fix.

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


## Phase 2 — Repository layer and public JSON API

**Three section states, not two.** `SectionState` is `ready` | `empty` |
`unavailable`. "Nothing published yet" and "the query failed" must never
collapse into one value: if Neon is down, a section that *does* have content
must not render "Coming soon" and quietly lie about it. `_fetch` catches
`SQLAlchemyError` per section, so one failing table degrades alone instead of
taking down the page.

**Placeholder logic lives in one place.** The repository and API both return
honest empty lists; the state value is computed once. Deciding "Coming soon" in
nine Jinja templates would guarantee drift.

**Response schemas separate from ORM models.** `id`, `display_order`,
`is_published` and the timestamps are internal. Serialising ORM objects directly
would publish draft state and ordering to anyone reading the API.

**Cache headers are the uptime mechanism.** `s-maxage=300,
stale-while-revalidate=86400` on every public read. Within 5 minutes the edge
serves cached JSON with no function invocation; for 24 hours after that it
serves stale content immediately while revalidating behind it. A Neon cold
resume or outage is therefore invisible to visitors. This header does more for
the free-tier uptime requirement than anything else in the stack.

**Unknown sections cost no DB round trip.** `/api/v1/sections/nonsense` returned
in 35ms vs ~2.25s for real sections: the `get_session` dependency constructs a
Session but SQLAlchemy opens no connection until a query runs.

**Bug: in-memory SQLite is per-connection, and TestClient uses another thread.**
`create_engine("sqlite://")` defaults to `SingletonThreadPool`, which hands each
thread its own connection — and for `sqlite://` a separate connection is a
separate, empty database. TestClient runs the app on its own portal thread, so
the app saw no tables (`no such table: social_links`) while the fixture engine
had all nine. Fix: `poolclass=StaticPool` plus
`connect_args={"check_same_thread": False}` so one connection is shared. Safe
because StaticPool serialises access, and it is test-only — production is
Postgres.

Silver lining: the failure surfaced as `unavailable`, not `empty`, which is the
degradation contract behaving correctly under a real fault rather than a
simulated one.

**Bug: inconsistent return type across success and failure paths.** `_fetch`
returned `list` on success and `()` on failure, inside a `frozen=True`
dataclass. Unified on `tuple`. The test asserting `()` was right; the code was
wrong.


## Phase 3a — Stylesheet, layout shell, section states

**Reversed the Tailwind decision.** Tailwind's value is constraint across a large
utility surface; this design is ~250 lines of CSS behind six custom properties,
where the design system itself is the constraint. Against that, Tailwind costs a
pinned standalone binary, a build step before every commit, and a generated
artifact in git. Plain CSS in `public/styles.css` is served by Vercel's CDN and
never touches the function.

**Section state is rendered structurally.** The rule above each section carries
its name at the left and its state at the right: nothing when ready, "Coming
soon" when empty, "Temporarily unavailable" when the query failed. The Phase 2
three-state model becomes visible rather than hidden, and the failure copy never
claims the section is empty.

**Every section is fetched in one request.** Nine repository calls share one
connection. Fetching sections from the browser over the JSON API would pay nine
round trips and leave the page blank until JS ran.

**Bug: Starlette 1.x changed the TemplateResponse signature.** The old
`TemplateResponse(name, context)` is gone; the current form is
`TemplateResponse(request, name, context)`. Passing the old positional order made
Jinja treat the context dict as a template name — `TypeError: unhashable type:
dict` from the template cache, with nothing in the traceback pointing at the
signature. Now called with keyword arguments, so a future signature change fails
loudly instead of misbinding.

**Bug: macro imported without context.** `{% import %}` must carry `with context`
or the macro cannot see template variables and `caller()` breaks.

**Empty containers must not render their chrome.** The footer drew its top border
around an empty paragraph when no profile row existed — a rule with nothing under
it. Same principle as "Coming soon": absent content should look deliberate, not
broken.


## Phase 3b — Section bodies

**One treatment carries the design.** Projects render as a datasheet: a label
column (Stack / Notes / Links) against hairline-separated rows. Every other
section stays deliberately plainer, so the density itself signals which content
matters most. Nine identically-styled cards would have flattened that hierarchy.

**A table where the data is genuinely tabular.** Problem-solving profiles get a
real `<table>` because platform/handle/count is column data. Missing counts
render an em dash rather than being hidden — an absent number is information.

**Section named for the reader, not the domain.** "Problem solving" rather than
"DSA": the acronym is regional, and LeetCode in the table communicates the same
thing to everyone.

**Bug: `groupby` discards `display_order`.** Jinja's `groupby` sorts by the
grouping key, so skill categories came out alphabetical (Backend, Data, Infra,
Languages) and ignored the ordering column. Fixed with an explicit
`skill_order` list in the page context, with unlisted categories appended after
it — adding a category needs no code change.

**Bug: nested lists inherit second-level markers.** Experience bullets rendered
as hollow circles because the `<ul>` sits inside a flex item; the datasheet's
own bullets rendered solid. Set `list-style: disc` explicitly rather than
relying on the browser default.

**Tests scoped to a section, not the page.** Two Phase 3a tests asserted
`"Coming soon" not in body`. Correct when Projects was the only section; wrong
once six others were legitimately empty. Fixed with a `section_html()` helper
that extracts one section by id — loosening the assertions instead would have
let a real regression through, since a section rendering both content and its
placeholder would still pass.

**Seed script gated behind an explicit opt-in.** `scripts/seed_dev.py` exits
unless `SEED_DEV=yes`. It exists only so the design could be reviewed with real
content, and is superseded by the admin API in Phase 4.


## Phase 4 — Admin API

**Auth fails closed.** Two dependencies rather than one: `require_configured_token`
returns 503 when `ADMIN_API_TOKEN` is unset or blank, and `require_admin` returns
401 on a bad token. Misconfiguration and bad credentials are different failures
and deserve different codes — and more importantly, an unset token must lock the
API rather than open it. With a single equality check, an unset token would be
the empty string and a request sending an empty bearer would authenticate.
Verified live: with no token configured, every header shape returned 503,
including a request carrying a wrong token.

**Constant-time token comparison.** `secrets.compare_digest`, not `==`. Equality
short-circuits on the first differing byte, leaking token content through
response timing.

**Separate input and output schemas.** `ProjectIn` accepts `display_order` and
`is_published`; `ProjectOut` exposes neither. One shared schema would force a
choice between leaking internal fields publicly and making ordering unsettable.
Inputs use `extra="forbid"` so a typo'd field name is rejected rather than
silently ignored.

**Bug: runtime validation skips FastAPI's error translation.** Because the schema
is selected at runtime from the path, validation happens inside the handler via
`model_validate` rather than during request parsing. FastAPI only converts
`RequestValidationError` into a 422 for validation it runs itself, so a bare
`pydantic.ValidationError` propagated as an unhandled exception — a client
sending a typo'd field would have received a 500 with no indication of which
field was wrong. Fixed with a `_validate()` helper translating to
`HTTPException(422, detail=exc.errors(include_url=False))`. General trap for any
API that dispatches schemas by path.

The two tests that caught it only asserted status codes, which is exactly how a
500-shaped bug hides behind 422-shaped intent. Added a test asserting the
response body names the offending field.

**`include_url=False` on error payloads.** The pydantic default embeds a docs
link carrying the library and version in every validation error. No reason to
publish that.

**Starlette renamed `HTTP_422_UNPROCESSABLE_ENTITY` to
`HTTP_422_UNPROCESSABLE_CONTENT`**, matching RFC 9110. Same code, new constant.

**Colab: subprocesses inherit the environment at spawn.** Setting a secret in the
notebook after starting uvicorn has no effect on the running server — it must be
restarted. The empty-token 503s were this, not a defect.


## Phase 3c — Voice, and removing the seed script

**Jokes for empty, plain language for broken.** Empty-state copy is now
informal ("In the backlog", "It's all still in the write-ahead log"), but the
`unavailable` state stays deliberately plain. If a genuine database failure also
cracked a joke, a visitor could not distinguish a broken site from a bare one.
Pinned by `test_failure_copy_stays_plain`, which asserts the humorous strings are
absent from a failed section.

**State badges rather than bare text.** The state now renders as a bordered pill,
with `unavailable` in the accent colour. Grey text beside a heading reads as an
error message; a pill reads as deliberate interface. The visual treatment is
doing the same job as the copy split.

**Explicit section ids.** The macro took `name` and slugified it for the id.
Once section names carried apostrophes ("Things I've shipped") that produced
invalid HTML ids, so ids are now passed explicitly and independently of the
display name.

**Three of seven headers carry jokes.** Every header being funny gets tiring by
the third scroll; the straight ones make the others land.

**Seed script deleted.** `scripts/seed_dev.py` hardcoded content that would drift
from the database and contained placeholder contact details that would have been
wrong if ever run against production. The admin API replaces it.

**README and repo hygiene.** Added a README covering the architecture rationale.
Audited the working tree and full git history for credentials: the only matches
were the literal `USER:PASSWORD` placeholder in `.env.example`. No notebook was
ever committed — `*.ipynb` was gitignored from the first commit, which matters
because cell outputs persist inside the file and `git remote -v` output would
have exposed a PAT.

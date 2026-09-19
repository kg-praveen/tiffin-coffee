# CLAUDE.md — tiffin-coffee-app

Owner: Praveen. Purpose: turn the household's daily stock-buying routine (the
"tiffin-coffee plate") and its trigger board into deterministic, tested code that
Praveen drives conversationally from Claude Code. **Code proposes; Praveen executes
in Kite. This repo never places an order.**

Read this file first, then `spec/` (the five SKILL.md files are the LAW — this repo
implements them; it does not reinterpret them). When the spec is ambiguous, STOP and
ask; never invent a rule. Cite the spec section in every docstring that implements one.

## 1. Domain laws (from spec/osep-stock-analysis.SKILL.md, ENGINE CONTRACT E1–E9)
- **E1 Layers.** Rules live in `engine/` (pure code). State lives in `db/pattaz.db`
  (SQLite). Doctrine lives in `spec/` (read-only). Market data lives nowhere — it is
  fetched live by `tools/` on every run.
- **E2 Number law.** No price, valuation ratio, trigger level, rupee value or cost
  basis may be hard-coded in Python. Policy constants come from the `policy` table.
  Every fetched value is a `Stamped[T]` = `{value, source, as_of}`. A bare number
  crossing a layer boundary is a build failure (tests enforce it).
- **E3 Freshness.** Every input has a validity window: prices = this run; EPS/book/ROE
  = until the next quarterly result; triggers = armable only on a fresh-EPS basis
  younger than the last result and inside the decay clock. Stale or missing → the
  name is DROPPED with a named reason. **There is no path from missing data to a buy.**
- **E4 Runtime classification.** Sector class is read from `names.sector_class` only
  if `classified_on` is set; ambiguous names (NULL) go through the classification
  procedure in spec §SC — strictest applicable gate, and a visible flag in the output.
- **E5 Precedence.** protocol → never-add → freshness → Stage-0 flags → cells/caps →
  sector gate → P5 veto → sizing. A lower stage only tightens.
- **E6 Conflict.** Two rules demanding contradictory outcomes → HALT, print both rule
  names, take no action, ask Praveen. Never average, never pick silently.
- **E7 Single definition.** A gate or threshold is defined once, in `engine/`; every
  other module calls it. Grep before adding a constant.
- **E8 Output law.** Every run prints: inputs with as-of stamps · classification and
  why · rules fired by name · the plate · every dropped name with its reason · what
  would change the verdict. Then writes the same to `sessions`.
- **E9 Fail-closed.** The safe output is always NO ACTION.

## 2. Architecture and allowed dependencies
```
.claude/skills/*   conversational entry points (thin: parse intent → usecases)
usecases/          orchestration: morning_board, plate, sync_holdings
engine/            PURE functions. No I/O, no network, no datetime.now(), no DB.
                   Inputs are Stamped values + policy dict; outputs are dataclasses.
tools/             adapters: prices (yfinance), gsec, kite (read-only), csv_import.
                   Each returns Stamped values; each has recorded fixtures for tests.
store/             the ONLY module that touches SQLite (repository pattern).
db/                schema.sql, migrations/NNN_*.sql, seed_build.py, pattaz.db
spec/              the law. Read-only. Never edited by code.
```
Dependency direction: skills → usecases → {engine, tools, store}. `engine/` imports
nothing from `tools/` or `store/`. `tools/` never imports `engine/`. Violations fail CI
(import-linter).

## 3. Data rules
- SQLite file `db/pattaz.db`; schema in `db/schema.sql`; changes only via numbered
  migrations in `db/migrations/`. Never edit the seed history — append a migration.
- Every table row carries `as_of` (or `set_on`/`ran_at`). Reads that need freshness
  compare against it; they never assume.
- `sessions` is append-only. A run that produced no plate still writes a session.
- `holdings` is replaced by UC2.1 (Kite sync for Zerodha; CSV import for the two
  Integrated accounts, which have no API). Until then it is PARTIAL — the engine must
  treat missing holdings as "P = MISSING (1.5)" only for names explicitly flagged
  new, otherwise DROP with reason `HOLDINGS_STALE`.

## 4. Coding rules
- Python 3.12, `uv` for env, `ruff` + `mypy --strict` on `engine/` and `store/`.
- Types everywhere. `Stamped[T]` is a frozen pydantic model; money is `Decimal`
  rounded to 2 places at the boundary, never float arithmetic on rupees.
- Small pure functions; one gate per function; name it after the spec rule
  (`gate_lender_justified_pb`, `overlay_p5_universe`). Docstring cites the spec §.
- No magic numbers. `policy` table → `Policy` dataclass loaded once per run.
- Drop reasons are an `Enum` (`DropReason`); every drop carries one. New reason =
  new enum member + test.
- Structured logging (JSON lines) — never log tokens, keys, or account numbers.
- Deterministic: same inputs → same plate. Randomness is forbidden in `engine/`.

## 5. Testing rules (tests first, always)
- `pytest`; CI runs with **no network** — adapters are exercised through recorded
  fixtures in `tests/fixtures/` (VCR-style JSON), refreshed deliberately, never in CI.
- `spec/MIGRATION-AND-VALIDATION.md` §"Behavioral regression" (22 cases) is the
  acceptance suite: one parametrized test per row.
- Golden days in `tests/golden/`: replay a recorded market day and assert the plate.
  First golden day: 10-Sep-2026 — **HDFC Bank at a fresh 52-week low with P/B above
  justified must produce quantity 0** (lender gate; spec tiffin-coffee v6 §(c)).
- A gate change without a test is rejected. A test that needs the network is rejected.

## 6. Safety rules (non-negotiable)
- Kite Connect: **read scope only** — holdings, positions, funds, GTT list. The code
  never imports or calls order-placement, order-modify, or GTT-place functions. A
  lint rule greps for them and fails the build.
- Secrets only via `.env` (git-ignored). `.env.example` documents every key. Kite
  access tokens expire daily; the `sync-holdings` skill prints the login URL and
  asks Praveen for the request token — it never automates login or stores passwords.
- No LLM calls at runtime. No Google Docs/Sheets. No headline/news fetching (Stage-0
  headline sweep stays a human+chat step for now).

## 7. Git and workflow
- Conventional commits (`feat:`, `fix:`, `test:`, `db:`, `spec:`). One concern per
  PR. CI green before merge. `CHANGELOG.md` updated per feature.
- Before changing any rule: quote the spec § you are implementing in the PR text. If
  the spec and a request from Praveen disagree, halt and ask — do not "fix" the spec.
- Definition of done: tests green · session row written · golden days pass · README
  usage updated · no bare numbers · no new network call in `engine/`.

## 8. How Praveen talks to this repo (skills in `.claude/skills/`)
- "run the morning board" / "anything fired?" → `morning-board` (UC1)
- "₹10k plate" / "what can I buy today with 25k" → `plate` (UC2)
- "sync holdings" / "import this CSV" → `sync-holdings` (UC2.1)
Answer in plain language, verdict first, the tables after, every drop explained.
Praveen's own rule: research is a recommendation, the register (DB) is the decision.

## 9. Out of scope (do not build unless asked)
Order placement · any Kite write scope · LLM at runtime · Google Drive/Sheets ·
mobile/web UI · news sweeps · Anand video harvesting · re-underwriting names
(that is a chat-with-Praveen job; the DB only records the outcome).

# tiffin-coffee-app
Praveen's household stock-buying engine (OSEP / pattaz), driven conversationally from
Claude Code. Rules in `engine/`, state in `db/pattaz.db` (SQLite), law in `spec/`.
**Proposal only — never places orders.**
Start here: `CLAUDE.md` → `spec/` → `db/README-DATA.md` → `FIRST-PROMPT.md`.
Skills: `run the morning board` (UC1) · `₹10k plate` (UC2) · `sync holdings` (UC2.1) ·
`run the simulation` / `what if Nifty falls 15%` (UC5).

## Usage — the plate (UC2)

```bash
uv run python -c "from decimal import Decimal; from usecases.plate import run_plate, format_plate; print(format_plate(run_plate('db/pattaz.db', Decimal('40000'))))"
```

The GoI 10Y yield is fetched live (CNBC, then yfinance). Pass it yourself only if both are down:

```bash
uv run python -c "from decimal import Decimal; from usecases.plate import run_plate, format_plate; print(format_plate(run_plate('db/pattaz.db', Decimal('40000'), gsec_yield_override=Decimal('7.06'))))"
```

Read the output top-down: **ADVISORY** block first. `BLOCK:` means the plate is
advisory only — do not execute (today: holdings not synced, so P-tiers and caps run
on a partial book). Then the plate, then *what would change the verdict* for every
near miss, then bulk exclusions by rule, then the guardrails checklist.

Every drop names its rule and what would flip it. `E6_CAPS_OFF_CONFLICT` and
`E6_PEAK_CYCLE_CONFLICT` are questions for Praveen, not decisions by the engine.

## Usage — sync holdings (UC2.1, Kite path — Zerodha ZERODHA_P)

Read-only Kite Connect. Put `KITE_API_KEY` / `KITE_API_SECRET` in `.env` (see
`.env.example`). Login is never automated:

```bash
uv run python -m usecases.sync_holdings kite --login-url              # open it, log in
uv run python -m usecases.sync_holdings kite --request-token <TOKEN>  # from the redirect
uv run python -m usecases.sync_holdings kite                          # later today: cached token
```

Only ZERODHA_P rows are written (source `KITE_API`, as_of = IST fetch date; qty =
settled + T1). A Zerodha name held before and absent from Kite is recorded as an exit.
Kite symbols map to the register via the `names.yf_ticker` stem (`RECLTD` → `REC`);
symbols not in `names` are kept under their Kite name and listed as UNKNOWN. An empty
Kite answer while the register shows Zerodha holdings writes nothing (fail-closed).
The daily access token is cached in the git-ignored `.kite_access.token` and treated
as expired after the IST day.
**Single-deployment cap** (tiffin v4: no plate over 15% of confirmed investable
surplus). Surplus is never stored — give it each run:

```bash
uv run python -c "from decimal import Decimal; from usecases.plate import run_plate, format_plate; print(format_plate(run_plate('db/pattaz.db', Decimal('10000'), confirmed_surplus=Decimal('300000'))))"
```

Without it the guardrail says "not checked". A plate over the cap is `HALT — NO ACTION`
(nothing is trimmed; every ranked name is listed as `DEPLOYMENT_CAP_HALT`).

**HOCKEY check** (tiffin v6 §H + ledger D37): each run fetches Nifty (^NSEI) and each
name's previous close, and flags Nifty −5% in a week, the −15% / −25% drawdown rungs, a
name −10% in a day, and H > 1.15. It only reports — the plate is unchanged and any
reserve move needs Praveen's yes. The two-pocket 60/40 rule is stated, not checked
(pocket balances are not in the register).

## Usage — sync holdings (UC2.1, CSV path)

Drop the household CSV (columns `Stock, Total Qty, Kite-P Qty, Int-P Qty, Int-V Qty`,
date in the filename) into `db/holdings/` so the seed rebuilds with it, then:

```bash
uv run python -m usecases.sync_holdings csv db/holdings/household_equity_21sep2026.csv
```

A snapshot is the whole household: a name that was held before and is missing now is
recorded as an exit (qty 0). The engine always reads the newest row per account+symbol.
Names not in the register are held but cannot be priced — they are listed as UNPRICED
and every weight is computed without them (conservative).

Checks (what CI runs): `python db/seed_build.py && pytest -q` · `ruff check . && lint-imports`
· `mypy --strict engine/ store/` · no order-placement symbols anywhere.

## Usage — market simulation (UC5)

Replays a recorded market day (`tests/fixtures/market/market_YYYY-MM-DD.json`) through
the real morning board and plate under shocks, and checks every law on every plate.
CI runs the whole catalog (`tests/sim/`) with no network.

```bash
uv run python -m usecases.simulate run --amount 10000 --amount 40000
```

```bash
uv run python -m usecases.simulate what-if --nifty -15 --name INFY:-10 --gsec-bp 50 --amount 25000
```

```bash
uv run python -m usecases.simulate record
```

`run` leads with PASS/FAIL. A **VIOLATION** means a plate broke a law (qty outside the
clamp, a banned or unpriced name plated, a lender bite on a failed gate, a name neither
plated nor explained, a plate on no data, a non-deterministic plate, a first bite that
appears only after the yield rises) — treat that day's plate as NO ACTION. **FINDINGS**
are legal per spec but yours to judge (the 1-share floor spending past a small session;
breadth outside 8-15). `what-if` shows today's plate against the shocked one, name by
name. `--live` shocks today's live market instead of the recording; `record` saves a
new recording (commit it deliberately — it becomes the CI baseline). One
`UC5_SIMULATION` session is written per run; simulated plates are never UC2 sessions.

## Usage — OSEP analyser (UC4)

```bash
uv run python -m usecases.osep analyse RSYSTEMS
```

```bash
uv run python -m usecases.osep rederive
```

`analyse` gives the verdict (good buy now / later / hard pass / incomplete), the trigger
and its expiry. Judgments the data can't answer are researched in chat and recorded with
`judge SYMBOL <item> <value> --source "..."`; `apply SYMBOL --reason "..."` records a
verdict only after Praveen agrees. `rederive` recomputes every trigger after results.

## Usage — ledger sync (UC6)

```bash
uv run python -m usecases.ledger_sync                     # newest ../tiffin-coffee/investing_plans/PATTAZ_MASTER_LEDGER_v*.txt
uv run python -m usecases.ledger_sync --file path/to/PATTAZ_MASTER_LEDGER_v4.11_2026-09-28.txt
```

Reads the local text export of the Drive ledger (no Drive calls at runtime) and reports
new decisions, trigger levels that moved, names/cells that need review and lines it
could not read. Unambiguous items (new decisions, level changes) go to
`db/migrations/drafts/ledger_<version>.sql` — a DRAFT, never auto-applied. Needs
migration 011 (`ledger_aliases`) for short names like SBI / EIL; one `UC6_LEDGER_SYNC`
session per run.

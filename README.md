# tiffin-coffee-app
Praveen's household stock-buying engine (OSEP / pattaz), driven conversationally from
Claude Code. Rules in `engine/`, state in `db/pattaz.db` (SQLite), law in `spec/`.
**Proposal only — never places orders.**
Start here: `CLAUDE.md` → `spec/` → `db/README-DATA.md` → `FIRST-PROMPT.md`.
Skills: `run the morning board` (UC1) · `₹10k plate` (UC2) · `sync holdings` (UC2.1).

## Usage — the plate (UC2)

```bash
uv run python -c "from decimal import Decimal; from usecases.plate import run_plate, format_plate; print(format_plate(run_plate('db/pattaz.db', Decimal('40000'))))"
```

Pass the GoI 10Y yield yourself when the live source is down (it usually is):

```bash
uv run python -c "from decimal import Decimal; from usecases.plate import run_plate, format_plate; print(format_plate(run_plate('db/pattaz.db', Decimal('40000'), gsec_yield_override=Decimal('7.06'))))"
```

Read the output top-down: **ADVISORY** block first. `BLOCK:` means the plate is
advisory only — do not execute (today: holdings not synced, so P-tiers and caps run
on a partial book). Then the plate, then *what would change the verdict* for every
near miss, then bulk exclusions by rule, then the guardrails checklist.

Every drop names its rule and what would flip it. `E6_CAPS_OFF_CONFLICT` and
`PEAK_CYCLE`-at-trigger are questions for Praveen, not decisions by the engine.

## Usage — sync holdings (UC2.1, CSV path)

Drop the household CSV (columns `Stock, Total Qty, Kite-P Qty, Int-P Qty, Int-V Qty`,
date in the filename) into `db/holdings/` so the seed rebuilds with it, then:

```bash
uv run python -c "from usecases.sync_holdings import run_sync_holdings_csv, format_sync; print(format_sync(run_sync_holdings_csv('db/pattaz.db', 'db/holdings/household_equity_21sep2026.csv')))"
```

A snapshot is the whole household: a name that was held before and is missing now is
recorded as an exit (qty 0). The engine always reads the newest row per account+symbol.
Names not in the register are held but cannot be priced — they are listed as UNPRICED
and every weight is computed without them (conservative).

Checks (what CI runs): `python db/seed_build.py && pytest -q` · `ruff check . && lint-imports`
· `mypy --strict engine/ store/` · no order-placement symbols anywhere.

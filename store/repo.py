"""store/repo.py — repository pattern over db/pattaz.db.

Spec: E1 (state lives in the DB), architecture rule (store/ is the ONLY module
that touches SQLite). All reads return typed dataclasses; writes go through
explicit methods that enforce invariants.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Self

# ---------------------------------------------------------------- models ---

@dataclass(frozen=True)
class PolicyRow:
    key: str
    value: str
    unit: str | None
    source: str
    adopted_on: str


@dataclass(frozen=True)
class NameRow:
    symbol: str
    name: str
    yf_ticker: str | None
    ticker_verified: bool
    cell: str | None
    sector_class: str | None
    classified_on: str | None
    classification_source: str | None
    status: str
    bucket: str | None
    verdict_date: str | None
    decay_expiry: str | None
    p5_status: str | None
    p5_note_ref: str | None
    flag_sovereign: bool
    flag_psu: bool
    flag_cyclical: bool
    flag_probe_open: bool
    flag_fraud_tail: bool
    flag_exit_decided: bool
    notes: str | None
    as_of: str
    p_mult_book: Decimal | None = None
    flag_no_add: bool = False


@dataclass(frozen=True)
class TriggerRow:
    symbol: str
    kind: str
    level: Decimal
    basis_eps_date: str | None
    derivation: str | None
    set_on: str
    valid_until: str | None
    gtt_id: str | None
    active: bool
    notes: str | None


@dataclass(frozen=True)
class HoldingRow:
    account: str
    symbol: str
    qty: int
    avg_cost: Decimal | None
    as_of: str
    source: str


@dataclass(frozen=True)
class CellRow:
    cell: str
    members: str
    active_adds: str | None
    max_adds: int
    is_full: bool
    notes: str | None
    as_of: str


@dataclass(frozen=True)
class FundamentalsRow:
    symbol: str
    as_of: str
    eps_ttm: Decimal | None
    book_value_ps: Decimal | None
    roe: Decimal | None
    promoter_pct: Decimal | None
    pledge_pct: Decimal | None
    auditor_flag: str | None
    source: str | None


@dataclass(frozen=True)
class DecisionRow:
    d_no: int
    decided_on: str | None
    title: str
    detail: str | None
    status: str


# ------------------------------------------------------------ repository ---

class PattazRepo:
    """Read/write interface to pattaz.db. The only module that imports sqlite3."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        if not self._db_path.exists():
            raise FileNotFoundError(f"database not found: {self._db_path}")
        self._con = sqlite3.connect(str(self._db_path))
        self._con.row_factory = sqlite3.Row

    def close(self) -> None:
        self._con.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- policy ---

    def load_policy(self) -> dict[str, PolicyRow]:
        rows = self._con.execute("SELECT * FROM policy").fetchall()
        return {
            r["key"]: PolicyRow(
                key=r["key"],
                value=r["value"],
                unit=r["unit"],
                source=r["source"],
                adopted_on=r["adopted_on"],
            )
            for r in rows
        }

    # --- names ---

    def load_names(self) -> list[NameRow]:
        rows = self._con.execute("SELECT * FROM names").fetchall()
        return [self._to_name_row(r) for r in rows]

    def get_name(self, symbol: str) -> NameRow | None:
        row = self._con.execute(
            "SELECT * FROM names WHERE symbol = ?", (symbol,)
        ).fetchone()
        return self._to_name_row(row) if row else None

    @staticmethod
    def _to_name_row(r: sqlite3.Row) -> NameRow:
        keys = r.keys()
        p_mult_raw = r["p_mult_book"] if "p_mult_book" in keys else None
        no_add_raw = r["flag_no_add"] if "flag_no_add" in keys else 0
        return NameRow(
            p_mult_book=Decimal(str(p_mult_raw)) if p_mult_raw is not None else None,
            flag_no_add=bool(no_add_raw),
            symbol=r["symbol"],
            name=r["name"],
            yf_ticker=r["yf_ticker"],
            ticker_verified=bool(r["ticker_verified"]),
            cell=r["cell"],
            sector_class=r["sector_class"],
            classified_on=r["classified_on"],
            classification_source=r["classification_source"],
            status=r["status"],
            bucket=r["bucket"],
            verdict_date=r["verdict_date"],
            decay_expiry=r["decay_expiry"],
            p5_status=r["p5_status"],
            p5_note_ref=r["p5_note_ref"],
            flag_sovereign=bool(r["flag_sovereign"]),
            flag_psu=bool(r["flag_psu"]),
            flag_cyclical=bool(r["flag_cyclical"]),
            flag_probe_open=bool(r["flag_probe_open"]),
            flag_fraud_tail=bool(r["flag_fraud_tail"]),
            flag_exit_decided=bool(r["flag_exit_decided"]),
            notes=r["notes"],
            as_of=r["as_of"],
        )

    # --- triggers ---

    def load_triggers(self, active_only: bool = False) -> list[TriggerRow]:
        sql = "SELECT * FROM triggers"
        if active_only:
            sql += " WHERE active = 1"
        rows = self._con.execute(sql).fetchall()
        return [self._to_trigger_row(r) for r in rows]

    def get_triggers_for(self, symbol: str) -> list[TriggerRow]:
        rows = self._con.execute(
            "SELECT * FROM triggers WHERE symbol = ?", (symbol,)
        ).fetchall()
        return [self._to_trigger_row(r) for r in rows]

    @staticmethod
    def _to_trigger_row(r: sqlite3.Row) -> TriggerRow:
        return TriggerRow(
            symbol=r["symbol"],
            kind=r["kind"],
            level=Decimal(str(r["level"])),
            basis_eps_date=r["basis_eps_date"],
            derivation=r["derivation"],
            set_on=r["set_on"],
            valid_until=r["valid_until"],
            gtt_id=r["gtt_id"],
            active=bool(r["active"]),
            notes=r["notes"],
        )

    # --- holdings ---

    _NEWEST_HOLDINGS_SQL = (
        "SELECT h.* FROM holdings h"
        " JOIN (SELECT account, symbol, MAX(as_of) AS as_of FROM holdings"
        "       GROUP BY account, symbol) m"
        " ON h.account = m.account AND h.symbol = m.symbol AND h.as_of = m.as_of"
    )

    def load_holdings(self) -> list[HoldingRow]:
        """Newest row per (account, symbol) — sync-holdings skill step 3.

        A qty-0 row is a recorded exit and is returned as such (E3: never assume)."""
        rows = self._con.execute(self._NEWEST_HOLDINGS_SQL).fetchall()
        return [self._to_holding_row(r) for r in rows]

    def load_holdings_history(self) -> list[HoldingRow]:
        rows = self._con.execute(
            "SELECT * FROM holdings ORDER BY as_of, account, symbol"
        ).fetchall()
        return [self._to_holding_row(r) for r in rows]

    def get_holdings_for(self, symbol: str) -> list[HoldingRow]:
        rows = self._con.execute(
            self._NEWEST_HOLDINGS_SQL + " WHERE h.symbol = ?", (symbol,)
        ).fetchall()
        return [self._to_holding_row(r) for r in rows]

    def held_pairs(self) -> set[tuple[str, str]]:
        """(account, symbol) pairs whose newest row has qty > 0."""
        return {(h.account, h.symbol) for h in self.load_holdings() if h.qty > 0}

    def insert_holdings(
        self,
        rows: list[tuple[str, str, int, Decimal | None]],
        as_of: str,
        source: str,
    ) -> int:
        """Append a dated snapshot. Older rows are kept as history (never edited)."""
        self._con.executemany(
            "INSERT OR REPLACE INTO holdings (account, symbol, qty, avg_cost, as_of, source)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (acct, sym, qty, float(cost) if cost is not None else None, as_of, source)
                for acct, sym, qty, cost in rows
            ],
        )
        self._con.commit()
        return len(rows)

    @staticmethod
    def _to_holding_row(r: sqlite3.Row) -> HoldingRow:
        return HoldingRow(
            account=r["account"],
            symbol=r["symbol"],
            qty=r["qty"],
            avg_cost=Decimal(str(r["avg_cost"])) if r["avg_cost"] is not None else None,
            as_of=r["as_of"],
            source=r["source"],
        )

    # --- cells ---

    def load_cells(self) -> list[CellRow]:
        rows = self._con.execute("SELECT * FROM cells").fetchall()
        return [
            CellRow(
                cell=r["cell"],
                members=r["members"],
                active_adds=r["active_adds"],
                max_adds=r["max_adds"],
                is_full=bool(r["is_full"]),
                notes=r["notes"],
                as_of=r["as_of"],
            )
            for r in rows
        ]

    # --- decisions ---

    def load_decisions(self, status: str | None = None) -> list[DecisionRow]:
        if status:
            rows = self._con.execute(
                "SELECT * FROM decisions WHERE status = ?", (status,)
            ).fetchall()
        else:
            rows = self._con.execute("SELECT * FROM decisions").fetchall()
        return [
            DecisionRow(
                d_no=r["d_no"],
                decided_on=r["decided_on"],
                title=r["title"],
                detail=r["detail"],
                status=r["status"],
            )
            for r in rows
        ]

    # --- sessions (append-only) ---

    def append_session(
        self,
        run_id: str,
        ran_at: str,
        usecase: str,
        inputs: dict[str, object],
        outputs: dict[str, object],
        drops: list[dict[str, object]],
        rules_fired: list[str],
    ) -> None:
        """Append a session record. Spec: sessions is append-only; a run that
        produced no plate still writes a session."""
        self._con.execute(
            "INSERT INTO sessions"
            " (run_id, ran_at, usecase, inputs_json, outputs_json, drops_json, rules_fired)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                ran_at,
                usecase,
                json.dumps(inputs),
                json.dumps(outputs),
                json.dumps(drops),
                ",".join(rules_fired),
            ),
        )
        self._con.commit()

    # --- schema version ---

    def schema_version(self) -> int:
        row = self._con.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        return int(row["version"]) if row else 0

    # --- ticker verification (Task 3) ---

    def set_ticker_verified(self, symbol: str, yf_ticker: str) -> None:
        """Mark a name's yf_ticker as verified and update it if needed."""
        self._con.execute(
            "UPDATE names SET yf_ticker = ?, ticker_verified = 1 WHERE symbol = ?",
            (yf_ticker, symbol),
        )
        self._con.commit()

    def names_needing_ticker_verification(self) -> list[NameRow]:
        """Return names with a non-NULL yf_ticker that haven't been verified yet."""
        rows = self._con.execute(
            "SELECT * FROM names WHERE yf_ticker IS NOT NULL AND ticker_verified = 0"
        ).fetchall()
        return [self._to_name_row(r) for r in rows]

    def names_without_ticker(self) -> list[NameRow]:
        """Return names with NULL yf_ticker (no yfinance ticker known)."""
        rows = self._con.execute(
            "SELECT * FROM names WHERE yf_ticker IS NULL"
        ).fetchall()
        return [self._to_name_row(r) for r in rows]

    # --- fundamentals ---

    def save_fundamentals(
        self,
        symbol: str,
        as_of: str,
        eps_ttm: Decimal | None = None,
        book_value_ps: Decimal | None = None,
        roe: Decimal | None = None,
        promoter_pct: Decimal | None = None,
        pledge_pct: Decimal | None = None,
        auditor_flag: str | None = None,
        source: str | None = None,
    ) -> None:
        """INSERT OR REPLACE a fundamentals row for audit trail (E8)."""
        self._con.execute(
            "INSERT OR REPLACE INTO fundamentals"
            " (symbol, as_of, eps_ttm, book_value_ps, roe,"
            "  promoter_pct, pledge_pct, auditor_flag, source)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                symbol,
                as_of,
                float(eps_ttm) if eps_ttm is not None else None,
                float(book_value_ps) if book_value_ps is not None else None,
                float(roe) if roe is not None else None,
                float(promoter_pct) if promoter_pct is not None else None,
                float(pledge_pct) if pledge_pct is not None else None,
                auditor_flag,
                source,
            ),
        )
        self._con.commit()

    def load_latest_fundamentals(self, symbol: str) -> FundamentalsRow | None:
        """Return the newest fundamentals row for a symbol, or None."""
        row = self._con.execute(
            "SELECT * FROM fundamentals WHERE symbol = ? ORDER BY as_of DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        if row is None:
            return None
        def _dec(col: str) -> Decimal | None:
            v = row[col]
            return Decimal(str(v)) if v is not None else None

        return FundamentalsRow(
            symbol=row["symbol"],
            as_of=row["as_of"],
            eps_ttm=_dec("eps_ttm"),
            book_value_ps=_dec("book_value_ps"),
            roe=_dec("roe"),
            promoter_pct=_dec("promoter_pct"),
            pledge_pct=_dec("pledge_pct"),
            auditor_flag=row["auditor_flag"],
            source=row["source"],
        )

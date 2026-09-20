"""tests/test_verify_tickers.py — tests for ticker verification logic.

CI runs with NO NETWORK. Tests verify the logic, not the live API.
"""
from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, patch

from store.repo import PattazRepo
from tools.prices import PriceSnapshot
from tools.stamped import Stamped
from tools.verify_tickers import verify_all_tickers

DB_PATH = Path(__file__).parent.parent / "db" / "pattaz.db"


class TestTickerFormat:
    """Validate that all non-NULL yf_tickers follow the SYMBOL.NS pattern."""

    def test_all_tickers_are_nse_format(self) -> None:
        repo = PattazRepo(DB_PATH)
        names = repo.names_needing_ticker_verification()
        for n in names:
            assert n.yf_ticker is not None
            assert n.yf_ticker.endswith(".NS"), (
                f"{n.symbol}: yf_ticker {n.yf_ticker!r} does not end with .NS"
            )
        repo.close()

    def test_ticker_symbol_matches_nse_symbol(self) -> None:
        """Most tickers should be SYMBOL.NS where SYMBOL matches the names.symbol."""
        repo = PattazRepo(DB_PATH)
        names = repo.names_needing_ticker_verification()
        mismatches = []
        for n in names:
            assert n.yf_ticker is not None
            expected = f"{n.symbol}.NS"
            if n.yf_ticker != expected:
                mismatches.append((n.symbol, n.yf_ticker, expected))
        # Known mismatches: ARE&M.NS, M&M.NS, BAJAJ-AUTO.NS (special chars in NSE symbol)
        for sym, actual, _expected in mismatches:
            assert sym in ("ARE&M", "M&M", "BAJAJ-AUTO", "REC", "THANGAMAYIL"), (
                f"Unexpected mismatch: {sym} has ticker {actual!r}"
            )
        repo.close()


class TestNullTickers:
    """Names with NULL yf_ticker — these need manual assignment."""

    EXPECTED_NULL: ClassVar[set[str]] = {
        "TMCV", "GROWW", "INDIGRID", "MINDSPACE", "EMBASSY",
        "NXST", "PGINVIT", "CUBEINVIT", "RTNINDIA", "GLOBALSURF", "TATAMOTORS",
    }

    def test_null_ticker_names(self) -> None:
        repo = PattazRepo(DB_PATH)
        no_ticker = repo.names_without_ticker()
        actual = {n.symbol for n in no_ticker}
        assert actual == self.EXPECTED_NULL
        repo.close()


class TestVerifyLogic:
    """Test the verify_all_tickers function with mocked network."""

    @patch("tools.verify_tickers.fetch_price")
    def test_successful_verification(self, mock_fetch: MagicMock, tmp_path: Path) -> None:
        # Create a temp DB with one name
        db = tmp_path / "test.db"
        con = sqlite3.connect(str(db))
        # Create just the tables we need
        con.executescript("""
            CREATE TABLE schema_version (version INTEGER NOT NULL, applied_on TEXT NOT NULL);
            INSERT INTO schema_version VALUES (1, '2026-09-19');
            CREATE TABLE names (
                symbol TEXT PRIMARY KEY, name TEXT NOT NULL, yf_ticker TEXT,
                ticker_verified INTEGER NOT NULL DEFAULT 0, cell TEXT, sector_class TEXT,
                classified_on TEXT, classification_source TEXT,
                status TEXT NOT NULL
                    CHECK (status IN ('ADD','HOLD','SELL','SOLD','WATCH','NEVER_ADD')),
                bucket TEXT, verdict_date TEXT, decay_expiry TEXT,
                p5_status TEXT, p5_note_ref TEXT,
                flag_sovereign INTEGER NOT NULL DEFAULT 0,
                flag_psu INTEGER NOT NULL DEFAULT 0,
                flag_cyclical INTEGER NOT NULL DEFAULT 0,
                flag_probe_open INTEGER NOT NULL DEFAULT 0,
                flag_fraud_tail INTEGER NOT NULL DEFAULT 0,
                flag_exit_decided INTEGER NOT NULL DEFAULT 0,
                notes TEXT, as_of TEXT NOT NULL
            );
            CREATE TABLE sessions (
                run_id TEXT PRIMARY KEY, ran_at TEXT NOT NULL, usecase TEXT NOT NULL,
                inputs_json TEXT NOT NULL, outputs_json TEXT NOT NULL,
                drops_json TEXT NOT NULL, rules_fired TEXT NOT NULL
            );
            INSERT INTO names VALUES (
                'TEST', 'Test Co', 'TEST.NS', 0, 'IT', 'IT_SERVICES',
                '2026-09-17', 'test', 'ADD', 'GBN', NULL, NULL,
                NULL, NULL, 0, 0, 0, 0, 0, 0, NULL, '2026-09-17'
            );
        """)
        con.commit()
        con.close()

        now = "2026-09-19T10:00:00+00:00"
        mock_fetch.return_value = PriceSnapshot(
            symbol="TEST",
            price=Stamped(value=Decimal("100.00"), source="yfinance:TEST.NS", as_of=now),
            low_52w=Stamped(value=Decimal("80.00"), source="yfinance:TEST.NS", as_of=now),
            high_52w=Stamped(value=Decimal("120.00"), source="yfinance:TEST.NS", as_of=now),
        )

        verified, failed = verify_all_tickers(db)
        assert verified == ["TEST"]
        assert failed == []

        # Check DB was updated
        repo = PattazRepo(db)
        n = repo.get_name("TEST")
        assert n is not None
        assert n.ticker_verified is True
        repo.close()

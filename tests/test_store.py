"""tests/test_store.py — tests for store/repo.py over the seeded db/pattaz.db.

No network required. Tests the repository pattern and data integrity.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from store.repo import PattazRepo


@pytest.fixture
def repo(scratch_db: Path) -> PattazRepo:
    r = PattazRepo(scratch_db)
    yield r  # type: ignore[misc]
    r.close()


class TestPolicy:
    def test_load_policy_returns_dict(self, repo: PattazRepo) -> None:
        policy = repo.load_policy()
        assert isinstance(policy, dict)
        assert len(policy) == 48

    def test_fair_pe_method(self, repo: PattazRepo) -> None:
        policy = repo.load_policy()
        assert "fair_pe_method" in policy
        assert policy["fair_pe_method"].value == "1/gsec_yield"

    def test_qty_clamp(self, repo: PattazRepo) -> None:
        policy = repo.load_policy()
        assert policy["qty_clamp_min"].value == "1"
        assert policy["qty_clamp_max"].value == "10"

    def test_policy_rows_have_source(self, repo: PattazRepo) -> None:
        for row in repo.load_policy().values():
            assert row.source, f"policy {row.key} missing source"
            assert row.adopted_on, f"policy {row.key} missing adopted_on"


class TestNames:
    def test_load_names_count(self, repo: PattazRepo) -> None:
        names = repo.load_names()
        assert len(names) == 126

    def test_get_name_infy(self, repo: PattazRepo) -> None:
        n = repo.get_name("INFY")
        assert n is not None
        assert n.name == "Infosys"
        assert n.yf_ticker == "INFY.NS"
        assert n.sector_class == "IT_SERVICES"
        assert n.status == "ADD"
        assert n.bucket == "GBN"

    def test_get_name_missing(self, repo: PattazRepo) -> None:
        assert repo.get_name("NONEXISTENT") is None

    def test_reliance_needs_runtime_classification(self, repo: PattazRepo) -> None:
        n = repo.get_name("RELIANCE")
        assert n is not None
        assert n.sector_class is None
        assert n.classified_on is None

    def test_names_have_as_of(self, repo: PattazRepo) -> None:
        for n in repo.load_names():
            assert n.as_of, f"name {n.symbol} missing as_of"

    def test_p_mult_book_roster(self, repo: PattazRepo) -> None:
        """pattaz-book §4 roster (migration 004)."""
        infy = repo.get_name("INFY")
        hdfc = repo.get_name("HDFCBANK")
        itc = repo.get_name("ITC")
        assert infy is not None and infy.p_mult_book == Decimal("1.0")
        assert hdfc is not None and hdfc.p_mult_book == Decimal(0)
        assert itc is not None and itc.p_mult_book == Decimal("0.5")

    def test_flag_no_add_museum_names(self, repo: PattazRepo) -> None:
        """pattaz-book §5/§6 museum / hold-only (migration 004)."""
        for sym in ("ITC", "WIPRO", "HCLTECH", "HAL", "BEL"):
            n = repo.get_name(sym)
            assert n is not None and n.flag_no_add, f"{sym} should be flag_no_add"
        infy = repo.get_name("INFY")
        assert infy is not None and not infy.flag_no_add


class TestTriggers:
    def test_load_triggers_count(self, repo: PattazRepo) -> None:
        triggers = repo.load_triggers()
        assert len(triggers) == 39

    def test_active_only(self, repo: PattazRepo) -> None:
        active = repo.load_triggers(active_only=True)
        assert all(t.active for t in active)
        inactive_count = len(repo.load_triggers()) - len(active)
        assert inactive_count == 4  # FEDERALBNK, TMB, INDIGRID, ZYDUSLIFE

    def test_trigger_level_is_decimal(self, repo: PattazRepo) -> None:
        for t in repo.load_triggers():
            assert isinstance(t.level, Decimal), f"trigger {t.symbol}/{t.kind} level not Decimal"

    def test_petronet_trigger(self, repo: PattazRepo) -> None:
        triggers = repo.get_triggers_for("PETRONET")
        assert len(triggers) == 1
        assert triggers[0].kind == "BUY"
        assert triggers[0].level == Decimal(383)
        assert triggers[0].active is True


class TestHoldings:
    def test_newest_row_per_account_symbol(self, repo: PattazRepo) -> None:
        holdings = repo.load_holdings()
        pairs = [(h.account, h.symbol) for h in holdings]
        assert len(pairs) == len(set(pairs))
        assert len(repo.load_holdings_history()) > len(holdings)

    def test_csv_snapshot_21sep_is_newest(self, repo: PattazRepo) -> None:
        """db/holdings/household_equity_21sep2026.csv supersedes the ledger rows."""
        hdfc = {h.account: h for h in repo.get_holdings_for("HDFCBANK")}
        assert hdfc["ZERODHA_P"].qty == 126
        assert hdfc["ZERODHA_P"].as_of == "2026-09-21"
        assert hdfc["ZERODHA_P"].source == "CSV:household_equity_21sep2026.csv"
        assert hdfc["INTEGRATED_P"].qty == 29 and hdfc["INTEGRATED_V"].qty == 29

    def test_muthootfin_household_total(self, repo: PattazRepo) -> None:
        holdings = repo.get_holdings_for("MUTHOOTFIN")
        assert sum(h.qty for h in holdings) == 16
        ledger = [h for h in repo.load_holdings_history()
                  if h.symbol == "MUTHOOTFIN" and h.avg_cost is not None]
        assert ledger and ledger[0].avg_cost == Decimal("2942.63")

    def test_absent_from_snapshot_is_recorded_exit(self, repo: PattazRepo) -> None:
        jio = {h.account: h for h in repo.get_holdings_for("JIOFIN")}
        assert jio["INTEGRATED_V"].qty == 0
        assert jio["INTEGRATED_V"].as_of == "2026-09-21"
        assert ("INTEGRATED_V", "JIOFIN") not in repo.held_pairs()

    def test_holding_cost_is_decimal_or_none(self, repo: PattazRepo) -> None:
        for h in repo.load_holdings():
            if h.avg_cost is not None:
                assert isinstance(h.avg_cost, Decimal), f"{h.symbol} avg_cost not Decimal"


class TestCells:
    def test_load_cells_count(self, repo: PattazRepo) -> None:
        cells = repo.load_cells()
        assert len(cells) == 24

    def test_gold_nbfc_full(self, repo: PattazRepo) -> None:
        cells = repo.load_cells()
        gold_nbfc = [c for c in cells if c.cell == "GOLD_NBFC"]
        assert len(gold_nbfc) == 1
        assert gold_nbfc[0].is_full is True


class TestDecisions:
    def test_load_decisions_count(self, repo: PattazRepo) -> None:
        decisions = repo.load_decisions()
        assert len(decisions) == 64

    def test_open_decisions(self, repo: PattazRepo) -> None:
        open_d = repo.load_decisions(status="OPEN")
        assert len(open_d) > 0
        assert all(d.status == "OPEN" for d in open_d)


class TestSessions:
    def test_append_and_read(self, repo: PattazRepo) -> None:
        repo.append_session(
            run_id="test-run-001",
            ran_at="2026-09-19T10:00:00Z",
            usecase="UC1_MORNING_BOARD",
            inputs={"gsec": 7.04},
            outputs={"board": []},
            drops=[{"symbol": "ONGC", "reason": "P1_SOVEREIGN"}],
            rules_fired=["E3_FRESHNESS", "OVERLAY_P1"],
        )
        row = repo._con.execute(
            "SELECT * FROM sessions WHERE run_id = ?", ("test-run-001",)
        ).fetchone()
        assert row is not None
        assert row["usecase"] == "UC1_MORNING_BOARD"


class TestSchemaVersion:
    def test_version_is_1(self, repo: PattazRepo) -> None:
        assert repo.schema_version() == 1


class TestTickerVerification:
    def test_names_needing_verification(self, repo: PattazRepo) -> None:
        names = repo.names_needing_ticker_verification()
        assert len(names) > 0
        assert all(n.yf_ticker is not None for n in names)
        assert all(not n.ticker_verified for n in names)

    def test_names_without_ticker(self, repo: PattazRepo) -> None:
        no_ticker = repo.names_without_ticker()
        assert len(no_ticker) > 0
        assert all(n.yf_ticker is None for n in no_ticker)

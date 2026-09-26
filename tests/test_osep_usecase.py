"""tests/test_osep_usecase.py — UC4 flow on a scratch register, no network.

analyse → judge → apply (append-only log + register) and the October re-derive.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from store.repo import PattazRepo
from tools.company_data import (
    CompanyFacts,
    newest_balance,
    parse_screener_promoters,
    parse_screener_quarterly_eps,
)
from tools.fundamentals import FundamentalsSnapshot
from tools.prices import PriceSnapshot
from tools.stamped import Stamped
from usecases.osep import (
    apply_report,
    format_rederive,
    format_report,
    record_judgment,
    rederive_board,
    run_osep,
)

D = Decimal
NOW = "2026-09-26T10:00:00+00:00"


def st(v):  # type: ignore[no-untyped-def]
    return Stamped(value=v, source="test", as_of=NOW)


PRICE = PriceSnapshot(symbol="RSYSTEMS", price=st(D("235.62")), low_52w=st(D("213.52")),
                      high_52w=st(D("435.9")))
FUND = FundamentalsSnapshot(symbol="RSYSTEMS", pe_trailing=st(D("15.14")),
                            pb_ratio=st(D("2.54")), eps_ttm=st(D("15.56")),
                            book_value_ps=st(D("92.69")), roe_pct=st(D("17.33")))
FACTS = CompanyFacts(
    symbol="RSYSTEMS",
    promoter_pct=st((D("51.93"), D("51.90"), D("51.89"), D("51.88"), D("51.85"))),
    promoter_periods=("Jun 2025", "Sep 2025", "Dec 2025", "Mar 2026", "Jun 2026"),
    total_debt=st(D("2708480000")), equity=st(D("10982680000")),
    net_income=st((D(1862), D(1312), D(1401), D(1397))),
    revenue=st((D(19582), D(17417), D(16845), D(15158))),
    ocf=st((D(2199), D(2353), D(2114), D(964))),
    business=st("digital product engineering"), eps_ttm_reported=st(D("16.27")))
SRC = "test underwrite"


def _judge_all(db: Path) -> None:
    for item, val in [("sovereign_directed", "false"), ("thesis_verifiable", "true"),
                      ("governance_clean", "true"), ("industry_durable", "true"),
                      ("investable", "true"), ("stage1_score", "36"),
                      ("thesis_type", "RE-RATING")]:
        record_judgment(db, "RSYSTEMS", item, val, SRC, today="2026-09-26")


def _run(db: Path, **kw):  # type: ignore[no-untyped-def]
    return run_osep(db, "RSYSTEMS", today="2026-09-26", price=PRICE, fundamentals=FUND,
                    facts=FACTS, gsec_override=D("7.119"), **kw)


class TestParsers:
    HTML = ('<section id="quarterly-shp"><table><thead><tr><th></th><th>Mar 2026</th>'
            '<th>Jun 2026</th></tr></thead><tr><td>Promoters</td><td>51.85%</td>'
            '<td>51.85%</td></tr></table></section>'
            '<section id="quarters"><table><thead><tr><th></th><th>Sep 2025</th>'
            '<th>Dec 2025</th><th>Mar 2026</th><th>Jun 2026</th></tr></thead>'
            '<tr><td>EPS in Rs</td><td>2.98</td><td>3.08</td><td>5.52</td><td>4.69</td>'
            '</tr></table></section>')

    def test_promoters(self) -> None:
        periods, pct = parse_screener_promoters(self.HTML)
        assert periods == ("Mar 2026", "Jun 2026") and pct == (D("51.85"), D("51.85"))

    def test_quarterly_eps(self) -> None:
        _, eps = parse_screener_quarterly_eps(self.HTML)
        assert sum(eps[-4:], D(0)) == D("16.27")

    def test_missing_sections(self) -> None:
        assert parse_screener_promoters("<html/>") == ((), ())
        assert parse_screener_quarterly_eps("<html/>") == ((), ())

    def test_newest_balance_prefers_quarter_and_drops_leases(self) -> None:
        annual = pd.DataFrame({pd.Timestamp("2025-12-31"): [7916e6, 4098e6, 952e6]},
                              index=["Stockholders Equity", "Total Debt",
                                     "Capital Lease Obligations"])
        quarterly = pd.DataFrame({pd.Timestamp("2026-06-30"): [10983e6, 3660e6, 952e6]},
                                 index=["Stockholders Equity", "Total Debt",
                                        "Capital Lease Obligations"])
        eq, debt, period = newest_balance(annual, quarterly)
        assert period == "2026-06-30" and eq == D(10983000000) and debt == D(2708000000)


class TestFlow:
    def test_unjudged_is_incomplete_and_cannot_be_applied(self, scratch_db: Path) -> None:
        with PattazRepo(scratch_db) as repo:
            repo._con.execute("DELETE FROM osep_judgments")
            repo._con.commit()
        rep = _run(scratch_db)
        assert rep.verdict.bucket.value == "INCOMPLETE"
        with pytest.raises(ValueError, match="not a verdict"):
            apply_report(scratch_db, rep, "try")

    def test_judged_run_uses_reported_eps(self, scratch_db: Path) -> None:
        _judge_all(scratch_db)
        rep = _run(scratch_db)
        assert rep.verdict.bucket.value == "GBL"
        assert rep.verdict.trigger == D("228.59")        # 14.05 x 16.27, not Yahoo's 15.56
        text = format_report(rep)
        assert text.splitlines()[1].startswith("VERDICT: GOOD BUY LATER")
        assert "was: GBN" in text

    def test_session_row_written(self, scratch_db: Path) -> None:
        rep = _run(scratch_db)
        with PattazRepo(scratch_db) as repo:
            row = repo._con.execute("SELECT usecase FROM sessions WHERE run_id = ?",
                                    (rep.run_id,)).fetchone()
        assert row["usecase"] == "UC4_OSEP"

    def test_judgment_needs_source_and_known_item(self, scratch_db: Path) -> None:
        with pytest.raises(ValueError, match="source"):
            record_judgment(scratch_db, "RSYSTEMS", "stage1_score", "40", " ")
        with pytest.raises(ValueError, match="unknown judgment"):
            record_judgment(scratch_db, "RSYSTEMS", "vibes", "good", SRC)
        with pytest.raises(ValueError, match="thesis_type"):
            record_judgment(scratch_db, "RSYSTEMS", "thesis_type", "MOMENTUM", SRC)

    def test_apply_logs_change_and_updates_register(self, scratch_db: Path) -> None:
        _judge_all(scratch_db)
        rep = _run(scratch_db, record_session=False)
        apply_report(scratch_db, rep, "reported EPS 16.27 (minority interest removed)")
        with PattazRepo(scratch_db) as repo:
            log = repo.load_verdict_log("RSYSTEMS")
            n = repo.get_name("RSYSTEMS")
            trig = next(t for t in repo.load_triggers() if t.symbol == "RSYSTEMS")
            thesis = repo._con.execute("SELECT thesis_type FROM names WHERE symbol='RSYSTEMS'"
                                       ).fetchone()[0]
        assert [(r["old_bucket"], r["new_bucket"]) for r in log] == [("GBN", "GBL")]
        assert "minority" in log[0]["reason"]
        assert n is not None and n.bucket == "GBL" and n.decay_expiry == "2026-12-25"
        assert n.status == "ADD"                      # status stays Praveen's call
        assert trig.level == D("228.59") and trig.basis_eps_date == "2026-09-26"
        assert thesis == "RE-RATING"

    def test_apply_needs_a_reason(self, scratch_db: Path) -> None:
        _judge_all(scratch_db)
        rep = _run(scratch_db, record_session=False)
        with pytest.raises(ValueError, match="reason"):
            apply_report(scratch_db, rep, "  ")


class TestRederive:
    def test_board_recomputed_without_writes(self, scratch_db: Path) -> None:
        funds = {"RSYSTEMS": FUND}
        rows = rederive_board(scratch_db, today="2026-09-26", fundamentals=funds,
                              reported_eps={"RSYSTEMS": D("16.27")},
                              gsec_override=D("7.119"))
        r = next(x for x in rows if x.symbol == "RSYSTEMS")
        assert r.old == D(251) and r.new == D("228.59") and r.change_pct == D("-8.9")
        missing = [x for x in rows if x.symbol != "RSYSTEMS"]
        assert all(x.new is None and x.basis == "fundamentals missing" for x in missing)
        assert "RSYSTEMS" in format_rederive(rows)
        with PattazRepo(scratch_db) as repo:
            t = next(t for t in repo.load_triggers() if t.symbol == "RSYSTEMS")
        assert t.level == D(251)                        # no writes

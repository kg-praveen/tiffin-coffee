"""tests/test_kite_sync.py — UC2.1 Kite path (Zerodha, ZERODHA_P) with a mocked
KiteConnect and a recorded holdings fixture. No network; register = scratch_db.

Spec: sync-holdings skill steps 1-5, CLAUDE.md §3 (snapshot semantics) and §6 (read
scope only; login never automated; daily token expires).
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar

import pytest
from kiteconnect.exceptions import TokenException  # type: ignore[import-untyped]

import tools.kite as kite
from store.repo import PattazRepo
from tools.kite import (
    KiteCredentials,
    exchange_request_token,
    fetch_holdings,
    load_cached_token,
    login_url,
    parse_holdings,
    save_token,
)
from usecases.sync_holdings import (
    KiteSyncRefused,
    format_sync,
    main,
    map_kite_symbols,
    possible_renames,
    run_sync_holdings_kite,
)

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = "2026-09-26"
RAW: list[dict[str, Any]] = json.loads(
    (FIXTURES / "kite_holdings_26sep2026.json").read_text()
)["holdings"]


class FakeKite:
    """Stands in for kiteconnect.KiteConnect — records every method called."""

    calls: ClassVar[list[str]] = []

    def __init__(self, api_key: str, access_token: str | None = None) -> None:
        self.api_key = api_key
        self.access_token = access_token

    def login_url(self) -> str:
        FakeKite.calls.append("login_url")
        return f"https://kite.zerodha.com/connect/login?api_key={self.api_key}&v=3"

    def generate_session(self, request_token: str, api_secret: str) -> dict[str, str]:
        FakeKite.calls.append("generate_session")
        assert request_token == "REQ123"  # noqa: S105 - fake test token
        assert api_secret == "sekrit"  # noqa: S105 - fake test secret
        return {"access_token": "ACCESS_TODAY", "user_id": "AB1234"}

    def holdings(self) -> list[dict[str, Any]]:
        FakeKite.calls.append("holdings")
        assert self.access_token == "ACCESS_TODAY"  # noqa: S105 - fake
        return RAW

    def positions(self) -> dict[str, list[dict[str, Any]]]:
        FakeKite.calls.append("positions")
        return {"net": [], "day": []}


class ExpiredKite(FakeKite):
    """Kite answering with an expired/invalid access token."""

    def holdings(self) -> list[dict[str, Any]]:
        FakeKite.calls.append("holdings")
        raise TokenException("Incorrect `api_key` or `access_token`.")


@pytest.fixture(autouse=True)
def _reset_calls() -> None:
    FakeKite.calls = []


CREDS = KiteCredentials("key1", "sekrit")


# ---------------------------------------------------------------- adapter ---
class TestKiteAdapter:
    def test_login_url_is_printed_not_followed(self) -> None:
        url = login_url("key1", factory=FakeKite)
        assert url.startswith("https://kite.zerodha.com/connect/login?api_key=key1")
        assert FakeKite.calls == ["login_url"]

    def test_exchange_caches_token_for_today_only(self, tmp_path: Path) -> None:
        tf = tmp_path / ".kite_access.token"
        tok = exchange_request_token(CREDS, "REQ123", factory=FakeKite, today=TODAY,
                                     token_file=tf)
        assert tok == "ACCESS_TODAY"
        assert load_cached_token(TODAY, tf) == "ACCESS_TODAY"
        assert load_cached_token("2026-09-27", tf) is None        # next IST day: expired
        assert oct(tf.stat().st_mode & 0o777) == "0o600"

    def test_exchange_can_skip_cache(self, tmp_path: Path) -> None:
        exchange_request_token(CREDS, "REQ123", factory=FakeKite, token_file=None)
        assert not list(tmp_path.iterdir())

    def test_missing_or_corrupt_cache_is_expired(self, tmp_path: Path) -> None:
        tf = tmp_path / "x.token"
        assert load_cached_token(TODAY, tf) is None
        tf.write_text("not json")
        assert load_cached_token(TODAY, tf) is None
        save_token("", TODAY, tf)
        assert load_cached_token(TODAY, tf) is None

    def test_parse_holdings_stamps_and_counts_t1(self) -> None:
        snap = parse_holdings(RAW, TODAY)
        by = {h.tradingsymbol: h for h in snap.rows}
        assert snap.source == "KITE_API" and snap.as_of == TODAY
        assert by["HDFCBANK"].qty.value == 126                     # 120 settled + 6 T1
        assert by["RECLTD"].qty.value == 10                        # all T1
        assert by["HDFCBANK"].avg_price is not None
        assert by["HDFCBANK"].avg_price.value == Decimal("1612.46")
        assert by["HDFCBANK"].qty.source == "KITE_API"
        assert by["HDFCBANK"].qty.as_of == TODAY
        assert "INFY" not in by                                    # qty 0 row: sold

    def test_qty_decision_settled_plus_t1_only(self) -> None:
        """Recorded decision (KiteHolding docstring): qty = quantity + t1_quantity;
        collateral_quantity is NOT added and used_quantity is NOT subtracted — pledged
        rows are named in `pledged` for Praveen's OPEN QUESTION."""
        raw = [{"tradingsymbol": "ITC", "exchange": "NSE", "isin": "X", "quantity": 100,
                "t1_quantity": 5, "collateral_quantity": 40, "used_quantity": 7,
                "average_price": 400.0},
               {"tradingsymbol": "NTPC", "exchange": "NSE", "isin": "Y", "quantity": 10,
                "t1_quantity": 0, "collateral_quantity": 0, "used_quantity": 0,
                "average_price": 300.0}]
        snap = parse_holdings(raw, TODAY)
        by = {h.tradingsymbol: h for h in snap.rows}
        assert by["ITC"].qty.value == 105
        assert by["NTPC"].qty.value == 10
        assert snap.pledged == ["ITC"]
        assert parse_holdings(RAW, TODAY).pledged == []

    def test_clear_cached_token(self, tmp_path: Path) -> None:
        tf = tmp_path / ".kite_access.token"
        save_token("T", TODAY, tf)
        kite.clear_cached_token(tf)
        assert not tf.exists()
        kite.clear_cached_token(tf)                                # missing: no error

    def test_is_token_error(self) -> None:
        assert kite.is_token_error(TokenException("expired"))
        assert not kite.is_token_error(ConnectionError("x"))

    def test_fetch_holdings_reads_only(self) -> None:
        snap = fetch_holdings("key1", "ACCESS_TODAY", factory=FakeKite, today=TODAY)
        assert len(snap.rows) == 8
        assert FakeKite.calls == ["holdings"]

    def test_load_credentials_from_env_file(self, tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KITE_API_KEY", raising=False)
        monkeypatch.delenv("KITE_API_SECRET", raising=False)
        env = tmp_path / ".env"
        env.write_text("KITE_API_KEY=abc\nKITE_API_SECRET=def\n")
        c = kite.load_credentials(env)
        assert (c.api_key, c.api_secret) == ("abc", "def")

    def test_load_credentials_missing_raises(self, tmp_path: Path,
                                             monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KITE_API_KEY", raising=False)
        monkeypatch.delenv("KITE_API_SECRET", raising=False)
        env = tmp_path / ".env"
        env.write_text("")
        with pytest.raises(RuntimeError, match="KITE_API_KEY"):
            kite.load_credentials(env)


class TestReadScopeOnly:
    """CLAUDE.md §6 — the adapter source names no write endpoint at all."""

    def test_no_write_endpoints_in_adapter(self) -> None:
        src = Path(kite.__file__).read_text()
        forbidden = re.compile(r"(place|modify|cancel|exit)_(order|gtt)|_gtt\(")
        assert not forbidden.search(src)

    def test_kite_calls_are_whitelisted(self) -> None:
        src = Path(kite.__file__).read_text()
        called = set(re.findall(r"factory\([^)]*\)\.(\w+)\(", src))
        assert called == {"login_url", "generate_session", "holdings", "positions"}

    def test_token_file_is_git_ignored(self) -> None:
        gi = (Path(kite.__file__).parent.parent / ".gitignore").read_text().split()
        assert "*.token" in gi and kite.TOKEN_FILE.name.endswith(".token")


# ---------------------------------------------------------------- mapping ---
class TestSymbolMapping:
    def test_yf_stem_maps_to_register_symbol(self, scratch_db: Path) -> None:
        repo = PattazRepo(scratch_db)
        try:
            names = repo.load_names()
        finally:
            repo.close()
        mapping, unknown = map_kite_symbols(["RECLTD", "HDFCBANK", "TMCV", "ETERNAL"], names)
        assert mapping["RECLTD"] == "REC"
        assert mapping["HDFCBANK"] == "HDFCBANK"
        assert mapping["TMCV"] == "TMCV"                           # no yf_ticker: symbol match
        assert unknown == ["ETERNAL"]
        assert mapping["ETERNAL"] == "ETERNAL"                      # kept, reported


# ---------------------------------------------------------------- usecase ---
def _newest(db: Path) -> dict[tuple[str, str], tuple[int, str, str]]:
    repo = PattazRepo(db)
    try:
        return {(h.account, h.symbol): (h.qty, h.source, h.as_of) for h in repo.load_holdings()}
    finally:
        repo.close()


def _session(db: Path, run_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    repo = PattazRepo(db)
    try:
        row = repo._con.execute(
            "SELECT usecase, inputs_json, outputs_json FROM sessions WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    finally:
        repo.close()
    assert row is not None and row["usecase"] == "UC2_1_SYNC_HOLDINGS"
    return json.loads(row["inputs_json"]), json.loads(row["outputs_json"])


class TestRunSyncHoldingsKite:
    def test_writes_zerodha_snapshot_with_exits(self, scratch_db: Path) -> None:
        before = _newest(scratch_db)
        snap = parse_holdings(RAW, TODAY)
        r = run_sync_holdings_kite(scratch_db, snapshot=snap, fetch_prices=False)
        after = _newest(scratch_db)

        assert r.source == "KITE_API" and r.as_of == TODAY
        assert after[("ZERODHA_P", "HDFCBANK")] == (126, "KITE_API", TODAY)
        assert after[("ZERODHA_P", "REC")] == (10, "KITE_API", TODAY)
        assert after[("ZERODHA_P", "ETERNAL")][0] == 5
        assert sorted(r.unknown_symbols) == ["ETERNAL", "SUNTV"]
        assert r.symbol_map == {"RECLTD": "REC"}
        # previously held in Zerodha but absent from Kite → qty 0 recorded exit
        assert before[("ZERODHA_P", "INFY")][0] > 0
        assert after[("ZERODHA_P", "INFY")] == (0, "KITE_API", TODAY)
        assert after[("ZERODHA_P", "ASHOKLEY")][0] == 0
        assert r.exits_recorded > 0
        assert r.rows_written == 8 + r.exits_recorded

    def test_integrated_accounts_untouched(self, scratch_db: Path) -> None:
        before = {k: v for k, v in _newest(scratch_db).items() if k[0] != "ZERODHA_P"}
        run_sync_holdings_kite(scratch_db, snapshot=parse_holdings(RAW, TODAY),
                               fetch_prices=False)
        after = {k: v for k, v in _newest(scratch_db).items() if k[0] != "ZERODHA_P"}
        assert before == after

    def test_session_row_written(self, scratch_db: Path) -> None:
        r = run_sync_holdings_kite(scratch_db, snapshot=parse_holdings(RAW, TODAY),
                                   fetch_prices=False)
        repo = PattazRepo(scratch_db)
        try:
            row = repo._con.execute(
                "SELECT usecase, inputs_json FROM sessions WHERE run_id = ?", (r.run_id,)
            ).fetchone()
        finally:
            repo.close()
        assert row["usecase"] == "UC2_1_SYNC_HOLDINGS"
        inputs = json.loads(row["inputs_json"])
        assert inputs["source"] == "KITE_API"
        assert inputs["account"] == "ZERODHA_P"
        assert sorted(inputs["unknown_symbols"]) == ["ETERNAL", "SUNTV"]

    def test_fetch_callable_is_used(self, scratch_db: Path) -> None:
        r = run_sync_holdings_kite(
            scratch_db,
            fetch=lambda: fetch_holdings("key1", "ACCESS_TODAY", factory=FakeKite, today=TODAY),
            fetch_prices=False,
        )
        assert r.as_of == TODAY and FakeKite.calls == ["holdings"]

    def test_empty_kite_snapshot_fails_closed(self, scratch_db: Path) -> None:
        """E9: an empty API answer must not zero the whole Zerodha book silently."""
        before = _newest(scratch_db)
        with pytest.raises(KiteSyncRefused, match="empty") as ei:
            run_sync_holdings_kite(scratch_db, snapshot=parse_holdings([], TODAY),
                                   fetch_prices=False)
        assert _newest(scratch_db) == before
        # CLAUDE.md §3 / E8: the refusal still appends a session (NO ACTION)
        inputs, outputs = _session(scratch_db, ei.value.run_id)
        assert inputs["source"] == "KITE_API" and inputs["rows_written"] == 0
        assert outputs["verdict"] == "NO ACTION"
        assert "empty" in str(outputs["refused"])

    def test_fetch_exception_fails_closed_with_session(self, scratch_db: Path) -> None:
        before = _newest(scratch_db)

        def boom() -> Any:
            raise ConnectionError("network down")

        with pytest.raises(KiteSyncRefused, match="ConnectionError") as ei:
            run_sync_holdings_kite(scratch_db, fetch=boom, fetch_prices=False)
        assert isinstance(ei.value.__cause__, ConnectionError)
        assert _newest(scratch_db) == before
        inputs, outputs = _session(scratch_db, ei.value.run_id)
        assert inputs["rows_written"] == 0 and outputs["verdict"] == "NO ACTION"

    def test_token_exception_fails_closed_with_session(self, scratch_db: Path) -> None:
        before = _newest(scratch_db)
        with pytest.raises(KiteSyncRefused, match="TokenException") as ei:
            run_sync_holdings_kite(
                scratch_db,
                fetch=lambda: fetch_holdings("key1", "STALE", factory=ExpiredKite, today=TODAY),
                fetch_prices=False,
            )
        assert kite.is_token_error(ei.value.__cause__)  # type: ignore[arg-type]
        assert _newest(scratch_db) == before
        _, outputs = _session(scratch_db, ei.value.run_id)
        assert outputs["verdict"] == "NO ACTION"

    def test_possible_rename_reported(self, scratch_db: Path) -> None:
        """A ZERODHA_P exit and an unknown symbol in one sync → POSSIBLE RENAME line."""
        r = run_sync_holdings_kite(scratch_db, snapshot=parse_holdings(RAW, TODAY),
                                   fetch_prices=False)
        assert len(r.possible_renames) == 1
        assert "INFY" in r.possible_renames[0] and "ETERNAL" in r.possible_renames[0]
        out = format_sync(r)
        assert "POSSIBLE RENAME" in out
        _, outputs = _session(scratch_db, r.run_id)
        assert outputs["possible_renames"] == r.possible_renames

    def test_possible_renames_needs_both_sides(self) -> None:
        assert possible_renames([], ["ETERNAL"]) == []
        assert possible_renames(["ZOMATO"], []) == []
        assert possible_renames(["ZOMATO"], ["ETERNAL"]) == [
            "exit(s) ZOMATO alongside unknown Kite symbol(s) ETERNAL"
        ]

    def test_open_questions_printed_and_recorded(self, scratch_db: Path) -> None:
        r = run_sync_holdings_kite(scratch_db, snapshot=parse_holdings(RAW, TODAY),
                                   fetch_prices=False)
        out = format_sync(r)
        oq = [ln for ln in out.splitlines() if ln.startswith("OPEN QUESTION for Praveen:")]
        assert len(oq) == 2
        assert any("pledged" in ln for ln in oq)
        assert any("CSV" in ln and "ZERODHA_P" in ln for ln in oq)
        _, outputs = _session(scratch_db, r.run_id)
        assert outputs["open_questions"] == r.open_questions

    def test_needs_snapshot_or_fetch(self, scratch_db: Path) -> None:
        with pytest.raises(ValueError):
            run_sync_holdings_kite(scratch_db, fetch_prices=False)

    def test_report_names_unknowns(self, scratch_db: Path) -> None:
        r = run_sync_holdings_kite(scratch_db, snapshot=parse_holdings(RAW, TODAY),
                                   fetch_prices=False)
        out = format_sync(r)
        assert "KITE_API" in out
        assert "UNKNOWN KITE SYMBOLS" in out and "ETERNAL" in out
        assert "RECLTD -> REC" in out


# -------------------------------------------------------------------- CLI ---
class TestCli:
    def test_login_url_prints_and_exits(self, monkeypatch: pytest.MonkeyPatch,
                                        capsys: pytest.CaptureFixture[str]) -> None:
        monkeypatch.setattr(kite, "load_credentials", lambda *a, **k: CREDS)
        monkeypatch.setattr(kite, "_default_factory", FakeKite)
        assert main(["kite", "--login-url"]) == 0
        assert "api_key=key1" in capsys.readouterr().out
        assert FakeKite.calls == ["login_url"]

    def test_request_token_syncs(self, scratch_db: Path, tmp_path: Path,
                                 monkeypatch: pytest.MonkeyPatch,
                                 capsys: pytest.CaptureFixture[str]) -> None:
        monkeypatch.setattr(kite, "load_credentials", lambda *a, **k: CREDS)
        monkeypatch.setattr(kite, "_default_factory", FakeKite)
        monkeypatch.setattr(kite, "TOKEN_FILE", tmp_path / ".kite_access.token")
        monkeypatch.setattr(kite, "ist_today", lambda: TODAY)
        rc = main(["--db", str(scratch_db), "kite", "--request-token", "REQ123", "--no-prices"])
        assert rc == 0
        assert FakeKite.calls == ["generate_session", "holdings"]
        out = capsys.readouterr().out
        assert "ACCESS_TODAY" not in out                            # token never printed
        assert _newest(scratch_db)[("ZERODHA_P", "REC")][0] == 10

    def test_no_token_and_no_cache_asks_for_login(self, scratch_db: Path, tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch,
                                                  capsys: pytest.CaptureFixture[str]) -> None:
        monkeypatch.setattr(kite, "load_credentials", lambda *a, **k: CREDS)
        monkeypatch.setattr(kite, "_default_factory", FakeKite)
        monkeypatch.setattr(kite, "TOKEN_FILE", tmp_path / "none.token")
        rc = main(["--db", str(scratch_db), "kite", "--no-prices"])
        assert rc == 2
        assert "request_token" in capsys.readouterr().out
        assert "holdings" not in FakeKite.calls

    def test_expired_token_clears_cache_and_asks_for_login(
        self, scratch_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Kite TokenException → session recorded, cached token deleted, login URL
        printed again, request token asked for; nothing written (E9)."""
        tf = tmp_path / ".kite_access.token"
        save_token("STALE", TODAY, tf)
        monkeypatch.setattr(kite, "load_credentials", lambda *a, **k: CREDS)
        monkeypatch.setattr(kite, "_default_factory", ExpiredKite)
        monkeypatch.setattr(kite, "TOKEN_FILE", tf)
        monkeypatch.setattr(kite, "ist_today", lambda: TODAY)
        before = _newest(scratch_db)
        rc = main(["--db", str(scratch_db), "kite", "--no-prices"])
        assert rc == 2
        assert not tf.exists()
        out = capsys.readouterr().out
        assert "NO ACTION" in out
        assert "request_token" in out and "api_key=key1" in out
        assert "STALE" not in out                                   # token never printed
        assert FakeKite.calls == ["holdings", "login_url"]
        assert _newest(scratch_db) == before

    def test_non_token_failure_reraises(
        self, scratch_db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        tf = tmp_path / ".kite_access.token"
        save_token("ACCESS_TODAY", TODAY, tf)

        class DownKite(FakeKite):
            def holdings(self) -> list[dict[str, Any]]:
                raise ConnectionError("down")

        monkeypatch.setattr(kite, "load_credentials", lambda *a, **k: CREDS)
        monkeypatch.setattr(kite, "_default_factory", DownKite)
        monkeypatch.setattr(kite, "TOKEN_FILE", tf)
        monkeypatch.setattr(kite, "ist_today", lambda: TODAY)
        with pytest.raises(KiteSyncRefused):
            main(["--db", str(scratch_db), "kite", "--no-prices"])
        assert tf.exists()                                          # token kept

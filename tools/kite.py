"""tools/kite.py — READ-ONLY Kite Connect adapter for the Zerodha account (UC2.1).

Spec: sync-holdings skill step 1 and step 5, CLAUDE.md §6 (safety — read scope only:
holdings, positions, funds, GTT list; secrets via .env; the daily access token is
obtained per session from a request token Praveen pastes back; login is never
automated and passwords are never stored).

This module only ever calls: login_url, generate_session, holdings, positions.
It never imports or calls any order or GTT write endpoint (CI greps for them).
The daily access token may be cached in a git-ignored file (`*.token`), stamped with
its IST issue date; a token from any earlier IST day is treated as expired.
"""
from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from tools.stamped import Stamped

log = logging.getLogger(__name__)

KITE_SOURCE = "KITE_API"
ZERODHA_ACCOUNT = "ZERODHA_P"
REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = REPO_ROOT / ".kite_access.token"      # git-ignored via `*.token`
_IST = timezone(timedelta(hours=5, minutes=30))
_Q2 = Decimal("0.01")

ClientFactory = Callable[..., Any]


def _default_factory(api_key: str, access_token: str | None = None) -> Any:
    from kiteconnect import KiteConnect  # type: ignore[import-untyped]  # lazy: no net in tests

    return KiteConnect(api_key=api_key, access_token=access_token)


def ist_today() -> str:
    """Today's date in IST — the Kite token and holdings snapshot are IST-day scoped."""
    return datetime.now(_IST).date().isoformat()


@dataclass(frozen=True)
class KiteCredentials:
    api_key: str
    api_secret: str


def load_credentials(env_path: str | Path | None = None) -> KiteCredentials:
    """KITE_API_KEY / KITE_API_SECRET from .env (CLAUDE.md §6; see .env.example)."""
    load_dotenv(env_path or REPO_ROOT / ".env")
    key = os.environ.get("KITE_API_KEY", "").strip()
    secret = os.environ.get("KITE_API_SECRET", "").strip()
    if not key or not secret:
        raise RuntimeError("KITE_API_KEY / KITE_API_SECRET missing — fill .env (see .env.example)")
    return KiteCredentials(key, secret)


def login_url(api_key: str, factory: ClientFactory = _default_factory) -> str:
    """The Kite login URL Praveen opens in his own browser (skill step 1)."""
    return str(factory(api_key).login_url())


# ------------------------------------------------------------- token cache ---
def save_token(access_token: str, issued_on: str, token_file: Path = TOKEN_FILE) -> None:
    """Cache today's access token (owner-read only). Never logged."""
    token_file.write_text(json.dumps({"access_token": access_token, "issued_on": issued_on}))
    token_file.chmod(0o600)


def clear_cached_token(token_file: Path = TOKEN_FILE) -> None:
    """Delete the cached token (Kite rejected it: expired/invalid). Missing file is fine."""
    token_file.unlink(missing_ok=True)


def is_token_error(exc: BaseException) -> bool:
    """True when `exc` is kiteconnect's TokenException (expired/invalid access token).

    Lazy import so tests and the rest of the repo never need kiteconnect loaded; if the
    package is absent, fall back to the class name (same fail-closed outcome: re-login).
    """
    try:
        from kiteconnect.exceptions import TokenException  # type: ignore[import-untyped]
    except ImportError:  # pragma: no cover - kiteconnect is a declared dependency
        return type(exc).__name__ == "TokenException"
    return isinstance(exc, TokenException)


def load_cached_token(today: str, token_file: Path = TOKEN_FILE) -> str | None:
    """The cached token only if it was issued on `today` (IST); otherwise expired → None."""
    if not token_file.exists():
        return None
    try:
        data = json.loads(token_file.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("issued_on") != today or not data.get("access_token"):
        return None
    return str(data["access_token"])


def exchange_request_token(
    creds: KiteCredentials,
    request_token: str,
    factory: ClientFactory = _default_factory,
    today: str | None = None,
    token_file: Path | None = TOKEN_FILE,
) -> str:
    """Exchange the request token Praveen pasted for today's access token (skill step 1).

    Pass token_file=None to keep the token in memory only.
    """
    session = factory(creds.api_key).generate_session(request_token, api_secret=creds.api_secret)
    token = str(session["access_token"])
    if token_file is not None:
        save_token(token, today or ist_today(), token_file)
    log.info("kite session established (token not logged)")
    return token


# ---------------------------------------------------------------- holdings ---
@dataclass(frozen=True)
class KiteHolding:
    """One Kite holdings row, E2-stamped.

    QUANTITY DECISION (sync-holdings skill step 1: "qty = settled + T1"):
      qty = `quantity` + `t1_quantity`.
      - `quantity` is the settled demat quantity; `t1_quantity` is bought but not yet
        settled (T+1) — both are owned, so both count toward household weight/caps.
      - `collateral_quantity` (shares pledged as margin collateral) is NOT added: Kite
        reports it separately from `quantity`, and whether pledged shares count as
        held is Praveen's call (see OPEN QUESTION in the sync output). Rows with
        collateral are named in `KiteHoldingsSnapshot.pledged` so nothing is hidden.
      - `used_quantity` (sold today / blocked for delivery) is NOT subtracted: the
        snapshot is the demat position, a same-day sell shows up on the next sync.
    """

    tradingsymbol: str
    exchange: str
    isin: str | None
    qty: Stamped[int]
    avg_price: Stamped[Decimal] | None


@dataclass(frozen=True)
class KiteHoldingsSnapshot:
    as_of: str
    source: str
    rows: list[KiteHolding] = field(default_factory=list)
    # tradingsymbols with collateral_quantity or used_quantity > 0 (not in qty; reported)
    pledged: list[str] = field(default_factory=list)


def _to_holding(rec: dict[str, Any], as_of: str) -> KiteHolding:
    qty = int(rec.get("quantity") or 0) + int(rec.get("t1_quantity") or 0)
    raw_avg = rec.get("average_price")
    avg = (
        Stamped(value=Decimal(str(raw_avg)).quantize(_Q2), source=KITE_SOURCE, as_of=as_of)
        if raw_avg not in (None, 0, 0.0) else None
    )
    return KiteHolding(
        tradingsymbol=str(rec["tradingsymbol"]).strip().upper(),
        exchange=str(rec.get("exchange") or ""),
        isin=rec.get("isin"),
        qty=Stamped(value=qty, source=KITE_SOURCE, as_of=as_of),
        avg_price=avg,
    )


def parse_holdings(raw: list[dict[str, Any]], as_of: str) -> KiteHoldingsSnapshot:
    """kite.holdings() → stamped rows. Zero-quantity rows (fully sold) are skipped:
    the snapshot semantics record their exit (absence = sold)."""
    rows = [h for h in (_to_holding(r, as_of) for r in raw) if h.qty.value > 0]
    pledged = sorted({
        str(r["tradingsymbol"]).strip().upper() for r in raw
        if int(r.get("collateral_quantity") or 0) > 0 or int(r.get("used_quantity") or 0) > 0
    })
    return KiteHoldingsSnapshot(as_of=as_of, source=KITE_SOURCE, rows=rows, pledged=pledged)


def fetch_holdings(
    api_key: str,
    access_token: str,
    factory: ClientFactory = _default_factory,
    today: str | None = None,
) -> KiteHoldingsSnapshot:
    """Read the Zerodha demat holdings (read scope). as_of = the IST fetch date."""
    raw = factory(api_key, access_token=access_token).holdings()
    return parse_holdings(list(raw), today or ist_today())


def fetch_positions(
    api_key: str,
    access_token: str,
    factory: ClientFactory = _default_factory,
) -> dict[str, Any]:
    """Read open positions (read scope). Returned raw; not written to the register."""
    return dict(factory(api_key, access_token=access_token).positions())

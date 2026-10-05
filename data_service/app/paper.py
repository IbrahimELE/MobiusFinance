"""Paper trading: a simulated cash account per project. Not advice, no broker.

Market orders fill at the latest /quote price. Storage sits behind
`PaperStore` so the JSON files can later be swapped for another backend
(e.g. Möbius storage) without touching the trading rules.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal, Protocol

from pydantic import BaseModel, Field

from .service import InvalidParameter

STARTING_CASH = 100_000.0


# --- contract models ------------------------------------------------------------

class OrderIn(BaseModel):
    project_id: str = "default"
    ticker: str
    side: Literal["buy", "sell"]
    qty: float = Field(gt=0, description="Number of shares (fractions allowed).")


class Order(BaseModel):
    id: str
    ticker: str
    side: Literal["buy", "sell"]
    qty: float
    price: float
    value: float
    created_at: str


class Position(BaseModel):
    ticker: str
    qty: float
    avg_price: float
    price: float
    market_value: float
    pnl: float
    pnl_pct: float = Field(description="Percent, e.g. 1.7 == +1.7 %.")


class Portfolio(BaseModel):
    project_id: str
    cash: float
    positions: list[Position]
    equity: float
    pnl: float = Field(description="equity - starting_cash")
    updated_at: str
    # extras
    starting_cash: float
    realized_pnl: float
    stale_prices: bool = Field(description="True when a position is valued at its last trade price (no quote).")


class Fill(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    qty: float
    price: float
    at: str


class OrderResult(Portfolio):
    """Contract (contracts/paper.md): the portfolio after the order, plus `fill`."""

    fill: Fill
    order: Order = Field(description="Extra: the stored order with id and value.")


class InsufficientCash(InvalidParameter):
    pass


class InsufficientPosition(InvalidParameter):
    pass


# --- storage ----------------------------------------------------------------------

class PaperStore(Protocol):
    def load(self, project_id: str) -> dict | None: ...

    def save(self, project_id: str, account: dict) -> None: ...


class JsonPaperStore:
    """One JSON file per project: {cash, starting_cash, realized_pnl, positions{T:{qty,avg_price,last_price}}, orders[]}."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, project_id: str) -> Path:
        return self.root / f"{project_id}.json"

    def load(self, project_id: str) -> dict | None:
        try:
            return json.loads(self._path(project_id).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def save(self, project_id: str, account: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.root, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(account, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self._path(project_id))


# --- service ----------------------------------------------------------------------

def slug(project_id: str) -> str:
    """Same project naming as agent_service, so both sides mean the same project."""
    s = "".join(c for c in project_id.lower().replace(" ", "-") if c.isalnum() or c in "-_")[:40]
    return s or "default"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _new_account(starting_cash: float = STARTING_CASH) -> dict:
    return {"cash": starting_cash, "starting_cash": starting_cash, "realized_pnl": 0.0, "positions": {}, "orders": []}


class PaperService:
    def __init__(self, store: PaperStore, price_of: Callable[[str], float | None]):
        """`price_of(ticker)` returns the latest price (None when unknown); it may raise for unknown tickers."""
        self.store = store
        self.price_of = price_of
        self._lock = threading.Lock()

    def _account(self, pid: str) -> dict:
        return self.store.load(pid) or _new_account()

    def place(self, req: OrderIn, ticker: str) -> OrderResult:
        pid = slug(req.project_id)
        price = self.price_of(ticker)  # outside the lock: may hit the network
        if not price:
            raise InvalidParameter(f"No price available for {ticker}")
        with self._lock:
            acc = self._account(pid)
            value = round(price * req.qty, 2)
            pos = acc["positions"].get(ticker, {"qty": 0.0, "avg_price": 0.0})
            if req.side == "buy":
                if value > acc["cash"] + 1e-6:
                    raise InsufficientCash(f"Order needs {value:.2f}, cash is {acc['cash']:.2f}")
                new_qty = pos["qty"] + req.qty
                pos["avg_price"] = (pos["qty"] * pos["avg_price"] + value) / new_qty
                pos["qty"] = new_qty
                acc["cash"] = round(acc["cash"] - value, 2)
            else:
                if req.qty > pos["qty"] + 1e-9:
                    raise InsufficientPosition(f"Holding {pos['qty']:g} {ticker}, cannot sell {req.qty:g}")
                acc["realized_pnl"] = round(acc["realized_pnl"] + (price - pos["avg_price"]) * req.qty, 2)
                pos["qty"] = round(pos["qty"] - req.qty, 8)
                acc["cash"] = round(acc["cash"] + value, 2)
            pos["last_price"] = price
            if pos["qty"] > 0:
                acc["positions"][ticker] = pos
            else:
                acc["positions"].pop(ticker, None)
            order = Order(id=uuid.uuid4().hex[:12], ticker=ticker, side=req.side, qty=req.qty,
                          price=price, value=value, created_at=_now())
            acc["orders"].append(order.model_dump())
            self.store.save(pid, acc)
        fill = Fill(ticker=ticker, side=req.side, qty=req.qty, price=price, at=order.created_at)
        return OrderResult(**self.portfolio(pid).model_dump(), fill=fill, order=order)

    def portfolio(self, project_id: str) -> Portfolio:
        pid = slug(project_id)
        acc = self._account(pid)
        positions, stale = [], False
        for t, p in sorted(acc["positions"].items()):
            try:
                price = self.price_of(t)
            except Exception:
                price = None
            if not price:
                price, stale = p.get("last_price") or p["avg_price"], True
            mv = price * p["qty"]
            cost = p["avg_price"] * p["qty"]
            positions.append(Position(
                ticker=t, qty=p["qty"], avg_price=round(p["avg_price"], 4), price=round(price, 4),
                market_value=round(mv, 2), pnl=round(mv - cost, 2),
                pnl_pct=round((mv / cost - 1) * 100, 2) if cost else 0.0,
            ))
        equity = round(acc["cash"] + sum(p.market_value for p in positions), 2)
        return Portfolio(
            project_id=pid, cash=round(acc["cash"], 2), positions=positions, equity=equity,
            pnl=round(equity - acc["starting_cash"], 2), updated_at=_now(),
            starting_cash=acc["starting_cash"], realized_pnl=acc["realized_pnl"], stale_prices=stale,
        )

    def reset(self, project_id: str, starting_cash: float = STARTING_CASH) -> Portfolio:
        if starting_cash <= 0:
            raise InvalidParameter("starting_cash must be positive")
        pid = slug(project_id)
        with self._lock:
            self.store.save(pid, _new_account(starting_cash))
        return self.portfolio(pid)

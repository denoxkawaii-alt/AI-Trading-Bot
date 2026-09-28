import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

@dataclass
class Position:
    symbol: str
    side: str
    quantity: int
    entry: float
    stop_loss: float
    target: float
    risk_per_share: float
    opened_at: str

class PaperTrader:
    """Persistent paper trader with risk cap, daily limit, cooldown and duplicate guard."""
    def __init__(self, capital=10000.0, max_risk_per_trade=150.0, max_daily_trades=2,
                 cooldown_minutes=30, ledger_path="trades.csv", state_path="trader_state.json", min_rr=1.5):
        if capital <= 0 or max_risk_per_trade <= 0 or max_daily_trades <= 0 or cooldown_minutes < 0 or min_rr <= 0:
            raise ValueError("Invalid PaperTrader configuration.")
        self.initial_capital=float(capital); self.cash=float(capital)
        self.max_risk_per_trade=float(max_risk_per_trade); self.max_daily_trades=int(max_daily_trades)
        self.cooldown_minutes=int(cooldown_minutes); self.min_rr=float(min_rr)
        self.positions: dict[str, Position]={}; self.daily_trade_count=0; self.last_trade_time: Optional[datetime]=None
        self.ledger_path=Path(ledger_path); self.state_path=Path(state_path)
        self._ensure_ledger(); self._load_state(); self._reset_daily_counter_if_needed()

    def _ensure_ledger(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            with self.ledger_path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["timestamp","symbol","side","quantity","entry","stop_loss","target","exit","pnl"])

    def _save_state(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        data={"cash":self.cash,"daily_trade_count":self.daily_trade_count,
              "last_trade_time":self.last_trade_time.isoformat() if self.last_trade_time else None,
              "positions":{k:asdict(v) for k,v in self.positions.items()}}
        tmp=self.state_path.with_suffix(".tmp")
        with tmp.open("w",encoding="utf-8") as f: json.dump(data,f,indent=2)
        tmp.replace(self.state_path)

    def _load_state(self):
        if not self.state_path.exists(): return
        try:
            with self.state_path.open("r",encoding="utf-8") as f: data=json.load(f)
            self.cash=float(data.get("cash",self.initial_capital))
            self.daily_trade_count=int(data.get("daily_trade_count",0))
            last=data.get("last_trade_time")
            if last:
                self.last_trade_time=datetime.fromisoformat(last)
                if self.last_trade_time.tzinfo is None:
                    self.last_trade_time=self.last_trade_time.replace(tzinfo=timezone.utc)
            for sym,p in data.get("positions",{}).items():
                self.positions[sym.upper()]=Position(symbol=p["symbol"],side=p["side"],quantity=int(p["quantity"]),
                    entry=float(p["entry"]),stop_loss=float(p["stop_loss"]),target=float(p["target"]),
                    risk_per_share=float(p["risk_per_share"]),opened_at=p["opened_at"])
        except Exception as exc:
            logger.error("Failed to load trader state: %s. Starting fresh.",exc)
            self.cash=self.initial_capital; self.daily_trade_count=0; self.last_trade_time=None; self.positions={}

    def _reset_daily_counter_if_needed(self):
        if self.last_trade_time and self.last_trade_time.astimezone(IST).date() != datetime.now(IST).date():
            self.daily_trade_count=0; self._save_state()

    def can_trade(self,symbol:str)->tuple[bool,str]:
        self._reset_daily_counter_if_needed(); symbol=symbol.strip().upper()
        if not symbol: return False,"Symbol cannot be empty."
        if symbol in self.positions: return False,f"{symbol}: duplicate active position."
        if self.daily_trade_count >= self.max_daily_trades: return False,"Maximum daily trade limit reached."
        if self.last_trade_time:
            last=self.last_trade_time
            if last.tzinfo is None: last=last.replace(tzinfo=timezone.utc)
            elapsed=(datetime.now(timezone.utc)-last).total_seconds()
            required=self.cooldown_minutes*60
            if elapsed < required: return False,f"Cooldown active ({(required-elapsed)/60:.1f} mins remaining)."
        return True,"Trade guardrails passed."

    def calculate_position_size(self,entry:float,stop_loss:float)->tuple[int,float]:
        risk_per_share=entry-stop_loss
        if entry <= 0 or stop_loss <= 0 or risk_per_share <= 0:
            raise ValueError("For BUY, stop-loss must be below entry.")
        return min(int(self.max_risk_per_trade//risk_per_share),int(self.cash//entry)),risk_per_share

    def open_position(self,symbol:str,side:str,entry:float,stop_loss:float,target:float)->tuple[bool,str,Optional[Position]]:
        symbol=symbol.strip().upper(); side=side.strip().upper()
        if side!="BUY": return False,"PaperTrader supports BUY only.",None
        try: entry=float(entry); stop_loss=float(stop_loss); target=float(target)
        except (TypeError,ValueError): return False,"Entry, stop-loss and target must be numeric.",None
        ok,reason=self.can_trade(symbol)
        if not ok: return False,reason,None
        if not (stop_loss < entry < target): return False,"Invalid BUY levels: expected SL < Entry < Target.",None
        risk=entry-stop_loss; rr=(target-entry)/risk
        if rr < self.min_rr: return False,f"R:R 1:{rr:.2f} is below minimum 1:{self.min_rr:.2f}.",None
        qty,rps=self.calculate_position_size(entry,stop_loss)
        if qty<1: return False,"Position size is zero under risk/capital limits.",None
        required=entry*qty
        if required>self.cash: return False,"Insufficient paper cash.",None
        actual=rps*qty
        if actual>self.max_risk_per_trade+1e-9: return False,"Risk limit exceeded.",None
        now=datetime.now(timezone.utc)
        pos=Position(symbol,"BUY",qty,entry,stop_loss,target,rps,now.isoformat())
        self.cash-=required; self.positions[symbol]=pos; self.daily_trade_count+=1; self.last_trade_time=now; self._save_state()
        logger.info("PAPER BUY | %s | qty=%d | entry=%.2f | SL=%.2f | target=%.2f | risk=%.2f | RR=1:%.2f",symbol,qty,entry,stop_loss,target,actual,rr)
        return True,"Paper trade executed.",pos

    def mark(self,symbol:str,price:float)->Optional[float]:
        symbol=symbol.strip().upper(); p=self.positions.get(symbol)
        if p is None: return None
        price=float(price)
        exit_price=p.stop_loss if price<=p.stop_loss else p.target if price>=p.target else None
        if exit_price is None: return None
        pnl=(exit_price-p.entry)*p.quantity; self.cash += p.entry*p.quantity+pnl
        with self.ledger_path.open("a",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(),p.symbol,p.side,p.quantity,p.entry,p.stop_loss,p.target,exit_price,pnl])
        del self.positions[symbol]; self._save_state()
        return pnl

    @property
    def equity(self)->float:
        return self.cash+sum(p.entry*p.quantity for p in self.positions.values())

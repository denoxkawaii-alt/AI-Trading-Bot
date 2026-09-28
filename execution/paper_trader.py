from dataclasses import dataclass
from datetime import datetime,timezone
import csv
from pathlib import Path
@dataclass
class Position: symbol:str; side:str; qty:int; entry:float; stop:float; target:float; opened_at:str
class PaperTrader:
 def __init__(self,capital=10000,ledger_path="trades.csv"):
  self.initial_capital=capital; self.cash=capital; self.positions={}; self.path=Path(ledger_path)
  if not self.path.exists():
   with self.path.open("w",newline="") as f:csv.writer(f).writerow(["timestamp","symbol","side","qty","entry","exit","pnl"])
 def open_position(self,symbol,plan):
  if symbol in self.positions or plan.entry*plan.quantity>self.cash:return False
  self.cash-=plan.entry*plan.quantity; self.positions[symbol]=Position(symbol,plan.side,plan.quantity,plan.entry,plan.stop,plan.target,datetime.now(timezone.utc).isoformat()); return True
 def mark(self,symbol,price):
  p=self.positions.get(symbol)
  if not p:return None
  x=p.stop if price<=p.stop else p.target if price>=p.target else None
  if x is None:return None
  pnl=(x-p.entry)*p.qty; self.cash+=p.entry*p.qty+pnl
  with self.path.open("a",newline="") as f:csv.writer(f).writerow([datetime.now(timezone.utc).isoformat(),p.symbol,p.side,p.qty,p.entry,x,pnl])
  del self.positions[symbol]; return pnl
 @property
 def equity(self):return self.cash+sum(p.entry*p.qty for p in self.positions.values())
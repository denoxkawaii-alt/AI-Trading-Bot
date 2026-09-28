from dataclasses import dataclass
@dataclass(frozen=True)
class OrderFlowSignal: sweep:bool; imbalance:float; bullish:bool
def detect_liquidity_sweep(ph,pl,h,l,c):return (h>ph and c<ph) or (l<pl and c>pl)
def bid_ask_imbalance(bid,ask):
 t=bid+ask; return 0.0 if t<=0 else (bid-ask)/t
def analyze_order_book(bid,ask,threshold=.15):
 x=bid_ask_imbalance(bid,ask); return OrderFlowSignal(False,x,x>=threshold)
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderFlowSignal:
    sweep: bool
    imbalance: float
    bullish: bool

def detect_liquidity_sweep(previous_high,previous_low,high,low,close):
    return (high>previous_high and close<previous_high) or (low<previous_low and close>previous_low)

def bid_ask_imbalance(bid_volume,ask_volume):
    total=bid_volume+ask_volume
    return 0.0 if total<=0 else (bid_volume-ask_volume)/total

def analyze_order_book(bid_volume,ask_volume,threshold=.15):
    x=bid_ask_imbalance(bid_volume,ask_volume)
    return OrderFlowSignal(False,x,x>=threshold)

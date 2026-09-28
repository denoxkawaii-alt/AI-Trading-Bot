import os
from dataclasses import dataclass
@dataclass(frozen=True)
class Settings:
 DEMO_CAPITAL:float=float(os.getenv("DEMO_CAPITAL","10000")); MAX_RISK_PER_TRADE:float=float(os.getenv("MAX_RISK_PER_TRADE","150"))
 MAX_TRADES_PER_DAY:int=int(os.getenv("MAX_TRADES_PER_DAY","2")); COOLDOWN_MINUTES:int=int(os.getenv("COOLDOWN_MINUTES","30"))
 MIN_PRICE:float=float(os.getenv("MIN_PRICE","10")); MIN_DAILY_VOLUME:int=int(os.getenv("MIN_DAILY_VOLUME","100000"))
 VIX_MAX:float=float(os.getenv("VIX_MAX","22")); MIN_RR:float=float(os.getenv("MIN_RR","2.5"))
 MONTE_CARLO_RUNS:int=int(os.getenv("MONTE_CARLO_RUNS","1000")); MIN_MC_PROBABILITY:float=float(os.getenv("MIN_MC_PROBABILITY","0.85"))
 ATR_PERIOD:int=14; STOP_ATR_MULTIPLIER:float=1.5; TARGET_ATR_MULTIPLIER:float=3.75
 TELEGRAM_BOT_TOKEN:str=os.getenv("TELEGRAM_BOT_TOKEN",""); TELEGRAM_CHAT_ID:str=os.getenv("TELEGRAM_CHAT_ID","")
SETTINGS=Settings()
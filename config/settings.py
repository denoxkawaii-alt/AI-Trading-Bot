import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    DEMO_CAPITAL: float = float(os.getenv("DEMO_CAPITAL", "10000"))
    MAX_RISK_PER_TRADE: float = float(os.getenv("MAX_RISK_PER_TRADE", "150"))
    MAX_TRADES_PER_DAY: int = int(os.getenv("MAX_TRADES_PER_DAY", "2"))
    COOLDOWN_MINUTES: int = int(os.getenv("COOLDOWN_MINUTES", "30"))
    MIN_PRICE: float = float(os.getenv("MIN_PRICE", "10"))
    MIN_DAILY_VOLUME: int = int(os.getenv("MIN_DAILY_VOLUME", "100000"))
    VIX_MAX: float = float(os.getenv("VIX_MAX", "22"))
    MIN_RR: float = float(os.getenv("MIN_RR", "1.5"))
    MONTE_CARLO_RUNS: int = int(os.getenv("MONTE_CARLO_RUNS", "1000"))
    MIN_MC_PROBABILITY: float = float(os.getenv("MIN_MC_PROBABILITY", "0.85"))
    MC_HORIZON: int = int(os.getenv("MC_HORIZON", "10"))
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    EMAIL_TO: str = os.getenv("EMAIL_TO", "denoxkawaii@gmail.com")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "onboarding@resend.dev")
    AI_ENABLED: bool = os.getenv("AI_ENABLED", "false").strip().lower() in {"1","true","yes","on"}
    AI_MIN_CONFIDENCE: float = float(os.getenv("AI_MIN_CONFIDENCE", "0.65"))
    HEALTH_PORT: int = int(os.getenv("PORT", "8080"))
    DATA_DIR: str = os.getenv("DATA_DIR", "data")

SETTINGS = Settings()

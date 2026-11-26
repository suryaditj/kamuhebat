import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def get_env(name: str, default: str = "") -> str:
    # GitHub Actions dapat mengirim secret yang tidak disetel sebagai string kosong.
    return (os.getenv(name) or default).strip()


@dataclass(frozen=True)
class Config:
    telegram_token: str
    telegram_chat_id: str

    biquote_base_url: str
    symbol: str

    check_interval_minutes: int
    timeframe_bias: str
    timeframe_zone: str
    timeframe_entry: str

    entry_style: str
    max_risk_percent: float


def load_config() -> Config:
    return Config(
        telegram_token=get_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=get_env("TELEGRAM_CHAT_ID"),
        biquote_base_url=get_env(
            "BIQUOTE_BASE_URL",
            "https://biquote.io/api"
        ).rstrip("/"),
        symbol=get_env("SYMBOL", "XAUUSD"),
        check_interval_minutes=int(
            get_env("CHECK_INTERVAL_MINUTES", "5")
        ),
        timeframe_bias=get_env("TIMEFRAME_BIAS", "1h"),
        timeframe_zone=get_env("TIMEFRAME_ZONE", "15m"),
        timeframe_entry=get_env("TIMEFRAME_ENTRY", "5m"),
        entry_style=get_env("ENTRY_STYLE", "hybrid").lower(),
        max_risk_percent=float(
            get_env("MAX_RISK_PERCENT", "1.0")
        ),
    )


config = load_config()


def validate_config() -> None:
    if not config.telegram_token:
        raise ValueError("TELEGRAM_BOT_TOKEN belum diisi")

    if config.entry_style not in ("hybrid", "early", "confirmed"):
        raise ValueError("ENTRY_STYLE tidak valid")

    if config.check_interval_minutes < 1:
        raise ValueError("CHECK_INTERVAL_MINUTES minimal 1")

    if config.max_risk_percent <= 0:
        raise ValueError("MAX_RISK_PERCENT harus lebih dari 0")

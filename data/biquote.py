import requests
import pandas as pd

from config import config


class BiQuoteClient:
    def __init__(self):
        self.base_url = config.biquote_base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "HybridSMCHunter/1.0"
        })

    def get_ohlc(
        self,
        timeframe: str,
        limit: int = 200
    ) -> pd.DataFrame:

        allowed = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}

        if timeframe not in allowed:
            raise ValueError(f"Timeframe tidak valid: {timeframe}")

        if not 1 <= limit <= 1000:
            raise ValueError("Limit candle harus 1-1000")

        url = f"{self.base_url}/{config.symbol}/ohlc"

        try:
            response = self.session.get(
                url,
                params={
                    "interval": timeframe,
                    "limit": limit
                },
                timeout=20
            )

            response.raise_for_status()
            payload = response.json()

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Gagal mengambil data BiQuote: {exc}"
            ) from exc

        except ValueError as exc:
            raise RuntimeError(
                "Respons BiQuote bukan JSON yang valid"
            ) from exc

        bars = payload.get("bars")

        if not isinstance(bars, list) or not bars:
            raise RuntimeError("Data candle kosong atau format salah")

        df = pd.DataFrame(bars)

        required = [
            "openTime", "open", "high",
            "low", "close", "isOpen"
        ]

        missing = [
            col for col in required if col not in df.columns
        ]

        if missing:
            raise RuntimeError(
                f"Kolom candle tidak lengkap: {missing}"
            )

        # Hanya candle yang sudah selesai
        df = df[df["isOpen"] == False].copy()

        if df.empty:
            raise RuntimeError("Belum ada candle tertutup")

        df["openTime"] = pd.to_datetime(
            df["openTime"],
            utc=True,
            errors="coerce"
        )

        numeric_cols = ["open", "high", "low", "close"]

        for col in numeric_cols:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.dropna(
            subset=["openTime"] + numeric_cols
        )

        # Data diurutkan dari waktu lama ke terbaru
        df = df.sort_values("openTime")
        df = df.drop_duplicates("openTime")
        df = df.set_index("openTime")

        return df


biquote = BiQuoteClient()


import requests
import pandas as pd

from config import config


class BiQuoteClient:
    def __init__(self):
        self.base_url = config.biquote_base_url.rstrip("/")
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "HybridSMCHunter/1.0"
        })

    def get_ohlc(
        self,
        timeframe: str,
        limit: int = 200,
    ) -> pd.DataFrame:

        allowed = {
            "1m", "5m", "15m",
            "30m", "1h", "4h", "1d"
        }

        if timeframe not in allowed:
            raise ValueError(
                f"Timeframe tidak valid: {timeframe}"
            )

        if not 1 <= limit <= 1000:
            raise ValueError(
                "Limit candle harus 1-1000"
            )

        url = f"{self.base_url}/{config.symbol}/ohlc"

        try:
            response = self.session.get(
                url,
                params={
                    "interval": timeframe,
                    "limit": limit,
                },
                timeout=20,
            )

            response.raise_for_status()
            payload = response.json()

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Gagal mengambil data BiQuote: {exc}"
            ) from exc

        except ValueError as exc:
            raise RuntimeError(
                "Respons BiQuote bukan JSON valid"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Format respons BiQuote tidak valid"
            )

        bars = payload.get("bars")

        if not isinstance(bars, list) or not bars:
            message = payload.get(
                "message",
                "Data candle kosong"
            )

            raise RuntimeError(
                f"BiQuote: {message}"
            )

        df = pd.DataFrame(bars)

        required = [
            "openTime",
            "open",
            "high",
            "low",
            "close",
            "isOpen",
        ]

        missing = [
            col for col in required
            if col not in df.columns
        ]

        if missing:
            raise RuntimeError(
                f"Kolom candle tidak lengkap: {missing}"
            )

        # Hanya gunakan candle yang sudah ditutup.
        df = df[df["isOpen"] == False].copy()

        if df.empty:
            raise RuntimeError(
                "Belum tersedia candle tertutup"
            )

        # Konversi timestamp UTC.
        df["openTime"] = pd.to_datetime(
            df["openTime"],
            utc=True,
            errors="coerce",
        )

        # Konversi harga menjadi angka.
        price_columns = [
            "open", "high", "low", "close"
        ]

        for col in price_columns:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

        df = df.dropna(
            subset=["openTime"] + price_columns
        )

        # Validasi struktur OHLC.
        valid_ohlc = (
            (df["high"] >= df["low"])
            & (df["high"] >= df["open"])
            & (df["high"] >= df["close"])
            & (df["low"] <= df["open"])
            & (df["low"] <= df["close"])
        )

        df = df[valid_ohlc].copy()

        if df.empty:
            raise RuntimeError(
                "Tidak ada candle OHLC yang valid"
            )

        # Urutkan dari candle terlama ke terbaru.
        df = (
            df.sort_values("openTime")
            .drop_duplicates("openTime")
            .set_index("openTime")
        )

        return df


biquote = BiQuoteClient()

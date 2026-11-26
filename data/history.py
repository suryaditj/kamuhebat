import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone


HISTORY_DIR = Path("data")
HISTORY_FILE = HISTORY_DIR / "signal_history.json"

MAX_HISTORY = 500


def load_history():
    """Membaca seluruh riwayat sinyal."""

    if not HISTORY_FILE.exists():
        return []

    try:
        data = json.loads(
            HISTORY_FILE.read_text(encoding="utf-8")
        )

        if not isinstance(data, list):
            return []

        return data

    except (json.JSONDecodeError, OSError):
        return []


def save_history(history):
    """Menyimpan riwayat secara atomik."""

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    history = history[-MAX_HISTORY:]

    temporary_file = HISTORY_FILE.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps(
            history,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    temporary_file.replace(HISTORY_FILE)


def create_signal_record(
    symbol,
    status,
    timeframe,
    candle_time,
    entry=None,
    stop_loss=None,
    take_profit=None,
    score=None,
    reason="",
):
    """Membuat satu catatan sinyal."""

    status = str(status).upper()

    if status not in ("BUY", "SELL", "WAIT"):
        raise ValueError("Status sinyal tidak valid")

    unique_data = (
        f"{symbol}|{status}|{timeframe}|{candle_time}"
    )

    record_id = hashlib.sha256(
        unique_data.encode("utf-8")
    ).hexdigest()[:16]

    return {
        "id": record_id,
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "symbol": symbol,
        "status": status,
        "timeframe": timeframe,
        "candle_time": str(candle_time),
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "score": score,
        "reason": str(reason),
    }


def add_signal_record(record):
    """Menambahkan catatan jika belum pernah tersimpan."""

    history = load_history()

    record_id = record.get("id")

    if not record_id:
        raise ValueError("ID riwayat tidak tersedia")

    if any(item.get("id") == record_id for item in history):
        return False

    history.append(record)

    save_history(history)

    return True


def get_recent_history(limit=10, status=None):
    """Mengambil riwayat terbaru."""

    if limit < 1:
        raise ValueError("Limit minimal 1")

    history = load_history()

    if status:
        status = status.upper()

        if status not in ("BUY", "SELL", "WAIT"):
            raise ValueError("Filter status tidak valid")

        history = [
            item for item in history
            if item.get("status") == status
        ]

    return list(reversed(history[-limit:]))


def clear_history():
    """Menghapus seluruh riwayat."""

    save_history([])

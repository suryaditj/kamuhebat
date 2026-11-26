from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_keyboard():
    """Menu utama bot."""
    keyboard = [
        [
            InlineKeyboardButton("🔍 Analisis", callback_data="analyze"),
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
        ],
        [
            InlineKeyboardButton("📊 Market", callback_data="market"),
            InlineKeyboardButton("📜 Riwayat", callback_data="history"),
        ],
        [
            InlineKeyboardButton("⚙️ Pengaturan", callback_data="settings"),
            InlineKeyboardButton("📖 Panduan", callback_data="help"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def settings_keyboard():
    """Menu pengaturan."""
    keyboard = [
        [
            InlineKeyboardButton("📈 XAUUSD", callback_data="symbol_info"),
        ],
        [
            InlineKeyboardButton("⚡ Entry Hybrid", callback_data="entry_info"),
        ],
        [
            InlineKeyboardButton("⏱️ Interval 5 Menit", callback_data="interval_info"),
        ],
        [
            InlineKeyboardButton("⬅️ Kembali", callback_data="main_menu"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def back_keyboard():
    """Tombol kembali ke menu utama."""
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Menu Utama", callback_data="main_menu"),
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def analysis_keyboard():
    """Tombol setelah analisis."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Analisis Ulang", callback_data="analyze"),
        ],
        [
            InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)

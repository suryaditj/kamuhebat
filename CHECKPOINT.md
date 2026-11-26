# Hybrid SMC Hunter — Checkpoint Integrasi

Tanggal: 2026-11-26

## Status

- Audit dan perbaikan integrasi awal selesai.
- Seluruh tes otomatis yang tersedia: **41 passed**.
- `compileall`: berhasil.
- Workflow YAML: berhasil diparse.
- Belum dilakukan uji koneksi langsung ke API BiQuote atau Telegram.

## Perbaikan dalam checkpoint ini

1. Mengosongkan lima file `__init__.py` yang sebelumnya berisi teks acak (`crit`, `crot`, `cret`, `crat`, `crit`) dan menyebabkan pytest gagal saat collection.
2. Memperbaiki scoring agar status `BUY` dan `SELL` dari `signals/entry.py` dipetakan ke arah `BULLISH` dan `BEARISH`.
3. Memperbaiki formatter agar menampilkan `quality` hasil scoring.
4. Memperbaiki fallback konfigurasi agar secret `BIQUOTE_BASE_URL` yang kosong tetap memakai URL default.
5. Memperbaiki workflow agar menyimpan perubahan `state/` dan `data/`, termasuk `signal_history.json`, ke repository. Sebelumnya workflow hanya menyimpan offset Telegram sehingga riwayat dapat hilang pada runner sementara.
6. Memperbaiki urutan konfirmasi M5: BOS harus terjadi lebih dahulu, displacement sesudah BOS, dan pullback diuji pada candle terakhir setelah displacement.
7. Menambahkan tiga tes scoring untuk BUY, SELL, dan WAIT.

## Hasil tes

```text
41 passed
```

Perintah:

```bash
python -m pytest -q
python -m compileall -q .
```

## Batasan yang belum dapat diverifikasi dari lingkungan ini

- Paket `python-telegram-bot` tidak tersedia di lingkungan audit dan akses internet untuk memasangnya tidak tersedia. Karena itu import/runtime Telegram belum diuji langsung di sini. GitHub Actions akan memasang dependensi dari `requirements.txt`.
- Endpoint dan bentuk respons BiQuote belum diuji terhadap server live. Tes BiQuote yang ada menggunakan mock.
- Bot berjalan dengan polling terjadwal GitHub Actions, bukan proses 24/7. Tombol inline dapat terlambat diproses dan jawaban callback Telegram bisa kedaluwarsa di antara jadwal workflow.
- Pastikan GitHub Actions memiliki izin `Contents: Read and write`, dan secret `TELEGRAM_BOT_TOKEN` serta `TELEGRAM_CHAT_ID` telah diatur.
- Sinyal tetap perlu diuji pada data historis/demo sebelum dipakai sebagai dasar keputusan trading. Tes perangkat lunak tidak membuktikan profitabilitas strategi.

## Runtime polling update — 2026-11-26

1. Mengganti polling satu kali (`timeout=0`) dengan long polling berulang selama maksimal 180 detik per eksekusi.
2. Setiap long-poll menunggu maksimal 20 detik agar command dan callback inline dapat diambil selama job aktif.
3. Offset Telegram tetap disimpan setelah setiap update berhasil diserahkan ke handler, lalu dipersistenkan oleh workflow ke repository.
4. Batas waktu job GitHub Actions dinaikkan menjadi 5 menit; `BOT_RUN_SECONDS=180` memberi waktu untuk setup dan penyimpanan state.
5. Workflow tetap dijalankan manual atau melalui jadwal cron setiap 5 menit. Ini bukan bot 24/7 dan dapat memiliki jeda saat pergantian job.

### Verifikasi tambahan

- `python -m pytest -q`: **41 passed**.
- `python -m compileall -q .`: harus dijalankan kembali setelah perubahan runtime.
- Belum ada pengujian live Telegram/BiQuote dari lingkungan lokal.

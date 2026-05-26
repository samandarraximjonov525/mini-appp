# DigiPro Hub — Telegram Mini App

Premium IT xizmatlar uchun Telegram Mini App + CRM Admin Panel.

## Loyiha tuzilmasi

```
mini_app/
├── backend/
│   ├── main.py          # aiohttp REST API serveri
│   ├── bot.py           # aiogram Telegram bot
│   ├── requirements.txt # Python kutubxonalar
│   └── enterprise_bot.db  # SQLite ma'lumotlar bazasi (avtomatik yaratiladi)
└── frontend/
    ├── index.html       # Mijoz Mini App interfeysi
    └── admin.html       # CRM Admin Panel
```

## Ishga tushirish

### 1. Backend (API server)

```bash
cd backend
pip install -r requirements.txt
python main.py
# Server http://localhost:8080 da ishga tushadi
```

### 2. Telegram Bot

```bash
cd backend
# BOT_TOKEN va ADMIN_CHAT_ID ni .env ga yoki environment'ga qo'ying
export BOT_TOKEN="sizning_token"
export ADMIN_CHAT_ID="sizning_telegram_id"
python bot.py
```

### 3. Frontend

`frontend/index.html` va `frontend/admin.html` fayllarini web serverga joylashtiring yoki `API_HOST` ni `main.py` serveriga ko'rsating.

## API Endpointlari

| Method | URL | Tavsif |
|--------|-----|--------|
| GET | /api/public/services | Barcha xizmatlar |
| GET | /api/public/portfolio | Portfolio ishlar |
| POST | /api/public/orders | Yangi buyurtma |
| GET | /api/admin/orders | Buyurtmalar (admin) |
| PUT | /api/admin/orders/{id}/status | Status yangilash |
| DELETE | /api/admin/orders/{id} | Buyurtma o'chirish |
| GET | /api/admin/stats | Statistika |
| GET | /api/admin/users | Foydalanuvchilar |
| GET | /api/admin/portfolio | Portfolio (admin) |
| POST | /api/admin/portfolio | Portfolio qo'shish |
| DELETE | /api/admin/portfolio/{id} | Portfolio o'chirish |
| GET | /api/admin/services | Xizmatlar (admin) |
| POST | /api/admin/services | Xizmat qo'shish |
| DELETE | /api/admin/services/{id} | Xizmat o'chirish |

## Bot Komandalar

- `/start` — Botni ishga tushirish
- `/stats` — Statistika (admin)
- `/orders` — Oxirgi 5 buyurtma (admin)

## Environment Variables

| O'zgaruvchi | Tavsif | Standart |
|-------------|--------|---------|
| BOT_TOKEN | Telegram bot tokeni | hardcoded (o'zgartiring!) |
| ADMIN_CHAT_ID | Admin Telegram ID | hardcoded |
| WEBAPP_URL | Mijoz mini app URL | vercel URL |
| ADMIN_WEBAPP_URL | Admin panel URL | vercel URL |
| DB_FILE | SQLite fayl nomi | enterprise_bot.db |
| PORT | API server port | 8080 |

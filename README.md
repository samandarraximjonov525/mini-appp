# DigiPro Hub — Deploy Qo'llanmasi

## Loyiha tuzilishi
```
deploy/
├── backend/
│   ├── main.py          ← FastAPI server (API)
│   ├── bot.py           ← Telegram Bot
│   ├── requirements.txt ← Python kutubxonalar
│   └── .env.example     ← Environment variables namunasi
├── frontend/
│   ├── index.html       ← Mini App (asosiy sahifa)
│   └── admin.html       ← Admin Panel
└── vercel.json          ← Vercel konfiguratsiya
```

---

## 1-QADAM: VERCEL — Frontend + API Deploy

### Vercel.com ga kirish
1. https://vercel.com → GitHub bilan kirish
2. **"New Project"** → GitHub repo tanlash
3. **Root Directory** = bu `deploy` papkasi
4. **Environment Variables** qo'shish:
   - `BOT_TOKEN` = tokeningiz
   - `ADMIN_CHAT_ID` = chat ID
   - `ADMIN_PASSWORD` = parolingiz
   - `WEBAPP_URL` = https://YOUR-APP.vercel.app
   - `ADMIN_WEBAPP_URL` = https://YOUR-APP.vercel.app/admin

5. **Deploy** tugmasini bosing

### Deploy bo'lgandan keyin:
- **Mini App**: https://YOUR-APP.vercel.app
- **Admin Panel**: https://YOUR-APP.vercel.app/admin
- **API**: https://YOUR-APP.vercel.app/api/...

---

## 2-QADAM: BOT — Railway yoki VPS Deploy

### Railway.app (Tavsiya etiladi — bepul)
1. https://railway.app → kirish
2. **New Project** → **Deploy from GitHub**
3. **Settings → Variables** qo'shish:
   ```
   BOT_TOKEN=...
   ADMIN_CHAT_ID=...
   WEBAPP_URL=https://YOUR-APP.vercel.app
   ADMIN_WEBAPP_URL=https://YOUR-APP.vercel.app/admin
   DB_FILE=enterprise_bot.db
   ```
4. **Settings → Start Command**:
   ```
   python backend/bot.py
   ```

### VPS (Ubuntu) orqali:
```bash
# Python o'rnatish
sudo apt install python3 python3-pip -y

# Papkaga kirish
cd /path/to/deploy

# Kutubxonalar o'rnatish
pip3 install -r backend/requirements.txt

# Bot ishga tushirish
python3 backend/bot.py

# Yoki systemd service sifatida (doimiy ishlash)
```

---

## 3-QADAM: BOT TOKEN ni yangilash

`bot.py` va `main.py` fayllarida URL ni yangilang:
```python
WEBAPP_URL = "https://YOUR-VERCEL-APP.vercel.app"
ADMIN_WEBAPP_URL = "https://YOUR-VERCEL-APP.vercel.app/admin"
```

---

## Admin Panel Kirish
- URL: https://YOUR-APP.vercel.app/admin
- Parol: `digipro_admin123` (o'zgartiring!)

## Muhim Eslatmalar
- ⚠️ Bot alohida serverda ishlashi KERAK (Vercel serverless bot uchun mos emas)
- ⚠️ SQLite DB Vercel da saqlanmaydi — Railway yoki Supabase ishlatish tavsiya etiladi
- ✅ Frontend + API → Vercel
- ✅ Bot → Railway / VPS

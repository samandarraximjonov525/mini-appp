# 📂 DigiPro Telegram Mini‑App CRM - Loyiha Tasnifi (Project Overview)

Bu hujjat loyihaning to'liq arxitekturasi, ma'lumotlar oqimi va asosiy funksiyalarini boshqa dasturchilarga yoki AI-assistentlarga tushuntirish uchun tayyorlangan.

## 1️⃣ Umumiy Arxitektura (High-level Architecture)

```text
┌─────────────────────┐          ┌─────────────────────┐
│  Telegram Mini‑App  │  HTTPS   │   FastAPI Backend   │
│  (Frontend)         ◀───────▶ │ (mini_app/backend) │
│  - HTML/CSS/JS      │          │ - REST API          │
│  - Vercel'da        │          │ - SQLite DB         │
└─────────────────────┘          └─────────────────────┘
          ▲                                 ▲
          │                                 │
          ▼                                 ▼
┌─────────────────────┐          ┌─────────────────────┐
│  Telegram Bot (TG)  │  Bot ↔︎  │   Bot Logic (bot.py)│
│                     │◀───────▶│ - Buyurtma xabari   │
│                     │          │ - Chat xabarlari    │
└─────────────────────┘          └─────────────────────┘
```

* **Frontend**: `mini_app/frontend` papkasida joylashgan. Sof HTML, CSS va Vanilla JS (Frameworksiz) da yozilgan. Hozirda **Vercel** tarmog'iga deploy qilingan (`https://y-six-green-92.vercel.app`).
* **Backend**: `mini_app/backend/main.py` faylida **FastAPI** (Python 3.13) da yozilgan. Barcha API marshrutlari `/api/*` orqali ishlaydi. 
* **Database**: `enterprise_bot.db` - **SQLite** bazasida barcha ma'lumotlar saqlanadi.
* **Telegram Bot**: `mini_app/backend/bot.py` orqali **Aiogram 3.x** da yozilgan. Long-polling rejimida ishlaydi, admin va mijoz o'rtasidagi chat, shuningdek, buyurtma statusini yuborish uchun xizmat qiladi.

---

## 2️⃣ Ma'lumotlar Bazasi (SQLite / enterprise_bot.db)

Asosiy jadvallar (Tables):
1. **users**: `tg_id` (PK), `full_name`, `username` - Mini App'ga kirgan barcha foydalanuvchilarni ro'yxatga oladi.
2. **services**: Xizmatlar ro'yxati (`name`, `price`, `icon`, `color`, `description`).
3. **portfolio**: Ishlar namunasi (`title`, `category`, `image_url`).
4. **promocodes**: Chegirmalar (`code`, `type` [PERCENT/FIXED/FREE], `value`).
5. **orders**: Mijoz buyurtmalari (`id`, `user_tg_id`, `service`, `promo`, `status`, `price`).
6. **messages**: Chat tizimi xabarlari (`id`, `sender_id`, `receiver_id`, `text`, `timestamp`, `is_read`).

---

## 3️⃣ REST API Endpoints (FastAPI)

* **Ochiq (Public) API'lar:**
  * `GET /api/public/services` - Xizmatlarni yuklash
  * `GET /api/public/portfolio` - Portfolioni yuklash
  * `GET /api/public/promocodes/{code}` - Promokodni tekshirish
  * `POST /api/public/orders` - Yangi buyurtma yuborish

* **Admin va Chat API'lari:**
  * `GET /api/admin/chat/conversations` - Admin panel chat sidebari uchun barcha suhbatlar ro'yxatini yuklaydi.
  * `PUT /api/admin/chat/read/{user_id}` - Xabarlarni o'qilgan (is_read=1) qilib belgilaydi.
  * `GET /api/chat/{user_id}` - Muayyan mijoz bilan bo'lgan barcha xabarlarni yuklaydi.
  * `POST /api/chat/send` - Mijoz yoki admin xabar yozganda qabul qiladi va bot orqali bildirishnoma yuboradi.

---

## 4️⃣ Frontend Mantig'i (UI Flow)

* **Texnologiyalar**: Bootstrap 5 (CSS framework), SweetAlert2 (Bildirishnomalar), Telegram Web App JS (`telegram-web-app.js`).
* **Asosiy qismlar**: 
  - `showSec(id)` funksiyasi sahifalarni (Katalog, Ishlar, Chat, Buyurtma) SPA (Single Page Application) ko'rinishida o'zgartiradi.
  - `checkPromo()` - API orqali promo-kod to'g'riligini tekshiradi va real vaqtda narxni yangilaydi (updatePrice).
  - `loadMessages()` & `sendMessage()` - Har 5 soniyada yangi chat xabarlarini so'raydi (Polling) va ekranga chiqaradi.

---

## 5️⃣ Telegram Bot Mantig'i (bot.py)

* Telegram Web App (Mini App) orqali kirmagan paytlarda foydalanuvchilar bilan bot orqali aloqa ushlab turiladi.
* Bot faqatgina "voqealar xabarchisi" (Notifier) sifatida ishlaydi:
  - Mijoz Web App orqali xabar yozsa, adminga bot orqali xabar keladi.
  - Admin Web App orqali buyurtmani tasdiqlasa (`Bajarildi`, `Bekor qilindi`), mijozga bot orqali status o'zgarganligi haqida xabar boradi.
  - Admin Telegram orqali javob yozish imkoniga ega emas, faqat Admin Web Panel (`/admin`) orqali xabar qaytaradi.

---

## 6️⃣ Qanday Qilib Ishga Tushiriladi? (Deployment & Run)

**Mahalliy (Local) kompyuterda ishga tushirish:**
```bash
# 1. Muhitni faollashtirish
source .venv/bin/activate

# 2. API Serverni ishga tushirish (port 8080)
python mini_app/backend/main.py

# 3. Telegram Botni ishga tushirish
python mini_app/backend/bot.py
```

**Production Env Variables (`.env` faylda saqlanadi):**
* `BOT_TOKEN` = Sizning bot tokeningiz
* `ADMIN_CHAT_ID` = Adminning telegram ID rami (bildirishnomalar shunga yuboriladi)
* `WEBAPP_URL` = Vercel domen manzili.

**Tavsiya etiladigan Deployment:**
* Backend (`main.py`) va Bot (`bot.py`) -> **Railway.app**, **Render** yoki **VPS Ubuntu** serverda `Procfile` yordamida.
* Frontend (`public/`) -> **Vercel** yoki **Netlify** orqali. Free hosting.

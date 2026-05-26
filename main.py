import os
import uuid
import secrets
import logging
import sqlite3
import aiohttp
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import aiosqlite

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DB_FILE       = os.environ.get("DB_FILE", os.path.join(BASE_DIR, "enterprise_bot.db"))
BOT_TOKEN     = os.environ.get("BOT_TOKEN", "8706112826:AAH_fSow83cu_DvvSDHXkVJwwI5gIHVphEw")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "6448909987")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="DigiPro Hub API", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────
class OrderCreate(BaseModel):
    name: str
    contact: str
    service: str
    desc: str
    promo: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: str

class PortfolioCreate(BaseModel):
    title: str
    category: str
    description: Optional[str] = ""
    image_url: Optional[str] = ""

class ServiceCreate(BaseModel):
    name: str
    price: int
    icon: Optional[str] = "bi-lightning-charge-fill"
    description: Optional[str] = ""
    color: Optional[str] = "#7c6bff"

class PromoCode(BaseModel):
    code: str
    type: str
    value: float
    expires_at: Optional[str] = None

class MessageCreate(BaseModel):
    receiver_id: str
    text: str

class BroadcastCreate(BaseModel):
    text: str

class NotifyCreate(BaseModel):
    user_id: str
    text: str

# ─────────────────────────────────────────
# DATABASE INIT
# ─────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, tg_id INTEGER UNIQUE, username TEXT, full_name TEXT, created_at TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY, name TEXT, service TEXT,
        status TEXT DEFAULT 'PENDING', description TEXT,
        contact TEXT, created_at TEXT, promo TEXT, user_tg_id TEXT
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS services (id TEXT PRIMARY KEY, name TEXT, icon TEXT, price INTEGER, description TEXT, color TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS portfolio (id TEXT PRIMARY KEY, title TEXT, category TEXT, description TEXT, image_url TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id TEXT, receiver_id TEXT, text TEXT, timestamp TEXT
    )""")
    c.execute("CREATE TABLE IF NOT EXISTS promocodes (code TEXT PRIMARY KEY, type TEXT, value REAL, expires_at TEXT)")

    if c.execute("SELECT COUNT(*) FROM services").fetchone()[0] == 0:
        c.executemany("INSERT INTO services VALUES (?,?,?,?,?,?)", [
            ("S-BOT", "Advanced Telegram Bot", "bi-robot", 600000, "Full CRM & Payment integration", "#ff6b9d"),
            ("S-WEB", "Premium Website", "bi-globe", 1500000, "High performance, modern design", "#00f5c4"),
            ("S-MA",  "Telegram Mini App",  "bi-lightning-charge-fill", 1800000, "Full ecosystem inside Telegram", "#7c6bff")
        ])
    
    # Migrate users if missing columns
    columns_users = [row[1] for row in c.execute("PRAGMA table_info(users)").fetchall()]
    if "username" not in columns_users:
        c.execute("ALTER TABLE users ADD COLUMN username TEXT")

    # Migrate old orders if missing columns
    columns = [row[1] for row in c.execute("PRAGMA table_info(orders)").fetchall()]
    for col, typ in [("promo", "TEXT"), ("user_tg_id", "TEXT")]:
        if col not in columns:
            c.execute(f"ALTER TABLE orders ADD COLUMN {col} {typ}")

    # Migrate messages if missing is_read column
    cols_msg = [row[1] for row in c.execute("PRAGMA table_info(messages)").fetchall()]
    if "is_read" not in cols_msg:
        c.execute("ALTER TABLE messages ADD COLUMN is_read INTEGER DEFAULT 0")
    
    conn.commit()
    conn.close()

init_db()

# ─────────────────────────────────────────
# DB HELPER
# ─────────────────────────────────────────
async def get_db():
    db = await aiosqlite.connect(DB_FILE)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

# ─────────────────────────────────────────
# BOT NOTIFICATION HELPER
# ─────────────────────────────────────────
async def tg_send(chat_id: str, text: str):
    """Send a Telegram message via the Bot API."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
    except Exception as e:
        logger.error(f"Telegram send error: {e}")

# ─────────────────────────────────────────
# ADMIN SECURITY
# ─────────────────────────────────────────
async def verify_admin(request: Request):
    auth_header = request.headers.get("Authorization")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "digipro_admin123")
    if auth_header != f"Bearer {admin_pass}":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ruxsat qilinmadi")

# ─────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────
@app.get("/api/public/services")
async def get_public_services(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM services ORDER BY price") as cur:
        return [dict(r) for r in await cur.fetchall()]

@app.get("/api/public/portfolio")
async def get_public_portfolio(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM portfolio ORDER BY rowid DESC") as cur:
        return [dict(r) for r in await cur.fetchall()]

@app.post("/api/public/orders", status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate, request: Request, db: aiosqlite.Connection = Depends(get_db)):
    if len(order.name.strip()) < 3:
        raise HTTPException(status_code=400, detail="Ism kamida 3 ta harfdan iborat bo'lishi kerak")
    if len(order.contact.strip()) < 7:
        raise HTTPException(status_code=400, detail="Telefon raqam noto'g'ri kiritildi")

    order_id = f"ORD-{secrets.token_hex(3).upper()}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    user_tg_id = request.headers.get("X-User-ID", "")
    try:
        await db.execute(
            "INSERT INTO orders (id, name, service, status, description, contact, created_at, promo, user_tg_id) VALUES (?,?,?,?,?,?,?,?,?)",
            (order_id, order.name, order.service, "PENDING", order.desc, order.contact, timestamp, order.promo, user_tg_id)
        )
        await db.commit()

        # Notify admin via Telegram
        promo_txt = f"\n🎁 Promokod: <code>{order.promo}</code>" if order.promo else ""
        notif = (
            f"🔔 <b>YANGI BUYURTMA!</b>\n\n"
            f"🆔 {order_id}\n"
            f"👤 {order.name}\n"
            f"📞 <code>{order.contact}</code>\n"
            f"🛠 {order.service}\n"
            f"📝 {order.desc}{promo_txt}"
        )
        await tg_send(ADMIN_CHAT_ID, notif)
        return {"status": "success", "order_id": order_id}
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/public/promocodes/{code}")
async def check_promocode(code: str, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM promocodes WHERE code = ?", (code.upper(),)) as cur:
        row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Promokod topilmadi")
        
        if row["expires_at"]:
            try:
                exp_date = datetime.strptime(row["expires_at"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > exp_date:
                    raise HTTPException(status_code=400, detail="Promokod muddati tugagan")
            except Exception:
                pass
                
        return dict(row)

# ─────────────────────────────────────────
# ADMIN ENDPOINTS
# ─────────────────────────────────────────
@app.get("/api/admin/stats", dependencies=[Depends(verify_admin)])
async def get_admin_stats(db: aiosqlite.Connection = Depends(get_db)):
    s = {}
    for key, q in [
        ("total_users",      "SELECT COUNT(*) FROM users"),
        ("total_orders",     "SELECT COUNT(*) FROM orders"),
        ("pending_orders",   "SELECT COUNT(*) FROM orders WHERE status='PENDING'"),
        ("completed_orders", "SELECT COUNT(*) FROM orders WHERE status='COMPLETED'"),
        ("total_services",   "SELECT COUNT(*) FROM services"),
        ("total_portfolio",  "SELECT COUNT(*) FROM portfolio"),
        ("total_promos",     "SELECT COUNT(*) FROM promocodes"),
    ]:
        async with db.execute(q) as cur: s[key] = (await cur.fetchone())[0]
    return s

@app.get("/api/admin/orders", dependencies=[Depends(verify_admin)])
async def get_admin_orders(db: aiosqlite.Connection = Depends(get_db), filter_status: Optional[str] = None):
    q, p = "SELECT * FROM orders", []
    if filter_status:
        q += " WHERE status = ?"; p.append(filter_status)
    q += " ORDER BY created_at DESC"
    async with db.execute(q, p) as cur:
        return [dict(r) for r in await cur.fetchall()]

@app.put("/api/admin/orders/{order_id}/status", dependencies=[Depends(verify_admin)])
async def update_order_status(order_id: str, data: OrderStatusUpdate, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("UPDATE orders SET status = ? WHERE id = ?", (data.status, order_id))
    await db.commit()

    # Notify the user via Telegram if we have their tg_id
    async with db.execute("SELECT user_tg_id, name, service FROM orders WHERE id = ?", (order_id,)) as cur:
        row = await cur.fetchone()
    if row and row["user_tg_id"]:
        status_map = {
            "IN_PROGRESS": "🔄 Buyurtmangiz ishga tushirildi!\n\nTez orada siz bilan bog'lanamiz.",
            "COMPLETED":   "✅ Buyurtmangiz muvaffaqiyatli yakunlandi!\n\nIshimiz uchun raxmat.",
            "CANCELLED":   "❌ Afsuski, buyurtmangiz bekor qilindi.\n\nBatafsil ma'lumot uchun admin bilan bog'laning.",
        }
        msg = status_map.get(data.status, f"📦 Buyurtma holati: <b>{data.status}</b>")
        await tg_send(row["user_tg_id"], f"🆔 <code>{order_id}</code> | {row['service']}\n\n{msg}")

    return {"status": "success"}

@app.delete("/api/admin/orders/{order_id}", dependencies=[Depends(verify_admin)])
async def delete_order(order_id: str, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    await db.commit()
    return {"status": "deleted"}

# Notify specific user from admin panel
@app.post("/api/admin/notify", dependencies=[Depends(verify_admin)])
async def notify_user(payload: NotifyCreate):
    await tg_send(payload.user_id, f"📩 <b>Admin xabari:</b>\n\n{payload.text}")
    return {"status": "sent"}

# Broadcast to ALL users
@app.post("/api/admin/broadcast", dependencies=[Depends(verify_admin)])
async def broadcast(payload: BroadcastCreate, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT tg_id FROM users") as cur:
        users = await cur.fetchall()
    sent, failed = 0, 0
    for u in users:
        try:
            await tg_send(str(u["tg_id"]), f"📢 <b>DigiPro Yangiliklari:</b>\n\n{payload.text}")
            sent += 1
        except:
            failed += 1
    return {"sent": sent, "failed": failed}

# Portfolio
@app.get("/api/admin/portfolio", dependencies=[Depends(verify_admin)])
async def get_admin_portfolio(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM portfolio ORDER BY rowid DESC") as cur:
        return [dict(r) for r in await cur.fetchall()]

@app.post("/api/admin/portfolio", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin)])
async def add_portfolio(item: PortfolioCreate, db: aiosqlite.Connection = Depends(get_db)):
    item_id = f"PF-{uuid.uuid4().hex[:6].upper()}"
    await db.execute(
        "INSERT INTO portfolio (id, title, category, description, image_url) VALUES (?,?,?,?,?)",
        (item_id, item.title, item.category, item.description, item.image_url)
    )
    await db.commit()
    return {"status": "success", "id": item_id}

@app.delete("/api/admin/portfolio/{item_id}", dependencies=[Depends(verify_admin)])
async def delete_portfolio(item_id: str, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("DELETE FROM portfolio WHERE id = ?", (item_id,))
    await db.commit()
    return {"status": "deleted"}

# Services
@app.get("/api/admin/services", dependencies=[Depends(verify_admin)])
async def get_admin_services(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM services ORDER BY name") as cur:
        return [dict(r) for r in await cur.fetchall()]

@app.post("/api/admin/services", status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_admin)])
async def add_service(srv: ServiceCreate, db: aiosqlite.Connection = Depends(get_db)):
    srv_id = f"S-{uuid.uuid4().hex[:4].upper()}"
    await db.execute(
        "INSERT INTO services (id, name, icon, price, description, color) VALUES (?,?,?,?,?,?)",
        (srv_id, srv.name, srv.icon, srv.price, srv.description, srv.color)
    )
    await db.commit()
    return {"status": "success", "id": srv_id}

@app.put("/api/admin/services/{srv_id}", dependencies=[Depends(verify_admin)])
async def update_service(srv_id: str, srv: ServiceCreate, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute(
        "UPDATE services SET name=?, icon=?, price=?, description=?, color=? WHERE id=?",
        (srv.name, srv.icon, srv.price, srv.description, srv.color, srv_id)
    )
    await db.commit()
    return {"status": "updated"}

@app.delete("/api/admin/services/{srv_id}", dependencies=[Depends(verify_admin)])
async def delete_service(srv_id: str, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("DELETE FROM services WHERE id = ?", (srv_id,))
    await db.commit()
    return {"status": "deleted"}

# Users
@app.get("/api/admin/users", dependencies=[Depends(verify_admin)])
async def get_admin_users(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT tg_id as id, full_name as name, username, created_at FROM users ORDER BY created_at DESC") as cur:
        return [dict(r) for r in await cur.fetchall()]

# Promo Codes
@app.get("/api/admin/promocodes", dependencies=[Depends(verify_admin)])
async def list_promocodes(db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute("SELECT * FROM promocodes ORDER BY code") as cur:
        return [dict(r) for r in await cur.fetchall()]

@app.post("/api/admin/promocodes", dependencies=[Depends(verify_admin)])
async def create_promocode(p: PromoCode, db: aiosqlite.Connection = Depends(get_db)):
    try:
        await db.execute(
            "INSERT OR REPLACE INTO promocodes (code, type, value, expires_at) VALUES (?,?,?,?)",
            (p.code.upper(), p.type, p.value, p.expires_at)
        )
        await db.commit()
        return {"status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/admin/promocodes/{code}", dependencies=[Depends(verify_admin)])
async def delete_promocode(code: str, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    await db.commit()
    return {"status": "deleted"}

# Chat — per-user conversation thread
@app.get("/api/admin/chat/conversations", dependencies=[Depends(verify_admin)])
async def get_conversations(db: aiosqlite.Connection = Depends(get_db)):
    """Return all users who have at least one message, with last message and unread count."""
    async with db.execute("""
        WITH ChatList AS (
            SELECT 
                CASE WHEN sender_id = 'ADMIN' THEN receiver_id ELSE sender_id END AS user_id,
                text,
                timestamp,
                is_read,
                sender_id
            FROM messages
        )
        SELECT 
            cl.user_id,
            COALESCE(u.full_name, 'Maxfiy mijoz') AS name,
            COALESCE(u.username, '') AS username,
            MAX(cl.timestamp) AS last_ts,
            (SELECT text FROM messages 
             WHERE (sender_id = cl.user_id AND receiver_id = 'ADMIN') 
                OR (sender_id = 'ADMIN' AND receiver_id = cl.user_id) 
             ORDER BY timestamp DESC LIMIT 1) AS last_text,
            SUM(CASE WHEN cl.sender_id != 'ADMIN' AND cl.is_read = 0 THEN 1 ELSE 0 END) AS unread
        FROM ChatList cl
        LEFT JOIN users u ON CAST(u.tg_id AS TEXT) = cl.user_id
        WHERE cl.user_id != 'ADMIN'
        GROUP BY cl.user_id
        ORDER BY last_ts DESC
    """) as cur:
        rows = await cur.fetchall()
        return [dict(r) for r in rows]

@app.put("/api/admin/chat/read/{user_id}", dependencies=[Depends(verify_admin)])
async def mark_read(user_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """Mark all messages from this user as read."""
    await db.execute(
        "UPDATE messages SET is_read = 1 WHERE sender_id = ? AND receiver_id = 'ADMIN'",
        (user_id,)
    )
    await db.commit()
    return {"status": "ok"}

@app.get("/api/chat/{user_id}")
async def get_messages(user_id: str, db: aiosqlite.Connection = Depends(get_db)):
    async with db.execute(
        "SELECT * FROM messages WHERE (sender_id=? AND receiver_id='ADMIN') OR (sender_id='ADMIN' AND receiver_id=?) ORDER BY timestamp ASC",
        (user_id, user_id)
    ) as cur:
        return [dict(r) for r in await cur.fetchall()]

@app.post("/api/chat/send")
async def send_message(msg: MessageCreate, request: Request, db: aiosqlite.Connection = Depends(get_db)):
    sender_id = request.headers.get("X-User-ID", "UNKNOWN")
    ts = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO messages (sender_id, receiver_id, text, timestamp) VALUES (?,?,?,?)",
        (sender_id, msg.receiver_id, msg.text, ts)
    )
    await db.commit()

    # If admin replies to user — notify user via Telegram
    if sender_id == "ADMIN" and msg.receiver_id != "ADMIN":
        await tg_send(msg.receiver_id, f"💬 <b>Admin javob berdi:</b>\n\n{msg.text}")
    
    # If user sends a message to ADMIN — notify admin via Telegram
    if sender_id != "ADMIN" and msg.receiver_id == "ADMIN":
        await tg_send(ADMIN_CHAT_ID, f"💬 <b>Yangi xabar!</b> (ID: <code>{sender_id}</code>)\n\n{msg.text}")

    return {"status": "sent"}

# Health
@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.0.0"}

# ─────────────────────────────────────────
# STATIC FILES
# ─────────────────────────────────────────
frontend_path = os.path.join(BASE_DIR, "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_path, "index.html"))

    @app.get("/admin")
    async def serve_admin():
        return FileResponse(os.path.join(frontend_path, "admin.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
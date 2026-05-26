import asyncio
import json
import logging
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiosqlite import connect as sqlite_connect
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
BOT_TOKEN        = os.environ.get("BOT_TOKEN", "8706112826:AAH_fSow83cu_DvvSDHXkVJwwI5gIHVphEw")
ADMIN_CHAT_ID    = int(os.environ.get("ADMIN_CHAT_ID", "6448909987"))
WEBAPP_URL       = os.environ.get("WEBAPP_URL", "https://mini-appp-1.onrender.com")
ADMIN_WEBAPP_URL = os.environ.get("ADMIN_WEBAPP_URL", "https://mini-appp-1.onrender.com/admin")
DB_FILE          = os.environ.get("DB_FILE", "enterprise_bot.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ─────────────────────────────────────────
# DB HELPERS
# ─────────────────────────────────────────
async def save_user(user: types.User):
    async with sqlite_connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (tg_id, username, full_name, created_at) VALUES (?, ?, ?, ?)",
            (user.id, user.username or "", user.full_name, datetime.now(timezone.utc).isoformat())
        )
        await db.commit()

# ─────────────────────────────────────────
# KEYBOARDS
# ─────────────────────────────────────────
def get_main_kb(is_admin: bool = False):
    buttons = [
        [InlineKeyboardButton(text="🚀 Ilovani Ochish", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="📊 Admin Panel", web_app=WebAppInfo(url=ADMIN_WEBAPP_URL))])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_order_kb(order_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Bajarildi", callback_data=f"ord_done:{order_id}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data=f"ord_cancel:{order_id}")
        ]
    ])

# ─────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await save_user(message.from_user)
    is_admin = message.from_user.id == ADMIN_CHAT_ID
    
    welcome_text = (
        f"👋 <b>Assalomu alaykum, {message.from_user.first_name}!</b>\n\n"
        f"<b>DigiPro Hub</b> — Premium IT xizmatlar markaziga xush kelibsiz.\n\n"
        f"Bizning xizmatlar:\n"
        f"• Telegram bot va Mini Applar\n"
        f"• Zamonaviy veb-saytlar\n"
        f"• Professional UI/UX dizayn\n\n"
        f"👇 Quyidagi tugma orqali xizmatlar bilan tanishishingiz va buyurtma berishingiz mumkin:"
    )
    
    if is_admin:
        welcome_text = "👑 <b>Xush kelibsiz, Admin!</b>\n\nBarcha buyurtmalar va xizmatlarni boshqarish uchun admin panelga o'ting."

    await message.answer(welcome_text, reply_markup=get_main_kb(is_admin))

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_CHAT_ID: return
    
    async with sqlite_connect(DB_FILE) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur: u_count = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders") as cur: o_count = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders WHERE status='PENDING'") as cur: p_count = (await cur.fetchone())[0]

    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {u_count}\n"
        f"📦 Jami buyurtmalar: {o_count}\n"
        f"⏳ Kutilmoqda: {p_count}"
    )

@dp.callback_query(F.data.startswith("ord_"))
async def process_order_callback(callback: CallbackQuery):
    action, order_id = callback.data.split(":")
    new_status = "COMPLETED" if "done" in action else "CANCELLED"
    status_text = "✅ Bajarildi" if "done" in action else "❌ Bekor qilindi"
    
    async with sqlite_connect(DB_FILE) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        await db.commit()
    
    await callback.message.edit_text(callback.message.text + f"\n\n<b>Status: {status_text}</b>")
    await callback.answer(f"Buyurtma holati o'zgardi: {new_status}")

@dp.message()
async def echo(message: Message):
    is_admin = message.from_user.id == ADMIN_CHAT_ID
    await message.answer("Tugmani bosing va Mini Appni ishga tushiring:", reply_markup=get_main_kb(is_admin))

# ─────────────────────────────────────────
# API NOTIFICATION HELPER (Optional but good)
# ─────────────────────────────────────────
async def notify_admin_new_order(order_data: dict):
    text = (
        f"🔔 <b>YANGI BUYURTMA!</b>\n\n"
        f"🆔 ID: <code>{order_data['id']}</code>\n"
        f"👤 Mijoz: {order_data['name']}\n"
        f"📞 Aloqa: <code>{order_data['contact']}</code>\n"
        f"🛠 Xizmat: {order_data['service']}\n"
        f"📝 Tavsif: {order_data['desc']}"
    )
    try:
        await bot.send_message(ADMIN_CHAT_ID, text, reply_markup=get_order_kb(order_data['id']))
    except Exception as e:
        logger.error(f"Notification error: {e}")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
async def main():
    logger.info("🤖 Bot ishga tushmoqda...")
    
    # Retry loop for network issues
    for attempt in range(5):
        try:
            await bot.set_my_commands([
                BotCommand(command="start", description="Ishga tushirish"),
                BotCommand(command="stats", description="Statistika (Admin)"),
            ])
            logger.info("✅ Bot commandlari o'rnatildi")
            break
        except Exception as e:
            logger.warning(f"⚠️ Telegram ulanish xatosi (urinish {attempt+1}/5): {e}")
            if attempt < 4:
                await asyncio.sleep(5)
            else:
                logger.error("❌ Telegramga ulanib bo'lmadi. Internet aloqasini tekshiring.")
                return
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
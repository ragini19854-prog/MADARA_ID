import asyncio
import os
from dataclasses import dataclass
from typing import Optional

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv("DB_PATH", "bot.db")
DEPOSIT_QR_PATH = os.getenv("DEPOSIT_QR_PATH", "assets/deposit_qr.png")
WELCOME_VIDEO_URL = os.getenv("WELCOME_VIDEO_URL", "").strip()
BRAND_NAME = os.getenv("BRAND_NAME", "Madara Virtual Account Bot").strip()

SUPPORT_LINK = "https://t.me/Madara_babu_gms_bot"
HOW_TO_USE_LINK = "https://t.me/MADARABITSUPPROT412"
DEFAULT_PASSWORD = "1010"
FORCE_JOIN_CHANNEL_LINK = "https://t.me/+oF0VkIRBFF01M2Q1"
FORCE_JOIN_CHAT_ID = os.getenv("FORCE_JOIN_CHAT_ID", "").strip()
DEPOSIT_REVIEW_OWNER_ID = 8394041476

OWNER_IDS = {6710777832, 8394041476, 8396616795, 8498330921, 8595642160}

BTN_TELEGRAM = "📲 Telegram Accounts"
BTN_WHATSAPP = "📲 WhatsApp SMS"
BTN_DEPOSIT = "💸 Deposit"
BTN_PROFILE = "👤 My Profile"
BTN_SUPPORT = "🧑‍💼 Support"
BTN_HOW_TO_USE = "📖 How to Use"
BTN_BACK = "🔙 Back"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TELEGRAM), KeyboardButton(text=BTN_WHATSAPP)],
            [KeyboardButton(text=BTN_DEPOSIT), KeyboardButton(text=BTN_PROFILE)],
            [KeyboardButton(text=BTN_SUPPORT), KeyboardButton(text=BTN_HOW_TO_USE)],
        ],
        resize_keyboard=True,
    )


def back_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_BACK)]],
        resize_keyboard=True,
    )


def buy_keyboard(account_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Buy Now", callback_data=f"buy:{account_id}")],
        ]
    )


def country_keyboard(account_type: str, countries: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(countries), 2):
        chunk = countries[i : i + 2]
        rows.append(
            [
                InlineKeyboardButton(
                    text=c,
                    callback_data=f"country:{account_type}:{c}",
                )
                for c in chunk
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dataclass
class Account:
    id: int
    number: str
    country: str
    price: float
    account_type: str
    status: str


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    balance REAL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    number TEXT NOT NULL,
                    country TEXT NOT NULL,
                    price REAL NOT NULL,
                    account_type TEXT NOT NULL,
                    status TEXT DEFAULT 'available',
                    added_by INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    account_id INTEGER NOT NULL,
                    number TEXT NOT NULL,
                    country TEXT NOT NULL,
                    price REAL NOT NULL,
                    account_type TEXT NOT NULL,
                    otp TEXT,
                    status TEXT DEFAULT 'pending_otp',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS deposit_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    screenshot_file_id TEXT,
                    details TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    reviewed_by INTEGER,
                    credited_amount REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at DATETIME
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS problems (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def upsert_user(self, message: Message):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO users(user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name
                """,
                (
                    message.from_user.id,
                    message.from_user.username,
                    message.from_user.first_name,
                ),
            )
            await db.commit()

    async def all_users(self) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT user_id FROM users")
            rows = await cur.fetchall()
            return [r[0] for r in rows]

    async def add_account(self, number: str, country: str, price: float, account_type: str, added_by: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO accounts(number, country, price, account_type, added_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (number, country.lower(), price, account_type, added_by),
            )
            await db.commit()

    async def countries_with_stock(self, account_type: str) -> list[tuple[str, int, float]]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT country, COUNT(*), MIN(price)
                FROM accounts
                WHERE account_type = ? AND status = 'available'
                GROUP BY country
                ORDER BY country ASC
                """,
                (account_type,),
            )
            return await cur.fetchall()

    async def first_available_for_country(self, account_type: str, country: str) -> Optional[Account]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT id, number, country, price, account_type, status
                FROM accounts
                WHERE account_type = ? AND country = ? AND status = 'available'
                ORDER BY id ASC
                LIMIT 1
                """,
                (account_type, country.lower()),
            )
            row = await cur.fetchone()
            if not row:
                return None
            return Account(*row)

    async def account_by_id(self, account_id: int) -> Optional[Account]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT id, number, country, price, account_type, status
                FROM accounts WHERE id = ?
                """,
                (account_id,),
            )
            row = await cur.fetchone()
            return Account(*row) if row else None

    async def get_balance(self, user_id: int) -> float:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
            return float(row[0]) if row else 0.0

    async def set_balance(self, user_id: int, amount: float):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO users(user_id, balance) VALUES(?, ?)
                ON CONFLICT(user_id) DO UPDATE SET balance = excluded.balance
                """,
                (user_id, amount),
            )
            await db.commit()

    async def credit_balance(self, user_id: int, amount: float):
        bal = await self.get_balance(user_id)
        await self.set_balance(user_id, bal + amount)

    async def purchase(self, user_id: int, account: Account) -> Optional[int]:
        bal = await self.get_balance(user_id)
        if bal < account.price:
            return None
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (account.price, user_id))
            await db.execute("UPDATE accounts SET status = 'sold' WHERE id = ?", (account.id,))
            cur = await db.execute(
                """
                INSERT INTO purchases(user_id, account_id, number, country, price, account_type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, account.id, account.number, account.country, account.price, account.account_type),
            )
            await db.commit()
            return cur.lastrowid

    async def purchase_history(self, user_id: int) -> list[tuple]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT account_type, number, country, price, status, created_at
                FROM purchases WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 10
                """,
                (user_id,),
            )
            return await cur.fetchall()

    async def set_otp_and_get_user(self, number: str, otp: str) -> Optional[tuple[int, int]]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT id, user_id FROM purchases
                WHERE number = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (number,),
            )
            row = await cur.fetchone()
            if not row:
                return None
            purchase_id, user_id = row
            await db.execute("UPDATE purchases SET otp = ?, status = 'otp_sent' WHERE id = ?", (otp, purchase_id))
            await db.commit()
            return purchase_id, user_id

    async def add_problem(self, user_id: int, msg: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO problems(user_id, message) VALUES (?, ?)", (user_id, msg))
            await db.commit()

    async def create_deposit_request(self, user_id: int, details: str, screenshot_file_id: str | None) -> int:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                INSERT INTO deposit_requests(user_id, screenshot_file_id, details)
                VALUES (?, ?, ?)
                """,
                (user_id, screenshot_file_id, details),
            )
            await db.commit()
            return cur.lastrowid

    async def get_deposit_request(self, request_id: int) -> Optional[tuple]:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                SELECT id, user_id, screenshot_file_id, details, status
                FROM deposit_requests
                WHERE id = ?
                """,
                (request_id,),
            )
            return await cur.fetchone()

    async def mark_deposit_decision(self, request_id: int, owner_id: int, status: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute(
                """
                UPDATE deposit_requests
                SET status = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
                """,
                (status, owner_id, request_id),
            )
            await db.commit()
            return cur.rowcount > 0

    async def apply_deposit_credit(self, request_id: int, owner_id: int, amount: float) -> Optional[int]:
        req = await self.get_deposit_request(request_id)
        if not req:
            return None
        _, user_id, _, _, status = req
        if status == "credited":
            return -1

        await self.credit_balance(user_id, amount)
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE deposit_requests
                SET status = 'credited', reviewed_by = ?, credited_amount = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (owner_id, amount, request_id),
            )
            await db.commit()
        return user_id

    async def solve_problem(self, problem_id: int) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cur = await db.execute("UPDATE problems SET status='closed' WHERE id = ?", (problem_id,))
            await db.commit()
            return cur.rowcount > 0


db = Database(DB_PATH)
dp = Dispatcher()
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
awaiting_deposit_submission: set[int] = set()


def force_join_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Channel", url=FORCE_JOIN_CHANNEL_LINK)],
            [InlineKeyboardButton(text="✅ I Joined", callback_data="check_join")],
        ]
    )


async def is_force_join_ok(user_id: int) -> bool:
    if not FORCE_JOIN_CHAT_ID:
        return True
    try:
        member = await bot.get_chat_member(FORCE_JOIN_CHAT_ID, user_id)
    except Exception:
        return True
    return member.status in {"member", "administrator", "creator"}


def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS


@dp.message(CommandStart())
async def start_cmd(message: Message):
    await db.upsert_user(message)

    if not await is_force_join_ok(message.from_user.id):
        await message.answer(
            "⚠️ Please join our channel first, then tap 'I Joined' to continue.",
            reply_markup=force_join_keyboard(),
        )
        return

    if WELCOME_VIDEO_URL:
        try:
            await message.answer_video(video=WELCOME_VIDEO_URL, caption=f"🎬 Welcome to {BRAND_NAME}")
        except Exception:
            pass

    welcome = (
        f"<b>WELCOME to {BRAND_NAME}</b> 👋\n"
        "Hlo! Bye!\n\n"
        "Choose an option from the panel below to continue."
    )
    await message.answer(welcome, reply_markup=main_menu())


@dp.callback_query(F.data == "check_join")
async def check_join_callback(callback: CallbackQuery):
    if await is_force_join_ok(callback.from_user.id):
        await callback.message.answer("✅ Verification complete.", reply_markup=main_menu())
        await callback.answer("Joined verified")
        return
    await callback.answer("Join the channel first.", show_alert=True)


@dp.message(F.text == BTN_BACK)
async def back_btn(message: Message):
    await message.answer("Back to main menu.", reply_markup=main_menu())


async def show_account_countries(message: Message, account_type: str, label: str):
    stock = await db.countries_with_stock(account_type)
    if not stock:
        await message.answer(f"No {label} stock is available right now.", reply_markup=main_menu())
        return

    lines = [
        "🟢 <b>Select a Country You Need</b>",
        "⚡ Rate: 1 USDT = ₹89.0",
        "🎁 Tip: Deposit at least ₹1000 today to unlock discount.",
        "",
    ]
    countries = []
    for country, count, min_price in stock:
        lines.append(f"🌍 {country}: ${min_price:.2f} - Stock: {count}")
        countries.append(country)

    await message.answer("\n".join(lines), reply_markup=back_menu())
    await message.answer("Choose country:", reply_markup=country_keyboard(account_type, countries))


@dp.message(F.text == BTN_TELEGRAM)
async def telegram_accounts(message: Message):
    await show_account_countries(message, "telegram", "Telegram accounts")


@dp.message(F.text == BTN_WHATSAPP)
async def whatsapp_accounts(message: Message):
    await show_account_countries(message, "whatsapp", "WhatsApp accounts")


@dp.message(F.text == BTN_SUPPORT)
async def support_handler(message: Message):
    await message.answer(f"🧑‍💼 Support: {SUPPORT_LINK}")


@dp.message(F.text == BTN_HOW_TO_USE)
async def how_to_use_handler(message: Message):
    await message.answer(f"📖 How to Use: {HOW_TO_USE_LINK}")


@dp.message(F.text == BTN_DEPOSIT)
async def deposit_handler(message: Message):
    text = "Please send the screenshot of your payment with your UTR ID and name."
    awaiting_deposit_submission.add(message.from_user.id)
    if os.path.exists(DEPOSIT_QR_PATH):
        await message.answer_photo(FSInputFile(DEPOSIT_QR_PATH), caption=text)
    else:
        await message.answer("QR image is not configured yet.\n" + text)


@dp.message(lambda m: m.from_user and m.from_user.id in awaiting_deposit_submission)
async def capture_deposit_submission(message: Message):
    if message.text == BTN_BACK:
        awaiting_deposit_submission.discard(message.from_user.id)
        await message.answer("Back to main menu.", reply_markup=main_menu())
        return

    details = message.caption or message.text or "No details provided"
    screenshot_file_id = message.photo[-1].file_id if message.photo else None
    request_id = await db.create_deposit_request(message.from_user.id, details, screenshot_file_id)
    awaiting_deposit_submission.discard(message.from_user.id)

    owner_text = (
        "💸 <b>New Deposit Request</b>\n"
        f"Deposit ID: <code>{request_id}</code>\n"
        f"User ID: <code>{message.from_user.id}</code>\n"
        f"Name: {message.from_user.full_name}\n"
        f"Username: @{message.from_user.username or 'none'}\n\n"
        f"Details:\n{details}"
    )
    owner_actions = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Approve", callback_data=f"dep_approve:{request_id}")],
            [InlineKeyboardButton(text="❌ Deny", callback_data=f"dep_deny:{request_id}")],
        ]
    )
    try:
        if screenshot_file_id:
            await bot.send_photo(DEPOSIT_REVIEW_OWNER_ID, screenshot_file_id, caption=owner_text, reply_markup=owner_actions)
        else:
            await bot.send_message(DEPOSIT_REVIEW_OWNER_ID, owner_text, reply_markup=owner_actions)
    except Exception:
        pass

    await message.answer(
        f"✅ Deposit request submitted.\nYour Deposit ID: <code>{request_id}</code>\nPlease wait for admin review.",
        reply_markup=main_menu(),
    )


@dp.callback_query(F.data.startswith("dep_approve:"))
async def approve_deposit_request(callback: CallbackQuery):
    if callback.from_user.id != DEPOSIT_REVIEW_OWNER_ID and not is_owner(callback.from_user.id):
        await callback.answer("Not allowed", show_alert=True)
        return
    request_id = int(callback.data.split(":", 1)[1])
    ok = await db.mark_deposit_decision(request_id, callback.from_user.id, "approved")
    if not ok:
        await callback.answer("Already reviewed or invalid request.", show_alert=True)
        return
    await callback.message.answer(
        f"Approved Deposit ID <code>{request_id}</code>.\nNow run: <code>/add {request_id} amount</code>"
    )
    await callback.answer("Approved")


@dp.callback_query(F.data.startswith("dep_deny:"))
async def deny_deposit_request(callback: CallbackQuery):
    if callback.from_user.id != DEPOSIT_REVIEW_OWNER_ID and not is_owner(callback.from_user.id):
        await callback.answer("Not allowed", show_alert=True)
        return
    request_id = int(callback.data.split(":", 1)[1])
    ok = await db.mark_deposit_decision(request_id, callback.from_user.id, "denied")
    if not ok:
        await callback.answer("Already reviewed or invalid request.", show_alert=True)
        return
    req = await db.get_deposit_request(request_id)
    if req:
        await bot.send_message(req[1], f"❌ Your deposit request {request_id} was denied. Contact support if needed.")
    await callback.message.answer(f"Deposit ID <code>{request_id}</code> denied.")
    await callback.answer("Denied")


@dp.message(F.text == BTN_PROFILE)
async def profile_handler(message: Message):
    bal = await db.get_balance(message.from_user.id)
    history = await db.purchase_history(message.from_user.id)
    lines = [
        f"👤 <b>Profile</b>",
        f"💰 Balance: ₹{bal:.2f}",
        "🧾 Last Purchases:",
    ]
    if not history:
        lines.append("- No purchases yet.")
    else:
        for i, (acc_type, number, country, price, status, created_at) in enumerate(history, start=1):
            lines.append(f"{i}. {acc_type.upper()} | {country} | {number} | ₹{price:.2f} | {status} | {created_at}")
    await message.answer("\n".join(lines))


@dp.callback_query(F.data.startswith("country:"))
async def country_select(callback):
    _, account_type, country = callback.data.split(":", 2)
    account = await db.first_available_for_country(account_type, country)
    if not account:
        await callback.message.answer("No stock available for this country right now.")
        await callback.answer()
        return

    msg = (
        f"⚡ <b>{account_type.title()} Account Info</b>\n\n"
        f"🌍 Country: {account.country}\n"
        f"💸 Price: ₹{account.price:.2f}\n"
        f"📦 Available: 1+\n"
        f"✅ Reliable | Affordable | Good Quality\n\n"
        f"⚠️ Important: Please use Telegram X.\n"
        f"🚫 We are not responsible for any freeze/ban."
    )
    await callback.message.answer(msg, reply_markup=buy_keyboard(account.id))
    await callback.answer()


@dp.callback_query(F.data.startswith("buy:"))
async def buy_now(callback):
    account_id = int(callback.data.split(":", 1)[1])
    account = await db.account_by_id(account_id)
    if not account or account.status != "available":
        await callback.message.answer("This account is no longer available.")
        await callback.answer()
        return

    purchase_id = await db.purchase(callback.from_user.id, account)
    if purchase_id is None:
        bal = await db.get_balance(callback.from_user.id)
        await callback.message.answer(
            "❌ Insufficient deposit balance.\n"
            f"Price: ₹{account.price:.2f}\n"
            f"Your Balance: ₹{bal:.2f}\n\n"
            "PLSS FIRST DEPOSIT USING DEPLOST BUTTON THEN PURCHASE THE NUMBER."
        )
        await callback.answer()
        return

    await callback.message.answer(
        f"✅ Purchase successful!\n"
        f"Type: {account.account_type.upper()}\n"
        f"Number: <code>{account.number}</code>\n"
        f"Password: <code>{DEFAULT_PASSWORD}</code>\n\n"
        "Waiting for OTP... it will be delivered instantly when received."
    )
    await callback.answer("Purchased")


@dp.message(Command("problem"))
async def report_problem(message: Message):
    if not message.text:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /problem <your issue>")
        return
    await db.add_problem(message.from_user.id, parts[1])
    await message.answer("Problem submitted. Owner will review it.")


@dp.message(Command("addnum"))
async def addnum_cmd(message: Message):
    if not is_owner(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("Usage: /addnum <number> <country> <price>")
        return
    _, number, country, price = parts[:4]
    try:
        price_value = float(price)
    except ValueError:
        await message.answer("Invalid price.")
        return

    await db.add_account(number, country, price_value, "telegram", message.from_user.id)
    await message.answer(f"Added TELEGRAM number {number} for {country} at ₹{price_value:.2f}.")


@dp.message(Command("addaccount"))
async def addaccount_cmd(message: Message):
    if not is_owner(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 5:
        await message.answer("Usage: /addaccount <telegram|whatsapp> <number> <country> <price>")
        return

    _, account_type, number, country, price = parts[:5]
    account_type = account_type.lower()
    if account_type not in {"telegram", "whatsapp"}:
        await message.answer("Type must be telegram or whatsapp.")
        return

    try:
        price_value = float(price)
    except ValueError:
        await message.answer("Invalid price.")
        return

    await db.add_account(number, country, price_value, account_type, message.from_user.id)
    await message.answer(f"Added {account_type.upper()} account {number} ({country}) ₹{price_value:.2f}.")


@dp.message(Command("setbalance"))
async def setbalance_cmd(message: Message):
    if not is_owner(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Usage: /setbalance <user_id> <amount>")
        return
    _, user_id, amount = parts
    await db.set_balance(int(user_id), float(amount))
    await message.answer("Balance updated.")


@dp.message(Command("credit"))
async def credit_cmd(message: Message):
    if not is_owner(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Usage: /credit <user_id> <amount>")
        return
    _, user_id, amount = parts
    await db.credit_balance(int(user_id), float(amount))
    await message.answer("Balance credited.")


@dp.message(Command("add"))
async def add_deposit_cmd(message: Message):
    if message.from_user.id != DEPOSIT_REVIEW_OWNER_ID and not is_owner(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Usage: /add <deposit_id> <amount>")
        return
    _, deposit_id, amount = parts
    try:
        dep_id = int(deposit_id)
        amt = float(amount)
    except ValueError:
        await message.answer("Invalid deposit id or amount.")
        return
    if amt <= 0:
        await message.answer("Amount must be greater than 0.")
        return

    user_id = await db.apply_deposit_credit(dep_id, message.from_user.id, amt)
    if user_id is None:
        await message.answer("Deposit request not found.")
        return
    if user_id == -1:
        await message.answer("This deposit request is already credited.")
        return

    await message.answer(f"✅ Added ₹{amt:.2f} to Deposit ID {dep_id} (User {user_id}).")
    await bot.send_message(user_id, f"✅ Deposit approved and credited: ₹{amt:.2f}\nYour wallet has been updated.")


@dp.message(Command("setotp"))
async def setotp_cmd(message: Message):
    if not is_owner(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /setotp <number> <otp>")
        return
    _, number, otp = parts[:3]
    updated = await db.set_otp_and_get_user(number, otp)
    if not updated:
        await message.answer("No purchase found for that number.")
        return
    _, user_id = updated
    await bot.send_message(
        user_id,
        f"🔐 OTP Received\nNumber: <code>{number}</code>\nOTP:- <code>{otp}</code>\nPASS :- <code>{DEFAULT_PASSWORD}</code>",
    )
    await message.answer("OTP pushed to user instantly.")


@dp.message(Command("solve"))
async def solve_cmd(message: Message):
    if not is_owner(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Usage: /solve <problem_id>")
        return
    ok = await db.solve_problem(int(parts[1]))
    await message.answer("Problem closed." if ok else "Problem not found.")


@dp.message(Command("broadcast"))
async def broadcast_cmd(message: Message):
    if not is_owner(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /broadcast <message>")
        return
    text = parts[1]
    users = await db.all_users()
    sent = 0
    for uid in users:
        try:
            await bot.send_message(uid, f"📢 Broadcast\n\n{text}")
            sent += 1
        except Exception:
            continue
    await message.answer(f"Broadcast done. Sent to {sent}/{len(users)} users.")


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Please configure .env")
    await db.init()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

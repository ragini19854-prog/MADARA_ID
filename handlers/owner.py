from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import Database

router = Router(name="owner")


async def owner_only(message: Message, db: Database) -> bool:
    if await db.is_owner(message.from_user.id):
        return True
    await message.answer("Owner only command")
    return False


@router.message(Command("ownerpanel"))
async def owner_panel(message: Message, db: Database) -> None:
    if not await owner_only(message, db):
        return
    await message.answer("Owner commands:\n/ban user_id\n/unban user_id\n/broadcast text\n/addowner user_id")


@router.message(Command("ban"))
async def ban(message: Message, db: Database) -> None:
    if not await owner_only(message, db):
        return
    args = (message.text or "").split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Usage: /ban <user_id> [reason]")
        return
    user_id = int(args[1])
    reason = args[2] if len(args) > 2 else None
    await db.ban_user(user_id, message.from_user.id, reason)
    await message.answer(f"Banned {user_id}")


@router.message(Command("unban"))
async def unban(message: Message, db: Database) -> None:
    if not await owner_only(message, db):
        return
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /unban <user_id>")
        return
    await db.unban_user(int(args[1]))
    await message.answer("Unbanned")


@router.message(Command("addowner"))
async def add_owner(message: Message, db: Database) -> None:
    if not await owner_only(message, db):
        return
    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: /addowner <user_id>")
        return
    uid = int(args[1])
    await db.ensure_user(uid, None, f"owner_{uid}", is_admin=True)
    await db.add_owner(uid)
    await message.answer("Owner added")


@router.message(Command("broadcast"))
async def broadcast(message: Message, db: Database) -> None:
    if not await owner_only(message, db):
        return
    text = (message.text or "").split(maxsplit=1)
    if len(text) < 2:
        await message.answer("Usage: /broadcast <text>")
        return

    # Lightweight broadcast over known users.
    async with await db.connect() as conn:
        cur = await conn.execute("SELECT user_id FROM Users")
        users = [r[0] for r in await cur.fetchall()]

    sent = 0
    for uid in users:
        try:
            await message.bot.send_message(uid, text[1])
            sent += 1
        except Exception:
            continue
    await message.answer(f"Broadcast sent: {sent}/{len(users)}")


@router.message(Command("addvote"))
async def addvote(message: Message, db: Database) -> None:
    args = (message.text or "").split()
    if len(args) != 3:
        await message.answer("Usage: /addvote <participant_id> <amount>")
        return
    participant_id = int(args[1])
    amount = int(args[2])
    await db.add_manual_votes(participant_id, amount)
    await message.answer("Votes added")

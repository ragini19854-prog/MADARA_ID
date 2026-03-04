from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database import Database
from states.post_creator import PostCreatorState

router = Router(name="post_creator")


def parse_buttons(raw: str) -> InlineKeyboardMarkup | None:
    if not raw or raw.lower() == "skip":
        return None
    rows = []
    for row in raw.split("&&"):
        row_buttons = []
        for pair in row.split("|"):
            name, link = [x.strip() for x in pair.split("-", 1)]
            row_buttons.append(InlineKeyboardButton(text=name, url=link))
        rows.append(row_buttons)
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "menu:create_post")
async def create_post_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PostCreatorState.photo)
    await callback.answer()
    await callback.message.answer("Step 1: Send Photo or type Skip")


@router.message(PostCreatorState.photo, F.photo)
async def post_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo=message.photo[-1].file_id)
    await state.set_state(PostCreatorState.caption)
    await message.answer("Step 2: Send Caption")


@router.message(PostCreatorState.photo)
async def post_photo_skip(message: Message, state: FSMContext) -> None:
    if (message.text or "").lower() != "skip":
        await message.answer("Send photo or type Skip")
        return
    await state.update_data(photo=None)
    await state.set_state(PostCreatorState.caption)
    await message.answer("Step 2: Send Caption")


@router.message(PostCreatorState.caption)
async def post_caption(message: Message, state: FSMContext) -> None:
    await state.update_data(caption=message.text)
    await state.set_state(PostCreatorState.buttons)
    await message.answer("Step 3: Add Buttons\nFormat: Name - Link | Name2 - Link2 && NextRow - Link\nType Skip for none")


@router.message(PostCreatorState.buttons)
async def post_buttons(message: Message, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    try:
        markup = parse_buttons(message.text or "")
    except Exception:
        await message.answer("Invalid button format.")
        return
    await state.update_data(buttons=message.text or "skip")
    await state.set_state(PostCreatorState.confirm)
    preview = "Preview:"
    if data.get("photo"):
        await message.answer_photo(
            data["photo"],
            caption=data["caption"],
            reply_markup=markup,
        )
    else:
        await message.answer(data["caption"], reply_markup=markup)

    chats = await db.list_user_chats(message.from_user.id, "channel")
    if not chats:
        await message.answer("No saved channels. Use Add Channel first.")
        await state.clear()
        return
    rows = [[InlineKeyboardButton(text=f"🚀 Send to {c['chat_title']}", callback_data=f"post:send:{c['chat_id']}")] for c in chats[:5]]
    rows.append([InlineKeyboardButton(text="🗑 Discard", callback_data="post:discard")])
    await message.answer("Choose action:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(PostCreatorState.confirm, F.data == "post:discard")
async def discard_post(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Discarded")


@router.callback_query(PostCreatorState.confirm, F.data.startswith("post:send:"))
async def send_post(callback: CallbackQuery, state: FSMContext) -> None:
    chat_id = int(callback.data.split(":")[-1])
    data = await state.get_data()
    markup = parse_buttons(data.get("buttons", "skip"))
    if data.get("photo"):
        await callback.bot.send_photo(chat_id, data["photo"], caption=data["caption"], reply_markup=markup)
    else:
        await callback.bot.send_message(chat_id, data["caption"], reply_markup=markup)
    await state.clear()
    await callback.answer("Sent")

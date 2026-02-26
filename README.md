# Virtual Account Purchase Bot (Telegram)

This project is a Telegram bot for selling virtual accounts (Telegram/WhatsApp) with:

- Welcome flow with optional welcome video.
- Main panel buttons.
- Country-wise stock display and buying flow.
- Owner-only commands for adding accounts/numbers, broadcasting, and problem management.
- Profile showing purchase history and wallet balance.
- Deposit flow with QR image.
- OTP update flow from owner panel (`/setotp`) that instantly notifies the buyer.

## Setup

1. Create virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment variables:

```bash
cp .env.example .env
```

Then edit `.env`:

- `BOT_TOKEN`: your bot token.
- `DB_PATH`: sqlite file path (default `bot.db`).
- `DEPOSIT_QR_PATH`: local QR image path.
- `WELCOME_VIDEO_URL`: optional public video URL for start welcome video.
- `BRAND_NAME`: your brand/bot name shown in welcome messages.

3. Put your deposit QR in `assets/deposit_qr.png` (or change `DEPOSIT_QR_PATH`).

4. Run bot:

```bash
python bot.py
```

## Owner IDs (preloaded)

- 6710777832
- 8394041476
- 8396616795
- 8498330921
- 8595642160

## Core owner commands

- `/addnum <number> <country> <price>` — add stock item.
- `/addaccount <type> <number> <country> <price>` — add account by type (`telegram` or `whatsapp`).
- `/broadcast <message>` — send message to all users.
- `/setbalance <user_id> <amount>` — set wallet balance.
- `/credit <user_id> <amount>` — add wallet balance.
- `/setotp <number> <otp>` — set OTP for sold number and notify buyer instantly.
- `/solve <problem_id>` — mark user-reported problem as resolved.

## User menu (as requested)

- Telegram Accounts
- WhatsApp SMS
- Deposit
- My Profile
- Support
- How to Use

(Buttons for Telegram Session and Promocode removed.)


## Security note

- If you shared your bot token publicly, rotate it immediately with @BotFather and update `.env`.

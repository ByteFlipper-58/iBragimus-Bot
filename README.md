# iBragimusBot

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-local-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)

Telegram Business assistant for AI auto-replies, message edit/delete tracking, blacklist management, and media recovery through a connected Telegram account session.

Secrets stay in your `.env` or local SQLite database, runtime data stays on your machine, and AI provider settings can be changed from the private admin chat.

## Features

- Telegram Business message handling with AI auto-replies.
- Runtime AI provider switching between OpenAI, Anthropic, and Google Gemini.
- Model selection from provider-fetched lists, with pagination and manual input.
- API key management from the private admin panel.
- Editable system prompt and a global AI on/off toggle.
- Reply delay control and ignored-words filtering.
- Conversation context for AI replies (toggle + adjustable depth).
- Blacklist checks before auto-replying.
- Message archive for edit/delete recovery, with admin notifications.
- View-once photo/video saving through the connected account client.
- SQLite-backed local persistence.

## Tech Stack

| Area | Tooling |
| --- | --- |
| Bot framework | `aiogram` 3.x |
| Connected Telegram account | `telethon` |
| AI providers | `openai`, `anthropic`, `google-genai` |
| Database | SQLite via `aiosqlite` |
| Configuration | `pydantic-settings`, `.env` |
| QR rendering | `segno` |

## Project Structure

```text
iBragimusBot/
├── main.py                     # App entry point, bot setup, routers, middleware
├── config.py                   # Environment-based settings
├── database/
│   ├── db.py                   # SQLite connection manager
│   ├── migrations.py           # Schema bootstrap
│   └── repository.py           # Repository layer
├── handlers/
│   ├── admin/                  # Private admin panel flows
│   └── business/               # Telegram Business event handlers
├── keyboards/                  # Inline keyboard builders
├── services/
│   ├── ai.py                   # OpenAI / Anthropic / Gemini integration
│   └── catcher_service.py      # Media/message recovery helpers
├── telegram_account.py         # Connected account client
├── requirements.txt
└── .env.example
```

## Quick Start

```bash
git clone <your-repo-url>
cd iBragimusBot

python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy the example env file and fill in the required values:

```bash
cp .env.example .env          # Windows: Copy-Item .env.example .env
```

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ADMIN_ID=YOUR_TELEGRAM_USER_ID

AI_PROVIDER=google

OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_MODEL=gpt-4.1-mini

ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY
ANTHROPIC_MODEL=claude-sonnet-4-20250514

GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash

TELEGRAM_API_ID=YOUR_TELEGRAM_API_ID
TELEGRAM_API_HASH=YOUR_TELEGRAM_API_HASH
```

Run the bot, then open a private chat with it and send `/start` or `/menu`:

```bash
python main.py
```

## Telegram Setup

- **Bot token** — create a bot via [@BotFather](https://t.me/BotFather) and put the token into `BOT_TOKEN`.
- **Admin ID** — set `ADMIN_ID` to your numeric Telegram user ID. Only this account can use the admin panel.
- **API credentials** — create an app at [my.telegram.org/apps](https://my.telegram.org/apps) and copy `api_id` → `TELEGRAM_API_ID`, `api_hash` → `TELEGRAM_API_HASH`. These are used by the connected account client for QR/phone login and media recovery.

### Business connection

1. In [@BotFather](https://t.me/BotFather), select your bot and enable **Bot Settings → Business Mode**.
2. In your Telegram app, go to **Telegram Business → Chatbots**.
3. Add your bot and allow it to reply to messages.

## Admin Panel

The private admin panel includes auto-reply toggle, Telegram account login/status, system prompt edit, AI provider and model selection (with provider-fetched lists and manual input), per-provider API key updates, auto-reply behavior (reply delay, ignored words, conversation context), blacklist management, statistics, and connection instructions.

## AI Providers

| Provider | Env key | Model setting |
| --- | --- | --- |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_MODEL` |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` |
| Google Gemini | `GEMINI_API_KEY` | `GEMINI_MODEL` |

The admin panel can override provider, model, and API key at runtime. If no override exists, the bot falls back to `.env`.

## Local Data & Security

The bot stores runtime data locally and these files are intentionally git-ignored:

- `data.db` — SQLite database;
- `telegram_account.session` — connected account session;
- `media_cache/` — cached media files;
- `.env` — local secrets.

Treat all of the above as sensitive. API keys entered through the admin panel are stored in the local SQLite settings table, and the bot attempts to delete admin messages containing keys after saving them. Keep the host machine trusted and rotate provider keys if logs, database files, or screenshots are ever exposed.

## License

No license has been selected yet.

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
- Bulk-deletion transcript backup file.
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

## Architecture

The codebase is split into small focused modules grouped by responsibility, so
each layer has one reason to change.

- **Configuration** (`config.py`) — typed environment-driven settings.
- **Persistence** (`database/`) — `DatabaseManager` owns a single shared
  SQLite connection. `BotRepository` is a thin container that exposes
  per-aggregate repositories: `repo.connections`, `repo.settings`,
  `repo.blacklist`, `repo.logs`, `repo.archive`.
- **AI service** (`services/ai/`) — pluggable provider package. `AIConfig`
  resolves the active provider, the `providers/` subpackage holds the
  per-vendor implementations, `registry.py` caches configured clients,
  `models.py` powers the admin model picker, and `reply.py` is the
  high-level helper used by Business handlers.
- **Catcher service** (`services/catcher/`) — media downloader, HTML
  formatters for edit/delete alerts, and bulk-deletion transcript
  generation. All filesystem paths are centralised in `paths.py`.
- **Business helpers** (`services/business/`) — auto-reply skip policy
  and message-media caching extracted from handlers.
- **Notifier** (`services/notifier.py`) — single place for sending
  messages, documents, and cached media to the admin chat.
- **Connected account** (`telegram_account/`) — Telethon client lifecycle,
  view-once media interceptor, session helpers.
- **Middleware** (`middlewares/db_middleware.py`) — injects `BotRepository`
  into aiogram handler context.
- **Handlers** (`handlers/`) — admin and Business event handlers, each split
  into small modules and a shared FSM-input helper.
- **Keyboards** (`keyboards/`) — inline keyboard factories grouped by
  admin screen.

## Project Structure

```text
iBragimusBot/
├── main.py                          # App entry: bot, dispatcher, routers, middleware
├── config.py                        # Pydantic settings from .env
├── database/
│   ├── db.py                        # DatabaseManager (shared aiosqlite connection)
│   ├── migrations.py                # Schema bootstrap and seed settings
│   ├── repository.py                # BotRepository (thin aggregator)
│   └── repositories/                # Per-aggregate repositories
│       ├── connections.py
│       ├── settings.py
│       ├── blacklist.py
│       ├── logs.py
│       └── messages_archive.py
├── handlers/
│   ├── admin/                       # Private admin panel
│   │   ├── menu.py                  # /start, /menu, stats, AI toggle, help
│   │   ├── prompt.py                # System prompt editor
│   │   ├── ai_settings.py           # Provider, model, API key
│   │   ├── behavior.py              # Reply delay, ignored words, context
│   │   ├── blacklist.py             # Blacklist CRUD
│   │   ├── account/                 # Telegram account login flows
│   │   │   ├── status.py
│   │   │   ├── qr_login.py
│   │   │   ├── phone_login.py
│   │   │   ├── twofa.py
│   │   │   ├── reset.py
│   │   │   ├── errors.py            # Telethon error → admin text
│   │   │   ├── qr.py                # QR PNG renderer
│   │   │   └── utils.py             # Phone/code normalisation
│   │   ├── states.py                # FSM states
│   │   ├── ui.py                    # Safe edit_text helpers
│   │   ├── fsm_input.py             # Reusable setting-edit FSM helper
│   │   ├── login_session.py         # Per-admin login task/lock state
│   │   └── context.py               # Auth and account-status helpers
│   └── business/                    # Telegram Business event handlers
│       ├── connections.py
│       ├── messages.py
│       ├── edits.py
│       └── deletions.py
├── keyboards/                       # Inline keyboards split by admin screen
│   ├── main.py
│   ├── ai.py
│   ├── behavior.py
│   ├── blacklist.py
│   ├── account.py
│   └── common.py
├── services/
│   ├── ai/                          # AI provider integration
│   │   ├── config.py                # AIConfig + resolver
│   │   ├── providers/               # OpenAI, Anthropic, Google providers
│   │   ├── registry.py              # Cached provider factory
│   │   ├── models.py                # Model listing for the admin UI
│   │   └── reply.py                 # High-level generate_reply()
│   ├── catcher/                     # Edit/delete recovery utilities
│   │   ├── media_downloader.py
│   │   ├── formatters.py
│   │   ├── transcript.py
│   │   └── paths.py                 # Centralised media_cache paths
│   ├── business/                    # Business-handler helpers
│   │   ├── skip_policy.py
│   │   └── media_cache.py
│   └── notifier.py                  # Admin chat send helpers
├── telegram_account/                # Telethon client package
│   ├── client.py
│   ├── session.py
│   ├── view_once.py
│   └── media.py
├── middlewares/
│   └── db_middleware.py
├── requirements.txt
└── .env.example
```

## Quick Start

```bash
git clone https://github.com/ByteFlipper-58/iBragimus-Bot.git
cd iBragimus-Bot

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

The private admin panel includes:

- Auto-reply on/off toggle and Telegram account status.
- Telegram account login (QR, phone code, 2FA) and session reset.
- System prompt editing.
- AI provider, model (paginated provider-fetched list or manual input), and API key.
- Auto-reply behaviour: reply delay, ignored words, conversation context (toggle + depth).
- Blacklist management.
- Bot usage statistics.
- Telegram Business connection instructions.

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
- `media_cache/` — cached media files (per-chat, view-once, transcripts);
- `.env` — local secrets.

Treat all of the above as sensitive. API keys entered through the admin panel are stored in the local SQLite settings table, and the bot attempts to delete admin messages containing keys after saving them. Keep the host machine trusted and rotate provider keys if logs, database files, or screenshots are ever exposed.

## License

No license has been selected yet.

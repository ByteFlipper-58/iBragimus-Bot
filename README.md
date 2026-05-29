<div align="center">

# 🤖 iBragimusBot

**Telegram Business AI assistant** — auto-replies, edit/delete recovery,<br>
view-once media saving, and a private admin panel.

<p>
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/python-3.12+-3776AB.svg?logo=python&logoColor=white"></a>
  <a href="https://docs.aiogram.dev/"><img alt="aiogram" src="https://img.shields.io/badge/aiogram-3.x-2CA5E0.svg?logo=telegram&logoColor=white"></a>
  <a href="https://docs.telethon.dev/"><img alt="Telethon" src="https://img.shields.io/badge/telethon-1.x-26A5E4.svg?logo=telegram&logoColor=white"></a>
  <a href="https://www.sqlite.org/"><img alt="SQLite" src="https://img.shields.io/badge/SQLite-local-003B57.svg?logo=sqlite&logoColor=white"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-green.svg"></a>
</p>

<p>
  <a href="https://github.com/ByteFlipper-58/iBragimus-Bot/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/ByteFlipper-58/iBragimus-Bot?style=flat&logo=github&color=yellow"></a>
  <a href="https://github.com/ByteFlipper-58/iBragimus-Bot/network/members"><img alt="Forks" src="https://img.shields.io/github/forks/ByteFlipper-58/iBragimus-Bot?style=flat&logo=github"></a>
  <a href="https://github.com/ByteFlipper-58/iBragimus-Bot/issues"><img alt="Issues" src="https://img.shields.io/github/issues/ByteFlipper-58/iBragimus-Bot?style=flat&logo=github"></a>
  <a href="https://github.com/ByteFlipper-58/iBragimus-Bot/commits/main"><img alt="Last commit" src="https://img.shields.io/github/last-commit/ByteFlipper-58/iBragimus-Bot?style=flat&logo=github"></a>
  <img alt="Repo size" src="https://img.shields.io/github/repo-size/ByteFlipper-58/iBragimus-Bot?style=flat&logo=github">
  <img alt="Code size" src="https://img.shields.io/github/languages/code-size/ByteFlipper-58/iBragimus-Bot?style=flat&logo=github">
  <img alt="Top language" src="https://img.shields.io/github/languages/top/ByteFlipper-58/iBragimus-Bot?style=flat&logo=python&logoColor=white">
</p>

</div>

---

## ✨ Features

- 💬 &nbsp;AI auto-replies in Telegram Business chats
- 🧠 &nbsp;OpenAI · Anthropic · Google Gemini, switchable at runtime
- 📝 &nbsp;Editable system prompt, reply delay, ignored words, context depth
- 🚫 &nbsp;Blacklist with per-user reasons
- 🕘 &nbsp;Message archive — edit timeline and bulk-deletion transcripts
- 📸 &nbsp;View-once photo and video saving via Telethon
- 🔐 &nbsp;QR · phone · 2FA login for the connected account
- 💾 &nbsp;Single-file SQLite, no external services

---

## 📋 Requirements

- Python **3.12+**
- Bot token from [@BotFather](https://t.me/BotFather)
- API credentials from [my.telegram.org/apps](https://my.telegram.org/apps)
- An API key from one of: **OpenAI**, **Anthropic**, **Google AI**

---

## 🚀 Quick Start

```bash
git clone https://github.com/ByteFlipper-58/iBragimus-Bot.git
cd iBragimus-Bot

python -m venv .venv
source .venv/bin/activate            # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

cp .env.example .env                 # fill in BOT_TOKEN, ADMIN_ID, TELEGRAM_API_*
python main.py
```

Open a private chat with your bot and send `/start`.

---

## ⚙️ Configuration

<table>
  <thead>
    <tr><th>Variable</th><th align="center">Required</th><th>Description</th></tr>
  </thead>
  <tbody>
    <tr><td><code>BOT_TOKEN</code></td><td align="center">✅</td><td>Bot token from @BotFather</td></tr>
    <tr><td><code>ADMIN_ID</code></td><td align="center">✅</td><td>Numeric Telegram ID of the bot owner</td></tr>
    <tr><td><code>TELEGRAM_API_ID</code></td><td align="center">✅</td><td>API ID for the connected account</td></tr>
    <tr><td><code>TELEGRAM_API_HASH</code></td><td align="center">✅</td><td>API hash for the connected account</td></tr>
    <tr><td><code>AI_PROVIDER</code></td><td align="center">—</td><td><code>openai</code>, <code>anthropic</code>, or <code>google</code> (default <code>google</code>)</td></tr>
    <tr><td><code>OPENAI_API_KEY</code> · <code>OPENAI_MODEL</code></td><td align="center">—</td><td>OpenAI defaults</td></tr>
    <tr><td><code>ANTHROPIC_API_KEY</code> · <code>ANTHROPIC_MODEL</code></td><td align="center">—</td><td>Anthropic defaults</td></tr>
    <tr><td><code>GEMINI_API_KEY</code> · <code>GEMINI_MODEL</code></td><td align="center">—</td><td>Google Gemini defaults</td></tr>
    <tr><td><code>LOG_LEVEL</code></td><td align="center">—</td><td><code>DEBUG</code> / <code>INFO</code> / ... (default <code>INFO</code>)</td></tr>
    <tr><td><code>DB_BACKEND</code></td><td align="center">—</td><td><code>sqlite</code> (default) or <code>postgres</code></td></tr>
    <tr><td><code>DB_PATH</code></td><td align="center">—</td><td>SQLite path (default <code>data.db</code>, used when <code>DB_BACKEND=sqlite</code>)</td></tr>
    <tr><td><code>DATABASE_URL</code></td><td align="center">—</td><td>PostgreSQL DSN, required when <code>DB_BACKEND=postgres</code></td></tr>
  </tbody>
</table>

> Values set from the admin panel override the `.env` defaults.

### External PostgreSQL (optional)

Default storage is single-file SQLite. To use PostgreSQL instead:

```bash
pip install asyncpg
```

In `.env`:

```dotenv
DB_BACKEND=postgres
DATABASE_URL=postgresql://user:password@localhost:5432/ibragimusbot
```

The schema is created automatically on first launch. Existing SQLite data is **not** migrated.

---

## 🔌 Telegram Business

1. In [@BotFather](https://t.me/BotFather): **Bot Settings → Business Mode → Turn on**
2. In Telegram: **Settings → Telegram Business → Chatbots**, add the bot and allow replies
3. In the bot's admin panel: log in to the connected account via QR or phone

---

## 📁 Project Layout

<details>
<summary><b>Click to expand</b></summary>

```
config.py                 settings from .env
database/                 SQLite + per-aggregate repositories
handlers/admin/           private admin panel (FSM)
handlers/business/        Telegram Business event handlers
keyboards/                inline keyboards split by screen
services/ai/              AI providers, config, model listing
services/catcher/         media downloader, formatters, transcripts
services/business/        skip-policy and message media cache
services/notifier.py      admin chat send helpers
telegram_account/         Telethon client + view-once interceptor
middlewares/              aiogram middleware
main.py                   entry point
```

</details>

---

## 🔐 Security

`*.session`, `*.db`, `media_cache/`, and `.env` are **git-ignored**. API keys entered through the admin panel are stored in the local SQLite `settings` table, and admin messages with keys, codes, or 2FA passwords are deleted from the chat right after they are processed.

> Treat the host machine as trusted and rotate provider keys if logs or database files leak.

---

## 📄 License

Released under the [MIT License](LICENSE).

Copyright © 2026 **Ibragim Maltsagov** — developed by **[ByteFlipper](https://github.com/ByteFlipper-58)**.

<div align="center">
<sub>Built with ❤️ on top of <a href="https://docs.aiogram.dev/">aiogram</a> and <a href="https://docs.telethon.dev/">Telethon</a></sub>
</div>

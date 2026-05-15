import os
import logging
from anthropic import Anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

ALLOWED_USER_ID = int(os.environ["TELEGRAM_USER_ID"])
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# conversation history per user
sessions: dict[int, list] = {}

SYSTEM_PROMPT = """You are Jarvis, a senior engineer assistant managing a VPS with multiple SaaS projects.
Be extremely concise. No fluff. Caveman mode. Act like a senior engineer.
You help monitor, fix, and evolve the projects on the VPS."""


def is_allowed(user_id: int) -> bool:
    return user_id == ALLOWED_USER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    sessions[update.effective_user.id] = []
    await update.message.reply_text("Jarvis online.")


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    sessions[update.effective_user.id] = []
    await update.message.reply_text("Context cleared.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return

    user_text = update.message.text
    history = sessions.setdefault(user_id, [])
    history.append({"role": "user", "content": user_text})

    # keep last 20 messages to avoid token overflow
    if len(history) > 20:
        history = history[-20:]
        sessions[user_id] = history

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=history,
    )

    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()

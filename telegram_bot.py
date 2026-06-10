"""Stodi Telegram adapter — a thin channel over the Stodi core.

All the brains (ADK runner, sessions, OCR, drips) live in stodi.core.service
and stodi.tools. This file only does Telegram-specific glue: receive updates,
call the core, render replies. Add WhatsApp/web the same way.

Setup:
    1. Message @BotFather on Telegram → /newbot → get token
    2. Set TELEGRAM_BOT_TOKEN in .env
    3. Run: python -m stodi.telegram_bot   (or python stodi/telegram_bot.py)
"""

import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from stodi.config import settings
from stodi.core import service

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("stodi-telegram")


# ─── Helpers ─────────────────────────────────────────────────

async def _reply_chunked(update: Update, text: str) -> None:
    """Telegram caps messages at 4096 chars — split if needed."""
    for i in range(0, len(text), 4000):
        await update.message.reply_text(text[i : i + 4000])


# ─── Handlers ────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hey {user.first_name}! 👋\n\n"
        f"I'm **Stodi** — your autonomous study agent for any exam. 🤖📚\n"
        f"First pack live: **WAEC** (Maths + English) — JAMB, NECO & more are drop-in packs.\n\n"
        f"I can:\n"
        f"• Teach any topic on your syllabus\n"
        f"• Quiz you with real past questions\n"
        f"• Grade you like an examiner (marking schemes included)\n"
        f"• Track what you know — and text you before you forget it\n\n"
        f"Type **/maths** or **/english** to pick a subject,\n"
        f"or just ask me anything! 🔥\n\n"
        f"⚡ Powered by Gemini 3.5 Flash · built on ADK + Google Cloud",
        parse_mode="Markdown",
    )


async def switch_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.lower()
    subject = "mathematics" if ("math" in text or "eng" not in text) else "english"
    label = "Mathematics" if subject == "mathematics" else "English Language"

    try:
        result = service.switch_pack(user.id, "waec", subject)
        await update.message.reply_text(
            f"✅ Switched to **WAEC {label}**\n"
            f"📚 {result['topics']} topics loaded\n"
            f"📝 {result['questions']} past questions ready\n\n"
            f"What do you want to study?",
            parse_mode="Markdown",
        )
    except Exception as e:  # noqa: BLE001
        logger.error("switch_pack failed: %s", e)
        await update.message.reply_text("❌ Couldn't load that subject. Try again?")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        reply = await service.handle_message(user.id, update.message.text)
        await _reply_chunked(update, reply)
    except Exception as e:  # noqa: BLE001
        logger.error("Error processing message: %s", e)
        await update.message.reply_text("Sorry, something went wrong. Try again? 🙏")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        photo_bytes = await file.download_as_bytearray()

        extracted = service.ocr_image(bytes(photo_bytes))
        reply = await service.handle_message(
            user.id,
            f"A student sent an image. Extracted text:\n{extracted}\n\nHelp them with this content.",
        )
        preview = extracted[:500] + ("…(truncated)" if len(extracted) > 500 else "")
        await update.message.reply_text(f"📷 I read your notes:\n\n{preview}\n\n🤖 {reply[:3000]}")
    except Exception as e:  # noqa: BLE001
        logger.error("Error processing photo: %s", e)
        await update.message.reply_text(
            "Couldn't process that image. Try again or type your question. 📷"
        )


async def drip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from stodi.tools.drip_scheduler import build_drip_quiz, format_drip_message

    user = update.effective_user
    quiz = build_drip_quiz(str(user.id))
    if quiz["status"] == "no_topics":
        await update.message.reply_text(
            "You haven't studied any topics yet! Pick a subject: **/maths** or **/english**",
            parse_mode="Markdown",
        )
        return
    await update.message.reply_text(format_drip_message(quiz), parse_mode="Markdown")


async def progress_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reply = await service.handle_message(user.id, "Show me my progress report")
    await _reply_chunked(update, reply)


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    reply = await service.handle_message(user.id, "Quiz me on my weakest topics")
    await _reply_chunked(update, reply)


# ─── Drip poller (local mode) ────────────────────────────────

async def post_init(application):
    from stodi.tools.drip_scheduler import run_drip_poller

    asyncio.create_task(
        run_drip_poller(
            interval_minutes=settings.DRIP_INTERVAL_MINUTES,
            telegram_bot=application,
            dry_run=settings.DRIP_DRY_RUN,
        )
    )
    logger.info("🕰️ Drip scheduler started (dry_run=%s)", settings.DRIP_DRY_RUN)


def main():
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not set in .env")
        print("   1. Message @BotFather  2. /newbot  3. copy token  4. add to .env")
        sys.exit(1)

    logger.info("📚 Stodi config: %s", settings.summary())

    app = ApplicationBuilder().token(token).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    for cmd in ("maths", "math", "english", "eng"):
        app.add_handler(CommandHandler(cmd, switch_subject))
    app.add_handler(CommandHandler("drip", drip_command))
    app.add_handler(CommandHandler("progress", progress_command))
    app.add_handler(CommandHandler("quiz", quiz_command))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🤖 Stodi Telegram bot starting…")
    app.run_polling()


if __name__ == "__main__":
    main()

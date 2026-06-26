"""
ربات تلگرام هوشمند با Claude AI
=====================================
نیازمندی‌ها:
    pip install python-telegram-bot anthropic

متغیرهای محیطی مورد نیاز:
    TELEGRAM_BOT_TOKEN  - توکن ربات از @BotFather
    ANTHROPIC_API_KEY   - کلید API از console.anthropic.com
"""

import os
import logging
from anthropic import Anthropic
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─── تنظیمات ───────────────────────────────────────────────────────────────────

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]

SYSTEM_PROMPT = """تو یک دستیار هوشمند فارسی‌زبان هستی.
به سوالات کاربران با دقت، مهربانی و به زبان فارسی پاسخ بده.
پاسخ‌هایت را کوتاه و مفید نگه دار مگر اینکه توضیح بیشتری خواسته شود."""

MAX_HISTORY = 20  # حداکثر تعداد پیام‌هایی که در حافظه نگه داشته می‌شود

# ─── راه‌اندازی ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

# حافظه مکالمه به ازای هر کاربر (chat_id → list of messages)
conversation_history: dict[int, list[dict]] = {}


# ─── توابع کمکی ─────────────────────────────────────────────────────────────────

def get_history(chat_id: int) -> list[dict]:
    return conversation_history.setdefault(chat_id, [])


def trim_history(chat_id: int) -> None:
    history = conversation_history.get(chat_id, [])
    if len(history) > MAX_HISTORY:
        # حذف قدیمی‌ترین پیام‌ها (جفت user/assistant)
        conversation_history[chat_id] = history[-MAX_HISTORY:]


def ask_claude(chat_id: int, user_text: str) -> str:
    history = get_history(chat_id)
    history.append({"role": "user", "content": user_text})

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=history,
    )

    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})
    trim_history(chat_id)
    return reply


# ─── هندلرهای تلگرام ────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /start"""
    name = update.effective_user.first_name or "دوست عزیز"
    await update.message.reply_text(
        f"سلام {name}! 👋\n\n"
        "من یک دستیار هوشمند هستم. هر سوالی داری بپرس!\n\n"
        "دستورات:\n"
        "🔄 /reset — شروع مکالمه جدید\n"
        "ℹ️ /help  — راهنما"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /help"""
    await update.message.reply_text(
        "📖 راهنمای استفاده:\n\n"
        "• هر پیامی بفرستی، با هوش مصنوعی پاسخ می‌گیری.\n"
        "• مکالمه را به خاطر می‌سپارم تا بتوانی ادامه بدی.\n"
        "• با /reset می‌تونی مکالمه رو از صفر شروع کنی."
    )


async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دستور /reset — پاک کردن تاریخچه مکالمه"""
    chat_id = update.effective_chat.id
    conversation_history.pop(chat_id, None)
    await update.message.reply_text("✅ مکالمه ریست شد. می‌تونی از اول شروع کنی!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت پیام متنی و پاسخ با Claude"""
    chat_id   = update.effective_chat.id
    user_text = update.message.text

    # نشانه تایپ کردن
    await update.message.chat.send_action("typing")

    try:
        reply = ask_claude(chat_id, user_text)
        await update.message.reply_text(reply)
    except Exception as e:
        logger.error("خطا در ارتباط با Claude: %s", e)
        await update.message.reply_text(
            "⚠️ متأسفم، مشکلی پیش آمد. لطفاً دوباره تلاش کن."
        )


# ─── اجرای اصلی ─────────────────────────────────────────────────────────────────

def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CommandHandler("reset", cmd_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()

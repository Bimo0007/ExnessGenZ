"""
Telegram Bot - Clean Reply Keyboard with File ID Caching (Khmer Version)
=========================================================================
Flow:
  1. 5 main buttons shown at bottom (in Khmer)
  2. User taps one → the tutorial video for that topic is sent immediately
  3. Main buttons come back after the video
"""

import logging
import threading
import json
import os
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN")
FILE_IDS_PATH = "video_file_ids.json"

# ─── VIDEO FILE IDs ──────────────────────────────────────────────────────────
# How to get these:
#   1. Run the bot and open a chat with it on Telegram.
#   2. Send the actual video file to the bot (as a video, not a document).
#   3. The bot will reply with the file_id — copy it and paste it below.
# Once a topic's file_id is filled in here, no local video file is needed at all.
VIDEO_FILE_IDS = {
    "exness":     "BAACAgUAAxkBAAMPamiGhf_H85tRcxhbsSpdLSZhGeoAArAhAAJYmElXeEpHMnlyb089BA",  # paste exness file_id here
    "mt5":        "BAACAgUAAxkBAAMRamiGsbISklz6-E2WJXRDLUwSN9gAArEhAAJYmElXmZzU8jUVbBE9BA",  # paste mt5 file_id here
    "deposit":    "BAACAgUAAxkBAAMTamiGxTbmWM2WEOCij8obdppKtyQAArIhAAJYmElXOtBs-28LNJw9BA",  # paste deposit file_id here
    "withdraw":   "BAACAgUAAxkBAAMVamiG2MECQOGefjDWIgNn_6nAykIAArMhAAJYmElXQBww5NRjqkg9BA",  # paste withdraw file_id here
    "changelink": "BAACAgUAAxkBAAMXamiG52fUsYbZGqczKYK0ETvb3JMAArQhAAJYmElX3xGQA6GFoHg9BA",  # paste changelink file_id here
}

# Button text in Khmer
BTN_EXNESS     = "👉 របៀបបង្កើតគណនី Exness"
BTN_MT5        = "👉 របៀបបង្កើតគណនី MT5"
BTN_DEPOSIT    = "👉 វិធីដាក់ប្រាក់ក្នុងនៅក្នុង Exness"
BTN_WITHDRAW   = "👉 វិធីដកប្រាក់នៅក្នុង Exness"
BTN_CHANGELINK = "👉 របៀបប្តូរ Referral Link ក្នុង Exness"

BUTTON_TO_TOPIC = {
    BTN_EXNESS:     "exness",
    BTN_MT5:        "mt5",
    BTN_DEPOSIT:    "deposit",
    BTN_WITHDRAW:   "withdraw",
    BTN_CHANGELINK: "changelink",
}

# Video captions (Khmer)
VIDEO_CAPTIONS = {
    "exness":     "របៀបបង្កើតអាខោន Exness\nបញ្ចាក់ត្រូវដាក់ Partner code : genzfx\nRegister link : https://one.exnessonelink.com/a/genzfx/?campaign=42576\n\n➡️Partners Code : genzfx",
    "mt5":        "វិធីបង្កើតគណនី MT5",
    "deposit":    "វិធីដាក់ប្រាក់ក្នុងនៅក្នុង Exness",
    "withdraw":   "វិធីដកប្រាក់នៅក្នុង Exness",
    "changelink": "របៀបប្តូរ Referral Link ក្នុង Exness\nបញ្ចាក់ត្រូវដាក់ Partner code : genzfx\nRegister link : https://one.exnessonelink.com/a/genzfx/?campaign=42576\n\n➡️Partners Code : genzfx",
}

# ─── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── FILE ID MANAGEMENT ──────────────────────────────────────────────────────

def load_file_ids():
    """Load stored file IDs, starting from the hardcoded VIDEO_FILE_IDS
    and overlaying anything already saved in the JSON cache."""
    ids = {k: v for k, v in VIDEO_FILE_IDS.items() if v}

    if os.path.exists(FILE_IDS_PATH):
        try:
            with open(FILE_IDS_PATH, "r") as f:
                cached = json.load(f)
                ids.update({k: v for k, v in cached.items() if v})
        except json.JSONDecodeError:
            pass

    return ids

def save_file_ids(file_ids):
    """Save file IDs to JSON file."""
    with open(FILE_IDS_PATH, "w") as f:
        json.dump(file_ids, f, indent=4)

FILE_IDS = load_file_ids()

# ─── KEEP-ALIVE ──────────────────────────────────────────────────────────────

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running!", 200

def keep_alive():
    """Run Flask server to keep bot alive."""
    t = threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=8080))
    t.daemon = True
    t.start()

# ─── KEYBOARDS ───────────────────────────────────────────────────────────────

def main_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard with 5 tutorial buttons."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_EXNESS)],
            [KeyboardButton(BTN_MT5)],
            [KeyboardButton(BTN_DEPOSIT)],
            [KeyboardButton(BTN_WITHDRAW)],
            [KeyboardButton(BTN_CHANGELINK)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

# ─── HELPERS ─────────────────────────────────────────────────────────────────

async def send_topic_video(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    topic: str,
    caption: str,
) -> None:
    """Look up and send the video for a topic, then show the main keyboard."""
    video_key = topic

    try:
        if video_key in FILE_IDS and FILE_IDS[video_key]:
            logger.info(f"Sending {video_key} using cached file_id")
            await update.message.reply_video(
                video=FILE_IDS[video_key],
                caption=caption,
            )
        else:
            await update.message.reply_text(
                f"❌ មិនទាន់មានវីដេអូសម្រាប់៖ {video_key}\n\n"
                f"សូមផ្ញើវីដេអូនោះទៅ bot នេះម្តង bot នឹងឆ្លើយតប file_id មកវិញ "
                f"រួចយក file_id នោះទៅដាក់ក្នុងកូដ (VIDEO_FILE_IDS)។",
            )
            return

    except Exception as e:
        logger.error(f"Failed to send video {video_key}: {str(e)}")
        await update.message.reply_text(
            f"❌ មានបញ្ហាក្នុងការផ្ញើវីដេអូ៖ {str(e)}\n\n"
            f"សូមសាកល្បងម្តងទៀត ឬទាក់ទងអ្នកគ្រប់គ្រង។"
        )
        return

    # Send main menu back
    await update.message.reply_text(
        "👇 សូមជ្រើសរើសVideoខាងក្រោម៖",
        reply_markup=main_keyboard(),
    )

# ─── HANDLERS ────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    context.user_data.clear()
    await update.message.reply_text(
        "👋 សូមស្វាគមន៍មកកាន់GenZ Exess Support BOT!\n\n👇 សូមជ្រើសរើសVideoខាងក្រោម៖",
        reply_markup=main_keyboard(),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    help_text = (
        "🤖 ពាក្យបញ្ជារបស់ Bot៖\n\n"
        "/start - បង្ហាញម៉ឺនុយចម្បង\n"
        "/help - បង្ហាញជំនួយនេះ\n"
        "/status - ពិនិត្យស្ថានភាពវីដេអូ\n\n"
        "គ្រាន់តែចុចប៊ូតុងខាងក្រោមដើម្បីមើលមេរៀន! 👇"
    )
    await update.message.reply_text(help_text, reply_markup=main_keyboard())

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show status of all videos."""
    status_text = "📊 ស្ថានភាពវីដេអូ៖\n\n"

    for key in VIDEO_FILE_IDS.keys():
        has_file_id = bool(FILE_IDS.get(key))
        icon = "✅" if has_file_id else "⏳"
        status_text += f"{icon} {key}: {'មានវីដេអូរួចហើយ' if has_file_id else 'មិនទាន់មានវីដេអូ (ត្រូវផ្ញើវីដេអូ ដើម្បីយក file_id)'}\n"

    await update.message.reply_text(status_text, reply_markup=main_keyboard())

async def get_file_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Extract file_id from a message (for debugging)."""
    msg = update.message
    lines = ["📋 Media IDs ដែលរកឃើញ៖\n"]

    if msg.video:
        lines.append(f"🎞 VIDEO file_id:\n{msg.video.file_id}")
    if msg.document:
        lines.append(f"📄 DOCUMENT file_id:\n{msg.document.file_id}")
    if msg.animation:
        lines.append(f"🎬 ANIMATION file_id:\n{msg.animation.file_id}")

    if len(lines) <= 1:
        lines.append("មិនមានមេឌាណាមួយនៅក្នុងសារនេះទេ!")

    # No parse_mode here — file_ids often contain characters (_, *, etc.)
    # that break Telegram's Markdown parser.
    await msg.reply_text("\n".join(lines))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all text messages."""
    text = update.message.text

    # ── User clicked a main topic button ──
    if text in BUTTON_TO_TOPIC:
        topic = BUTTON_TO_TOPIC[text]
        caption = VIDEO_CAPTIONS.get(topic, text)
        await send_topic_video(update, context, topic, caption)
        return

    # ── User sent something else ──
    await update.message.reply_text(
        "❌ សូមចុចប៊ូតុងណាមួយខាងក្រោម 👇",
        reply_markup=main_keyboard(),
    )

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    """Start the bot."""

    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not found in .env file!")
        return

    keep_alive()

    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, get_file_id))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("✅ Bot is running... (Press Ctrl+C to stop)")
    logger.info(f"📊 Loaded {len(FILE_IDS)} cached file IDs")

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
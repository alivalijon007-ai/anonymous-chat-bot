import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 6604953148

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") + WEBHOOK_PATH
PORT = int(os.environ.get("PORT", 10000))

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================= STORAGE =================

ADMIN_STATE = {}
USERS = set()
USER_LANG = {}
USER_GENDER = {}
SEARCHING = []
PAIRS = {}

# ================= TEXTS =================

TEXTS = {
    "tj": {
        "choose_lang": "Забонро интихоб кунед:",
        "choose_gender": "Ҷинсро интихоб кунед:",
        "male": "👨 Мард",
        "female": "👩 Зан",
        "start": (
            "👋 Хуш омадед!\n\n"
            "🔒 Шумо комилан ноаён ҳастед:\n"
            "— Ном нишон дода намешавад\n"
            "— Телефон нишон дода намешавад\n\n"
            "/search нависед барои ҷустуҷӯ"
        ),
        "search": "🔍 Дар ҷустуҷӯи шарик...\n/stop — қатъ",
        "found": "✅ Шарик ёфт шуд! Метавонед суҳбат кунед.\n/stop — қатъ",
        "stop": "❌ Чат қатъ шуд.\n/search — дубора",
        "searchemo": "🔍",
    },
    "fa": {
        "choose_lang": "زبان را انتخاب کنید:",
        "choose_gender": "جنسیت را انتخاب کنید:",
        "male": "👨 مرد",
        "female": "👩 زن",
        "start": (
            "👋 خوش آمدید!\n\n"
            "🔒 شما کاملاً ناشناس هستید:\n"
            "— نام نمایش داده نمی‌شود\n"
            "— شماره تلفن نمایش داده نمی‌شود\n\n"
            "/search برای جستجو"
        ),
        "search": "🔍 در حال جستجو...\n/stop — توقف",
        "found": "✅ شریک پیدا شد!\n/stop — توقف",
        "stop": "❌ چت متوقف شد.\n/search — دوباره",
        "searchemo": "🔍",
    }
}

def t(user_id, key):
    return TEXTS.get(USER_LANG.get(user_id, "tj"), TEXTS["tj"])[key]

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS.add(user_id)

    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="lang:tj"),
            InlineKeyboardButton("🇮🇷 فارسی", callback_data="lang:fa"),
        ]
    ])

    await update.message.reply_text(
        "Choose language / Забонро интихоб кунед",
        reply_markup=kb
    )

# ================= CALLBACK =================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    if q.data.startswith("lang:"):
        lang = q.data.split(":")[1]
        USER_LANG[user_id] = lang

        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(TEXTS[lang]["male"], callback_data="gender:male"),
                InlineKeyboardButton(TEXTS[lang]["female"], callback_data="gender:female"),
            ]
        ])

        await q.edit_message_text(TEXTS[lang]["choose_gender"], reply_markup=kb)

    elif q.data.startswith("gender:"):
        USER_GENDER[user_id] = q.data.split(":")[1]
        await q.edit_message_text(t(user_id, "start"))

# ================= SEARCH =================

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS.add(user_id)

    if user_id in PAIRS or user_id in SEARCHING:
        return

    # матн
    await update.message.reply_text(t(user_id, "search"))
    # emoji дар паёми алоҳида
    await update.message.reply_text(t(user_id, "searchemo"))

    if SEARCHING:
        other = SEARCHING.pop(0)

        PAIRS[user_id] = other
        PAIRS[other] = user_id

        await context.bot.send_message(user_id, t(user_id, "found"))
        await context.bot.send_message(other, t(other, "found"))
    else:
        SEARCHING.append(user_id)

# ================= STOP =================

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in SEARCHING:
        SEARCHING.remove(user_id)
        await update.message.reply_text(t(user_id, "stop"))
        return

    if user_id in PAIRS:
        partner = PAIRS.pop(user_id)
        PAIRS.pop(partner, None)

        await context.bot.send_message(user_id, t(user_id, "stop"))
        await context.bot.send_message(partner, t(partner, "stop"))

# ================= RELAY =================

async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in PAIRS:
        return

    partner = PAIRS.get(user_id)
    if not partner:
        return

    if update.message.text:
        await context.bot.send_message(partner, update.message.text)
    elif update.message.photo:
        await context.bot.send_photo(
            partner,
            update.message.photo[-1].file_id,
            caption=update.message.caption
        )

# ================= BROADCAST =================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    ADMIN_STATE[ADMIN_ID] = True
    await update.message.reply_text("✉️ Паёми broadcast-ро фиристед")

async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not ADMIN_STATE.get(ADMIN_ID):
        return

    for uid in USERS:
        try:
            if update.message.text:
                await context.bot.send_message(uid, update.message.text)
            elif update.message.photo:
                await context.bot.send_photo(
                    uid,
                    update.message.photo[-1].file_id,
                    caption=update.message.caption
                )
        except:
            pass

    ADMIN_STATE.clear()
    await update.message.reply_text("✅ Broadcast анҷом ёфт")

# ================= MAIN =================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(
        MessageHandler(filters.User(ADMIN_ID) & ~filters.COMMAND, broadcast_handler),
        group=0
    )

    app.add_handler(
        MessageHandler(filters.ALL & ~filters.COMMAND, relay),
        group=1
    )

    logger.info("Starting webhook...")

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()

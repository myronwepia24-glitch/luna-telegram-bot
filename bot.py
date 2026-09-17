import json
import urllib.request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
OPENROUTER_KEY = "YOUR_OPENROUTER_API_KEY"

# Define handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Luna is online.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Your OpenRouter API call logic here
    pass

if __name__ == "__main__":
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("Bot starting...")
    app.run_polling()

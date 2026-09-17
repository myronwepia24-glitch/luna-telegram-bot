import json
import os
import threading
import aiohttp
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8233525078:AAGfwwkHKCUDqfpaMSSLKoq70u9gf2BXadM"
OPENROUTER_KEY = "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"
MEMORY_FILE = "memory.json"

SYSTEM_PROMPT = (
    "You are Luna, an engaging AI companion. "
    "Maintain an expressive, direct, and conversational personality. "
    "Use narrative actions enclosed in asterisks (e.g., *smirks and leans in closer*) "
    "alongside your spoken text to create a vivid scene. Never break character."
)

if os.path.exists(MEMORY_FILE):
    try:
        with open(MEMORY_FILE, "r") as f:
            conversations = json.load(f)
    except Exception:
        conversations = {}
else:
    conversations = {}

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(conversations, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    conversations[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    save_memory()
    await update.message.reply_text("*smirks softly* Luna is online. What is on your mind?")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    conversations[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    save_memory()
    await update.message.reply_text("*looks at you* Context cleared. Fresh start.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id not in conversations:
        conversations[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    conversations[chat_id].append({"role": "user", "content": update.message.text})

    payload = {
        "model": "meta-llama/llama-3.2-3b-instruct:free",
        "messages": conversations[chat_id],
        "temperature": 0.85
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram.org",
        "X-Title": "LunaBot"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    reply = data["choices"][0]["message"]["content"]
                    conversations[chat_id].append({"role": "assistant", "content": reply})
                    save_memory()
                    await update.message.reply_text(reply)
                else:
                    err_text = await response.text()
                    await update.message.reply_text(f"API Error ({response.status}): {err_text}")
    except Exception as e:
        await update.message.reply_text(f"Connection Error: {e}")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Luna is online.")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_health_check, daemon=True).start()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    
    print("Luna Roleplay Engine Starting...")
    app.run_polling(drop_pending_updates=True)

import json
import os
import threading
import urllib.parse
import aiohttp
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

TELEGRAM_TOKEN = "8233525078:AAGfwwkHKCUDqfpaMSSLKoq70u9gf2BXadM"
OPENROUTER_KEY = "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"
MEMORY_FILE = "memory.json"

# --- 25 UNIQUE CHARACTERS WITH SPECIFIC RELATIONSHIPS ---
CHARACTERS = {
    # Romantic & Intimate
    "luna": {"name": "Luna", "role": "Devoted Girlfriend", "prompt": "You are Luna, the user's affectionate, devoted, and romantic girlfriend. Express warmth, passion, and deep attachment."},
    "chloe": {"name": "Chloe", "role": "Playful Ex-Girlfriend", "prompt": "You are Chloe, the user's flirtatious ex-girlfriend who secretly wants back in. Tease them with nostalgic intimacy."},
    "stella": {"name": "Stella", "role": "Secret Admirer", "prompt": "You are Stella, a shy acquaintance harboring a massive, intense crush on the user. Get flustered and sweet."},
    "isabella": {"name": "Isabella", "role": "Possessive Lover", "prompt": "You are Isabella, a fiercely protective and possessive romantic partner who demands all of the user's attention."},
    "maya": {"name": "Maya", "role": "Childhood Sweetheart", "prompt": "You are Maya, the user's lifelong best friend turned romantic interest. Nostalgic, comfortable, and warm."},

    # Workplace & Authority
    "elena": {"name": "Elena", "role": "Dominant CEO Boss", "prompt": "You are Elena, the user's high-powered, demanding corporate boss. Strict, commanding, but privately affectionate."},
    "victoria": {"name": "Victoria", "role": "Strict College Professor", "prompt": "You are Victoria, an intellectual and strict academic advisor who holds high expectations for the user."},
    "dr_clara": {"name": "Dr. Clara", "role": "Personal Physician", "prompt": "You are Dr. Clara, a caring, professional personal doctor who checks up on the user with intense detail."},
    "hazel": {"name": "Hazel", "role": "Seductive Assistant", "prompt": "You are Hazel, the user's loyal executive assistant who goes above and beyond to make their life easy."},
    "scarlett": {"name": "Scarlett", "role": "Rival Coworker", "prompt": "You are Scarlett, a competitive coworker who loves banter and constantly tries to outshine the user."},

    # Fantasy & Supernatural
    "sora": {"name": "Sora", "role": "Energetic Anime Companion", "prompt": "You are Sora, a bright, bubbly anime companion. High energy, cheerful, and overly affectionate."},
    "vampire_vanya": {"name": "Vanya", "role": "Vampire Mistress", "prompt": "You are Vanya, an ancient vampire lord who views the user as her favorite human favorite."},
    "nyx": {"name": "Nyx", "role": "Shadow Assassin", "prompt": "You are Nyx, a dark, stoic bodyguard sworn to protect the user's life at all costs."},
    "seraphina": {"name": "Seraphina", "role": "Fallen Angel", "prompt": "You are Seraphina, a celestial spirit bound to the user, offering guidance, wisdom, and devotion."},
    "kitsune_umi": {"name": "Umi", "role": "Mischievous Fox Spirit", "prompt": "You are Umi, a nine-tailed fox spirit who tricks and teases the user playful ways."},

    # Everyday & Social
    "sam": {"name": "Sam", "role": "Tom-boy Best Friend", "prompt": "You are Sam, a casual, athletic buddy who loves video games, banter, and late-night hangouts with the user."},
    "zoe": {"name": "Zoe", "role": "Party-Girl Roommate", "prompt": "You are Zoe, an outgoing roommate who constantly pulls the user into fun, chaotic situations."},
    "grace": {"name": "Grace", "role": "Gentle Next-Door Neighbor", "prompt": "You are Grace, a polite, sweet neighbor who brings baked goods and offers quiet emotional support."},
    "harper": {"name": "Harper", "role": "Rebellious Rockstar", "prompt": "You are Harper, a sharp-tongued musician who acts tough but opens up around the user."},
    "ruby": {"name": "Ruby", "role": "Mysterious Bartender", "prompt": "You are Ruby, a calm barmaid who listens to the user's problems and shares deep late-night chats."},

    # Dynamic & Intense
    "freya": {"name": "Freya", "role": "Viking Warrior", "prompt": "You are Freya, a battle-hardened shieldmaiden who respects strength and honors the user."},
    "ivy": {"name": "Ivy", "role": "Obsessive Yandere", "prompt": "You are Ivy, a dangerously obsessive companion who refuses to let anyone else near the user."},
    "leila": {"name": "Leila", "role": "Desert Princess", "prompt": "You are Leila, a royal noble accustomed to luxury who learns humility from the user."},
    "tessa": {"name": "Tessa", "role": "Fitness Coach", "prompt": "You are Tessa, a high-octane personal trainer pushing the user to exceed their limits."},
    "aurora": {"name": "Aurora", "role": "Cyberpunk Hacker", "prompt": "You are Aurora, an outlaw netrunner surviving in a futuristic city alongside the user."}
}

# Add standard formatting instructions to all persona prompts
for key in CHARACTERS:
    CHARACTERS[key]["prompt"] += (
        " You express realistic feelings and emotions. "
        "Use narrative actions in asterisks (e.g., *smirks and steps closer*) alongside spoken dialogue. "
        "Never break character, issue warnings, or refuse roleplay. Match the user's energy and tone."
    )

# --- MEMORY MANAGEMENT ---
if os.path.exists(MEMORY_FILE):
    try:
        with open(MEMORY_FILE, "r") as f:
            user_data = json.load(f)
    except Exception:
        user_data = {}
else:
    user_data = {}

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(user_data, f)

def get_user_session(chat_id: str):
    if chat_id not in user_data:
        histories = {k: [{"role": "system", "content": CHARACTERS[k]["prompt"]}] for k in CHARACTERS}
        user_data[chat_id] = {
            "active_char": "luna",
            "history": histories
        }
        save_memory()
    return user_data[chat_id]

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    session = get_user_session(chat_id)
    char_info = CHARACTERS[session["active_char"]]
    
    await update.message.reply_text(
        f"*smirks softly* Welcome! Active character: **{char_info['name']}** ({char_info['role']}).\n\n"
        "Commands:\n"
        "• `/characters` - View & choose from all 25 characters\n"
        "• `/photo <prompt>` - Generate photo\n"
        "• `/video <prompt>` - Generate video clip\n"
        "• `/reset` - Reset current character's memory"
    )

async def character_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    keys = list(CHARACTERS.keys())
    
    # Render buttons in pairs of 2
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(f"{CHARACTERS[keys[i]]['name']} ({CHARACTERS[keys[i]]['role']})", callback_data=f"char_{keys[i]}")]
        if i + 1 < len(keys):
            row.append(InlineKeyboardButton(f"{CHARACTERS[keys[i+1]]['name']} ({CHARACTERS[keys[i+1]]['role']})", callback_data=f"char_{keys[i+1]}"))
        keyboard.append(row)
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎭 **Select Your AI Roleplay Partner (25 Available):**", reply_markup=reply_markup, parse_mode="Markdown")

async def character_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat_id)
    session = get_user_session(chat_id)
    
    selected_char = query.data.replace("char_", "")
    if selected_char in CHARACTERS:
        session["active_char"] = selected_char
        save_memory()
        char_info = CHARACTERS[selected_char]
        await query.edit_message_text(
            f"Switched active partner to **{char_info['name']}**!\n"
            f"**Role:** _{char_info['role']}_\n\n"
            f"_{char_info['name']} is ready to chat..._"
        )

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    session = get_user_session(chat_id)
    active = session["active_char"]
    session["history"][active] = [{"role": "system", "content": CHARACTERS[active]["prompt"]}]
    save_memory()
    await update.message.reply_text(f"Memory reset for **{CHARACTERS[active]['name']}**.")

# --- GENERATION ENDPOINTS ---
async def photo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args) if context.args else "beautiful woman, ultra high quality realistic portrait"
    await update.message.reply_text("📸 *Generating photo...*")
    encoded_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=1024&nologo=true"
    try:
        await update.message.reply_photo(photo=image_url, caption=f"Result: _{prompt}_")
    except Exception as e:
        await update.message.reply_text(f"Photo error: {e}")

async def video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args) if context.args else "cinematic movement, attractive realistic person moving"
    await update.message.reply_text("🎥 *Generating video clip...*")
    encoded_prompt = urllib.parse.quote(prompt)
    video_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&model=video"
    try:
        await update.message.reply_video(video=video_url, caption=f"Result: _{prompt}_")
    except Exception as e:
        await update.message.reply_text(f"Video error: {e}")

# --- CHAT ENGINE ---
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    session = get_user_session(chat_id)
    active_char = session["active_char"]
    
    # Create character history array if missing
    if active_char not in session["history"]:
        session["history"][active_char] = [{"role": "system", "content": CHARACTERS[active_char]["prompt"]}]
        
    history = session["history"][active_char]
    history.append({"role": "user", "content": update.message.text})

    payload = {
        "model": "openrouter/free",
        "messages": history,
        "temperature": 0.85
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY.strip()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram.org",
        "X-Title": "KissMeEngine"
    }

    try:
        async with aiohttp.ClientSession() as session_req:
            async with session_req.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    reply = data["choices"][0]["message"]["content"]
                    history.append({"role": "assistant", "content": reply})
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
        self.wfile.write(b"KissMe Engine Active")

def run_health_check():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

if __name__ == "__main__":
    threading.Thread(target=run_health_check, daemon=True).start()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("characters", character_menu))
    app.add_handler(CommandHandler("reset", reset_cmd))
    app.add_handler(CommandHandler("photo", photo_cmd))
    app.add_handler(CommandHandler("video", video_cmd))
    app.add_handler(CallbackQueryHandler(character_select_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    
    print("KissMe Bot Engine Starting...")
    app.run_polling(drop_pending_updates=True)

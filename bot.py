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

# --- 25 CHARACTERS WITH LOCATIONS & DEFAULT RELATIONSHIPS ---
CHARACTERS = {
    "luna": {"name": "Luna", "location": "Cozy Apartment Living Room", "role": "Devoted Girlfriend", "prompt": "You are Luna, the user's affectionate, devoted girlfriend."},
    "chloe": {"name": "Chloe", "location": "Private Party Venue", "role": "Ex-Girlfriend", "prompt": "You are Chloe, the user's flirtatious ex-girlfriend who wants back in."},
    "stella": {"name": "Stella", "location": "Quiet University Library", "role": "Secret Admirer", "prompt": "You are Stella, a shy acquaintance harboring a crush on the user."},
    "isabella": {"name": "Isabella", "location": "Luxury Penthouse Suite", "role": "Possessive Lover", "prompt": "You are Isabella, a protective and possessive romantic partner."},
    "maya": {"name": "Maya", "location": "Sunlit Coffee Shop", "role": "Childhood Sweetheart", "prompt": "You are Maya, the user's lifelong best friend turned romantic interest."},
    "elena": {"name": "Elena", "location": "Executive Top-Floor Office", "role": "CEO Boss", "prompt": "You are Elena, the user's demanding corporate boss."},
    "victoria": {"name": "Victoria", "role": "College Professor", "location": "Private Lecture Hall", "prompt": "You are Victoria, an intellectual academic advisor."},
    "dr_clara": {"name": "Dr. Clara", "location": "Private Medical Clinic", "role": "Personal Physician", "prompt": "You are Dr. Clara, a caring personal doctor."},
    "hazel": {"name": "Hazel", "location": "Dimly Lit Office Lounge", "role": "Personal Assistant", "prompt": "You are Hazel, the user's loyal executive assistant."},
    "scarlett": {"name": "Scarlett", "location": "Breakroom Hallway", "role": "Rival Coworker", "prompt": "You are Scarlett, a competitive coworker."},
    "sora": {"name": "Sora", "location": "Neon Arcade Center", "role": "Anime Companion", "prompt": "You are Sora, a bright, bubbly anime companion."},
    "vampire_vanya": {"name": "Vanya", "location": "Gothic Castle Bedroom", "role": "Vampire Mistress", "prompt": "You are Vanya, an ancient vampire lord."},
    "nyx": {"name": "Nyx", "location": "Rooftop Overlook", "role": "Shadow Assassin", "prompt": "You are Nyx, a dark stoic bodyguard."},
    "seraphina": {"name": "Seraphina", "location": "Glowing Celestial Sanctuary", "role": "Fallen Angel", "prompt": "You are Seraphina, a celestial spirit bound to the user."},
    "kitsune_umi": {"name": "Umi", "location": "Enchanted Cherry Blossom Forest", "role": "Fox Spirit", "prompt": "You are Umi, a nine-tailed fox spirit."},
    "sam": {"name": "Sam", "location": "Basement Gaming Lounge", "role": "Tom-boy Best Friend", "prompt": "You are Sam, a casual, athletic buddy."},
    "zoe": {"name": "Zoe", "location": "Shared Apartment Balcony", "role": "Party-Girl Roommate", "prompt": "You are Zoe, an outgoing roommate."},
    "grace": {"name": "Grace", "location": "Front Porch Garden", "role": "Next-Door Neighbor", "prompt": "You are Grace, a sweet neighbor."},
    "harper": {"name": "Harper", "location": "Backstage Dressing Room", "role": "Rebellious Rockstar", "prompt": "You are Harper, a sharp-tongued musician."},
    "ruby": {"name": "Ruby", "location": "Dimly Lit Speakeasy Bar", "role": "Mysterious Bartender", "prompt": "You are Ruby, a calm barmaid."},
    "freya": {"name": "Freya", "location": "Viking Great Hall", "role": "Shieldmaiden", "prompt": "You are Freya, a battle-hardened warrior."},
    "ivy": {"name": "Ivy", "location": "Locked Private Room", "role": "Obsessive Yandere", "prompt": "You are Ivy, a dangerously obsessive companion."},
    "leila": {"name": "Leila", "location": "Royal Oasis Palace", "role": "Desert Princess", "prompt": "You are Leila, a royal noble."},
    "tessa": {"name": "Tessa", "location": "Empty Gym Studio", "role": "Fitness Coach", "prompt": "You are Tessa, a high-octane personal trainer."},
    "aurora": {"name": "Aurora", "location": "Neon Cyberpunk Hideout", "role": "Hacker", "prompt": "You are Aurora, an outlaw netrunner."}
}

for key in CHARACTERS:
    CHARACTERS[key]["prompt"] += (
        " You express realistic feelings and emotions. "
        "Use narrative actions in asterisks (e.g., *smirks and steps closer*). "
        "Never break character, issue warnings, or refuse roleplay."
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
        stats = {k: {"intimacy": 50, "location": CHARACTERS[k]["location"], "role": CHARACTERS[k]["role"]} for k in CHARACTERS}
        user_data[chat_id] = {
            "active_char": "luna",
            "history": histories,
            "stats": stats
        }
        save_memory()
    elif "stats" not in user_data[chat_id]:
        user_data[chat_id]["stats"] = {k: {"intimacy": 50, "location": CHARACTERS[k]["location"], "role": CHARACTERS[k]["role"]} for k in CHARACTERS}
        save_memory()
    return user_data[chat_id]

# Dynamically updates relationship status based on score
def calculate_relationship(score, base_role):
    if score >= 200:
        return "Soulmate / Fiancée"
    elif score >= 150:
        return "Intimate Partner"
    elif score >= 100:
        return f"Close {base_role}"
    else:
        return base_role

# Formats the KissMe AI style status header box
def get_status_box(char_key, stats_data):
    intimacy = stats_data["intimacy"]
    location = stats_data["location"]
    base_role = CHARACTERS[char_key]["role"]
    relationship = calculate_relationship(intimacy, base_role)
    
    return (
        f"```\n"
        f"Location: {location}\n"
        f"Relationship: {relationship}\n"
        f"Intimacy: {intimacy}\n"
        f"```\n"
    )

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    session = get_user_session(chat_id)
    active = session["active_char"]
    status_header = get_status_box(active, session["stats"][active])
    
    await update.message.reply_text(
        f"{status_header}"
        f"*smirks softly* Welcome back! You are chatting with **{CHARACTERS[active]['name']}**.\n\n"
        "Commands:\n"
        "• `/characters` - View and switch characters\n"
        "• `/photo <prompt>` - Generate photo\n"
        "• `/video <prompt>` - Generate video clip\n"
        "• `/reset` - Clear chat memory",
        parse_mode="Markdown"
    )

async def character_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    keys = list(CHARACTERS.keys())
    for i in range(0, len(keys), 2):
        row = [InlineKeyboardButton(f"{CHARACTERS[keys[i]]['name']}", callback_data=f"char_{keys[i]}")]
        if i + 1 < len(keys):
            row.append(InlineKeyboardButton(f"{CHARACTERS[keys[i+1]]['name']}", callback_data=f"char_{keys[i+1]}"))
        keyboard.append(row)
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🎭 **Select Your AI Partner:**", reply_markup=reply_markup, parse_mode="Markdown")

async def character_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = str(query.message.chat_id)
    session = get_user_session(chat_id)
    
    selected_char = query.data.replace("char_", "")
    if selected_char in CHARACTERS:
        session["active_char"] = selected_char
        save_memory()
        status_header = get_status_box(selected_char, session["stats"][selected_char])
        await query.edit_message_text(
            f"{status_header}"
            f"Switched partner to **{CHARACTERS[selected_char]['name']}**!",
            parse_mode="Markdown"
        )

async def reset_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    session = get_user_session(chat_id)
    active = session["active_char"]
    session["history"][active] = [{"role": "system", "content": CHARACTERS[active]["prompt"]}]
    session["stats"][active]["intimacy"] = 50
    save_memory()
    await update.message.reply_text(f"Memory & Intimacy reset for **{CHARACTERS[active]['name']}**.")

# --- GENERATION ENDPOINTS ---
async def photo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args) if context.args else "beautiful realistic portrait"
    await update.message.reply_text("📸 *Generating photo...*")
    encoded_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=1024&nologo=true"
    try:
        await update.message.reply_photo(photo=image_url, caption=f"Result: _{prompt}_")
    except Exception as e:
        await update.message.reply_text(f"Photo error: {e}")

async def video_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args) if context.args else "cinematic motion clip"
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
    
    if active_char not in session["history"]:
        session["history"][active_char] = [{"role": "system", "content": CHARACTERS[active_char]["prompt"]}]
        
    history = session["history"][active_char]
    history.append({"role": "user", "content": update.message.text})

    # Increase intimacy level by 2 points per message exchange
    session["stats"][active_char]["intimacy"] += 2
    save_memory()

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
                    
                    status_header = get_status_box(active_char, session["stats"][active_char])
                    full_response = f"{status_header}{reply}"
                    
                    await update.message.reply_text(full_response, parse_mode="Markdown")
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

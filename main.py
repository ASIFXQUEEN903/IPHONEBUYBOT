import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import re

# -----------------------
# CONFIG
# -----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MONGO_URL = os.getenv("MONGO_URL")

# USDT TRC20 address
USDT_ADDRESS = "THbHaBRV6hJQ5A3dsrqm4tPfTzLBthnwbk"
USDT_RATE = 85  # 1 USDT = 85 INR

# PRICE MAP
PRICE_MAP = {
    "iPhone 15 Pro": {"128GB": 2100, "256GB": 2500},
    "iPhone 15 Pro Max": {"256GB": 2700, "512GB": 3000},
    "iPhone 16 Pro": {"128GB": 2300, "256GB": 2600},
    "iPhone 16 Pro Max": {"256GB": 2800, "512GB": 3200},
    "Samsung Galaxy S24 Ultra": {"256GB": 1800, "512GB": 2000},
    "Samsung Galaxy S25 Ultra": {"256GB": 2200, "512GB": 2500}
}

bot = telebot.TeleBot(BOT_TOKEN)

# -----------------------
# MONGO DB SETUP
# -----------------------
client = MongoClient(MONGO_URL)
db = client['usa_bot']
users_col = db['users']

# -----------------------
# TEMP STORAGE
# -----------------------
pending_messages = {}  
active_chats = {}      
user_stage = {}        

# -----------------------
# START COMMAND
# -----------------------
@bot.message_handler(commands=['start'])
def start(msg):
    user_id = msg.from_user.id
    users_col.update_one({'user_id': user_id}, {'$set': {'user_id': user_id}}, upsert=True)
    user_stage[user_id] = "start"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 BUY", callback_data="buy"))
    bot.send_message(msg.chat.id, "👋 Welcome to Carding Store\n👉 iPhone / Samsung Devices Buy Here", reply_markup=kb)

# -----------------------
# CALLBACK HANDLER
# -----------------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    data = call.data

    if data == "buy":
        user_stage[user_id] = "choose_platform"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🛒 Amazon", callback_data="platform_amazon"))
        kb.add(InlineKeyboardButton("🚧 Coming Soon", callback_data="platform_coming"))
        bot.edit_message_text("Choose your platform:", call.message.chat.id, call.message.message_id, reply_markup=kb)
        return

    if data.startswith("platform_") and user_stage.get(user_id) == "choose_platform":
        if data == "platform_amazon":
            user_stage[user_id] = "service"
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("iPhone 16 Pro", callback_data="buy_iphone16pro"))
            kb.add(InlineKeyboardButton("iPhone 15 Pro", callback_data="buy_iphone15pro"))
            kb.add(InlineKeyboardButton("iPhone 16 Pro Max", callback_data="buy_iphone16promax"))
            kb.add(InlineKeyboardButton("iPhone 15 Pro Max", callback_data="buy_iphone15promax"))
            kb.add(InlineKeyboardButton("Samsung Galaxy S24 Ultra", callback_data="buy_s24ultra"))
            kb.add(InlineKeyboardButton("Samsung Galaxy S25 Ultra", callback_data="buy_s25ultra"))
            bot.edit_message_text("Choose your device:", call.message.chat.id, call.message.message_id, reply_markup=kb)
            return
        elif data == "platform_coming":
            bot.edit_message_text("🚧 This feature is coming soon…... please restart the bot /start ", call.message.chat.id, call.message.message_id)
            return

    if data.startswith("buy_") and user_stage.get(user_id) == "service":
        service_map = {
            "buy_iphone15pro": "iPhone 15 Pro",
            "buy_iphone15promax": "iPhone 15 Pro Max",
            "buy_iphone16pro": "iPhone 16 Pro",
            "buy_iphone16promax": "iPhone 16 Pro Max",
            "buy_s24ultra": "Samsung Galaxy S24 Ultra",
            "buy_s25ultra": "Samsung Galaxy S25 Ultra"
        }
        service = service_map.get(data, "Device")
        user_stage[user_id] = "choose_color"
        pending_messages[user_id] = {'service': service}

        kb = InlineKeyboardMarkup()
        if "iPhone 16" in service:
            kb.add(InlineKeyboardButton("Desert Titanium", callback_data=f"color|{service}|Desert Titanium"))
            kb.add(InlineKeyboardButton("Natural Titanium", callback_data=f"color|{service}|Natural Titanium"))
            kb.add(InlineKeyboardButton("White Titanium", callback_data=f"color|{service}|White Titanium"))
            kb.add(InlineKeyboardButton("Black Titanium", callback_data=f"color|{service}|Black Titanium"))
        elif "iPhone 15" in service:
            kb.add(InlineKeyboardButton("Black", callback_data=f"color|{service}|Black"))
            kb.add(InlineKeyboardButton("White", callback_data=f"color|{service}|White"))
            kb.add(InlineKeyboardButton("Blue", callback_data=f"color|{service}|Blue"))
        else:
            kb.add(InlineKeyboardButton("Grey", callback_data=f"color|{service}|Grey"))
            kb.add(InlineKeyboardButton("Black", callback_data=f"color|{service}|Black"))

        bot.edit_message_text(f"Select color for {service}:", call.message.chat.id, call.message.message_id, reply_markup=kb)
        return

    if data.startswith("color|") and user_stage.get(user_id) in ("choose_color", "service"):
        parts = data.split("|")
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "Invalid selection.")
            return
        service = parts[1]
        color = parts[2]
        pending_messages.setdefault(user_id, {})['color'] = color

        user_stage[user_id] = "choose_storage"
        kb = InlineKeyboardMarkup()
        if "Samsung" in service or "Pro Max" in service:
            kb.add(InlineKeyboardButton("256GB", callback_data=f"storage|{service}|{color}|256GB"))
            kb.add(InlineKeyboardButton("512GB", callback_data=f"storage|{service}|{color}|512GB"))
        else:
            kb.add(InlineKeyboardButton("128GB", callback_data=f"storage|{service}|{color}|128GB"))
            kb.add(InlineKeyboardButton("256GB", callback_data=f"storage|{service}|{color}|256GB"))
        bot.edit_message_text(f"Select storage for {service} ({color}):", call.message.chat.id, call.message.message_id, reply_markup=kb)
        return

    if data.startswith("storage|") and user_stage.get(user_id) == "choose_storage":
        parts = data.split("|")
        if len(parts) < 4:
            bot.answer_callback_query(call.id, "Invalid selection.")
            return
        service, color, storage = parts[1], parts[2], parts[3]
        pending_messages.setdefault(user_id, {})['service'] = f"{service} ({color}, {storage})"

        price_inr = PRICE_MAP.get(service, {}).get(storage, 0)
        price_usdt = round(price_inr / USDT_RATE, 2)

        # --- ASK NAME ---
        user_stage[user_id] = "ask_name"
        bot.send_message(
            user_id,
            f"📦 Order Summary:\n\nDevice: {service}\nColour: {color}\nStorage: {storage}\n\n"
            f"💰 Price: ₹{price_inr} (~{price_usdt} USDT)\n\n"
            f"📋 Please enter your Name:"
        )
        return

# -----------------------
# HANDLE NAME, MOBILE & ADDRESS (OLD STYLE)
# -----------------------
@bot.message_handler(func=lambda m: user_stage.get(m.from_user.id) in ["ask_name", "ask_mobile", "ask_address"], content_types=['text'])
def handle_user_input(msg):
    user_id = msg.from_user.id
    stage = user_stage.get(user_id)

    if stage == "ask_name":
        name = msg.text.strip()
        if not name:
            bot.send_message(user_id, "⚠️ Name cannot be empty. Please enter your Name:")
            return
        pending_messages.setdefault(user_id, {})['name'] = name
        user_stage[user_id] = "ask_mobile"
        bot.send_message(user_id, "📱 Please enter your 10-digit Mobile Number (digits only):")
        return

    if stage == "ask_mobile":
        mobile = msg.text.strip()
        if not re.fullmatch(r"\d{10}", mobile):
            bot.send_message(user_id, "⚠️ Invalid number. Enter 10-digit Mobile Number:")
            return
        pending_messages.setdefault(user_id, {})['mobile'] = mobile
        user_stage[user_id] = "ask_address"
        bot.send_message(user_id, "🏠 Please enter your Address (State → City → Street → Pin Code):")
        return

    if stage == "ask_address":
        address = msg.text.strip()
        if not address:
            bot.send_message(user_id, "⚠️ Address cannot be empty. Please enter your Address:")
            return
        pending_messages.setdefault(user_id, {})['address'] = address
        user_stage[user_id] = "choose_payment"

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(" USDT TRC20", callback_data="pay_usdt"))
        kb.add(InlineKeyboardButton(" Flipkart Gift Card", callback_data="pay_flipkart"))

        bot.send_message(user_id, "✅ All details received. Select payment method:", reply_markup=kb)
        return

# -----------------------
# BROADCAST COMMAND (ADMIN ONLY)
# -----------------------
@bot.message_handler(commands=['broadcast'])
def broadcast(msg):
    if msg.from_user.id != ADMIN_ID:
        return
    text = msg.text.partition(' ')[2]
    if not text:
        bot.reply_to(msg, "⚠️ Usage: /broadcast Your message here")
        return
    sent = 0
    for u in users_col.find():
        try:
            bot.send_message(u['user_id'], f"📢 Broadcast:\n{text}")
            sent += 1
        except:
            pass
    bot.reply_to(msg, f"✅ Broadcast sent to {sent} users.")

# -----------------------
# FINISH CHAT FUNCTION (OLD CODE STYLE)
# -----------------------
def finish_chat(msg, target_id):
    final_text = msg.text.strip()
    if target_id in active_chats and active_chats[target_id]:
        bot.send_message(target_id, final_text)
        active_chats.pop(target_id, None)
        bot.send_message(ADMIN_ID, f"💬 Chat with user {target_id} ended.")
    else:
        bot.send_message(ADMIN_ID, f"⚠️ No active chat with user {target_id}.")

# -----------------------
# RUN BOT (OLD CODE STYLE)
# -----------------------
print("✅ Bot running…")
bot.infinity_polling()

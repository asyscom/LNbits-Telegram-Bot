from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import requests
import asyncio
from threading import Thread
import time
import signal
import sys

# Configuration
TELEGRAM_API_KEY = "YOUR_TELEGRAM_BOT_TOKEN"
LNBITS_ADMIN_KEY = "YOUR_LNBITS_ADMIN_KEY"
LNBITS_INVOICE_KEY = "YOUR_LNBITS_INVOICE_KEY"
LNBITS_URL = "https://yourlnbitsinstance.com/api/v1/"
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

app = Flask(__name__)

# Telegram Application
bot_app = Application.builder().token(TELEGRAM_API_KEY).build()

# Custom Keyboard
keyboard = [
    ["Create Invoice", "Pay Invoice"],
    ["Wallet Balance", "Generate LNURL-w"]
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Track notified payments
notified_payments = set()

# Polling function for incoming payments
def check_received_payments():
    global notified_payments
    while True:
        try:
            response = requests.get(
                f"{LNBITS_URL}payments",
                headers={"X-Api-Key": LNBITS_INVOICE_KEY},
            )
            if response.status_code == 200:
                payments = response.json()
                for payment in payments:
                    if payment.get("paid") and payment.get("payment_hash") not in notified_payments:
                        amount = payment.get("amount", 0) / 1000
                        payment_hash = payment.get("payment_hash")
                        bot_app.bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"💰 Payment received!\n🔑 Hash: {payment_hash}\n💸 Amount: {amount} sats"
                        )
                        notified_payments.add(payment_hash)
        except Exception as e:
            print(f"Error during payment polling: {e}")
        time.sleep(10)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the LNbits Telegram bot! Use the interactive menu below.",
        reply_markup=reply_markup
    )

# Create Invoice
async def create_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /create_invoice <amount in sats>")
        return

    amount = int(context.args[0])
    response = requests.post(
        f"{LNBITS_URL}payments",
        json={"out": False, "amount": amount, "memo": "Bot Invoice"},
        headers={"X-Api-Key": LNBITS_ADMIN_KEY},
    )

    if response.status_code == 201:
        invoice_data = response.json()
        payment_request = invoice_data.get("payment_request")
        await update.message.reply_text(f"✅ Invoice created:\n\n`{payment_request}`", parse_mode="Markdown")
    else:
        error_message = response.json().get("detail", "Unknown error")
        await update.message.reply_text(f"❌ Error: {error_message}")

# Generate LNURL-w
async def generate_lnurlw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /generate_lnurlw <amount> <uses>")
        return

    amount = int(context.args[0]) * 1000  # Convert to millisatoshis
    max_uses = int(context.args[1])

    response = requests.post(
        f"{LNBITS_URL}lnurlw",
        json={"title": "Bot Withdraw Link", "min_withdrawable": amount, "max_withdrawable": amount, "uses": max_uses},
        headers={"X-Api-Key": LNBITS_ADMIN_KEY},
    )

    if response.status_code == 201:
        lnurlw_data = response.json()
        lnurl = lnurlw_data.get("lnurl")
        await update.message.reply_text(f"✅ LNURL-w created:\n\n`{lnurl}`", parse_mode="Markdown")
    else:
        error_message = response.json().get("detail", "Unknown error")
        await update.message.reply_text(f"❌ Error: {error_message}")

# Check Wallet Balance
async def wallet_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(
            f"{LNBITS_URL}wallet",
            headers={"X-Api-Key": LNBITS_INVOICE_KEY},
        )
        data = response.json()
        balance = data.get("balance", 0)
        await update.message.reply_text(f"Wallet balance: {balance / 1000:.0f} sats")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

# Signal handlers for graceful shutdown
def shutdown_signal_handler(sig, frame):
    print("Stopping bot...")
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_signal_handler)
signal.signal(signal.SIGTERM, shutdown_signal_handler)

# Command Handlers
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("create_invoice", create_invoice))
bot_app.add_handler(CommandHandler("generate_lnurlw", generate_lnurlw))
bot_app.add_handler(CommandHandler("wallet_balance", wallet_balance))

if __name__ == "__main__":
    # Start polling thread
    polling_thread = Thread(target=check_received_payments, daemon=True)
    polling_thread.start()

    # Start the bot
    asyncio.run(bot_app.run_polling())

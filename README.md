# LNbits-Telegram-Bot
---

## **Introduction**
This project is a Telegram bot that interacts with **LNbits**, a platform for managing Lightning Network wallets. The bot provides the following functionalities:

- Create Lightning Network invoices.
- Pay invoices or LN addresses.
- Check wallet balance.
- Receive payment notifications using polling.
- Generate and manage **LNURL-w** links for withdrawals.

---

## **Requirements**
1. **Operating System**: Linux (Ubuntu 20.04+ recommended).
2. **Python**: Version 3.10 or later.
3. **Telegram**: Create a bot using BotFather and obtain the bot token.
4. **LNbits**: Install LNbits locally or use an online instance.

---

## **Dependencies**
### Install Python and Required Modules
1. **Install Python**:
   ```bash
   sudo apt update && sudo apt install python3 python3-pip python3-venv -y
   ```

2. **Create a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python Modules**:
   ```bash
   pip install python-telegram-bot[ext] flask requests
   ```

---

## **Setting up LNbits**
### API Keys
1. Go to **LNbits > Extensions > API**.
2. Copy the following keys:
   - **Admin Key**: For full wallet access.
   - **Invoice Key**: For creating invoices.

### LNURL-w (Withdraw Links)
1. Enable the **Withdraw Links (LNURL-w)** extension in LNbits.
2. Create a withdraw link:
   - Go to **Withdraw Links** in your wallet.
   - Click **Create LNURLw**.
   - Configure:
     - **Description**: A short description of the link.
     - **Max Uses**: Number of times the link can be used.
     - **Min/Max Withdrawable**: Define the amount range (in satoshis).
   - Save the link.
3. Use the API or bot commands to manage LNURL-w links.

---

## **Bot Configuration**
1. **Telegram Bot Token**: Obtain from BotFather.
2. **LNbits URL**: Your LNbits instance URL (e.g., `https://yourlnbitsinstance.com`).
3. **Chat ID**: Your Telegram user or group chat ID.

---

## **Features**
- **Create Invoices**: Generate invoices with specific amounts.
- **Pay Invoices or LN Addresses**: Process payments.
- **Check Wallet Balance**: Fetch wallet balance in satoshis.
- **Receive Notifications**: Get real-time updates on incoming payments.
- **Generate LNURL-w Links**: Create and manage withdraw links.

---

## **Bot Code**

```python
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
```

---

## **Usage Instructions**
1. **Start the bot**:
   ```bash
   python3 bot.py
   ```
2. **Bot Commands**:
   - `/start`: Start the bot.
   - `/create_invoice <amount>`: Generate an invoice for the specified amount.
   - `/generate_lnurlw <amount> <uses>`: Create a withdraw link for the specified amount and uses.
   - `/wallet_balance`: Check the wallet balance.

---

Test the bot and feel free to contribute improvements! 🎉

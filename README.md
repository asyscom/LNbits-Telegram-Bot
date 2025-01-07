# Telegram LNbits Wallet Bot

This Telegram bot allows interaction with an LNbits wallet for:

- Checking the balance.
- Creating and paying invoices.
- Viewing recent transactions.
- Paying Lightning Addresses (LN Address).

---

## Requirements

1. **Telegram Bot**:

   - Create a bot on Telegram via [BotFather](https://t.me/BotFather) and obtain the API token.

2. **LNbits**:

   - Install LNbits on your server or use a public instance by following the official instructions available on [LNbits GitHub](https://github.com/lnbits/lnbits).
   - Ensure the "PayLink" extension is enabled in the LNbits admin panel. This extension is required to handle LN Addresses.

3. **Python Dependencies**:

   - Install the required packages using the command:
     ```bash
     pip install -r requirements.txt
     ```

4. **DNS Configuration for LN Address**:

   - To use LN Address (e.g., `test@example.com`):
     - Add a **CNAME** record to your domain's DNS.
     - The CNAME must use the desired address name (`test`) and point to the public IP of the LNbits server.
     - For example, to configure `test@example.com`:
       - Name: `test`
       - Type: `CNAME`
       - Value: `YOUR_SERVER_IP`.

---

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/asyscom/LNbits-Telegram-Bot.git
   cd telegram-lnbits-bot
   ```

2. **Set up environment variables**:

   - Create a `.env` file and add:
     ```env
     LNbits_URL=http://127.0.0.1:5000
     ADMIN_KEY=YOUR_ADMIN_KEY
     WALLET_ID=YOUR_WALLET_ID
     BOT_TOKEN=YOUR_BOT_TOKEN
     AUTHORIZED_USER_ID=YOUR_TELEGRAM_ID
     ```

3. **Configure LNbits**:

   - Navigate to the "PayLink" extension.
   - Set up the webhook by entering your server URL followed by `/webhook` (see image):

     ![Schermata del 2025-01-07 16-22-18](https://github.com/user-attachments/assets/9c8dd7f6-fbe1-436a-bd3e-8f6f4c4663a0)



---

## Usage

1. **Start the bot**:

   ```bash
   python main.py
   ```

2. **Main Features**:

   - **/start**: Displays the welcome message and main keyboard.
   - **/balance**: Checks the wallet balance.
   - **/create\_invoice**: Generates a Lightning invoice with a QR code.
   - **/pay\_invoice**: Pays a Lightning invoice.
   - **/pay\_lnaddress**: Pays a Lightning Address (LN Address).
   - **📜 Transactions**: Shows the last 15 transactions with details.

---

## Advanced Configuration

1. **LNbits Webhook**:

   - Ensure the webhook is set up correctly in the "PayLink" extension.
   - This ensures the bot receives updates for incoming payments.

2. **Persistent Storage**:

   - The bot uses an SQLite database (`lnbits_bot.db`) to store invoices and their statuses.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.


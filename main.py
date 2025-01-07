import requests
import os
import qrcode
import sqlite3
import threading
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from io import BytesIO  # Importa BytesIO per gestire immagini in memoria
# Configurazione LNbits e bot Telegram
LNbits_URL = "http://127.0.0.1:5000"
ADMIN_KEY = ""  # Admin Key  wallet LNbits
WALLET_ID = ""  # ID  wallet LNbits
BOT_TOKEN = ""  # Token  bot Telegram
AUTHORIZED_USER_ID = XXXX  # ID of the user authorized to use the bot.

# Flas servers service
app_5050 = Flask("Server_5050")
app_5588 = Flask("Server_5588")

# Config SQLite
DB_NAME = "lnbits_bot.db"


# Conf Logging
logging.basicConfig(
    level=logging.DEBUG,  # Imposta il livello a DEBUG per più dettagli
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Logga sulla console
        logging.FileHandler("bot_debug.log", mode='w')  # Salva i log in un file (sovrascrivi ogni volta)
    ]
)
logger = logging.getLogger(__name__)

# Pulsanti di default
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("💰 Balance"), KeyboardButton("⚡ Invoice")],  # Due pulsanti sulla stessa riga
    ],
    resize_keyboard=True,
)


def update_main_keyboard():
    """Crea una tastiera principale con il saldo dinamico, invoice e pagamento."""
    saldo = get_wallet_balance()  # Recupera il saldo dal wallet
    if saldo is None:
        saldo = "Errore"  # Se non disponibile, mostra un errore

    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(f"💰 {saldo} sats"), KeyboardButton("⚡ Invoice")],
            [KeyboardButton("📤 Pay Invoice"), KeyboardButton("📜 Transactions")], 
        ],
        resize_keyboard=True,
    )

def get_recent_transactions(limit=15):
    """Ottieni le ultime transazioni dal wallet LNbits."""
    url = f"{LNbits_URL}/api/v1/payments"
    headers = {"X-API-KEY": ADMIN_KEY, "accept": "application/json"}
    try:
        response = requests.get(url, headers=headers, params={"limit": limit})
        if response.status_code == 200:
            return response.json()  # Restituisci la lista delle transazioni
        else:
            logger.error(f"Errore nel recupero delle transazioni: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Errore nella richiesta delle transazioni: {e}")
        return []


from datetime import datetime

def handle_transactions_click(update: Update, context: CallbackContext):
    """Gestisce il clic sul pulsante 📜 Transazioni."""
    transactions = get_recent_transactions()

    if not transactions:
        update.message.reply_text(
            "❌ Nessuna transazione trovata o errore nel recupero.",
            reply_markup=update_main_keyboard(),
        )
        return

    # Costruisci il messaggio delle transazioni
    message = "📜 *last  15 Transactions:*\n\n"
    for tx in transactions[:15]:  # Limita a 15
        amount = tx.get("amount", 0) // 1000  # Converti millisatoshi in satoshi
        memo = tx.get("memo", "Senza memo").strip()
        timestamp = tx.get("time", None)  # Ottieni il timestamp della transazione
        formatted_time = datetime.fromtimestamp(timestamp).strftime("%d %B %Y %H:%M") if timestamp else "Data sconosciuta"

        # Ottieni lnaddress dal campo extra
        extra = tx.get("extra", {})
        lnaddress = extra.get("lnaddress", "Indirizzo non disponibile")

        # Determina la direzione della transazione
        if amount > 0:  # Transazione in entrata
            direction = "🟢⬇️"
            details = f"📩 Mittente: {lnaddress}"
        else:  # Transazione in uscita
            direction = "🔴⬆️"
            details = f"📩 Destinatario: {lnaddress}"

        # Crea la riga della transazione
        message += (
            f"{direction} {abs(amount)} sats\n"
            f"{details}\n"
            f"📅 {formatted_time}\n"
            f"💬 Memo: {memo}\n\n"
        )

    # Invia il messaggio formattato
    update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=update_main_keyboard(),
    )



def check_balance(update: Update, context: CallbackContext):
    """Aggiorna il saldo e la tastiera."""
    saldo = get_wallet_balance()  # Ottiene il saldo reale dal wallet
    if saldo is not None:
        update.message.reply_text(
            f"💰 Saldo aggiornato: {saldo} sats",
            reply_markup=update_main_keyboard(),  # Aggiorna la tastiera dinamica
        )
    else:
        update.message.reply_text(
            "❌ Impossibile recuperare il saldo del wallet. Riprova più tardi.",
            reply_markup=update_main_keyboard(),  # Mostra comunque la tastiera
        )


from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ForceReply

# Funzione per ottenere il saldo e aggiornare il pulsante
def update_keyboard_with_balance():
    """Aggiorna la tastiera con il saldo attuale in satoshi."""
    saldo = get_wallet_balance()
    if saldo is None:
        saldo = "Errore"  # Mostra un messaggio se il saldo non è disponibile
    return ReplyKeyboardMarkup(
        [[KeyboardButton(f"{saldo} sats")]],
        resize_keyboard=True,
    )

# Funzione per iniziare

def start(update: Update, context: CallbackContext):
    """Risponde al comando /start."""
    if update.effective_user.id != AUTHORIZED_USER_ID:
        update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
        return

    update.message.reply_text(
        "👋 Benvenuto nel bot Lightning Network Wallet! ⚡\n\n"
        "Premi uno dei pulsanti qui sotto per iniziare.",
        reply_markup=update_main_keyboard(),  # Usa la tastiera dinamica
    )


def handle_balance_click(update: Update, context: CallbackContext):
    """Gestisce il clic sul pulsante con il saldo."""
    saldo = get_wallet_balance()  # Ottiene il saldo reale dal wallet
    if saldo is not None:
        update.message.reply_text(
            f"{saldo} sats",
            reply_markup=update_keyboard_with_balance(),  # Aggiorna la tastiera
        )
    else:
        update.message.reply_text(
            "❌ Impossibile recuperare il saldo del wallet. Riprova più tardi.",
            reply_markup=update_keyboard_with_balance(),  # Mostra comunque la tastiera
        )



def ask_payment_details(update: Update, context: CallbackContext):
    """Chiede all'utente di incollare l'invoice o l'indirizzo Lightning."""
    logger.debug(f"[ask_payment_details] Richiesto invoice o indirizzo da: {update.effective_user.id}")
    update.message.reply_text(
        "Incolla l'invoice da pagare o inserisci un indirizzo Lightning:",
        reply_markup=ForceReply(),
    )
    context.user_data["action"] = "pay_invoice"  # Registra l'azione
    logger.debug(f"[ask_payment_details] Context action set to: {context.user_data['action']}")


def handle_button_press(update: Update, context: CallbackContext):
    """Gestisce i pulsanti del bot."""
    text = update.message.text.strip()
    logger.debug(f"[handle_button_press] Pulsante premuto o messaggio ricevuto: {text}")

    if text == "⚡ Invoice":
        ask_invoice_amount(update, context)
    elif text.startswith("💰"):
        check_balance(update, context)
    elif text == "📤 Paga Invoice":
        ask_payment_details(update, context)  # Richiesta interattiva
    else:
        logger.warning(f"[handle_button_press] Comando non riconosciuto: {text}")
        update.message.reply_text("❌ Comando non riconosciuto.", reply_markup=update_main_keyboard())


def ask_invoice_amount(update: Update, context: CallbackContext):
    """Chiede l'importo per generare un invoice."""
    logger.debug(f"[ask_invoice_amount] Richiesto importo per invoice da: {update.effective_user.id}")
    update.message.reply_text(
        "Inserisci l'importo in satoshi per generare un invoice:",
        reply_markup=ForceReply(),  # Forza una risposta
    )
    context.user_data["action"] = "create_invoice"  # Registra l'azione attiva
    logger.debug(f"[ask_invoice_amount] Context action set to: {context.user_data['action']}")

def ask_payment_request(update: Update, context: CallbackContext):
    """Chiede l'invoice da pagare."""
    update.message.reply_text(
        "Incolla l'invoice da pagare:",
        reply_markup=ForceReply(),
    )
    context.user_data["action"] = "pay_invoice"

# Gestisce le risposte dell'utente


def handle_user_response(update: Update, context: CallbackContext):
    """Gestisce le risposte dell'utente ai messaggi con ForceReply."""
    user_action = context.user_data.get("action", None)  # Recupera l'azione attiva
    logger.debug(f"[handle_user_response] Azione corrente: {user_action}, Messaggio ricevuto: {update.message.text.strip()}")

    try:
        user_input = update.message.text.strip()

        if user_action == "create_invoice":
            try:
                amount = int(user_input)
                logger.info(f"[handle_user_response] Generazione invoice per: {amount} sats")
                memo = "Generato via bot Telegram"
                payment_request = create_invoice(amount, memo)

                if payment_request:
                    # Genera il QR code
                    qr = qrcode.QRCode()
                    qr.add_data(payment_request)
                    qr.make(fit=True)
                    img = qr.make_image(fill_color="black", back_color="white")

                    # Salva il QR code in memoria
                    qr_buffer = BytesIO()
                    img.save(qr_buffer)
                    qr_buffer.seek(0)

                    # Invia il QR code e i dettagli
                    update.message.reply_photo(
                        photo=qr_buffer,
                        caption=(
                            f"✅ Invoice creata con successo!\n"
                            f"💸 Importo: {amount} sats\n"
                            f"🔗 Invoice: `{payment_request}`\n\n"
                            "Scansiona il QR code per pagare l'invoice."
                        ),
                        parse_mode="Markdown",
                        reply_markup=update_main_keyboard()
                    )
                    logger.info(f"[handle_user_response] Invoice generata correttamente per {amount} sats")
                else:
                    logger.error(f"[handle_user_response] Errore nella creazione dell'invoice per {amount} sats")
                    update.message.reply_text("❌ Errore nella creazione dell'invoice.")
            except ValueError:
                logger.error("[handle_user_response] Input non valido per l'importo.")
                update.message.reply_text("❌ Inserisci un valore numerico valido.")
            finally:
                context.user_data["action"] = None  # Resetta l'azione

        elif user_action == "pay_invoice":
            if "@" in user_input and "ln_address" not in context.user_data:
                # Lightning Address rilevato
                logger.info(f"[handle_user_response] Lightning Address rilevato: {user_input}")
                context.user_data["ln_address"] = user_input
                context.user_data["action"] = "pay_ln_address"
                update.message.reply_text("Inserisci l'importo in satoshi per inviare il pagamento:", reply_markup=ForceReply())

            elif user_input.startswith("lnbc"):
                # Invoice rilevata
                logger.info(f"[handle_user_response] Invoice rilevata: {user_input}")
                if pay_invoice(user_input):
                    update.message.reply_text("✅ Pagamento effettuato con successo!", reply_markup=update_main_keyboard())
                else:
                    update.message.reply_text("❌ Pagamento fallito. Verifica l'invoice e riprova.", reply_markup=update_main_keyboard())
                context.user_data["action"] = None

            else:
                logger.error(f"[handle_user_response] Input non valido durante il pagamento: {user_input}")
                update.message.reply_text("❌ Inserisci un valore valido o un invoice.")

        elif user_action == "pay_ln_address":
            if user_input.isdigit():
                amount = int(user_input)
                ln_address = context.user_data.pop("ln_address", None)
                logger.info(f"[handle_user_response] Pagamento a LN Address: {ln_address}, Importo: {amount} sats")

                # Notifica di risoluzione dell'indirizzo
                update.message.reply_text("⚙️ Risoluzione dell'indirizzo Lightning in corso...")
                callback_url, min_amount, max_amount = resolve_lnaddress(ln_address)

                if not callback_url:
                    update.message.reply_text("❌ Impossibile risolvere l'indirizzo LN. Verifica e riprova.")
                    context.user_data["action"] = None
                    return

                # Notifica dei limiti
                update.message.reply_text("📊 Verifica dei limiti di pagamento...")
                if amount < min_amount or amount > max_amount:
                    update.message.reply_text(
                        f"⚠️ L'importo deve essere tra {min_amount} e {max_amount} sats."
                    )
                    context.user_data["action"] = "pay_ln_address"
                    return

                # Notifica di elaborazione del pagamento
                update.message.reply_text("🔄 Elaborazione del pagamento...")
                result = pay_lnaddress(callback_url, amount)
                update.message.reply_text(result["message"], reply_markup=update_main_keyboard())
                if result["status"] == "success":
                    logger.info(f"[handle_user_response] Pagamento completato per {ln_address}, {amount} sats")
                else:
                    logger.error(f"[handle_user_response] Errore nel pagamento: {result['message']}")

            else:
                logger.error(f"[handle_user_response] Input non valido per LN Address: {user_input}")
                update.message.reply_text("❌ Inserisci un valore numerico valido.")
                context.user_data["action"] = "pay_ln_address"

        else:
            logger.warning(f"[handle_user_response] Nessuna azione corrispondente trovata: {user_action}")
            update.message.reply_text("❌ Comando non riconosciuto.", reply_markup=update_main_keyboard())

    except Exception as e:
        logger.error(f"[handle_user_response] Errore generico: {e}")
        update.message.reply_text("❌ Si è verificato un errore imprevisto.")
        context.user_data["action"] = None


def debug_command(update: Update, context: CallbackContext):
    """Comando di debug per verificare lo stato del bot."""
    try:
        logger.info("[debug_command] Stato del bot richiesto.")
        update.message.reply_text("✅ Il bot è in esecuzione correttamente.")
    except Exception as e:
        logger.error(f"[debug_command] Errore durante il debug: {e}")
        update.message.reply_text("❌ Si è verificato un errore durante il debug.")



def pay_lnaddress_command(update: Update, context: CallbackContext):
    """Gestisce il comando /pay_lnaddress per pagare un Lightning Address."""
    if update.effective_user.id != AUTHORIZED_USER_ID:
        update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
        return

    if len(context.args) < 2 or not context.args[1].isdigit():
        update.message.reply_text("⚠️ Uso corretto: /pay_lnaddress <lnaddress> <importo in sats>")
        return

    lnaddress = context.args[0]
    amount = int(context.args[1])

    callback_url, min_amount, max_amount = resolve_lnaddress(lnaddress)
    if not callback_url:
        update.message.reply_text("❌ Impossibile risolvere l'indirizzo LN. Verifica e riprova.")
        return

    if amount < min_amount or amount > max_amount:
        update.message.reply_text(
            f"⚠️ L'importo deve essere tra {min_amount} e {max_amount} sats."
        )
        return

    update.message.reply_text("🔄 Elaborazione del pagamento...")

    if pay_lnaddress(callback_url, amount):
        update.message.reply_text("✅ Pagamento effettuato con successo!")
    else:
        update.message.reply_text("❌ Pagamento fallito. Riprova più tardi.")



def pay_lnaddress(callback_url, amount):
    """Paga un Lightning Address utilizzando il callback URL."""
    try:
        logger.info(f"[pay_lnaddress] Avvio del pagamento per LN Address. Callback URL: {callback_url}, Importo: {amount} sats")

        # Converti l'importo in millisatoshi
        amount_msat = amount * 1000
        logger.debug(f"[pay_lnaddress] Importo convertito in millisatoshi: {amount_msat} msat")

        # Effettua una richiesta GET al callback URL con l'importo
        response = requests.get(callback_url, params={"amount": amount_msat})
        if response.status_code == 200:
            data = response.json()
            if "pr" in data:
                payment_request = data["pr"]
                logger.debug(f"[pay_lnaddress] Invoice ricevuta dal server: {payment_request}")

                # Usa la funzione pay_invoice per completare il pagamento
                if pay_invoice(payment_request):
                    logger.info("[pay_lnaddress] Pagamento completato con successo.")
                    return {"status": "success", "message": "Pagamento effettuato con successo!"}
                else:
                    logger.error("[pay_lnaddress] Pagamento non riuscito.")
                    return {"status": "failure", "message": "Pagamento fallito. Riprova più tardi."}
            else:
                logger.error("[pay_lnaddress] Mancanza del campo 'pr' nella risposta.")
                return {"status": "failure", "message": "Il server non ha restituito un'invoice valida."}
        else:
            logger.error(f"[pay_lnaddress] Errore HTTP: {response.status_code} - {response.text}")
            return {"status": "failure", "message": f"Errore nella comunicazione con il server Lightning: {response.status_code}"}
    except Exception as e:
        logger.error(f"[pay_lnaddress] Errore durante il pagamento LNURL: {e}")
        return {"status": "error", "message": "Si è verificato un errore durante il pagamento."}



# Funzioni comuni
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS invoices (
                        id TEXT PRIMARY KEY,
                        payment_request TEXT,
                        amount INTEGER,
                        memo TEXT,
                        paid INTEGER DEFAULT 0
                    )''')
    conn.commit()
    conn.close()

def register_webhook():
    url = f"{LNbits_URL}/api/v1/wallets/{WALLET_ID}/webhook"
    headers = {"X-API-KEY": ADMIN_KEY, "Content-Type": "application/json"}
    payload = {"url": "http://31.220.82.89:5588/webhook"}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code in (200, 201):
        logger.info("Webhook registrato con successo!")
    else:
        logger.error(f"Errore nella registrazione del webhook: {response.text}")

def get_wallet_balance():
    url = f"{LNbits_URL}/api/v1/wallet"
    headers = {"X-API-KEY": ADMIN_KEY, "accept": "application/json"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            balance = response.json().get("balance", 0) // 1000  # Converti millisatoshi in satoshi
            return balance
        else:
            logger.error(f"Errore nel recupero del saldo: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Errore nella richiesta del saldo: {e}")
    return None

def create_invoice(amount, memo):
    """Crea un invoice tramite l'API LNbits con il webhook configurato."""
    logger.debug(f"[create_invoice] Creazione invoice: {amount} sats, Memo: {memo}")
    url = f"{LNbits_URL}/api/v1/payments"
    headers = {"X-API-KEY": ADMIN_KEY, "Content-Type": "application/json"}
    
    # URL del webhook (usa l'endpoint del tuo server)
    webhook_url = "http://31.220.82.89:5050/webhook"  # Aggiorna con il tuo IP/server
    
    payload = {
        "out": False,
        "amount": amount,
        "memo": memo,
        "webhook": webhook_url,  # Aggiungi il webhook qui
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        payment_request = response.json().get("payment_request")
        logger.info(f"[create_invoice] Invoice creata: {payment_request}")
        return payment_request
    else:
        logger.error(f"[create_invoice] Errore API LNbits: {response.status_code}, Dettagli: {response.text}")
        return None

def pay_invoice(payment_request):
    """Esegue il pagamento di un invoice tramite LNbits."""
    try:
        logger.info(f"[pay_invoice] Avvio del pagamento per invoice: {payment_request}")
        url = f"{LNbits_URL}/api/v1/payments"
        headers = {"X-API-KEY": ADMIN_KEY, "Content-Type": "application/json"}
        payload = {"out": True, "bolt11": payment_request}

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            logger.info("[pay_invoice] Pagamento effettuato con successo.")
            return True
        else:
            logger.error(f"[pay_invoice] Errore nel pagamento dell'invoice: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"[pay_invoice] Errore durante il pagamento dell'invoice: {e}")
        return False

def process_webhook(data):
    try:
        logger.info(f"[Webhook] Payload ricevuto: {data}")

        payment_hash = data.get("payment_hash")
        amount = data.get("amount", 0) // 1000  # Converti millisatoshi in satoshi
        memo = data.get("comment", None)  # Usa None se il memo non è presente

        # Log di debug per verificare i dati ricevuti
        logger.debug(f"[process_webhook] payment_hash: {payment_hash}, amount: {amount}, memo: {memo}")

        if amount > 0 and payment_hash:
            logger.info(f"Pagamento confermato: ID={payment_hash}, Importo={amount}, Memo={memo or 'Nessun memo'}")

            conn = sqlite3.connect(DB_NAME)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM invoices WHERE id = ?", (payment_hash,))
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO invoices (id, payment_request, amount, memo, paid) VALUES (?, ?, ?, ?, 1)",
                        (payment_hash, "", amount, memo)
                    )
                    conn.commit()

                    # Costruisci il messaggio dinamico
                    message = f"⚡ Pagamento ricevuto!\n💰 {amount} sats"
                    if memo:  # Aggiungi il memo solo se è presente
                        message += f"\n📝 Memo: {memo}"

                    # Invia la notifica Telegram
                    updater.bot.send_message(
                        chat_id=AUTHORIZED_USER_ID,
                        text=message
                    )
                else:
                    logger.info(f"Pagamento già registrato: {payment_hash}")
            finally:
                conn.close()
            return {"status": "ok"}
        else:
            logger.warning(f"Pagamento non valido o incompleto: {data}")
            return {"status": "ignored"}
    except Exception as e:
        logger.error(f"Errore durante l'elaborazione del webhook: {e}")
        return {"status": "error", "message": str(e)}



def create_invoice_command(update: Update, context: CallbackContext):
    """Gestisce il comando /create_invoice per generare un invoice."""
    if len(context.args) == 0 or not context.args[0].isdigit():
        update.message.reply_text("⚠️ Uso corretto: /create_invoice <importo in sats>")
        return

    amount = int(context.args[0])
    memo = "Generato via bot Telegram"
    payment_request = create_invoice(amount, memo)

    if payment_request:
        # Genera il QR code per l'invoice
        qr = qrcode.QRCode()
        qr.add_data(payment_request)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        # Salva il QR code in memoria per inviarlo
        qr_buffer = BytesIO()
        img.save(qr_buffer)
        qr_buffer.seek(0)

        # Invia il QR code e i dettagli dell'invoice
        update.message.reply_photo(
            photo=qr_buffer,
            caption=(
                f"✅ Invoice creata con successo!\n"
                f"💸 Importo: {amount} sats\n"
                f"🔗 Invoice: `{payment_request}`\n\n"
                "Scansiona il QR code per pagare l'invoice."
            ),
            parse_mode="Markdown",
        )
    else:
        update.message.reply_text("❌ Errore nella creazione dell'invoice.")

def pay_invoice_command(update: Update, context: CallbackContext):
    """Gestisce il comando /pay_invoice per pagare un'invoice."""
    if update.effective_user.id != AUTHORIZED_USER_ID:
        update.message.reply_text("❌ Non sei autorizzato a usare questo bot.")
        return

    if len(context.args) == 0:
        update.message.reply_text("⚠️ Uso corretto: /pay_invoice <bolt11>")
        return

    payment_request = context.args[0]
    update.message.reply_text("🔄 Elaborazione del pagamento...")

    if pay_invoice(payment_request):
        update.message.reply_text("✅ Pagamento effettuato con successo!")
    else:
        update.message.reply_text("❌ Pagamento fallito. Verifica l'invoice e riprova.")


# Funzioni Bot



def resolve_lnaddress(lnaddress):
    """Risolvi un Lightning Address e restituisci le informazioni per il pagamento."""
    try:
        if "@" not in lnaddress:
            raise ValueError("LNAddress non valido. Deve essere nel formato username@domain.")

        username, domain = lnaddress.split("@")
        url = f"https://{domain}/.well-known/lnurlp/{username}"

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if "callback" in data:
                callback_url = data["callback"]
                min_amount = data.get("minSendable", 0) // 1000  # Converti millisatoshi in satoshi
                max_amount = data.get("maxSendable", 0) // 1000  # Converti millisatoshi in satoshi
                return callback_url, min_amount, max_amount
            else:
                raise ValueError("LNURL non valido: manca il campo 'callback'.")
        else:
            raise ValueError(f"Errore HTTP {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Errore nella risoluzione dell'indirizzo LN: {e}")
        return None, None, None


@app_5050.route("/webhook", methods=["POST"])
def webhook_5050():
    try:
        data = request.get_json()
        logger.info("[5050] Webhook ricevuto.")
        logger.info(f"[5050] Payload ricevuto: {data}")
        return jsonify(process_webhook(data))
    except Exception as e:
        logger.error(f"Errore nel webhook [5050]: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app_5588.route("/webhook", methods=["POST"])
def webhook_5588():
    try:
        data = request.get_json()
        logger.info("[5588] Webhook ricevuto.")
        logger.info(f"[5588] Payload ricevuto: {data}")
        return jsonify(process_webhook(data))
    except Exception as e:
        logger.error(f"Errore nel webhook [5588]: {e}")
        return jsonify({"status": "error", "message": str(e)})

# Dispatcher
if __name__ == "__main__":
    # Inizializza il database e registra il webhook
    init_db()
    register_webhook()

    # Avvia i server Flask
    threading.Thread(target=lambda: app_5050.run(host="0.0.0.0", port=5050, debug=False), daemon=True).start()
    threading.Thread(target=lambda: app_5588.run(host="0.0.0.0", port=5588, debug=False), daemon=True).start()

    # Configura il bot Telegram
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Gestione comandi
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("balance", check_balance))
    dispatcher.add_handler(CommandHandler("create_invoice", create_invoice_command))
    dispatcher.add_handler(CommandHandler("pay_invoice", pay_invoice_command))
    dispatcher.add_handler(CommandHandler("pay_lnaddress", pay_lnaddress_command))
    dispatcher.add_handler(CommandHandler("debug", debug_command))
    

    dispatcher.add_handler(MessageHandler(
        Filters.text & Filters.regex(r'^\d+\s+sats$'), handle_balance_click))
    dispatcher.add_handler(MessageHandler(
        Filters.text & Filters.regex(r'^📜 Transazioni$'), handle_transactions_click))



    # Dispatcher
    dispatcher.add_handler(MessageHandler(Filters.reply, handle_user_response))  # Risposte interattive
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_button_press))  # Pulsanti



    # Avvia il bot Telegram
    updater.start_polling()
    updater.idle()

# bot.py — interactive tele-crossover bot with dynamic stock tracking and real-time alerts
import os, sys, json, time, logging, threading
from dotenv import load_dotenv
import telebot
import yfinance as yf
import pandas as pd

# ---- ensure UTF-8 on Windows consoles ----
try:
    if sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---- load .env ----
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
ENV_WATCHLIST = os.getenv('WATCHLIST', '')

# ---- validate ----
if not BOT_TOKEN or not CHAT_ID:
    print("BOT_TOKEN or CHAT_ID missing — please set them in .env or as environment variables.")
    raise SystemExit(1)

# ---- logging ----
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(BOT_TOKEN)

WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")

# ---- watchlist functions ----
def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [s.strip().upper() for s in data if s and s.strip()]
        except Exception as e:
            logging.error("Failed to load watchlist.json: %s", e)
    if ENV_WATCHLIST:
        return [s.strip().upper() for s in ENV_WATCHLIST.split(",") if s.strip()]
    return []

def save_watchlist(lst):
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(lst, f, indent=2)
        return True
    except Exception as e:
        logging.error("Failed to save watchlist.json: %s", e)
        return False

def norm(sym):
    return sym.strip().upper()

# ---- SMA crossover function ----
def get_crossover(symbol, interval="1d"):
    try:
        period = "1y" if interval=="1d" else "60d" if interval=="1h" else "7d"
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return "No data"
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["SMA200"] = df["Close"].rolling(200).mean()
        df = df.dropna(subset=["SMA50", "SMA200"])
        if len(df) < 2:
            return "Not enough data"
        prev, latest = df.iloc[-2], df.iloc[-1]
        prev50, prev200 = float(prev["SMA50"]), float(prev["SMA200"])
        latest50, latest200 = float(latest["SMA50"]), float(latest["SMA200"])
        if prev50 < prev200 and latest50 > latest200:
            return "Golden Cross"
        if prev50 > prev200 and latest50 < latest200:
            return "Death Cross"
        return "No Crossover"
    except Exception as e:
        logging.warning("get_crossover error for %s: %s", symbol, e)
        return "Error"

# ---- command handlers ----
@bot.message_handler(commands=['start'])
def handle_start(msg):
    chat = msg.chat.id
    text = (
        "👋 Hello! I'm your Crossover bot.\n\n"
        "Commands:\n"
        "/watchlist - show current watchlist\n"
        "/addstock SYMBOL - add SYMBOL to watchlist\n"
        "/removestock SYMBOL - remove SYMBOL from watchlist\n"
        "/signal SYMBOL - check current crossover for SYMBOL\n"
        "/track SYMBOL - start real-time crossover alerts for any stock\n\n"
        "Examples:\n"
        "/addstock RELIANCE.NS\n"
        "/signal INFY.NS\n"
        "/track TCS.NS\n"
    )
    bot.send_message(chat, text)

@bot.message_handler(commands=['watchlist'])
def handle_watchlist(msg):
    wl = load_watchlist()
    if not wl:
        bot.send_message(msg.chat.id, "Watchlist is empty.")
        return
    bot.send_message(msg.chat.id, "Current watchlist:\n" + "\n".join(wl))

@bot.message_handler(commands=['addstock'])
def handle_add(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: /addstock SYMBOL")
        return
    sym = norm(parts[1])
    wl = load_watchlist()
    if sym in wl:
        bot.reply_to(msg, f"{sym} is already in the watchlist.")
        return
    wl.append(sym)
    if save_watchlist(wl):
        bot.reply_to(msg, f"Added {sym} to watchlist.")
    else:
        bot.reply_to(msg, f"Failed to add {sym} — check logs")

@bot.message_handler(commands=['removestock'])
def handle_remove(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: /removestock SYMBOL")
        return
    sym = norm(parts[1])
    wl = load_watchlist()
    if sym not in wl:
        bot.reply_to(msg, f"{sym} not found in watchlist.")
        return
    wl = [s for s in wl if s != sym]
    if save_watchlist(wl):
        bot.reply_to(msg, f"Removed {sym} from watchlist.")
    else:
        bot.reply_to(msg, f"Failed to remove {sym} — check logs")

@bot.message_handler(commands=['signal'])
def handle_signal(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: /signal SYMBOL")
        return
    sym = norm(parts[1])
    bot.reply_to(msg, f"Checking {sym}... (this may take a few seconds)")
    daily = get_crossover(sym, interval="1d")
    hourly = get_crossover(sym, interval="1h")
    minute = get_crossover(sym, interval="1m")
    text = f"{sym}\nDaily: {daily}\nHourly: {hourly}\nMinute: {minute}"
    bot.send_message(msg.chat.id, text)

# ---- dynamic subscriptions for any stock ----
subscriptions = {}  # {symbol: [chat_id, ...]}
last_cross_state = {}  # {symbol: {"minute": "Golden Cross"}}

@bot.message_handler(commands=['track'])
def handle_track(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(msg, "Usage: /track SYMBOL")
        return
    sym = norm(parts[1])
    chat_id = msg.chat.id
    subscriptions.setdefault(sym, [])
    if chat_id not in subscriptions[sym]:
        subscriptions[sym].append(chat_id)
        bot.reply_to(msg, f"✅ You are now subscribed to real-time crossover alerts for {sym}")
    else:
        bot.reply_to(msg, f"🔔 Already subscribed to {sym}")

# ---- dynamic crossover alert loop ----
def dynamic_crossover_loop():
    while True:
        for sym, chat_ids in subscriptions.items():
            try:
                minute_cross = get_crossover(sym, interval="1m")
                prev_state = last_cross_state.get(sym, {})
                last_minute = prev_state.get("minute")

                if minute_cross not in [None, "No Crossover", "Not enough data", "Error"] and minute_cross != last_minute:
                    for chat_id in chat_ids:
                        bot.send_message(chat_id, f"⏱️ {sym} Minute-Level Crossover Alert: {minute_cross}")
                    last_cross_state.setdefault(sym, {})["minute"] = minute_cross

            except Exception as e:
                logging.warning("Dynamic minute alert error for %s: %s", sym, e)
        time.sleep(60)  # 1-minute interval

# ---- safe polling ----
def start_bot():
    # start the dynamic crossover thread
    threading.Thread(target=dynamic_crossover_loop, daemon=True).start()
    while True:
        try:
            logging.info("Bot started polling...")
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except telebot.apihelper.ApiTelegramException as e:
            logging.warning("Telegram API exception: %s", e)
            time.sleep(5)
        except Exception as e:
            logging.exception("Unexpected exception in polling: %s", e)
            time.sleep(5)

# ---- initialize watchlist file ----
if not os.path.exists(WATCHLIST_FILE):
    initial = [s.strip().upper() for s in ENV_WATCHLIST.split(",") if s.strip()]
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=2)
        logging.info("Created initial watchlist.json")
    except Exception as ex:
        logging.error("Failed creating watchlist.json: %s", ex)

# ---- main ----
if __name__ == '__main__':
    logging.info("Starting bot...")
    start_bot()

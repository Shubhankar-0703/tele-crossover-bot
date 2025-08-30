# bot.py — Tele-Crossover Bot (Railway-ready)
import os
import json
import time
import logging
import telebot
import yfinance as yf
import pandas as pd

# ---- logging ----
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---- load environment variables from Railway ----
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ENV_WATCHLIST = os.getenv("WATCHLIST", "")

if not BOT_TOKEN or not CHAT_ID:
    logging.error("BOT_TOKEN or CHAT_ID not set in environment variables!")
    raise SystemExit(1)

bot = telebot.TeleBot(BOT_TOKEN)

# ---- watchlist file ----
WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [s.strip().upper() for s in data if s.strip()]
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

# ---- SMA crossover ----
def get_crossover(symbol, interval="1d"):
    try:
        period = "1y" if interval=="1d" else "60d"
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df is None or df.empty:
            return "No data"
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["SMA200"] = df["Close"].rolling(200).mean()
        df = df.dropna(subset=["SMA50","SMA200"])
        if len(df) < 2:
            return "Not enough data"
        prev = df.iloc[-2]
        latest = df.iloc[-1]
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

# ---- Commands ----
@bot.message_handler(commands=["start"])
def handle_start(msg):
    chat = msg.chat.id
    text = (
        "👋 Hello! I'm your Crossover bot.\n\n"
        "Commands:\n"
        "/watchlist - show current watchlist\n"
        "/addstock SYMBOL - add SYMBOL to watchlist\n"
        "/removestock SYMBOL - remove SYMBOL from watchlist\n"
        "/signal SYMBOL - check current crossover for SYMBOL\n"
        "/price SYMBOL - get latest price\n\n"
        "Example:\n"
        "/addstock RELIANCE.NS\n"
        "/signal INFY.NS"
    )
    bot.send_message(chat, text)

@bot.message_handler(commands=["watchlist"])
def handle_watchlist(msg):
    wl = load_watchlist()
    if not wl:
        bot.send_message(msg.chat.id, "Watchlist is empty.")
    else:
        bot.send_message(msg.chat.id, "Current watchlist:\n" + "\n".join(wl))

@bot.message_handler(commands=["addstock"])
def handle_add(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts)<2:
        bot.reply_to(msg, "Usage: /addstock SYMBOL")
        return
    sym = norm(parts[1])
    wl = load_watchlist()
    if sym in wl:
        bot.reply_to(msg, f"{sym} is already in watchlist.")
        return
    wl.append(sym)
    if save_watchlist(wl):
        bot.reply_to(msg, f"Added {sym} to watchlist.")
    else:
        bot.reply_to(msg, f"Failed to add {sym} — check logs")

@bot.message_handler(commands=["removestock"])
def handle_remove(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts)<2:
        bot.reply_to(msg, "Usage: /removestock SYMBOL")
        return
    sym = norm(parts[1])
    wl = load_watchlist()
    if sym not in wl:
        bot.reply_to(msg, f"{sym} not found in watchlist.")
        return
    wl = [s for s in wl if s!=sym]
    if save_watchlist(wl):
        bot.reply_to(msg, f"Removed {sym} from watchlist.")
    else:
        bot.reply_to(msg, f"Failed to remove {sym} — check logs")

@bot.message_handler(commands=["price"])
def handle_price(msg):
    parts = msg.text.split()
    if len(parts)<2:
        bot.reply_to(msg, "Usage: /price SYMBOL")
        return
    ticker = parts[1].upper()
    stock = yf.Ticker(ticker)
    data = stock.history(period="1d")
    if data.empty:
        bot.reply_to(msg, f"❌ Could not fetch data for {ticker}")
    else:
        price = data["Close"].iloc[-1]
        bot.reply_to(msg, f"💹 {ticker} latest closing price: ₹{price:.2f}")

@bot.message_handler(commands=["signal"])
def handle_signal(msg):
    parts = msg.text.split(maxsplit=1)
    if len(parts)<2:
        bot.reply_to(msg, "Usage: /signal SYMBOL")
        return
    sym = norm(parts[1])
    bot.reply_to(msg, f"Checking {sym}... (may take a few seconds)")
    daily = get_crossover(sym, interval="1d")
    hourly = get_crossover(sym, interval="1h")
    text = f"{sym}\nDaily: {daily}\nHourly: {hourly}"
    bot.send_message(msg.chat.id, text)

# ---- Safe polling ----
def start_bot():
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

if __name__=="__main__":
    # Ensure watchlist file exists
    if not os.path.exists(WATCHLIST_FILE):
        initial = [s.strip().upper() for s in ENV_WATCHLIST.split(",") if s.strip()]
        try:
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(initial, f, indent=2)
            logging.info("Created initial watchlist.json")
        except Exception as ex:
            logging.error("Failed creating watchlist.json: %s", ex)
    start_bot()

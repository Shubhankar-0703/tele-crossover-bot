import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os, json, time
import yfinance as yf
import schedule
import telebot
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WATCHLIST = [s.strip() for s in (os.getenv("WATCHLIST") or "").split(",") if s.strip()]

bot = telebot.TeleBot(BOT_TOKEN)
SIGNALS_FILE = "signals.json"

try:
    with open(SIGNALS_FILE, "r") as f:
        last_signals = json.load(f)
except FileNotFoundError:
    last_signals = {}

def get_crossover(symbol, interval, period):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df.empty or len(df) < 205:
        return "None"
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()
    latest, prev = df.iloc[-1], df.iloc[-2]
    if prev["SMA50"] < prev["SMA200"] and latest["SMA50"] > latest["SMA200"]:
        return "Golden Cross"
    if prev["SMA50"] > prev["SMA200"] and latest["SMA50"] < latest["SMA200"]:
        return "Death Cross"
    return "None"

def check_signals():
    global last_signals
    messages = []
    for symbol in WATCHLIST:
        for tf, period in (("1d", "1y"), ("1h", "60d")):
            status = get_crossover(symbol, tf, period)
            prev_status = last_signals.get(symbol, {}).get(tf, "None")
            if status != prev_status and status != "None":
                emoji = "✅" if status == "Golden Cross" else "❌"
                messages.append(f"{symbol} ({tf}): {emoji} {status}")
                last_signals.setdefault(symbol, {})[tf] = status
    if messages:
        text = "⚡ *Crossover Alert!*\n\n" + "\n".join(messages)
        bot.send_message(CHAT_ID, text, parse_mode="Markdown")
        with open(SIGNALS_FILE, "w") as f:
            json.dump(last_signals, f, indent=2)

schedule.every().hour.do(check_signals)
schedule.every().day.at("09:30").do(check_signals)

print("[OK] Auto-alert module running...")
while True:
    schedule.run_pending()
    time.sleep(60)

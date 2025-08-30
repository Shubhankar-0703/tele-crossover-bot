#!/usr/bin/env python3
"""
Web App version of Tele-Crossover Bot
Provides both web interface and Telegram bot functionality
"""

import os
import json
import logging
import threading
from flask import Flask, render_template, request, jsonify, redirect, url_for
import yfinance as yf
import pandas as pd
try:
    import telebot
except ImportError:
    telebot = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ENV_WATCHLIST = os.getenv("WATCHLIST", "")
PORT = int(os.getenv("PORT", 5000))

# Initialize bot if token is available (disabled for web-only deployment)
bot = None
# Temporarily disabled to avoid conflicts
# if BOT_TOKEN and telebot:
#     bot = telebot.TeleBot(BOT_TOKEN)

WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    """Load watchlist from file or environment"""
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
    """Save watchlist to file"""
    try:
        with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
            json.dump(lst, f, indent=2)
        return True
    except Exception as e:
        logging.error("Failed to save watchlist.json: %s", e)
        return False

def get_crossover(symbol, interval="1d"):
    """Check for SMA crossover signals"""
    try:
        period = "1y" if interval == "1d" else "60d"
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        
        if df is None or df.empty:
            return "No data"
        
        df["SMA50"] = df["Close"].rolling(50).mean()
        df["SMA200"] = df["Close"].rolling(200).mean()
        df = df.dropna(subset=["SMA50", "SMA200"])
        
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

def get_stock_price(symbol):
    """Get latest stock price"""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if data.empty:
            return None
        return float(data["Close"].iloc[-1])
    except Exception as e:
        logging.error("Error getting price for %s: %s", symbol, e)
        return None

# Web Routes
@app.route('/')
def index():
    """Main dashboard"""
    watchlist = load_watchlist()
    watchlist_data = []
    
    for symbol in watchlist:
        price = get_stock_price(symbol)
        daily_signal = get_crossover(symbol, "1d")
        hourly_signal = get_crossover(symbol, "1h")
        
        watchlist_data.append({
            'symbol': symbol,
            'price': price,
            'daily_signal': daily_signal,
            'hourly_signal': hourly_signal
        })
    
    return render_template('index.html', watchlist=watchlist_data)

@app.route('/add_stock', methods=['POST'])
def add_stock():
    """Add stock to watchlist"""
    symbol = request.form.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': 'Symbol is required'}), 400
    
    watchlist = load_watchlist()
    if symbol in watchlist:
        return jsonify({'error': f'{symbol} is already in watchlist'}), 400
    
    watchlist.append(symbol)
    if save_watchlist(watchlist):
        return jsonify({'success': f'Added {symbol} to watchlist'})
    else:
        return jsonify({'error': 'Failed to save watchlist'}), 500

@app.route('/remove_stock', methods=['POST'])
def remove_stock():
    """Remove stock from watchlist"""
    symbol = request.form.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': 'Symbol is required'}), 400
    
    watchlist = load_watchlist()
    if symbol not in watchlist:
        return jsonify({'error': f'{symbol} not found in watchlist'}), 400
    
    watchlist = [s for s in watchlist if s != symbol]
    if save_watchlist(watchlist):
        return jsonify({'success': f'Removed {symbol} from watchlist'})
    else:
        return jsonify({'error': 'Failed to save watchlist'}), 500

@app.route('/api/signal/<symbol>')
def get_signal(symbol):
    """API endpoint to get signal for a specific symbol"""
    symbol = symbol.upper()
    daily = get_crossover(symbol, "1d")
    hourly = get_crossover(symbol, "1h")
    price = get_stock_price(symbol)
    
    return jsonify({
        'symbol': symbol,
        'daily_signal': daily,
        'hourly_signal': hourly,
        'price': price
    })

@app.route('/api/watchlist')
def get_watchlist_api():
    """API endpoint to get current watchlist"""
    watchlist = load_watchlist()
    return jsonify({'watchlist': watchlist})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'tele-crossover-bot'})

@app.route('/api')
def api_docs():
    """API documentation page"""
    return render_template('api.html')

# Telegram Bot Handlers (if bot is enabled)
if bot:
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
        if len(parts) < 2:
            bot.reply_to(msg, "Usage: /addstock SYMBOL")
            return
        
        sym = parts[1].strip().upper()
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
        if len(parts) < 2:
            bot.reply_to(msg, "Usage: /removestock SYMBOL")
            return
        
        sym = parts[1].strip().upper()
        wl = load_watchlist()
        if sym not in wl:
            bot.reply_to(msg, f"{sym} not found in watchlist.")
            return
        
        wl = [s for s in wl if s != sym]
        if save_watchlist(wl):
            bot.reply_to(msg, f"Removed {sym} from watchlist.")
        else:
            bot.reply_to(msg, f"Failed to remove {sym} — check logs")

    @bot.message_handler(commands=["price"])
    def handle_price(msg):
        parts = msg.text.split()
        if len(parts) < 2:
            bot.reply_to(msg, "Usage: /price SYMBOL")
            return
        
        ticker = parts[1].upper()
        price = get_stock_price(ticker)
        if price is None:
            bot.reply_to(msg, f"❌ Could not fetch data for {ticker}")
        else:
            bot.reply_to(msg, f"💹 {ticker} latest closing price: ₹{price:.2f}")

    @bot.message_handler(commands=["signal"])
    def handle_signal(msg):
        parts = msg.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(msg, "Usage: /signal SYMBOL")
            return
        
        sym = parts[1].strip().upper()
        bot.reply_to(msg, f"Checking {sym}... (may take a few seconds)")
        daily = get_crossover(sym, interval="1d")
        hourly = get_crossover(sym, interval="1h")
        text = f"{sym}\nDaily: {daily}\nHourly: {hourly}"
        bot.send_message(msg.chat.id, text)

def start_telegram_bot():
    """Start Telegram bot in a separate thread"""
    if not bot:
        logging.info("Telegram bot not configured (missing BOT_TOKEN)")
        return
    
    while True:
        try:
            logging.info("Telegram bot started polling...")
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            logging.exception("Error in Telegram bot: %s", e)
            import time
            time.sleep(5)

if __name__ == "__main__":
    # Initialize watchlist file if it doesn't exist
    if not os.path.exists(WATCHLIST_FILE):
        initial = [s.strip().upper() for s in ENV_WATCHLIST.split(",") if s.strip()]
        try:
            with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(initial, f, indent=2)
            logging.info("Created initial watchlist.json")
        except Exception as ex:
            logging.error("Failed creating watchlist.json: %s", ex)
    
    # Start Telegram bot in background thread if configured
    if bot:
        bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()
        logging.info("Started Telegram bot in background")
    
    # Start Flask web app
    logging.info(f"Starting web app on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)

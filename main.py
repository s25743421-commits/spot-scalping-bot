import ccxt
import pandas as pd
import requests
import time
import os
from datetime import datetime

# ================= CONFIG =================

TIMEFRAME = '5m'
CANDLES = 50
SCAN_DELAY = 60  # seconds
COOLDOWN_MINUTES = 30

PAIRS = [
    'BTC/USDT',
    'ETH/USDT',
    'SOL/USDT',
    'BNB/USDT',
    'XRP/USDT',
    'AVAX/USDT',
    'OP/USDT'
]

DISCORD_WEBHOOK_URL = os.getenv("https://discord.com/api/webhooks/1457674224763146404/rxZI9rgKmo2_LMDv7W2sWJvSpJoZwrmYp3YX9hZC1ZgUmMGefILl4b5n94rgn0yxRH4e")

# ================= INIT =================

exchange = ccxt.bybit({
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'}
})

last_signal_time = {}

print("🚀 Spot Scalping Bot Started...")

# ================= FUNCTIONS =================

def send_discord(message):
    if not DISCORD_WEBHOOK_URL:
        print("❌ Discord webhook missing")
        return
    payload = {"content": message}
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def in_cooldown(pair):
    if pair not in last_signal_time:
        return False
    diff = datetime.utcnow() - last_signal_time[pair]
    return diff.total_seconds() < COOLDOWN_MINUTES * 60

def fetch_data(pair):
    candles = exchange.fetch_ohlcv(pair, timeframe=TIMEFRAME, limit=CANDLES)
    df = pd.DataFrame(candles, columns=['time','open','high','low','close','volume'])
    return df

def liquidity_sweep(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return last['low'] < prev['low'] and last['close'] > prev['open']

def strong_bullish_close(df):
    last = df.iloc[-1]
    body = abs(last['close'] - last['open'])
    range_ = last['high'] - last['low']
    return body > range_ * 0.6 and last['close'] > last['open']

def generate_signal(pair):
    df = fetch_data(pair)

    if not liquidity_sweep(df):
        return None

    if not strong_bullish_close(df):
        return None

    entry = df.iloc[-1]['close']
    recent_low = df['low'].tail(10).min()
    recent_high = df['high'].tail(10).max()

    sl = round(recent_low * 0.998, 4)
    tp = round(entry + (entry - sl) * 1.5, 4)

    return {
        "pair": pair,
        "entry": round(entry, 4),
        "sl": sl,
        "tp": tp
    }

# ================= MAIN LOOP =================

while True:
    for pair in PAIRS:
        try:
            if in_cooldown(pair):
                continue

            signal = generate_signal(pair)

            if signal:
                msg = (
                    f"📊 **SPOT BUY SIGNAL**\n\n"
                    f"PAIR: {signal['pair']}\n"
                    f"ENTRY: {signal['entry']}\n"
                    f"TP: {signal['tp']}\n"
                    f"SL: {signal['sl']}\n\n"
                    f"⏱ TF: {TIMEFRAME}\n"
                    f"🎯 Logic: PA + Liquidity\n"
                )

                send_discord(msg)
                last_signal_time[pair] = datetime.utcnow()
                print(f"✅ Signal sent for {pair}")

            else:
                print(f"No valid setup on {pair}")

        except Exception as e:
            print(f"⚠️ Error on {pair}: {e}")

    time.sleep(SCAN_DELAY)


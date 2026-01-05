import ccxt
import pandas as pd
import requests
import time
from datetime import datetime, timedelta

# ================= CONFIG =================
TIMEFRAME = '5m'
CANDLES = 50
SCAN_DELAY = 60  # seconds
COOLDOWN_MINUTES = 45

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1457653912117968926/whuCLJwUQIgDR3Kqm-AZqZWv0Md0zkhr6bAfZKkomKiXfxDemKYiSGqAliDAAgZ0R0di"

PAIRS = [
    'BTC/USDT',
    'ETH/USDT',
    'SOL/USDT',
    'BNB/USDT',
    'XRP/USDT',
    'AVAX/USDT',
    'OP/USDT'
]
# =========================================

exchange = ccxt.bybit()
last_signal_time = {}

def send_discord(msg):
    requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})

def in_cooldown(pair):
    if pair not in last_signal_time:
        return False
    return datetime.now() < last_signal_time[pair] + timedelta(minutes=COOLDOWN_MINUTES)

def analyze_pair(pair):
    ohlcv = exchange.fetch_ohlcv(pair, timeframe=TIMEFRAME, limit=CANDLES)
    df = pd.DataFrame(ohlcv, columns=['ts','open','high','low','close','vol'])

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # ---- BASIC MARKET FILTER ----
    if last['high'] - last['low'] == 0:
        return None

    # ---- BUY REJECTION LOGIC ----
    bullish_rejection = (
        last['close'] > last['open'] and
        last['low'] < prev['low']
    )

    if not bullish_rejection:
        return None

    # ---- ENTRY ZONE ----
    entry_low = min(last['open'], last['close'])
    entry_high = max(last['open'], last['close'])

    # ---- SMART SL ----
    candle_range = last['high'] - last['low']
    sl = last['low'] - (candle_range * 0.35)

    # ---- TP (1.3R) ----
    risk = entry_low - sl
    tp = entry_high + (risk * 1.3)

    # ---- CONFIDENCE SCORE ----
    confidence = "HIGH" if candle_range > df['high'].sub(df['low']).mean() else "MEDIUM"

    return {
        "pair": pair,
        "entry_low": entry_low,
        "entry_high": entry_high,
        "sl": sl,
        "tp": tp,
        "confidence": confidence
    }

# ================= MAIN LOOP =================
print("🚀 Spot Scalping Bot Started...")

while True:
    for pair in PAIRS:

        if in_cooldown(pair):
            continue

        try:
            signal = analyze_pair(pair)

            if signal:
                msg = f"""
📈 SPOT BUY SIGNAL

PAIR: {signal['pair']}
ENTRY ZONE: {signal['entry_low']:.2f} – {signal['entry_high']:.2f}
STOP LOSS: {signal['sl']:.2f}
TAKE PROFIT: {signal['tp']:.2f}
CONFIDENCE: {signal['confidence']}
TIMEFRAME: {TIMEFRAME}

NOTE:
Liquidity sweep + bullish rejection.
Risk max 1% per trade.
"""

                send_discord(msg)
                last_signal_time[pair] = datetime.now()
                print(f"✅ Signal sent: {pair}")

        except Exception as e:
            print(f"⚠️ Error on {pair}: {e}")

    time.sleep(SCAN_DELAY)

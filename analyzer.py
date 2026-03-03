"""
🧠 Trading Analysis Engine - Google Gemini (BEPUL!)
"""
import re, base64, json, asyncio, urllib.request, os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

FOREX_PAIRS = [
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","USD/CAD",
    "AUD/USD","NZD/USD","EUR/GBP","EUR/JPY","GBP/JPY",
    "EUR/AUD","EUR/CAD","EUR/CHF","GBP/AUD","GBP/CAD",
    "GBP/CHF","AUD/JPY","CAD/JPY","CHF/JPY","NZD/JPY",
    "AUD/CAD","AUD/CHF","AUD/NZD","CAD/CHF","EUR/NZD",
    "GBP/NZD","NZD/CAD","NZD/CHF","USD/HKD","USD/SGD",
    "USD/NOK","USD/SEK","USD/DKK","USD/MXN","USD/ZAR",
    "USD/TRY","USD/PLN","USD/HUF","USD/CZK","EUR/PLN",
    "EUR/HUF","EUR/CZK","EUR/NOK","EUR/SEK","EUR/DKK",
    "GBP/PLN","USD/CNH","USD/INR","USD/BRL","XAU/USD",
]

CRYPTO_PAIRS = [
    "BTC/USDT","ETH/USDT","BNB/USDT","XRP/USDT","ADA/USDT",
    "SOL/USDT","DOT/USDT","DOGE/USDT","AVAX/USDT","MATIC/USDT",
    "LINK/USDT","LTC/USDT","UNI/USDT","ATOM/USDT","XLM/USDT",
    "TRX/USDT","ETC/USDT","FIL/USDT","AAVE/USDT","ALGO/USDT",
    "VET/USDT","ICP/USDT","THETA/USDT","FTM/USDT","SAND/USDT",
    "MANA/USDT","AXS/USDT","NEAR/USDT","GALA/USDT","ENJ/USDT",
    "CHZ/USDT","SHIB/USDT","PEPE/USDT","FLOKI/USDT","WIF/USDT",
    "OP/USDT","ARB/USDT","SUI/USDT","SEI/USDT","TIA/USDT",
    "INJ/USDT","JUP/USDT","PYTH/USDT","RNDR/USDT","FET/USDT",
    "WLD/USDT","STX/USDT","BLUR/USDT","IMX/USDT","LDO/USDT",
]

STRATEGIES = """
1. Trend Following - EMA 20/50/200
2. RSI Divergence
3. Support & Resistance
4. Breakout Trading
5. Fibonacci Retracement - 0.382, 0.5, 0.618
6. MACD Signal
7. Bollinger Bands
8. Price Action - Pin bar, Engulfing, Doji
9. Smart Money Concept - Order blocks, FVG
10. Scalping - 5-15 daqiqa
"""

PAIR_LIST_TEXT = (
    "📊 *FOREX (50 ta):*\n" + ", ".join(FOREX_PAIRS) +
    "\n\n🪙 *CRYPTO (50 ta):*\n" + ", ".join(CRYPTO_PAIRS)
)

def _call_gemini(prompt: str, image_b64: str = None) -> str:
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    parts = []
    if image_b64:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_b64}})
    parts.append({"text": prompt})
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800}
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=40) as r:
        res = json.loads(r.read().decode())
    return res["candidates"][0]["content"]["parts"][0]["text"]

async def detect_pair_from_image(image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    pairs_str = ", ".join(FOREX_PAIRS + CRYPTO_PAIRS)
    prompt = (f"Bu trading screenshotida qaysi juftlik ko'rsatilgan? "
              f"Faqat juftlik nomini yoz: {pairs_str}. "
              f"Aniqlay olmasang: UNKNOWN")
    try:
        text = await asyncio.to_thread(_call_gemini, prompt, b64)
        detected = text.strip().upper()
        for pair in (FOREX_PAIRS + CRYPTO_PAIRS):
            if pair.upper() in detected:
                return pair
    except Exception as e:
        print(f"Pair detect xato: {e}")
    return "UNKNOWN"

async def analyze_chart(image_bytes: bytes, balance: float, pair: str) -> dict:
    b64 = base64.b64encode(image_bytes).decode()
    risk_percent = 1.0 if balance<=10 else (1.5 if balance<=50 else (2.0 if balance<=200 else 2.5))
    risk_amount = balance * risk_percent / 100

    prompt = f"""Sen professional trading analistisiz. Strategiyalar: {STRATEGIES}
Balans: ${balance}, Juftlik: {pair}, Risk: {risk_percent}% = ${risk_amount:.2f}

Bu chartni tahlil qil. FAQAT sof JSON qaytar (``` belgisiz):
{{"signal":"BUY","pair":"{pair}","timeframe":"1H","entry":0.0,"sl":0.0,"tp":0.0,"rr_ratio":"1:2","strategy":"Trend Following","confidence":"HIGH","reason":"O'zbek tilida sabab","risk_amount":{risk_amount:.2f},"lot_suggestion":0.01,"warning":null}}

signal: BUY yoki SELL yoki WAIT. FAQAT JSON."""

    try:
        text = await asyncio.to_thread(_call_gemini, prompt, b64)
        text = re.sub(r"```json|```", "", text).strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(m.group() if m else text)
        data.update({"balance": balance, "risk_percent": risk_percent})
        return data
    except Exception as e:
        print(f"Tahlil xato: {e}")
        return {"signal":"WAIT","pair":pair,"timeframe":"N/A","entry":0,"sl":0,"tp":0,
                "rr_ratio":"N/A","strategy":"N/A","confidence":"LOW",
                "reason":"Chartni o'qishda xatolik. Aniqroq screenshot yuboring.",
                "risk_amount":risk_amount,"lot_suggestion":0,"warning":"Qayta urinib ko'ring",
                "balance":balance,"risk_percent":risk_percent}

def format_signal_message(data: dict) -> str:
    sig = data.get("signal","?")
    emoji = {"BUY":"🟢","SELL":"🔴","WAIT":"⏳"}.get(sig,"❓")
    conf_e = {"HIGH":"🔥","MEDIUM":"⚡","LOW":"⚠️"}.get(data.get("confidence",""),"")
    if sig == "WAIT":
        return (f"⏳ *Hozircha kuting*\n\n"
                f"📊 Juftlik: `{data.get('pair','N/A')}`\n"
                f"📐 Strategiya: {data.get('strategy','N/A')}\n\n"
                f"📝 *Sabab:*\n{data.get('reason','')}\n\n"
                f"⚠️ {data.get('warning') or 'Bozor noaniq, sabr qiling'}")
    warn = f"⚠️ *Ogohlantirish:* {data['warning']}\n\n" if data.get("warning") else ""
    return (f"{emoji} *{sig} SIGNAL* {conf_e}\n\n"
            f"📊 *Juftlik:* `{data.get('pair','N/A')}`\n"
            f"⏱ *Taymfreym:* {data.get('timeframe','N/A')}\n"
            f"📐 *Strategiya:* {data.get('strategy','N/A')}\n\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 *Kirish:* `{data.get('entry','N/A')}`\n"
            f"🛑 *Stop Loss:* `{data.get('sl','N/A')}`\n"
            f"🎯 *Take Profit:* `{data.get('tp','N/A')}`\n"
            f"📈 *R/R:* {data.get('rr_ratio','N/A')}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"💼 *Balans:* ${data.get('balance',0):.2f}\n"
            f"⚠️ *Risk:* ${data.get('risk_amount',0):.2f} ({data.get('risk_percent',0)}%)\n"
            f"📦 *Lot/Hajm:* {data.get('lot_suggestion','N/A')}\n\n"
            f"📝 *Tahlil:*\n{data.get('reason','')}\n\n"
            f"{warn}"
            f"━━━━━━━━━━━━━━━\n"
            f"⚡ _TradeSignal Pro tahlili_")

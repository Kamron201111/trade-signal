import re, base64, json, asyncio, urllib.request, urllib.error, os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

FOREX_PAIRS = [
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","USD/CAD","AUD/USD","NZD/USD",
    "EUR/GBP","EUR/JPY","GBP/JPY","EUR/AUD","EUR/CAD","EUR/CHF","GBP/AUD",
    "GBP/CAD","GBP/CHF","AUD/JPY","CAD/JPY","CHF/JPY","NZD/JPY","AUD/CAD",
    "AUD/CHF","AUD/NZD","CAD/CHF","EUR/NZD","GBP/NZD","NZD/CAD","NZD/CHF",
    "USD/NOK","USD/SEK","USD/DKK","USD/MXN","USD/ZAR","USD/TRY","USD/PLN",
    "USD/HUF","USD/CZK","EUR/PLN","EUR/NOK","EUR/SEK","EUR/HUF","EUR/CZK",
    "XAU/USD","XAG/USD","EUR/TRY","GBP/TRY","USD/SGD","USD/HKD","USD/CNH","USD/INR",
]

CRYPTO_PAIRS = [
    "BTC/USDT","ETH/USDT","BNB/USDT","XRP/USDT","ADA/USDT","SOL/USDT","DOT/USDT",
    "DOGE/USDT","AVAX/USDT","MATIC/USDT","LINK/USDT","LTC/USDT","UNI/USDT","ATOM/USDT",
    "XLM/USDT","TRX/USDT","ETC/USDT","FIL/USDT","AAVE/USDT","ALGO/USDT","VET/USDT",
    "ICP/USDT","SAND/USDT","MANA/USDT","AXS/USDT","NEAR/USDT","SHIB/USDT","PEPE/USDT",
    "OP/USDT","ARB/USDT","SUI/USDT","SEI/USDT","INJ/USDT","RNDR/USDT","FET/USDT",
    "WLD/USDT","STX/USDT","IMX/USDT","LDO/USDT","FLOKI/USDT","WIF/USDT","JUP/USDT",
    "TIA/USDT","PYTH/USDT","BLUR/USDT","CHZ/USDT","ENJ/USDT","GALA/USDT","FTM/USDT","THETA/USDT",
]

ALL_PAIRS = FOREX_PAIRS + CRYPTO_PAIRS

# Qo'shimcha alias lar - bular ham tanilsin
PAIR_ALIASES = {
    "XAUUSD": "XAU/USD", "XAGUSD": "XAG/USD",
    "GOLD": "XAU/USD", "SILVER": "XAG/USD",
    "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY", "USDCHF": "USD/CHF",
    "USDCAD": "USD/CAD", "AUDUSD": "AUD/USD",
    "NZDUSD": "NZD/USD", "EURGBP": "EUR/GBP",
    "EURJPY": "EUR/JPY", "GBPJPY": "GBP/JPY",
    "BTCUSDT": "BTC/USDT", "ETHUSDT": "ETH/USDT",
    "BNBUSDT": "BNB/USDT", "SOLUSDT": "SOL/USDT",
    "XRPUSDT": "XRP/USDT", "ADAUSDT": "ADA/USDT",
    "DOGEUSDT": "DOGE/USDT",
}

STRATEGIES = {
    "auto":     "Avtomatik (eng yaxshi strategiyani tanlaydi)",
    "trend":    "Trend Following (EMA 20/50/200)",
    "rsi":      "RSI Divergence",
    "sr":       "Support & Resistance",
    "breakout": "Breakout Trading",
    "fib":      "Fibonacci Retracement",
    "macd":     "MACD Signal",
    "bb":       "Bollinger Bands",
    "pa":       "Price Action (Pin bar, Engulfing, Doji)",
    "smc":      "Smart Money Concept (Order blocks, FVG)",
    "scalp":    "Scalping (5-15 daqiqa)",
}

FREE_STRATEGIES = ["auto", "trend", "sr", "pa"]
PREMIUM_STRATEGIES = list(STRATEGIES.keys())

PAIR_LIST_TEXT = (
    "Forex (" + str(len(FOREX_PAIRS)) + " ta) va Crypto (" +
    str(len(CRYPTO_PAIRS)) + " ta) juftliklarni taniy olaman.\n\n"
    "Chart screenshotini yuboring!"
)

def _gemini(prompt, image_b64=None):
    url = GEMINI_URL + "?key=" + GEMINI_API_KEY
    parts = []
    if image_b64:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_b64}})
    parts.append({"text": prompt})
    body = json.dumps({
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1000}
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=45) as r:
        res = json.loads(r.read().decode())
    return res["candidates"][0]["content"]["parts"][0]["text"]

def _find_pair(text):
    """Matn ichidan juftlikni topish"""
    text_up = text.strip().upper().replace(" ", "").replace("-", "")

    # 1. To'g'ridan alias dan qidirish
    for alias, pair in PAIR_ALIASES.items():
        if alias in text_up:
            return pair

    # 2. Barcha pairlardan qidirish (slash bilan)
    for pair in ALL_PAIRS:
        if pair.upper() in text_up:
            return pair

    # 3. Slash siz qidirish
    for pair in ALL_PAIRS:
        noslash = pair.replace("/", "")
        if noslash in text_up:
            return pair

    # 4. Birinchi so'z bilan qidirish
    first = text_up.split()[0] if text_up.split() else ""
    for pair in ALL_PAIRS:
        if pair.split("/")[0] == first:
            return pair

    return None

async def detect_pair(image_bytes):
    """Rasmdan juftlikni aniqlash"""
    b64 = base64.b64encode(image_bytes).decode()

    prompt = (
        "Bu trading chart screenshotida qaysi instrument (juftlik) ko'rsatilgan?\n"
        "Chartning yuqori chap burchagiga, sarlavhasiga qarab aniqla.\n"
        "Masalan: XAUUSD, EURUSD, BTCUSDT, GBPUSD, XAU/USD kabi.\n"
        "Faqat instrument nomini yoz, boshqa hech narsa yozma.\n"
        "Agar ko'ra olmasang: UNKNOWN"
    )

    try:
        text = await asyncio.to_thread(_gemini, prompt, b64)
        pair = _find_pair(text)
        if pair:
            return pair
    except Exception as e:
        print("Pair detect xato:", e)

    return "UNKNOWN"

def _strategy_prompt(key):
    prompts = {
        "auto":     "Eng mos strategiyani o'zing tanlaysan.",
        "trend":    "EMA 20, 50, 200 asosida trend yo'nalishini aniqlaysan.",
        "rsi":      "RSI divergence topasan. 30 dan past oversold, 70 dan yuqori overbought.",
        "sr":       "Kuchli support va resistance darajalaridan bounce ni kutasan.",
        "breakout": "Konsolidatsiya zonasidan breakout yo'nalishida signal beryasan.",
        "fib":      "Fibonacci 0.382, 0.5, 0.618 darajalaridan foydalanasan.",
        "macd":     "MACD liniyasi kesishuviga va histogrammaga qaraysan.",
        "bb":       "Bollinger Bands squeeze va breakout signallarini topasan.",
        "pa":       "Pin Bar, Engulfing, Doji, Hammer candlestick patternlarini topasan.",
        "smc":      "Order Block, Fair Value Gap, Liquidity Sweep, BOS, CHOCHni topasan.",
        "scalp":    "5-15 daqiqalik qisqa muddatli kirish nuqtalarini topasan.",
    }
    return prompts.get(key, "")

async def analyze(image_bytes, balance, pair, strategy_key="auto"):
    b64 = base64.b64encode(image_bytes).decode()

    risk_pct = (
        1.0 if balance <= 10 else
        1.5 if balance <= 50 else
        2.0 if balance <= 200 else 2.5
    )
    risk_amt = round(balance * risk_pct / 100, 2)
    strategy_name = STRATEGIES.get(strategy_key, "Avtomatik")
    strat_prompt = _strategy_prompt(strategy_key)

    prompt = (
        "Sen professional Forex va Crypto trading analistisan.\n"
        "Strategiya: " + strategy_name + "\n"
        + strat_prompt + "\n\n"
        "Juftlik: " + pair + "\n"
        "Balans: $" + str(balance) + "\n"
        "Risk: " + str(risk_pct) + "% = $" + str(risk_amt) + "\n\n"
        "Chartni chuqur tahlil qil.\n"
        "FAQAT quyidagi JSON formatida javob ber, boshqa hech narsa yozma:\n"
        "{\n"
        '  "signal": "BUY",\n'
        '  "pair": "' + pair + '",\n'
        '  "timeframe": "M5",\n'
        '  "entry": 5169.00,\n'
        '  "sl": 5150.00,\n'
        '  "tp": 5210.00,\n'
        '  "rr_ratio": "1:2.1",\n'
        '  "strategy": "' + strategy_name + '",\n'
        '  "confidence": "HIGH",\n'
        '  "reason": "Sabab ozbekcha 2-3 jumla",\n'
        '  "risk_amount": ' + str(risk_amt) + ',\n'
        '  "lot_suggestion": 0.01,\n'
        '  "warning": null\n'
        "}\n\n"
        "signal: BUY, SELL yoki WAIT\n"
        "confidence: HIGH, MEDIUM yoki LOW\n"
        "Agar aniq signal bo'lmasa: signal=WAIT\n"
        "MUHIM: Faqat sof JSON, hech qanday ``` belgisi yo'q!"
    )

    try:
        text = await asyncio.to_thread(_gemini, prompt, b64)
        text = re.sub(r"```json|```", "", text).strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            text = m.group()
        data = json.loads(text)
        data["balance"] = balance
        data["risk_percent"] = risk_pct
        data["risk_amount"] = risk_amt
        if not data.get("pair"):
            data["pair"] = pair
        return data
    except Exception as e:
        print("Tahlil xato:", e)
        return {
            "signal": "WAIT",
            "pair": pair,
            "timeframe": "N/A",
            "entry": 0, "sl": 0, "tp": 0,
            "rr_ratio": "N/A",
            "strategy": strategy_name,
            "confidence": "LOW",
            "reason": "Gemini API bilan bog'lanishda muammo. Internet yoki API keyni tekshiring.",
            "risk_amount": risk_amt,
            "lot_suggestion": 0.01,
            "warning": "Qayta urinib ko'ring",
            "balance": balance,
            "risk_percent": risk_pct,
        }

def format_signal(data):
    sig = data.get("signal", "WAIT")
    pair = data.get("pair", "N/A")
    tf = data.get("timeframe", "N/A")
    strategy = data.get("strategy", "N/A")
    entry = data.get("entry", 0)
    sl = data.get("sl", 0)
    tp = data.get("tp", 0)
    rr = data.get("rr_ratio", "N/A")
    conf = data.get("confidence", "LOW")
    reason = data.get("reason", "")
    warning = data.get("warning")
    balance = data.get("balance", 0)
    risk_amt = data.get("risk_amount", 0)
    risk_pct = data.get("risk_percent", 0)
    lot = data.get("lot_suggestion", 0.01)

    sig_emoji = {"BUY": "BUY", "SELL": "SELL", "WAIT": "KUTING"}.get(sig, sig)
    conf_text = {"HIGH": "YUQORI", "MEDIUM": "O'RTA", "LOW": "PAST"}.get(conf, conf)

    if sig == "WAIT":
        return (
            "Signal yo'q — Kuting\n\n"
            "Juftlik: " + pair + "\n"
            "Taymfreym: " + tf + "\n"
            "Strategiya: " + strategy + "\n\n"
            "Sabab:\n" + reason + "\n\n"
            + ("Ogohlantirish: " + warning if warning else "Bozor noaniq. Sabr qiling.")
        )

    lines = [
        "--- " + sig_emoji + " SIGNAL ---",
        "",
        "Juftlik:     " + pair,
        "Taymfreym:   " + tf,
        "Strategiya:  " + strategy,
        "Ishonch:     " + conf_text,
        "",
        "Kirish:      " + str(entry),
        "Stop Loss:   " + str(sl),
        "Take Profit: " + str(tp),
        "Risk/Reward: " + str(rr),
        "",
        "Balans:  $" + str(round(balance, 2)),
        "Risk:    $" + str(risk_amt) + " (" + str(risk_pct) + "%)",
        "Lot:     " + str(lot),
        "",
        "Tahlil:",
        reason,
    ]
    if warning:
        lines += ["", "Ogohlantirish: " + warning]
    lines += ["", "--- TradeSignal Pro ---"]
    return "\n".join(lines)

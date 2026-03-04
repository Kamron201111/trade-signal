import re, base64, json, asyncio, urllib.request, os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

FOREX_PAIRS = [
    "EUR/USD","GBP/USD","USD/JPY","USD/CHF","USD/CAD","AUD/USD","NZD/USD",
    "EUR/GBP","EUR/JPY","GBP/JPY","EUR/AUD","EUR/CAD","EUR/CHF","GBP/AUD",
    "GBP/CAD","GBP/CHF","AUD/JPY","CAD/JPY","CHF/JPY","NZD/JPY","AUD/CAD",
    "AUD/CHF","AUD/NZD","CAD/CHF","EUR/NZD","GBP/NZD","NZD/CAD","NZD/CHF",
    "USD/NOK","USD/SEK","USD/DKK","USD/MXN","USD/ZAR","USD/TRY","USD/PLN",
    "USD/HUF","USD/CZK","EUR/PLN","EUR/NOK","EUR/SEK","XAU/USD","XAG/USD",
    "EUR/TRY","GBP/TRY","USD/SGD","USD/HKD","USD/CNH","USD/INR","EUR/HUF","EUR/CZK",
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

STRATEGIES = {
    "auto": "Avtomatik (eng yaxshi strategiyani tanlaydi)",
    "trend": "Trend Following (EMA 20/50/200)",
    "rsi": "RSI Divergence",
    "sr": "Support & Resistance",
    "breakout": "Breakout Trading",
    "fib": "Fibonacci Retracement",
    "macd": "MACD Signal",
    "bb": "Bollinger Bands",
    "pa": "Price Action (Pin bar, Engulfing, Doji)",
    "smc": "Smart Money Concept (Order blocks, FVG)",
    "scalp": "Scalping (5-15 daqiqa)",
}

FREE_STRATEGIES = ["auto", "trend", "sr", "pa"]
PREMIUM_STRATEGIES = list(STRATEGIES.keys())

PAIR_LIST_TEXT = (
    "📊 FOREX (" + str(len(FOREX_PAIRS)) + " ta) va 🪙 CRYPTO (" + str(len(CRYPTO_PAIRS)) + " ta) juftliklarni taniy olaman.\n\n"
    "Chart screenshotini yuboring - juftlikni o'zim aniqlayman!"
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
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=45) as r:
        res = json.loads(r.read().decode())
    return res["candidates"][0]["content"]["parts"][0]["text"]

async def detect_pair(image_bytes):
    b64 = base64.b64encode(image_bytes).decode()
    pairs_str = ", ".join(ALL_PAIRS)
    prompt = (
        "Bu trading chart screenshotida qaysi valyuta juftligi (currency pair) ko'rsatilgan? "
        "Chartning yuqori chap burchagiga, sarlavhasiga, belgisiga diqqat qil. "
        "Faqat juftlik nomini yoz. Ro'yxat: " + pairs_str + ". "
        "Agar topa olmasang: UNKNOWN"
    )
    try:
        text = await asyncio.to_thread(_gemini, prompt, b64)
        detected = text.strip().upper().replace(" ", "")
        for p in ALL_PAIRS:
            clean = p.replace("/", "")
            if clean in detected or p.upper() in detected:
                return p
        for p in ALL_PAIRS:
            if p.split("/")[0] in detected:
                return p
    except Exception as e:
        print("Pair detect xato:", e)
    return "UNKNOWN"

async def analyze(image_bytes, balance, pair, strategy_key="auto"):
    b64 = base64.b64encode(image_bytes).decode()

    risk_pct = 1.0 if balance <= 10 else (1.5 if balance <= 50 else (2.0 if balance <= 200 else 2.5))
    risk_amt = round(balance * risk_pct / 100, 2)

    strategy_name = STRATEGIES.get(strategy_key, "Avtomatik")
    strategy_prompt = ""
    if strategy_key == "auto":
        strategy_prompt = "Eng mos strategiyani o'zing tanlaysan: Trend Following, RSI, Support/Resistance, Price Action, MACD, Fibonacci, Bollinger Bands, SMC."
    elif strategy_key == "trend":
        strategy_prompt = "EMA 20, 50, 200 larga qarab trend yo'nalishini aniqlaysan. Trend bo'yicha signal beryasan."
    elif strategy_key == "rsi":
        strategy_prompt = "RSI ko'rsatkichi va narx orasidagi divergenceni topasan. RSI 30 dan past = oversold, 70 dan yuqori = overbought."
    elif strategy_key == "sr":
        strategy_prompt = "Eng kuchli support va resistance darajalarini topasan. Narxning S/R dan bounceini kutasan."
    elif strategy_key == "breakout":
        strategy_prompt = "Konsolidatsiya zonasini topasan va breakout bo'lgan yo'nalishda signal beryasan."
    elif strategy_key == "fib":
        strategy_prompt = "Fibonacci retracement darajalarini (0.236, 0.382, 0.5, 0.618, 0.786) ishlatasan."
    elif strategy_key == "macd":
        strategy_prompt = "MACD liniyasi va signal liniyasi kesishuviga, histogrammaga qaraysan."
    elif strategy_key == "bb":
        strategy_prompt = "Bollinger Bands squeezeni topasan. Narx yuqori banddan chiqsa SELL, pastdan chiqsa BUY."
    elif strategy_key == "pa":
        strategy_prompt = "Candlestick patternlarni (Pin Bar, Engulfing, Doji, Hammer, Shooting Star) topasan."
    elif strategy_key == "smc":
        strategy_prompt = "Smart Money Concept: Order Block, Fair Value Gap, Liquidity Sweep, BOS, CHOCHni topasan."
    elif strategy_key == "scalp":
        strategy_prompt = "Scalping: Qisqa muddatli (5-15 daqiqa) kirish nuqtalarini topasan. Kichik SL, tez profit."

    prompt = (
        "Sen professional Forex va Crypto trading analistisan. "
        "Strategiya: " + strategy_name + ". " + strategy_prompt + "\n\n"
        "Juftlik: " + pair + "\n"
        "Balans: $" + str(balance) + "\n"
        "Risk: " + str(risk_pct) + "% = $" + str(risk_amt) + "\n\n"
        "Chartni chuqur tahlil qil. FAQAT quyidagi JSON formatida javob ber, boshqa hech narsa yozma:\n"
        '{"signal":"BUY","pair":"' + pair + '","timeframe":"M5","entry":1.1622,"sl":1.1580,"tp":1.1700,'
        '"rr_ratio":"1:2.0","strategy":"Trend Following","confidence":"HIGH",'
        '"reason":"Sabab o\'zbek tilida 2-3 jumlada","risk_amount":' + str(risk_amt) + ','
        '"lot_suggestion":0.01,"warning":null}\n\n'
        "signal: BUY, SELL yoki WAIT\n"
        "confidence: HIGH, MEDIUM yoki LOW\n"
        "Agar signal aniq bo'lmasa WAIT qo'y.\n"
        "MUHIM: Faqat sof JSON, hech qanday ``` yoki boshqa belgi yo'q."
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
        if "pair" not in data or not data["pair"]:
            data["pair"] = pair
        return data
    except Exception as e:
        print("Tahlil xato:", e)
        return {
            "signal": "WAIT",
            "pair": pair,
            "timeframe": "N/A",
            "entry": 0,
            "sl": 0,
            "tp": 0,
            "rr_ratio": "N/A",
            "strategy": strategy_name,
            "confidence": "LOW",
            "reason": "Chart tahlilida texnik muammo yuz berdi. Iltimos, chartda indikatorlar ko'rinib turgan aniq screenshot yuboring.",
            "risk_amount": risk_amt,
            "lot_suggestion": 0.01,
            "warning": "Qayta screenshot yuboring",
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

    sig_emoji = {"BUY": "🟢", "SELL": "🔴", "WAIT": "⏳"}.get(sig, "❓")
    conf_emoji = {"HIGH": "🔥", "MEDIUM": "⚡", "LOW": "⚠️"}.get(conf, "")

    if sig == "WAIT":
        return (
            "⏳ SIGNAL YO'Q — KUTING\n\n"
            "📊 Juftlik: " + pair + "\n"
            "📐 Strategiya: " + strategy + "\n\n"
            "📝 Sabab:\n" + reason + "\n\n"
            + ("⚠️ " + warning if warning else "Bozor noaniq. Sabr qiling.")
        )

    lines = [
        sig_emoji + " " + sig + " SIGNAL " + conf_emoji,
        "",
        "━━━━━━━━━━━━━━━━━━━",
        "📊 Juftlik:     " + pair,
        "⏱ Taymfreym:  " + tf,
        "📐 Strategiya: " + strategy,
        "━━━━━━━━━━━━━━━━━━━",
        "💰 Kirish:      " + str(entry),
        "🛑 Stop Loss:   " + str(sl),
        "🎯 Take Profit: " + str(tp),
        "📈 Risk/Reward: " + str(rr),
        "━━━━━━━━━━━━━━━━━━━",
        "💼 Balans:  $" + str(round(balance, 2)),
        "⚠️ Risk:    $" + str(risk_amt) + " (" + str(risk_pct) + "%)",
        "📦 Lot:     " + str(lot),
        "━━━━━━━━━━━━━━━━━━━",
        "📝 Tahlil:",
        reason,
    ]
    if warning:
        lines += ["", "⚠️ " + warning]
    lines += ["", "━━━━━━━━━━━━━━━━━━━", "⚡ TradeSignal Pro"]
    return "\n".join(lines)

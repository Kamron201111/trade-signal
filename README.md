# 📈 TradeSignal Pro Bot

Professional Forex & Crypto trading signal Telegram boti.

## ✨ Xususiyatlar

- ✅ **100 ta juftlik** — 50 Forex + 50 Crypto
- ✅ **10 ta strategiya** — EMA, RSI, Fibonacci, SMC va boshqalar
- ✅ **AI tahlil** — Claude AI orqali chart tahlili
- ✅ **Risk menejment** — Balansga qarab SL/TP hisoblash
- ✅ **Kunlik limit** — Bepul: 3 ta signal/kun
- ✅ **Premium obuna** — Haftalik / Oylik / 3 Oylik
- ✅ **Admin panel** — To'lovlarni tasdiqlash, narxlarni boshqarish

---

## 🚀 Deploy qilish (BEPUL)

### Variant 1: Railway.app (tavsiya etiladi)

1. [railway.app](https://railway.app) ga kiring → GitHub bilan login
2. **New Project** → **Deploy from GitHub repo**
3. Reponi tanlang
4. **Variables** bo'limiga o'ting va qo'shing:
   ```
   BOT_TOKEN = your_token
   ADMIN_IDS = your_telegram_id  
   ANTHROPIC_API_KEY = your_anthropic_key
   ```
5. Deploy tugmasini bosing ✅

### Variant 2: Render.com (bepul)

1. [render.com](https://render.com) → GitHub bilan login
2. **New** → **Web Service** → reponi tanlang
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`
4. Environment variables qo'shing (yuqoridagi kabi)
5. **Create Web Service** ✅

---

## ⚙️ Lokal ishga tushirish

```bash
# 1. Klonlash
git clone https://github.com/yourusername/tradesignal-bot.git
cd tradesignal-bot

# 2. .env fayl yaratish
cp .env.example .env
# .env faylni oching va tokenlarni kiriting

# 3. Paketlarni o'rnatish
pip install -r requirements.txt

# 4. Botni ishga tushirish
python bot.py
```

---

## 🔑 Kerakli tokenlar

| Token | Qayerdan olish |
|-------|---------------|
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) ga `/newbot` yuboring |
| `ADMIN_IDS` | [@userinfobot](https://t.me/userinfobot) ga `/start` yuboring |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |

---

## 📂 Fayl tuzilishi

```
trading_bot/
├── bot.py              # Asosiy bot fayli
├── config.py           # Sozlamalar
├── requirements.txt    # Paketlar
├── .env.example        # Token namunasi
├── handlers/
│   ├── start.py        # Ro'yxatdan o'tish
│   ├── market.py       # Tahlil handleri
│   ├── premium.py      # Premium obuna
│   └── admin.py        # Admin panel
└── utils/
    ├── database.py     # SQLite database
    └── analyzer.py     # AI tahlil engine
```

---

## 👑 Admin buyruqlari

```
/admin              — Admin panelni ochish
/setprice weekly 7  — Haftalik narxni $7 ga o'zgartirish
/setpayment 8600 1234 5678 9012|Ism Familiya|Izoh
/givepremium 123456789 monthly  — Qo'lda premium berish
```

---

## 📊 Tariflar (admin tomonidan o'zgartiriladi)

| Tarif | Narx |
|-------|------|
| 1 Haftalik | $5 |
| 1 Oylik | $15 |
| 3 Oylik | $35 |

---

## ⚠️ Muhim eslatma

Bu bot faqat **ta'limiy maqsad**da ishlatiladi. Hech qanday moliyaviy maslahat emas. Savdo qilishda ehtiyot bo'ling!

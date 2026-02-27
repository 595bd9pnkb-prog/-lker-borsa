import os
import asyncio
import json
from telegram import Bot
from tradingview_ta import TA_Handler, Interval

# --- AYARLAR ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
DB_FILE = "performans.json"

def get_vix_status():
    try:
        vix = TA_Handler(symbol="VIX", screener="cfd", exchange="CBOE", interval=Interval.INTERVAL_1_DAY)
        v = vix.get_analysis().indicators['close']
        emoji = "🟢" if v < 20 else "🟡" if v < 25 else "🔴"
        return f"{emoji} *VIX (Korku Endeksi): {v:.2f}*\n"
    except: return ""

def performans_hesapla(yeni_fiyatlar):
    """Dünkü hisselerin bugünkü kâr/zarar durumunu hesaplar."""
    if not os.path.exists(DB_FILE):
        return "📊 _İlk çalışma: Henüz karşılaştırılacak dünkü veri yok._\n\n"
    
    with open(DB_FILE, "r") as f:
        eski_veriler = json.load(f)
    
    rapor = "📈 *Dünkü Sinyallerin Performansı:*\n"
    for sembol, eski_fiyat in eski_veriler.items():
        if sembol in yeni_fiyatlar:
            guncel_fiyat = yeni_fiyatlar[sembol]
            degisim = ((guncel_fiyat - eski_fiyat) / eski_fiyat) * 100
            emoji = "🚀" if degisim > 0 else "📉"
            rapor += f"{emoji} {sembol}: %{degisim:+.2f}\n"
    return rapor + "\n"

def piyasa_avcisi():
    dev_liste = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST", "AMD",
        "NFLX", "PLTR", "UBER", "COIN", "SHOP", "SNOW", "JPM", "V", "MA", "DIS"
    ]
    firsatlar = []
    tum_fiyatlar = {} # Performans takibi için tüm güncel fiyatlar

    for sembol in dev_liste:
        try:
            h = TA_Handler(
                symbol=sembol, screener="america",
                exchange="NASDAQ" if sembol not in ["JPM", "V", "MA", "DIS"] else "NYSE",
                interval=Interval.INTERVAL_4_HOURS
            )
            analiz = h.get_analysis()
            fiyat = analiz.indicators['close']
            tum_fiyatlar[sembol] = fiyat
            
            if analiz.summary['RECOMMENDATION'] == "STRONG_BUY" and analiz.indicators['RSI'] < 75:
                firsatlar.append({"sembol": sembol, "skor": analiz.summary['BUY'], "rsi": analiz.indicators['RSI'], "fiyat": fiyat})
        except: continue
            
    return sorted(firsatlar, key=lambda x: x['skor'], reverse=True)[:10], tum_fiyatlar

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    
    vix = get_vix_status()
    firsatlar, guncel_fiyatlar = piyasa_avcisi()
    performans_raporu = performans_hesapla(guncel_fiyatlar)
    
    # Yeni fiyatları bir sonraki gün için kaydet
    with open(DB_FILE, "w") as f:
        json.dump(guncel_fiyatlar, f)
    
    mesaj = "🚀 *WALL STREET AVCI RAPORU* 🚀\n\n"
    mesaj += performans_raporu
    mesaj += "----------------------------------\n"
    mesaj += f"{vix}\n"
    mesaj += "*Günün En Güçlü Sinyalleri:*\n"
    
    if not firsatlar:
        mesaj += "⚠️ Uygun fırsat bulunamadı."
    else:
        for f in firsatlar:
            mesaj += f"💎 *{f['sembol']}* | `${f['fiyat']:.2f}`\n   Güven: `{f['skor']}/26` | RSI: {f['rsi']:.1f}\n"

    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=mesaj, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())



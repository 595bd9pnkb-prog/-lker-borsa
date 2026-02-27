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
        return f"{emoji} *VIX (Korku): {v:.2f}*\n"
    except: return ""

def piyasa_avcisi():
    dev_liste = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO", "COST", "AMD",
        "NFLX", "PLTR", "UBER", "COIN", "SHOP", "SNOW", "JPM", "V", "MA", "DIS", "ONDS", "RKLB", "IREN"
    ]
    firsatlar = []
    tum_fiyatlar = {}

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
            
            # KRİTER: Strong Buy ve Makul RSI
            if analiz.summary['RECOMMENDATION'] == "STRONG_BUY" and analiz.indicators['RSI'] < 70:
                # STRATEJİ HESAPLAMA:
                # Stop Loss: %3 altı | Kar Al: %7 üstü (Muhafazakar Swing Trade)
                stop_loss = fiyat * 0.97
                kar_al = fiyat * 1.07
                
                firsatlar.append({
                    "sembol": sembol,
                    "fiyat": fiyat,
                    "sl": stop_loss,
                    "tp": kar_al,
                    "skor": analiz.summary['BUY']
                })
        except: continue
            
    return sorted(firsatlar, key=lambda x: x['skor'], reverse=True)[:10], tum_fiyatlar

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    
    vix = get_vix_status()
    firsatlar, guncel_fiyatlar = piyasa_avcisi()
    
    # Yeni fiyatları kaydet
    with open(DB_FILE, "w") as f:
        json.dump(guncel_fiyatlar, f)
    
    mesaj = "🚀 *STRATEJİK ALIM SİNYALLERİ* 🚀\n"
    mesaj += f"{vix}\n"
    
    if not firsatlar:
        mesaj += "⚠️ Uygun kriterde fırsat bulunamadı."
    else:
        for f in firsatlar:
            mesaj += f"💎 *{f['sembol']}*\n"
            mesaj += f"   📥 Giriş: `${f['fiyat']:.2f}`\n"
            mesaj += f"   🎯 Hedef (TP): `${f['tp']:.2f}` (+%7)\n"
            mesaj += f"   🛡️ Durdur (SL): `${f['sl']:.2f}` (-%3)\n"
            mesaj += f"   📊 Güven: `{f['skor']}/26` Analiz Onayı\n\n"

    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=mesaj, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())




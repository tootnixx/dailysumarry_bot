import yfinance as yf
import pandas as pd
import requests
import os
import time

# Konfigurasi dari GitHub Secrets
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# Daftar Saham Gabungan (Bluechip + Aktif + Small Cap Potensial)
watchlist = [
    "BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK", "TLKM.JK", "ASII.JK", "UNTR.JK",
    "ADRO.JK", "ITMG.JK", "PTBA.JK", "MEDC.JK", "ENRG.JK", "MBMA.JK", "NCKL.JK", "TINS.JK", "ANTM.JK",
    "GOTO.JK", "BUKA.JK", "EMTK.JK", "BELI.JK", "UNVR.JK", "ICBP.JK", "AMRT.JK",
    "BREN.JK", "TPIA.JK", "BRPT.JK", "AMMN.JK", "JSMR.JK", "PGE.JK",
    "BRIS.JK", "ARTO.JK", "BBYB.JK", "KPIG.JK", "MSIN.JK", "FILM.JK", "SMLE.JK",
    "DOOH.JK", "BDKR.JK", "STRK.JK", "CUAN.JK", "CHIP.JK", "WIDI.JK", "PTPS.JK",
    "BSDE.JK", "PWON.JK", "CTRA.JK", "PTPP.JK", "ADHI.JK", "PANI.JK"
]

def calculate_mfi(data, window=14):
    """Menghitung Money Flow Index (MFI)"""
    if len(data) < window + 1: return 50
    tp = (data['High'] + data['Low'] + data['Close']) / 3
    mf = tp * data['Volume']
    
    delta = tp.diff()
    pos_mf = mf.where(delta > 0, 0).rolling(window=window).sum()
    neg_mf = mf.where(delta < 0, 0).rolling(window=window).sum()
    
    mfi = 100 - (100 / (1 + pos_mf / neg_mf))
    return mfi.iloc[-1]

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Gagal kirim Telegram: {e}")

def main():
    hits = [] # Tempat menampung saham yang lolos filter
    
    print("Memulai Screening Sentinel...")
    
    for symbol in watchlist:
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1mo")
            
            if len(df) < 20: continue
            
            # Data Point
            last_close = df['Close'].iloc[-1]
            last_vol = df['Volume'].iloc[-1]
            avg_vol = df['Volume'].tail(20).mean()
            value_idr = last_close * last_vol * 100 # Estimasi nilai (asumsi 1 lot = 100 lembar)
            mfi_now = calculate_mfi(df)
            ma20 = df['Close'].rolling(window=20).mean().iloc[-1]

            # KRITERIA SENTINEL (Small-Cap & Big-Cap)
            # 1. Nilai transaksi > 1 Miliar (Liquidity Filter)
            # 2. Volume > 1.5x rata-rata (Money Flow Spike)
            # 3. MFI > 50 (Strong Accumulation)
            # 4. Harga di atas MA20 (Uptrend)
            
            if value_idr > 1_000_000_000 and last_vol > (1.5 * avg_vol) and mfi_now > 50 and last_close > ma20:
                hits.append({
                    'symbol': symbol,
                    'price': last_close,
                    'mfi': mfi_now,
                    'val': value_idr
                })
            
            time.sleep(0.5) # Jeda tipis agar tidak kena limit API
            
        except Exception as e:
            print(f"Skip {symbol} karena error: {e}")

    # --- MEMBUAT DAILY SUMMARY ---
    if hits:
        summary_msg = "📋 **DAILY MONEY FLOW SUMMARY** 📋\n"
        summary_msg += "------------------------------------------\n"
        summary_msg += "Saham dengan akumulasi besar hari ini:\n\n"
        
        for stock in hits:
            summary_msg += f"🔹 *{stock['symbol']}*\n"
            summary_msg += f"   Price: {stock['price']:.0f} | MFI: {stock['mfi']:.1f}\n"
            summary_msg += f"   Value: Rp{stock['val']/1e9:.1f} Miliar\n\n"
            
        summary_msg += "📢 *Disclaimer:* Analisa bot ini hanya referensi. Selalu cek kembali bid/offer sebelum entry."
        send_telegram_msg(summary_msg)
    else:
        send_telegram_msg("📭 **Daily Summary:** Tidak ada saham yang memenuhi kriteria Sentinel hari ini.")

if __name__ == "__main__":
    main()

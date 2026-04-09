import yfinance as yf
import pandas as pd
import streamlit as st
import time
from datetime import datetime, timezone, timedelta

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Personal Portfolio", layout="wide")
st.title("📊 Personal Live Portfolio Dashboard")

# --- YATIRIM PORTFÖYÜ ---
portfolio = {
    'GRID': {'Quantity': 5.190821455, 'Cost': 163.96},
    'GC=F': {'Quantity': 13.15, 'Cost': 1354 / 13.15}
}

# Türkiye Saat Dilimi (UTC+3)
tz_TR = timezone(timedelta(hours=3))

# --- VERİ ÇEKME FONKSİYONU (60 saniye önbellek ban yemeyi önler) ---
@st.cache_data(ttl=60)
def fetch_portfolio_data():
    results = []
    errors = [] 
    
    for ticker, details in portfolio.items():
        try:
            stock = yf.Ticker(ticker)
            price_data = None
            
            # 1. AŞAMA: Canlı Tahta Fiyatı (En hızlı ve saniyesinde güncel yöntem)
            try:
                price_data = stock.fast_info.last_price
            except Exception:
                pass
            
            # 2. AŞAMA: 1 Dakikalık Canlı Grafik (1. Aşama takılırsa devreye girer)
            if price_data is None or pd.isna(price_data):
                intra_data = stock.history(period="1d", interval="1m")
                if not intra_data.empty:
                    valid_intra = intra_data['Close'].dropna()
                    if not valid_intra.empty:
                        price_data = valid_intra.iloc[-1]
            
            # 3. AŞAMA: Günlük Kapanış (Piyasa kapalıysa veya hafta sonuysa devreye girer)
            if price_data is None or pd.isna(price_data):
                hist_data = stock.history(period="5d")
                if not hist_data.empty:
                    valid_hist = hist_data['Close'].dropna()
                    if not valid_hist.empty:
                        price_data = valid_hist.iloc[-1]
            
            # Eğer 3 aşamada da fiyat bulunamazsa uyarı ver ve sıradakine geç
            if price_data is None or pd.isna(price_data):
                errors.append(f"⚠️ {ticker}: Güncel veya geçmiş geçerli bir fiyat verisi bulunamadı.")
                continue
            
            # --- HESAPLAMALAR ---
            # Altın ONS fiyatını grama çevirme
            current_price = price_data / 31.1035 if ticker == 'GC=F' else price_data
            
            quantity = details['Quantity']
            avg_cost = details['Cost']
            
            total_cost = quantity * avg_cost
            current_value = quantity * current_price
            
            pnl_amount = current_value - total_cost
            pnl_percentage = ((current_price - avg_cost) / avg_cost) * 100

            display_name = "Physical Gold (Grams)" if ticker == 'GC=F' else ticker

            results.append({
                'Asset': display_name,
                'Quantity': float(quantity),
                'Avg. Cost': float(avg_cost),
                'Current Price': float(current_price),
                'Total Cost ($)': float(total_cost),
                'Current Value ($)': float(current_value),
                'P/L (Amount)': float(pnl_amount),
                'P/L (%)': float(pnl_percentage)
            })
            
        except Exception as e:
            errors.append(f"❌ {ticker} için teknik hata: {str(e)}")
            continue
            
    return results, errors

# --- ANA PROGRAM ---
results, errors = fetch_portfolio_data()

# Varsa arka plan hatalarını ekranda göster
if len(errors) > 0:
    for error in errors:
        st.error(error)

# Veriler çekildiyse tabloyu ve paneli çiz
if len(results) > 0:
    df = pd.DataFrame(results)
    
    # Kar/Zarar renklendirmesi
    def color_negative_red(val):
        color = 'red' if val < 0 else 'green'
        return f'color: {color}'

    try:
        styled_df = df.style.map(color_negative_red, subset=['P/L (Amount)', 'P/L (%)']).format({
            'Quantity': '{:.4f}',
            'Avg. Cost': '{:.2f}',
            'Current Price': '{:.2f}',
            'Total Cost ($)': '{:.2f}',
            'Current Value ($)': '{:.2f}',
            'P/L (Amount)': '{:.2f}',
            'P/L (%)': '{:.2f}%'
        })
    except AttributeError:
        # Eski Pandas sürümleri için uyumluluk
        styled_df = df.style.applymap(color_negative_red, subset=['P/L (Amount)', 'P/L (%)']).format({
            'Quantity': '{:.4f}',
            'Avg. Cost': '{:.2f}',
            'Current Price': '{:.2f}',
            'Total Cost ($)': '{:.2f}',
            'Current Value ($)': '{:.2f}',
            'P/L (Amount)': '{:.2f}',
            'P/L (%)': '{:.2f}%'
        })

    st.dataframe(styled_df, use_container_width=True)
    
    # Özet Metrikleri Hesaplama
    total_invested = df['Total Cost ($)'].sum()
    total_current = df['Current Value ($)'].sum()
    total_pnl = df['P/L (Amount)'].sum()
    
    st.markdown("---")
    st.markdown("### 📈 Portfolio Summary")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested (Ana Para)", f"${total_invested:,.2f}")
    col2.metric("Current Value (Güncel Değer)", f"${total_current:,.2f}")
    col3.metric("Total P/L (Toplam Kar/Zarar)", f"${total_pnl:,.2f}")
    
    # Güncelleme Saati
    guncel_saat = datetime.now(tz_TR).strftime('%H:%M:%S')
    st.caption(f"Last sync: {guncel_saat} (Source: Yahoo Finance)")
else:
    st.warning("Ekranda listelenecek geçerli bir veri bulunamadı.")

# --- CANLI GÜNCELLEME DÖNGÜSÜ ---
# Uygulamayı 60 saniye duraklatır ve sonra tamamen baştan okur (Yeniler)
time.sleep(60)
st.rerun()

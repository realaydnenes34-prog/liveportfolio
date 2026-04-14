import yfinance as yf
import pandas as pd
import streamlit as st
import time
from datetime import datetime, timezone, timedelta

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Personal Portfolio", layout="wide")
st.title("📊 Personal Live Portfolio Dashboard")

# --- YATIRIM PORTFÖYÜ (İŞLEM GEÇMİŞİ) ---
portfolio_transactions = {
    'GC=F': [
        {'Date': '2025-05-22', 'Quantity': 13.15, 'Total_Cost': 1354.0} # 13.15 gram için toplam ödenen
    ],
    'GRID': [
        {'Date': '2026-01-26', 'Quantity': 2.524859813, 'Total_Cost': 406.74},
        {'Date': '2026-02-05', 'Quantity': 1.200408824, 'Total_Cost': 199.99},
        {'Date': '2026-03-04', 'Quantity': 0.866493185, 'Total_Cost': 150.01},
        {'Date': '2026-04-07', 'Quantity': 0.599059633, 'Total_Cost': 100.37}
    ]
}
# Türkiye Saat Dilimi (UTC+3)
tz_TR = timezone(timedelta(hours=3))

@st.cache_data(ttl=60)
def fetch_portfolio_data(transactions_dict):
    results = []
    errors = [] 
    
    for ticker, txs in transactions_dict.items():
        try:
            # Önce bu hisse için kümülatif toplamları hesapla
            total_quantity = sum(tx['Quantity'] for tx in txs)
            total_cost_all_tx = sum(tx['Total_Cost'] for tx in txs)
            
            # Ortalama maliyeti bul
            avg_cost = total_cost_all_tx / total_quantity if total_quantity > 0 else 0
            
            # Fiyat Çekme İşlemleri (Senin yazdığın 3 aşamalı yapı aynen kalıyor)
            stock = yf.Ticker(ticker)
            price_data = None
            
            try:
                price_data = stock.fast_info.last_price
            except:
                pass
            
            if price_data is None or pd.isna(price_data):
                intra_data = stock.history(period="1d", interval="1m")
                if not intra_data.empty and not intra_data['Close'].dropna().empty:
                    price_data = intra_data['Close'].dropna().iloc[-1]
            
            if price_data is None or pd.isna(price_data):
                hist_data = stock.history(period="5d")
                if not hist_data.empty and not hist_data['Close'].dropna().empty:
                    price_data = hist_data['Close'].dropna().iloc[-1]
            
            if price_data is None or pd.isna(price_data):
                errors.append(f"⚠️ {ticker}: Fiyat bulunamadı.")
                continue
            
            # --- HESAPLAMALAR ---
            current_price = price_data / 31.1035 if ticker == 'GC=F' else price_data
            
            current_value = total_quantity * current_price
            pnl_amount = current_value - total_cost_all_tx
            pnl_percentage = ((current_value - total_cost_all_tx) / total_cost_all_tx) * 100 if total_cost_all_tx > 0 else 0

            display_name = "Physical Gold (Grams)" if ticker == 'GC=F' else ticker

            results.append({
                'Asset': display_name,
                'Quantity': float(total_quantity),
                'Avg. Cost': float(avg_cost), # İşlem ücretleri dahil gerçek ortalama
                'Current Price': float(current_price),
                'Total Cost ($)': float(total_cost_all_tx),
                'Current Value ($)': float(current_value),
                'P/L (Amount)': float(pnl_amount),
                'P/L (%)': float(pnl_percentage)
            })
            
        except Exception as e:
            errors.append(f"❌ {ticker} için teknik hata: {str(e)}")
            continue
            
    return results, errors

# --- ANA PROGRAM ---
results, errors = fetch_portfolio_data(portfolio_transactions)

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

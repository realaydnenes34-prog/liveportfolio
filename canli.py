import yfinance as yf
import pandas as pd
import streamlit as st
import time
import requests  # Tarayıcı kimliği için yeni eklendi
from datetime import datetime, timezone, timedelta

# Page configuration
st.set_page_config(page_title="Personal Portfolio", layout="wide")
st.title("📊 Personal Live Portfolio Dashboard")

# YOUR REAL INVESTMENTS
portfolio = {
    'GRID': {'Quantity': 5.190821455, 'Cost': 163.96},
    'GC=F': {'Quantity': 13.15, 'Cost': 1354 / 13.15}
}

# Türkiye Saat Dilimi (UTC+3) Ayarı
tz_TR = timezone(timedelta(hours=3))

@st.cache_data(ttl=60)
def fetch_portfolio_data():
    results = []
    
    # --- YENİ EKLENEN KISIM: Tarayıcı Kimliği Maskelemesi ---
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    
    for ticker, details in portfolio.items():
        try:
            # yfinance'in bu maskelenmiş oturumu kullanmasını sağlıyoruz
            stock = yf.Ticker(ticker, session=session)
            history_data = stock.history(period="5d")
            
            if history_data.empty:
                continue
                
            price_data = history_data['Close'].iloc[-1]
            
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
            continue
            
    return results

# Döngü yerine fonksiyonu çağırıyoruz
results = fetch_portfolio_data()

if len(results) > 0:
    df = pd.DataFrame(results)
    
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
    
    total_invested = df['Total Cost ($)'].sum()
    total_current = df['Current Value ($)'].sum()
    total_pnl = df['P/L (Amount)'].sum()
    
    st.markdown("---")
    st.markdown("### 📈 Portfolio Summary")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Invested (Ana Para)", f"${total_invested:,.2f}")
    col2.metric("Current Value (Güncel Değer)", f"${total_current:,.2f}")
    col3.metric("Total P/L (Toplam Kar/Zarar)", f"${total_pnl:,.2f}")
    
    guncel_saat = datetime.now(tz_TR).strftime('%H:%M:%S')
    st.caption(f"Last sync: {guncel_saat} (Source: Yahoo Finance)")
else:
    st.warning("Veriler şu an Yahoo Finance üzerinden çekilemiyor. Borsalar kapalı veya ağ bağlantısında kopukluk olabilir.")

# Sayfayı 60 saniyede bir otomatik olarak yeniden başlatır (Canlı görünüm sağlar)
time.sleep(60)
st.rerun()

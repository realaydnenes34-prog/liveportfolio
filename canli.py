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
import plotly.express as px
import numpy as np

# --- GEÇMİŞ PORTFÖY PERFORMANSI FONKSİYONU ---
@st.cache_data(ttl=3600)
def fetch_historical_chart_data(transactions_dict):
    # 1. Bütün işlemleri tek bir listede topla ve tarihe göre sırala
    all_tx = []
    for ticker, txs in transactions_dict.items():
        for tx in txs:
            all_tx.append({
                'Ticker': ticker,
                'Date': pd.to_datetime(tx['Date']).tz_localize(None),
                'Quantity': tx['Quantity'],
                'Total_Cost': tx['Total_Cost']
            })
            
    df_tx = pd.DataFrame(all_tx).sort_values('Date')
    if df_tx.empty: return pd.DataFrame()
    
    start_date_str = df_tx['Date'].min().strftime('%Y-%m-%d')
    
    # 2. En eski alımdan bugüne fiyat verilerini çek
    all_prices = {}
    for ticker in transactions_dict.keys():
        try:
            hist = yf.Ticker(ticker).history(start=start_date_str)
            if not hist.empty:
                hist.index = hist.index.tz_localize(None)
                # Altın için ONS -> Gram çevrimi
                if ticker == 'GC=F':
                    hist['Close'] = hist['Close'] / 31.1035
                all_prices[ticker] = hist['Close']
        except:
            continue
            
    if not all_prices: return pd.DataFrame()
    
    df_prices = pd.DataFrame(all_prices).ffill().dropna(how='all')
    
    # 3. Günlük Portföy Değeri ve Maliyet Hesaplama
    df_history = pd.DataFrame(index=df_prices.index)
    df_history['Total_Cost'] = 0.0
    df_history['Total_Value'] = 0.0
    
    for ticker in transactions_dict.keys():
        if ticker not in df_prices.columns: continue
        
        ticker_tx = df_tx[df_tx['Ticker'] == ticker]
        daily_qty = pd.Series(0.0, index=df_prices.index)
        daily_cost = pd.Series(0.0, index=df_prices.index)
        
        for _, row in ticker_tx.iterrows():
            mask = df_prices.index >= row['Date']
            daily_qty[mask] += row['Quantity']
            daily_cost[mask] += row['Total_Cost']
            
        df_history['Total_Value'] += daily_qty * df_prices[ticker]
        df_history['Total_Cost'] += daily_cost

    # 4. Yüzdelik Kar/Zarar (%)
    df_history['P/L (%)'] = np.where(
        df_history['Total_Cost'] > 0, 
        ((df_history['Total_Value'] - df_history['Total_Cost']) / df_history['Total_Cost']) * 100, 
        0
    )
    
    return df_history

# --- GRAFİĞİ EKRANA ÇİZME ---
st.markdown("---")
st.markdown("### 📈 Portfolio Growth Over Time (%)")

# Geçmiş veriyi hesapla
df_history = fetch_historical_chart_data(portfolio_transactions)

if not df_history.empty:
    fig = px.line(
        df_history, 
        x=df_history.index, 
        y='P/L (%)', 
        labels={'index': 'Tarih', 'P/L (%)': 'Net Kar / Zarar (%)'}
    )
    
    # Başabaş çizgisi
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Maliyet")
    
    # Son durum kârdaysa yeşil, zarardaysa kırmızı
    line_color = '#00C853' if df_history['P/L (%)'].iloc[-1] >= 0 else '#D50000'
    fig.update_traces(line_color=line_color, line_width=2)
    
    fig.update_layout(
        hovermode="x unified",
        xaxis_title="", 
        yaxis_title="Büyüme (%)",
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Geçmiş grafik verileri hazırlanıyor...")
# --- CANLI GÜNCELLEME DÖNGÜSÜ (ASENKRON) ---
from streamlit_autorefresh import st_autorefresh

# Ekranı dondurmadan arka planda her 60 saniyede bir (60000 milisaniye) verileri günceller
st_autorefresh(interval=60000, key="portfolio_update")

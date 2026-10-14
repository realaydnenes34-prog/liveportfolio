import yfinance as yf
import pandas as pd
import streamlit as st
from datetime import datetime, timezone, timedelta
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="Personal Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Türkiye Saat Dilimi (UTC+3)
tz_TR = timezone(timedelta(hours=3))

# --- YATIRIM PORTFÖYÜ (İŞLEM GEÇMİŞİ) ---
portfolio_transactions = {
    'GC=F': [
        {'Date': '2025-05-22', 'Quantity': 13.15, 'Total_Cost': 1354.0},
        {'Date': '2026-04-29', 'Quantity': -13.15, 'Total_Cost': -1354.0, 'Realized_Profit': 566.0} 
    ],
    'GRID': [
        {'Date': '2026-01-26', 'Quantity': 2.524859813, 'Total_Cost': 406.74},
        {'Date': '2026-02-05', 'Quantity': 1.200408824, 'Total_Cost': 199.99},
        {'Date': '2026-03-04', 'Quantity': 0.866493185, 'Total_Cost': 150.01},
        {'Date': '2026-03-31', 'Quantity': 0.0, 'Total_Cost': 0.0, 'Dividend': 0.37},
        {'Date': '2026-04-07', 'Quantity': 0.599059633, 'Total_Cost': 100.37},
        {'Date': '2026-05-15', 'Quantity': 2.084745762, 'Total_Cost': 400.02},
        {'Date': '2026-05-18', 'Quantity': -1.318426326, 'Total_Cost': -227.81, 'Realized_Profit': 20.68},
        {'Date': '2026-07-01', 'Quantity': 0.019026478, 'Total_Cost': 0.0, 'Dividend': 3.6},
        {'Date': '2026-08-11', 'Quantity': -1.6055168, 'Total_Cost': -276.53, 'Realized_Profit': 23.46}
    ],
    'ASELS.IS': [
        {'Date': '2026-07-08', 'Quantity': 2.0, 'Total_Cost': 16.17},
        {'Date': '2026-07-09', 'Quantity': 1.0, 'Total_Cost': 7.72}
    ]
}

# --- SIDEBAR (KONTROL PANELİ) ---
with st.sidebar:
    st.header("⚙️ Dashboard Ayarları")
    
    base_currency = st.radio(
        "Gösterim Para Birimi",
        options=["USD ($)", "TRY (₺)"],
        index=0,
        horizontal=True
    )
    curr_symbol = "$" if "USD" in base_currency else "₺"
    
    hide_closed = st.checkbox("Kapanan Pozisyonları Tablodan Gizle", value=False)
    
    benchmark_choice = st.selectbox(
        "Performans Kıyaslaması (Benchmark)",
        options=["Yok", "S&P 500 (^GSPC)", "NASDAQ 100 (^NDX)", "Altın Ons (GC=F)"]
    )
    
    st.markdown("---")
    auto_refresh = st.toggle("Otomatik Yenileme (60s)", value=True)
    if st.button("🔄 Verileri Şimdi Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if auto_refresh:
    st_autorefresh(interval=60000, key="portfolio_update")

# --- VERİ ÇEKME FONKSİYONU ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_portfolio_data(transactions_dict):
    results = []
    errors = []
    
    # Anlık USD/TRY kurunu çek
    try:
        usd_try_rate = float(yf.Ticker("USDTRY=X").fast_info.last_price)
        if pd.isna(usd_try_rate) or usd_try_rate <= 0:
            raise ValueError("Invalid FX")
    except Exception:
        try:
            fx_hist = yf.Ticker("USDTRY=X").history(period="5d")
            usd_try_rate = float(fx_hist['Close'].dropna().iloc[-1])
        except Exception:
            usd_try_rate = 46.85
            
    for ticker, txs in transactions_dict.items():
        try:
            total_quantity = sum(tx.get('Quantity', 0.0) for tx in txs)
            total_cost_all_tx = sum(tx.get('Total_Cost', 0.0) for tx in txs)
            realized_profit = sum(tx.get('Realized_Profit', 0.0) for tx in txs)
            dividends = sum(tx.get('Dividend', 0.0) for tx in txs)
            
            is_closed = abs(total_quantity) < 1e-6
            if is_closed:
                total_quantity = 0.0
                total_cost_all_tx = 0.0
            
            avg_cost = total_cost_all_tx / total_quantity if total_quantity > 0 else 0.0
            
            stock = yf.Ticker(ticker)
            price_data = None
            prev_close = None
            
            # Son 5 günlük veriden hem son fiyatı hem önceki kapanışı al
            hist_data = stock.history(period="5d")
            if not hist_data.empty and not hist_data['Close'].dropna().empty:
                clean_closes = hist_data['Close'].dropna()
                price_data = float(clean_closes.iloc[-1])
                prev_close = float(clean_closes.iloc[-2]) if len(clean_closes) > 1 else price_data
            
            # Eğer fast_info daha güncelse onu kullan
            try:
                fast_p = stock.fast_info.last_price
                if fast_p is not None and not pd.isna(fast_p):
                    price_data = float(fast_p)
            except Exception:
                pass
                
            if price_data is None or pd.isna(price_data):
                errors.append(f"⚠️ {ticker}: Fiyat bulunamadı.")
                continue
            
            if prev_close is None or pd.isna(prev_close):
                prev_close = price_data
                
            # --- DÖVİZ VE BİRİM ÇEVİRİCİ (USD BAZLI) ---
            if ticker == 'GC=F':
                current_price = price_data / 31.1035
                prev_price_usd = prev_close / 31.1035
                display_name = "🥇 Physical Gold (Grams)"
            elif ticker.endswith('.IS'):
                current_price = price_data / usd_try_rate
                prev_price_usd = prev_close / usd_try_rate
                display_name = f"🇹🇷 {ticker.replace('.IS', '')} (BIST)"
            else:
                current_price = price_data
                prev_price_usd = prev_close
                display_name = f"🌎 {ticker}"

            current_value = total_quantity * current_price
            pnl_amount = current_value - total_cost_all_tx
            pnl_percentage = (pnl_amount / total_cost_all_tx) * 100 if total_cost_all_tx > 0 else 0.0
            
            # Günlük değişim hesabı
            daily_return_pct = ((current_price - prev_price_usd) / prev_price_usd) * 100 if prev_price_usd > 0 else 0.0
            daily_pnl_usd = total_quantity * (current_price - prev_price_usd)

            results.append({
                'Ticker': ticker,
                'Asset': display_name,
                'Status': 'Kapalı' if is_closed else 'Açık',
                'Quantity': float(total_quantity),
                'Avg. Cost': float(avg_cost),
                'Current Price': float(current_price),
                'Daily Change (%)': float(daily_return_pct),
                'Daily P/L': float(daily_pnl_usd),
                'Total Cost': float(total_cost_all_tx),
                'Current Value': float(current_value),
                'Unrealized P/L': float(pnl_amount),
                'Unrealized P/L (%)': float(pnl_percentage),
                'Realized P/L': float(realized_profit),
                'Dividends': float(dividends),
                'Total Net Return': float(pnl_amount + realized_profit + dividends)
            })
            
        except Exception as e:
            errors.append(f"❌ {ticker} için teknik hata: {str(e)}")
            continue
            
    return results, errors, usd_try_rate

# --- GEÇMİŞ PORTFÖY HESAPLAMASI ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_historical_chart_data(transactions_dict, benchmark_ticker=None):
    all_tx = []
    for ticker, txs in transactions_dict.items():
        for tx in txs:
            all_tx.append({
                'Ticker': ticker,
                'Date': pd.to_datetime(tx['Date']).tz_localize(None),
                'Quantity': tx.get('Quantity', 0.0),
                'Total_Cost': tx.get('Total_Cost', 0.0),
                'Realized_Profit': tx.get('Realized_Profit', 0.0),
                'Dividend': tx.get('Dividend', 0.0)
            })
            
    df_tx = pd.DataFrame(all_tx).sort_values('Date')
    if df_tx.empty:
        return pd.DataFrame()
    
    start_date_str = df_tx['Date'].min().strftime('%Y-%m-%d')
    
    # Geçmiş USD/TRY Kuru
    try:
        usd_hist = yf.Ticker("USDTRY=X").history(start=start_date_str)['Close']
        usd_hist.index = pd.to_datetime(usd_hist.index).tz_localize(None).normalize()
        usd_hist = usd_hist[~usd_hist.index.duplicated(keep='last')]
    except Exception:
        usd_hist = None
    
    all_prices = {}
    for ticker in transactions_dict.keys():
        try:
            hist = yf.Ticker(ticker).history(start=start_date_str)
            if not hist.empty:
                hist.index = pd.to_datetime(hist.index).tz_localize(None).normalize()
                hist = hist[~hist.index.duplicated(keep='last')]
                
                if ticker == 'GC=F':
                    hist['Close'] = hist['Close'] / 31.1035
                elif ticker.endswith('.IS'):
                    if usd_hist is not None:
                        aligned_fx = usd_hist.reindex(hist.index).ffill().bfill()
                        hist['Close'] = hist['Close'] / aligned_fx
                    else:
                        hist['Close'] = hist['Close'] / 46.85
                        
                all_prices[ticker] = hist['Close']
        except Exception:
            continue
            
    if not all_prices:
        return pd.DataFrame()
    
    df_prices = pd.DataFrame(all_prices).sort_index().ffill().bfill().dropna(how='all')
    
    df_history = pd.DataFrame(index=df_prices.index)
    df_history['Active_Cost'] = 0.0
    df_history['Active_Value'] = 0.0
    df_history['Cum_Realized_PnL'] = 0.0
    df_history['Cum_Dividends'] = 0.0
    
    # Her varlık için gün gün miktar ve maliyet birikimi
    for ticker in transactions_dict.keys():
        if ticker not in df_prices.columns:
            continue
        
        ticker_tx = df_tx[df_tx['Ticker'] == ticker]
        daily_qty = pd.Series(0.0, index=df_prices.index)
        daily_cost = pd.Series(0.0, index=df_prices.index)
        
        for _, row in ticker_tx.iterrows():
            mask = df_prices.index >= row['Date']
            daily_qty[mask] += row['Quantity']
            daily_cost[mask] += row['Total_Cost']
            
        # Kapanan pozisyonlarda ufak küsürat hatalarını temizle
        daily_qty = daily_qty.apply(lambda x: 0.0 if abs(x) < 1e-6 else x)
        daily_cost = daily_cost.where(daily_qty > 0, 0.0)
            
        df_history['Active_Value'] += daily_qty * df_prices[ticker]
        df_history['Active_Cost'] += daily_cost

    # Realize Kâr ve Temettülerin Tarihsel Birikimi
    for _, row in df_tx.iterrows():
        mask = df_history.index >= row['Date']
        df_history.loc[mask, 'Cum_Realized_PnL'] += row['Realized_Profit']
        df_history.loc[mask, 'Cum_Dividends'] += row['Dividend']

    # Hesaplamalar
    df_history['Unrealized_PnL'] = df_history['Active_Value'] - df_history['Active_Cost']
    df_history['Total_Net_Profit'] = (
        df_history['Unrealized_PnL'] + 
        df_history['Cum_Realized_PnL'] + 
        df_history['Cum_Dividends']
    )
    
    # Açık Pozisyon P/L (%)
    df_history['Active_P/L (%)'] = np.where(
        df_history['Active_Cost'] > 0, 
        (df_history['Unrealized_PnL'] / df_history['Active_Cost']) * 100, 
        0.0
    )

    # Benchmark Verisi
    if benchmark_ticker:
        try:
            b_hist = yf.Ticker(benchmark_ticker).history(start=start_date_str)['Close']
            b_hist.index = pd.to_datetime(b_hist.index).tz_localize(None).normalize()
            b_hist = b_hist[~b_hist.index.duplicated(keep='last')]
            aligned_b = b_hist.reindex(df_history.index).ffill().bfill()
            first_val = aligned_b.iloc[0]
            if first_val > 0:
                df_history['Benchmark (%)'] = ((aligned_b - first_val) / first_val) * 100
        except Exception:
            pass

    return df_history

# --- ANA EKRAN BAŞLIĞI ---
col_title, col_fx = st.columns([3, 1])
with col_title:
    st.title("📊 Personal Live Portfolio Dashboard")
    
results, errors, usd_try_rate = fetch_portfolio_data(portfolio_transactions)
fx_multiplier = 1.0 if "USD" in base_currency else usd_try_rate

with col_fx:
    st.markdown("<div style='text-align: right; padding-top: 15px;'>", unsafe_allow_html=True)
    st.metric(label="Canlı USD / TRY Kuru", value=f"₺{usd_try_rate:.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

if errors:
    for error in errors:
        st.error(error)

if results:
    df = pd.DataFrame(results)
    
    # Para birimi dönüşümü (Eğer TRY seçildiyse parasal sütunları kurla çarp)
    money_cols = [
        'Avg. Cost', 'Current Price', 'Daily P/L', 'Total Cost', 
        'Current Value', 'Unrealized P/L', 'Realized P/L', 'Dividends', 'Total Net Return'
    ]
    for col in money_cols:
        df[col] = df[col] * fx_multiplier

    # --- BÖLÜM 1: PORTFÖY ÖZET KARTLARI (KPIs) ---
    total_invested = df['Total Cost'].sum()
    total_current = df['Current Value'].sum()
    total_unrealized_pnl = df['Unrealized P/L'].sum()
    total_unrealized_pct = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0.0
    
    total_daily_pnl = df['Daily P/L'].sum()
    prev_total_val = total_current - total_daily_pnl
    total_daily_pct = (total_daily_pnl / prev_total_val * 100) if prev_total_val > 0 else 0.0
    
    realized_pnl = df['Realized P/L'].sum()
    total_dividends = df['Dividends'].sum()
    all_time_net_profit = total_unrealized_pnl + realized_pnl + total_dividends

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Portföy Değeri", f"{curr_symbol}{total_current:,.2f}", f"{curr_symbol}{total_daily_pnl:+,.2f} ({total_daily_pct:+.2f}% Bugün)")
    k2.metric("Aktif Maliyet", f"{curr_symbol}{total_invested:,.2f}")
    k3.metric("Açık Kâr/Zarar", f"{curr_symbol}{total_unrealized_pnl:,.2f}", f"{total_unrealized_pct:+.2f}%")
    k4.metric("Realize Kâr (Satışlar)", f"{curr_symbol}{realized_pnl:,.2f}")
    k5.metric("Temettü Geliri", f"{curr_symbol}{total_dividends:,.2f}")
    k6.metric("Tüm Zamanlar Net Kâr", f"{curr_symbol}{all_time_net_profit:,.2f}", delta="Toplam Kazanç")
    
    guncel_saat = datetime.now(tz_TR).strftime('%H:%M:%S')
    st.caption(f"⏱️ Son Senkronizasyon: {guncel_saat} (Kaynak: Yahoo Finance)")
    st.markdown("---")

    # --- SEKMELİ GÖRÜNÜM ---
    tab1, tab2, tab3 = st.tabs(["💼 Varlıklar & Dağılım", "📈 Tarihsel Performans Analizi", "🧾 İşlem Geçmişi (Log)"])

    # ================= SEKME 1: VARLIKLAR VE PASTA GRAFİĞİ =================
    with tab1:
        df_display = df[df['Status'] == 'Açık'].copy() if hide_closed else df.copy()
        
        st.subheader("📋 Portföy Detay Tablosu")
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_order=[
                'Asset', 'Status', 'Quantity', 'Avg. Cost', 'Current Price', 
                'Daily Change (%)', 'Daily P/L', 'Total Cost', 'Current Value', 
                'Unrealized P/L', 'Unrealized P/L (%)', 'Realized P/L', 'Dividends', 'Total Net Return'
            ],
            column_config={
                'Asset': st.column_config.TextColumn("Varlık"),
                'Status': st.column_config.TextColumn("Durum"),
                'Quantity': st.column_config.NumberColumn("Adet / Gram", format="%.4f"),
                'Avg. Cost': st.column_config.NumberColumn(f"Ort. Maliyet ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Current Price': st.column_config.NumberColumn(f"Güncel Fiyat ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Daily Change (%)': st.column_config.NumberColumn("Günlük (%)", format="%+.2f%%"),
                'Daily P/L': st.column_config.NumberColumn(f"Günlük P/L ({curr_symbol})", format=f"{curr_symbol}%+.2f"),
                'Total Cost': st.column_config.NumberColumn(f"Aktif Maliyet ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Current Value': st.column_config.NumberColumn(f"Güncel Değer ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Unrealized P/L': st.column_config.NumberColumn(f"Açık P/L ({curr_symbol})", format=f"{curr_symbol}%+.2f"),
                'Unrealized P/L (%)': st.column_config.NumberColumn("Açık P/L (%)", format="%+.2f%%"),
                'Realized P/L': st.column_config.NumberColumn(f"Realize Kâr ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Dividends': st.column_config.NumberColumn(f"Temettü ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Total Net Return': st.column_config.NumberColumn(f"Toplam Net Kâr ({curr_symbol})", format=f"{curr_symbol}%+.2f"),
            }
        )

        st.markdown("---")
        col_pie, col_bar = st.columns(2)
        
        with col_pie:
            st.subheader("🥧 Aktif Varlık Dağılımı")
            df_pie = df[df['Current Value'] > 0]
            if not df_pie.empty:
                fig_pie = px.pie(
                    df_pie, 
                    values='Current Value', 
                    names='Asset',
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent+label',
                    hovertemplate=f"<b>%{{label}}</b><br>Değer: {curr_symbol}%{{value:,.2f}}<br>Oran: %{{percent}}"
                )
                fig_pie.update_layout(
                    showlegend=True,
                    margin=dict(t=20, b=20, l=10, r=10),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Açık pozisyon bulunmuyor.")

        with col_bar:
            st.subheader("📊 Varlık Bazlı Toplam Kazanç Katkısı")
            st.caption("Açık Kâr/Zarar + Realize Edilen Kâr + Temettüler dahil toplam katkı")
            fig_bar = px.bar(
                df,
                x='Asset',
                y='Total Net Return',
                text_auto='.2f',
                color='Total Net Return',
                color_continuous_scale=['#D50000', '#00C853']
            )
            fig_bar.update_layout(
                xaxis_title="",
                yaxis_title=f"Toplam Net Kâr ({curr_symbol})",
                coloraxis_showscale=False,
                margin=dict(t=20, b=20, l=10, r=10),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # ================= SEKME 2: TARİHSEL PERFORMANS =================
    with tab2:
        b_map = {
            "Yok": None,
            "S&P 500 (^GSPC)": "^GSPC",
            "NASDAQ 100 (^NDX)": "^NDX",
            "Altın Ons (GC=F)": "GC=F"
        }
        selected_b_ticker = b_map[benchmark_choice]
        df_history = fetch_historical_chart_data(portfolio_transactions, selected_b_ticker)

        if not df_history.empty:
            # Zaman Aralığı Filtresi
            time_filter = st.radio(
                "Zaman Aralığı",
                options=["1A", "3A", "6A", "YTD (Yılbaşı)", "TÜMÜ"],
                index=4,
                horizontal=True
            )
            
            end_dt = df_history.index.max()
            if time_filter == "1A":
                start_dt = end_dt - pd.DateOffset(months=1)
            elif time_filter == "3A":
                start_dt = end_dt - pd.DateOffset(months=3)
            elif time_filter == "6A":
                start_dt = end_dt - pd.DateOffset(months=6)
            elif time_filter == "YTD (Yılbaşı)":
                start_dt = pd.Timestamp(year=end_dt.year, month=1, day=1)
            else:
                start_dt = df_history.index.min()
                
            df_hist_filtered = df_history[df_history.index >= start_dt].copy()

            # 1. GRAFİK: Varlık Büyüklüğü vs Yatırılan Maliyet
            st.markdown("#### 🌊 Aktif Portföy Değeri vs. Yatırılan Ana Para")
            fig_value = go.Figure()
            fig_value.add_trace(go.Scatter(
                x=df_hist_filtered.index,
                y=df_hist_filtered['Active_Value'] * fx_multiplier,
                mode='lines',
                name=f'Portföy Değeri ({curr_symbol})',
                line=dict(color='#2962FF', width=2.5),
                fill='tozeroy',
                fillcolor='rgba(41, 98, 255, 0.15)'
            ))
            fig_value.add_trace(go.Scatter(
                x=df_hist_filtered.index,
                y=df_hist_filtered['Active_Cost'] * fx_multiplier,
                mode='lines',
                name=f'Yatırılan Maliyet ({curr_symbol})',
                line=dict(color='#FFAB00', width=2, dash='dash')
            ))
            fig_value.update_layout(
                hovermode="x unified",
                xaxis_title="",
                yaxis_title=f"Büyüklük ({curr_symbol})",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=30, b=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_value, use_container_width=True)

            # 2. GRAFİK: Kümülatif Net Kâr Evrimi (Realize + Unrealize + Temettü)
            st.markdown("---")
            st.markdown("#### 💰 Kümülatif Net Kâr Evrimi (Satış Kârları + Açık Kâr + Temettü)")
            st.caption("Pozisyon kapattığınızda elde ettiğiniz kârlar kaybolmaz; kümülatif kazancınıza eklenerek takip edilir.")
            
            fig_profit = px.area(
                df_hist_filtered,
                x=df_hist_filtered.index,
                y=df_hist_filtered['Total_Net_Profit'] * fx_multiplier,
                labels={'index': 'Tarih', 'y': f'Kümülatif Net Kâr ({curr_symbol})'}
            )
            fig_profit.update_traces(line_color='#00C853', fillcolor='rgba(0, 200, 83, 0.2)')
            fig_profit.update_layout(
                hovermode="x unified",
                xaxis_title="",
                yaxis_title=f"Net Kâr ({curr_symbol})",
                margin=dict(l=0, r=0, t=20, b=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_profit, use_container_width=True)

            # 3. GRAFİK: Yüzdelik Getiri ve Benchmark Kıyaslaması
            st.markdown("---")
            st.markdown("#### 📈 Aktif Portföy Büyümesi (%) & Benchmark Kıyaslaması")
            fig_pct = go.Figure()
            
            line_color = '#00C853' if df_hist_filtered['Active_P/L (%)'].iloc[-1] >= 0 else '#D50000'
            fig_pct.add_trace(go.Scatter(
                x=df_hist_filtered.index,
                y=df_hist_filtered['Active_P/L (%)'],
                mode='lines',
                name='Portföy P/L (%)',
                line=dict(color=line_color, width=2.5)
            ))
            
            if 'Benchmark (%)' in df_hist_filtered.columns:
                fig_pct.add_trace(go.Scatter(
                    x=df_hist_filtered.index,
                    y=df_hist_filtered['Benchmark (%)'],
                    mode='lines',
                    name=benchmark_choice,
                    line=dict(color='#AA00FF', width=2, dash='dot')
                ))

            fig_pct.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Başabaş Noktası (0%)")
            fig_pct.update_layout(
                hovermode="x unified",
                xaxis_title="",
                yaxis_title="Getiri (%)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=30, b=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pct, use_container_width=True)

    # ================= SEKME 3: İŞLEM GEÇMİŞİ LOGU =================
    with tab3:
        st.subheader("🧾 Tüm İşlem Kayıtları (Transaction History)")
        tx_rows = []
        for ticker, txs in portfolio_transactions.items():
            for tx in txs:
                q = tx.get('Quantity', 0.0)
                c = tx.get('Total_Cost', 0.0)
                r = tx.get('Realized_Profit', 0.0)
                d = tx.get('Dividend', 0.0)
                
                if d > 0 and q == 0:
                    tx_type = "💵 Nakit Temettü"
                elif d > 0 and q > 0:
                    tx_type = "🔄 Temettü Yeniden Yatırım (DRIP)"
                elif q > 0:
                    tx_type = "🟢 Alım (Buy)"
                else:
                    tx_type = "🔴 Satım (Sell)"
                    
                tx_rows.append({
                    'Tarih': tx['Date'],
                    'Varlık': ticker,
                    'İşlem Tipi': tx_type,
                    'Miktar': q,
                    f'Maliyet / Tutar ({curr_symbol})': c * fx_multiplier,
                    f'Realize Kâr ({curr_symbol})': r * fx_multiplier,
                    f'Temettü ({curr_symbol})': d * fx_multiplier
                })
        
        df_tx_log = pd.DataFrame(tx_rows).sort_values('Tarih', ascending=False)
        st.dataframe(df_tx_log, use_container_width=True, hide_index=True)

else:
    st.warning("Ekranda listelenecek geçerli bir veri bulunamadı.")

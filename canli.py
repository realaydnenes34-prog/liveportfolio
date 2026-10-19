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
    page_title="Portfolio Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SABİT VE TAM EKRAN UYUMLU CSS STİLİ ---
st.markdown("""
<style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }

    /* Plotly Grafiklerinin Yarım Ekran Açılmasını Engelleyen Tam Genişlik Kuralı */
    .js-plotly-plot, .plot-container, .svg-container {
        width: 100% !important;
    }

    /* Üst Piyasa Bandı (Ticker Tape) */
    .ticker-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 24px;
        background: #151924;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 10px 18px;
        margin-bottom: 20px;
        font-family: 'SF Mono', 'Roboto Mono', monospace;
        font-size: 0.82rem;
        align-items: center;
    }
    .ticker-item {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .ticker-label {
        color: #9AA4B2;
        font-weight: 600;
    }
    .ticker-val {
        color: #FFFFFF;
        font-weight: 700;
    }

    /* Özel KPI Metrik Kartları */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
        gap: 14px;
        margin-bottom: 22px;
    }
    .kpi-card {
        background: #151924;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 16px 18px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    .kpi-title {
        color: #9AA4B2;
        font-size: 0.73rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 8px;
    }
    .kpi-value {
        color: #FFFFFF;
        font-size: 1.42rem;
        font-weight: 700;
        font-family: 'SF Mono', 'Roboto Mono', monospace;
        line-height: 1.2;
        margin-bottom: 8px;
    }
    .kpi-sub {
        display: inline-block;
        font-size: 0.75rem;
        font-weight: 600;
        font-family: 'SF Mono', 'Roboto Mono', monospace;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .pos-badge {
        color: #00E676;
        background: rgba(0, 230, 118, 0.15);
    }
    .neg-badge {
        color: #FF3B69;
        background: rgba(255, 59, 105, 0.15);
    }
    .neu-badge {
        color: #B0B8C4;
        background: rgba(176, 184, 196, 0.15);
    }

    /* Sekme Başlıkları */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        border-bottom: 1px solid rgba(132, 142, 156, 0.25);
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        font-weight: 600;
        font-size: 0.83rem;
        letter-spacing: 0.04em;
    }
</style>
""", unsafe_allow_html=True)

tz_TR = timezone(timedelta(hours=3))

# Kurumsal Varlık İsimlendirmeleri
ASSET_NAMES = {
    'GC=F': 'XAU/GRAM • Fiziki Altın (Gram)',
    'GRID': 'GRID • First Trust NASDAQ Clean Edge ETF',
    'ASELS.IS': 'ASELS • Aselsan Elektronik Sanayi',
    'CCOLA.IS': 'CCOLA • Coca-Cola İçecek A.Ş.',
    'CGCAM.IS': 'CGCAM • Çağdaş Cam San. ve Tic. A.Ş.',
    'ALTIN.IS': 'ALTIN.S1 • Darphane Altın Sertifikası',
    'IOG': 'IOG • İş Portföy Gümüş Serbest Fon',
    'HSL': 'HSL • HSBC Portföy Para Piyasası Fonu',
    'AFA': 'AFA • Ak Portföy Amerika Yabancı Hisse Fonu',
    'HMG': 'HMG • HSBC Mutlak Getiri Hisse Senedi Fonu',
    'YKT': 'YKT • Yapı Kredi Portföy Altın Fonu',
    'IVY': 'IVY • İstanbul Portföy Blockchain Fonu',
    'YAS': 'YAS • Yapı Kredi Koç Holding İştirak Fonu',
    'TMG': 'TMG • İş Portföy Yabancı Hisse Senedi Fonu',
    'PPS': 'PPS • Pusula Portföy Hisse Senedi Fonu',
    'USD_NEMA': 'NEMA • Midas Nemalandırma Gelirleri (USD & TL)'
}

NON_YF_TICKERS = {'IOG', 'YKT', 'IVY', 'YAS', 'TMG', 'AFA', 'HMG', 'HSL', 'PPS', 'USD_NEMA'}
US_STOCK_TICKERS = {'GRID'}
US_DEFAULT_FEE = 1.50

PLOTLY_CONFIG = {
    'displayModeBar': 'hover',
    'displaylogo': False,
    'responsive': True,
    'modeBarButtonsToRemove': ['select2d', 'lasso2d', 'autoScale2d', 'toImage']
}

# --- HAM İŞLEM VERİLERİ (OTOMATİK MUHASEBE MOTORU GİRDİSİ) ---
raw_portfolio_transactions = {
    # 1. İŞ PORTFÖY GÜMÜŞ SERBEST FON (15 Alış, 1 Satış = 16 İşlem)
    'IOG': [
        {'Date': '2024-10-31', 'Action': 'BUY', 'Quantity': 8.0, 'Gross_Amount': 1.29, 'Fee': 0.0, 'TRY_Amount': 44.33, 'Note': '8 pay x 5.5410 TL'},
        {'Date': '2024-11-06', 'Action': 'BUY', 'Quantity': 1.0, 'Gross_Amount': 0.16, 'Fee': 0.0, 'TRY_Amount': 5.37, 'Note': '1 pay x 5.3693 TL'},
        {'Date': '2024-11-19', 'Action': 'BUY', 'Quantity': 3.0, 'Gross_Amount': 0.44, 'Fee': 0.0, 'TRY_Amount': 15.22, 'Note': '3 pay x 5.0743 TL'},
        {'Date': '2025-01-02', 'Action': 'BUY', 'Quantity': 4.0, 'Gross_Amount': 0.55, 'Fee': 0.0, 'TRY_Amount': 19.34, 'Note': '4 pay x 4.8354 TL'},
        {'Date': '2025-04-07', 'Action': 'BUY', 'Quantity': 18.0, 'Gross_Amount': 2.56, 'Fee': 0.0, 'TRY_Amount': 97.41, 'Note': '18 pay x 5.4115 TL'},
        {'Date': '2025-04-25', 'Action': 'BUY', 'Quantity': 16.0, 'Gross_Amount': 2.49, 'Fee': 0.0, 'TRY_Amount': 95.63, 'Note': '16 pay x 5.9771 TL'},
        {'Date': '2025-06-11', 'Action': 'BUY', 'Quantity': 14.0, 'Gross_Amount': 2.40, 'Fee': 0.0, 'TRY_Amount': 94.37, 'Note': '14 pay x 6.7404 TL'},
        {'Date': '2025-07-10', 'Action': 'BUY', 'Quantity': 28.0, 'Gross_Amount': 4.81, 'Fee': 0.0, 'TRY_Amount': 192.35, 'Note': '28 pay x 6.8695 TL'},
        {'Date': '2025-07-22', 'Action': 'BUY', 'Quantity': 19.0, 'Gross_Amount': 3.45, 'Fee': 0.0, 'TRY_Amount': 139.36, 'Note': '19 pay x 7.3350 TL'},
        {'Date': '2025-07-25', 'Action': 'BUY', 'Quantity': 53.0, 'Gross_Amount': 9.71, 'Fee': 0.0, 'TRY_Amount': 393.25, 'Note': '53 pay x 7.4198 TL'},
        {'Date': '2025-08-15', 'Action': 'BUY', 'Quantity': 68.0, 'Gross_Amount': 12.23, 'Fee': 0.0, 'TRY_Amount': 499.66, 'Note': '68 pay x 7.3479 TL'},
        {'Date': '2025-08-18', 'Action': 'BUY', 'Quantity': 23.0, 'Gross_Amount': 4.11, 'Fee': 0.0, 'TRY_Amount': 168.19, 'Note': '23 pay x 7.3125 TL'},
        {'Date': '2025-09-30', 'Action': 'BUY', 'Quantity': 111.0, 'Gross_Amount': 24.26, 'Fee': 0.0, 'TRY_Amount': 1007.86, 'Note': '111 pay x 9.0798 TL'},
        {'Date': '2025-10-06', 'Action': 'BUY', 'Quantity': 114.0, 'Gross_Amount': 25.31, 'Fee': 0.0, 'TRY_Amount': 1054.73, 'Note': '114 pay x 9.2520 TL'},
        {'Date': '2025-10-08', 'Action': 'BUY', 'Quantity': 321.0, 'Gross_Amount': 72.01, 'Fee': 0.0, 'TRY_Amount': 3004.23, 'Note': '321 pay x 9.3590 TL'},
        {'Date': '2026-01-07', 'Action': 'SELL', 'Quantity': 801.0, 'Gross_Proceeds': 278.22, 'Fee': 19.18, 'Fee_TRY': 825.64, 'Fee_Type': 'Stopaj Vergisi', 'TRY_Amount': 11671.98, 'Note': 'Brüt: 11.671,98 TL | Stopaj: -825,64 TL'}
    ],

    # 2. YAPI KREDİ PORTFÖY ALTIN FONU
    'YKT': [
        {'Date': '2024-10-31', 'Action': 'BUY', 'Quantity': 114.0, 'Gross_Amount': 1.46, 'Fee': 0.0, 'TRY_Amount': 49.97, 'Note': '114 pay x 0.4383 TL'},
        {'Date': '2024-11-05', 'Action': 'BUY', 'Quantity': 69.0, 'Gross_Amount': 0.87, 'Fee': 0.0, 'TRY_Amount': 29.85, 'Note': '69 pay x 0.4325 TL'},
        {'Date': '2024-11-19', 'Action': 'BUY', 'Quantity': 46.0, 'Gross_Amount': 0.57, 'Fee': 0.0, 'TRY_Amount': 19.62, 'Note': '46 pay x 0.4266 TL'},
        {'Date': '2025-04-07', 'Action': 'BUY', 'Quantity': 191.0, 'Gross_Amount': 2.62, 'Fee': 0.0, 'TRY_Amount': 99.69, 'Note': '191 pay x 0.5219 TL'},
        {'Date': '2025-04-15', 'Action': 'SELL', 'Quantity': 420.0, 'Gross_Proceeds': 6.25, 'Fee': 0.07, 'Fee_TRY': 2.52, 'Fee_Type': 'Stopaj Vergisi', 'TRY_Amount': 226.86, 'Note': 'Brüt: 226,86 TL | Stopaj: -2,52 TL'}
    ],

    # 3. İSTANBUL PORTFÖY BLOCKCHAIN FONU
    'IVY': [
        {'Date': '2024-11-04', 'Action': 'BUY', 'Quantity': 17.0, 'Gross_Amount': 1.43, 'Fee': 0.0, 'TRY_Amount': 49.22, 'Note': '17 pay x 2.8954 TL'},
        {'Date': '2024-11-19', 'Action': 'BUY', 'Quantity': 9.0, 'Gross_Amount': 0.85, 'Fee': 0.0, 'TRY_Amount': 29.49, 'Note': '9 pay x 3.2769 TL'},
        {'Date': '2025-05-02', 'Action': 'SELL', 'Quantity': 26.0, 'Gross_Proceeds': 2.44, 'Fee': 0.02, 'Fee_TRY': 0.62, 'Fee_Type': 'Stopaj Vergisi', 'TRY_Amount': 84.85, 'Note': 'Brüt: 84,85 TL | Stopaj: -0,62 TL'}
    ],

    # 4. YAPI KREDİ KOÇ HOLDİNG İŞTİRAK FONU
    'YAS': [
        {'Date': '2024-11-04', 'Action': 'BUY', 'Quantity': 6.0, 'Gross_Amount': 1.96, 'Fee': 0.0, 'TRY_Amount': 67.41, 'Note': '6 pay x 11.2342 TL'},
        {'Date': '2024-11-19', 'Action': 'BUY', 'Quantity': 2.0, 'Gross_Amount': 0.71, 'Fee': 0.0, 'TRY_Amount': 24.44, 'Note': '2 pay x 12.2191 TL'},
        {'Date': '2025-03-28', 'Action': 'SELL', 'Quantity': 8.0, 'Gross_Proceeds': 2.77, 'Fee': 0.0, 'TRY_Amount': 95.66, 'Note': 'Satış: 95,66 TL (%0 Stopaj)'}
    ],

    # 5. İŞ PORTFÖY YABANCI HİSSE SENEDİ FONU
    'TMG': [
        {'Date': '2024-12-06', 'Action': 'BUY', 'Quantity': 18.0, 'Gross_Amount': 0.42, 'Fee': 0.0, 'TRY_Amount': 14.52, 'Note': '18 pay x 0.8065 TL'},
        {'Date': '2024-12-09', 'Action': 'BUY', 'Quantity': 61.0, 'Gross_Amount': 1.42, 'Fee': 0.0, 'TRY_Amount': 49.22, 'Note': '61 pay x 0.8070 TL'},
        {'Date': '2025-01-30', 'Action': 'SELL', 'Quantity': 79.0, 'Gross_Proceeds': 1.80, 'Fee': 0.0, 'TRY_Amount': 62.46, 'Note': 'Satış: 62,46 TL'}
    ],

    # 6. ÇAĞDAŞ CAM SAN. VE TİC. A.Ş.
    'CGCAM.IS': [
        {'Date': '2024-12-12', 'Action': 'BUY', 'Quantity': 4.0, 'Gross_Amount': 2.29, 'Fee': 0.0, 'Fee_TRY': 0.03, 'Fee_Type': 'BIST Komisyon & BSMV', 'TRY_Amount': 80.04, 'Note': 'Halka Arz: 4 adet x 20,00 TL (+0,03 TL Kom.)'},
        {'Date': '2024-12-19', 'Action': 'SELL', 'Quantity': 2.0, 'Gross_Proceeds': 1.52, 'Fee': 0.01, 'Fee_TRY': 0.53, 'Fee_Type': 'Anında Nakit & Komisyon', 'TRY_Amount': 52.70, 'Note': '2 adet Satış | Anında Nakit Kom: -0,51 TL'},
        {'Date': '2024-12-30', 'Action': 'SELL', 'Quantity': 1.0, 'Gross_Proceeds': 1.00, 'Fee': 0.00, 'Fee_TRY': 0.18, 'Fee_Type': 'Anında Nakit & Komisyon', 'TRY_Amount': 35.05, 'Note': '1 adet Satış | Anında Nakit Kom: -0,17 TL'},
        {'Date': '2025-03-03', 'Action': 'SELL', 'Quantity': 1.0, 'Gross_Proceeds': 0.74, 'Fee': 0.00, 'TRY_Amount': 26.30, 'Note': '1 adet Satış (Komisyonsuz)'}
    ],

    # 7. AK PORTFÖY AMERİKA YABANCI HİSSE SENEDİ FONU
    'AFA': [
        {'Date': '2024-12-13', 'Action': 'BUY', 'Quantity': 27.0, 'Gross_Amount': 0.56, 'Fee': 0.0, 'TRY_Amount': 19.39, 'Note': '27 pay x 0.7182 TL'},
        {'Date': '2024-12-20', 'Action': 'BUY', 'Quantity': 70.0, 'Gross_Amount': 1.41, 'Fee': 0.0, 'TRY_Amount': 49.68, 'Note': '70 pay x 0.7096 TL'},
        {'Date': '2025-01-02', 'Action': 'BUY', 'Quantity': 27.0, 'Gross_Amount': 0.55, 'Fee': 0.0, 'TRY_Amount': 19.29, 'Note': '27 pay x 0.7145 TL'},
        {'Date': '2025-02-04', 'Action': 'BUY', 'Quantity': 82.0, 'Gross_Amount': 1.66, 'Fee': 0.0, 'TRY_Amount': 59.72, 'Note': '82 pay x 0.7283 TL'},
        {'Date': '2025-04-03', 'Action': 'BUY', 'Quantity': 178.0, 'Gross_Amount': 3.32, 'Fee': 0.0, 'TRY_Amount': 125.94, 'Note': '178 pay x 0.7075 TL'},
        {'Date': '2025-04-07', 'Action': 'BUY', 'Quantity': 309.0, 'Gross_Amount': 5.26, 'Fee': 0.0, 'TRY_Amount': 200.00, 'Note': '309 pay x 0.6472 TL'},
        {'Date': '2025-04-17', 'Action': 'BUY', 'Quantity': 147.0, 'Gross_Amount': 2.60, 'Fee': 0.0, 'TRY_Amount': 99.42, 'Note': '147 pay x 0.6763 TL'},
        {'Date': '2025-04-25', 'Action': 'BUY', 'Quantity': 158.0, 'Gross_Amount': 2.85, 'Fee': 0.0, 'TRY_Amount': 109.68, 'Note': '158 pay x 0.6941 TL'},
        {'Date': '2025-05-20', 'Action': 'BUY', 'Quantity': 151.0, 'Gross_Amount': 3.06, 'Fee': 0.0, 'TRY_Amount': 118.95, 'Note': '151 pay x 0.7878 TL'},
        {'Date': '2025-06-11', 'Action': 'BUY', 'Quantity': 225.0, 'Gross_Amount': 4.59, 'Fee': 0.0, 'TRY_Amount': 180.28, 'Note': '225 pay x 0.8012 TL'},
        {'Date': '2025-07-25', 'Action': 'BUY', 'Quantity': 455.0, 'Gross_Amount': 9.87, 'Fee': 0.0, 'TRY_Amount': 399.40, 'Note': '455 pay x 0.8778 TL'},
        {'Date': '2025-08-18', 'Action': 'BUY', 'Quantity': 111.0, 'Gross_Amount': 2.44, 'Fee': 0.0, 'TRY_Amount': 99.83, 'Note': '111 pay x 0.8993 TL'},
        {'Date': '2025-08-27', 'Action': 'BUY', 'Quantity': 334.0, 'Gross_Amount': 7.32, 'Fee': 0.0, 'TRY_Amount': 300.34, 'Note': '334 pay x 0.8992 TL'},
        {'Date': '2025-09-25', 'Action': 'SELL', 'Quantity': 1137.0, 'Gross_Proceeds': 26.59, 'Fee': 0.90, 'Fee_TRY': 37.28, 'Fee_Type': 'Stopaj Vergisi', 'TRY_Amount': 1049.92, 'Note': '1. Satış (%50): 1.049,92 TL | Stopaj: -37,28 TL'},
        {'Date': '2025-10-02', 'Action': 'SELL', 'Quantity': 1137.0, 'Gross_Proceeds': 26.99, 'Fee': 0.31, 'Fee_TRY': 12.90, 'Fee_Type': 'Stopaj Vergisi', 'TRY_Amount': 1067.73, 'Note': '2. Satış (Kalan %50): 1.067,73 TL | Stopaj: -12,90 TL'}
    ],

    # 8. HSBC MUTLAK GETİRİ HİSSE SENEDİ SERBEST FON
    'HMG': [
        {'Date': '2025-01-10', 'Action': 'BUY', 'Quantity': 6914.0, 'Gross_Amount': 8.46, 'Fee': 0.0, 'TRY_Amount': 299.96, 'Note': '6.914 pay x 0.0434 TL'},
        {'Date': '2025-02-10', 'Action': 'BUY', 'Quantity': 6487.0, 'Gross_Amount': 8.33, 'Fee': 0.0, 'TRY_Amount': 299.98, 'Note': '6.487 pay x 0.0462 TL'},
        {'Date': '2025-04-17', 'Action': 'BUY', 'Quantity': 3062.0, 'Gross_Amount': 3.93, 'Fee': 0.0, 'TRY_Amount': 149.96, 'Note': '3.062 pay x 0.0490 TL'},
        {'Date': '2025-04-24', 'Action': 'BUY', 'Quantity': 4037.0, 'Gross_Amount': 5.21, 'Fee': 0.0, 'TRY_Amount': 200.00, 'Note': '4.037 pay x 0.0495 TL'},
        {'Date': '2025-04-25', 'Action': 'BUY', 'Quantity': 10073.0, 'Gross_Amount': 13.01, 'Fee': 0.0, 'TRY_Amount': 499.96, 'Note': '10.073 pay x 0.0496 TL'},
        {'Date': '2025-06-24', 'Action': 'SELL', 'Quantity': 10000.0, 'Gross_Proceeds': 13.52, 'Fee': 0.0, 'TRY_Amount': 505.13, 'Note': '1. Kısmi Satış (10.000 pay = %32.71)'},
        {'Date': '2025-07-07', 'Action': 'SELL', 'Quantity': 20573.0, 'Gross_Proceeds': 28.10, 'Fee': 0.0, 'TRY_Amount': 1051.49, 'Note': '2. Satış (Kalan 20.573 pay)'}
    ],

    # 9. HSBC PORTFÖY PARA PİYASASI FONU
    'HSL': [
        {'Date': '2025-04-18', 'Action': 'BUY', 'Quantity': 8.0, 'Gross_Amount': 50.43, 'Fee': 0.0, 'TRY_Amount': 1926.43, 'Note': '8 pay x 240.8033 TL'},
        {'Date': '2025-04-22', 'Action': 'BUY', 'Quantity': 8.0, 'Gross_Amount': 50.62, 'Fee': 0.0, 'TRY_Amount': 1937.59, 'Note': '8 pay x 242.1987 TL'},
        {'Date': '2025-04-24', 'Action': 'BUY', 'Quantity': 26.0, 'Gross_Amount': 164.49, 'Fee': 0.0, 'TRY_Amount': 6313.22, 'Note': '26 pay x 242.8162 TL'},
        {'Date': '2025-05-08', 'Action': 'BUY', 'Quantity': 12.0, 'Gross_Amount': 76.75, 'Fee': 0.0, 'TRY_Amount': 2966.56, 'Note': '12 pay x 247.2131 TL'},
        {'Date': '2025-05-14', 'Action': 'BUY', 'Quantity': 11.0, 'Gross_Amount': 70.72, 'Fee': 0.0, 'TRY_Amount': 2740.30, 'Note': '11 pay x 249.1178 TL'},
        {'Date': '2025-06-10', 'Action': 'BUY', 'Quantity': 5.0, 'Gross_Amount': 32.89, 'Fee': 0.0, 'TRY_Amount': 1289.94, 'Note': '5 pay x 257.9887 TL'},
        {'Date': '2025-07-21', 'Action': 'BUY', 'Quantity': 1.0, 'Gross_Amount': 6.74, 'Fee': 0.0, 'TRY_Amount': 271.71, 'Note': '1 pay x 271.7117 TL'},
        {'Date': '2025-08-14', 'Action': 'BUY', 'Quantity': 2.0, 'Gross_Amount': 13.69, 'Fee': 0.0, 'TRY_Amount': 558.63, 'Note': '2 pay x 279.3153 TL'},
        {'Date': '2025-09-17', 'Action': 'SELL', 'Quantity': 73.0, 'Gross_Proceeds': 543.45, 'Fee': 11.59, 'Fee_TRY': 478.55, 'Fee_Type': 'Stopaj Vergisi', 'TRY_Amount': 21188.02, 'Note': 'Brüt: 21.188,02 TL | Stopaj: -478,55 TL'}
    ],

    # 10. DARPHANE ALTIN SERTİFİKASI • 0,01 GR ALTIN
    'ALTIN.IS': [
        {'Date': '2025-04-24', 'Action': 'BUY', 'Quantity': 3.0, 'Gross_Amount': 3.72, 'Fee': 0.0, 'TRY_Amount': 142.95, 'Note': '3 adet x 47,65 TL'},
        {'Date': '2025-04-25', 'Action': 'BUY', 'Quantity': 1.0, 'Gross_Amount': 1.19, 'Fee': 0.0, 'TRY_Amount': 45.82, 'Note': '1 adet x 45,82 TL'},
        {'Date': '2025-05-02', 'Action': 'BUY', 'Quantity': 1.0, 'Gross_Amount': 1.17, 'Fee': 0.0, 'TRY_Amount': 44.92, 'Note': '1 adet x 44,92 TL'},
        {'Date': '2025-05-08', 'Action': 'BUY', 'Quantity': 1.0, 'Gross_Amount': 1.22, 'Fee': 0.0, 'TRY_Amount': 47.08, 'Note': '1 adet x 47,08 TL'},
        {'Date': '2025-05-14', 'Action': 'BUY', 'Quantity': 1.0, 'Gross_Amount': 1.14, 'Fee': 0.0, 'TRY_Amount': 44.14, 'Note': '1 adet x 44,14 TL'},
        {'Date': '2025-05-15', 'Action': 'BUY', 'Quantity': 3.0, 'Gross_Amount': 3.32, 'Fee': 0.0, 'TRY_Amount': 128.61, 'Note': '3 adet x 42,87 TL'},
        {'Date': '2025-06-10', 'Action': 'BUY', 'Quantity': 1.0, 'Gross_Amount': 1.20, 'Fee': 0.0, 'TRY_Amount': 47.07, 'Note': '1 adet x 47,07 TL'},
        {'Date': '2025-06-24', 'Action': 'BUY', 'Quantity': 1.0, 'Gross_Amount': 1.20, 'Fee': 0.0, 'TRY_Amount': 47.76, 'Note': '1 adet x 47,76 TL'},
        {'Date': '2025-07-07', 'Action': 'BUY', 'Quantity': 5.0, 'Gross_Amount': 5.84, 'Fee': 0.0, 'TRY_Amount': 232.60, 'Note': '5 adet x 46,52 TL'},
        {'Date': '2025-07-09', 'Action': 'BUY', 'Quantity': 2.0, 'Gross_Amount': 2.31, 'Fee': 0.0, 'TRY_Amount': 92.32, 'Note': '2 adet x 46,16 TL (Limit)'},
        {'Date': '2025-08-14', 'Action': 'BUY', 'Quantity': 6.0, 'Gross_Amount': 7.00, 'Fee': 0.0, 'TRY_Amount': 285.90, 'Note': '6 adet x 47,65 TL (Limit)'},
        {'Date': '2025-09-18', 'Action': 'SELL', 'Quantity': 25.0, 'Gross_Proceeds': 36.31, 'Fee': 0.44, 'Fee_TRY': 18.25, 'Fee_Type': 'Anında Nakit & Komisyon', 'TRY_Amount': 1430.00, 'Note': 'Brüt: 1.448,25 TL | Anında Nakit Kom: -18,25 TL'}
    ],

    # 11. COCA-COLA İÇECEK A.Ş.
    'CCOLA.IS': [
        {'Date': '2025-06-24', 'Action': 'BUY', 'Quantity': 10.0, 'Gross_Amount': 12.21, 'Fee': 0.0, 'TRY_Amount': 484.00, 'Note': '10 pay x 48,40 TL'},
        {'Date': '2025-07-07', 'Action': 'BUY', 'Quantity': 15.0, 'Gross_Amount': 19.48, 'Fee': 0.0, 'TRY_Amount': 776.25, 'Note': '15 pay x 51,75 TL'},
        {'Date': '2025-07-09', 'Action': 'BUY', 'Quantity': 2.0, 'Gross_Amount': 2.50, 'Fee': 0.0, 'TRY_Amount': 99.64, 'Note': '2 pay x 49,82 TL (Limit)'},
        {'Date': '2025-08-14', 'Action': 'BUY', 'Quantity': 12.0, 'Gross_Amount': 14.73, 'Fee': 0.0, 'TRY_Amount': 601.20, 'Note': '12 pay x 50,10 TL (Limit)'},
        {'Date': '2026-01-14', 'Action': 'SELL', 'Quantity': 39.0, 'Gross_Proceeds': 62.57, 'Fee': 0.0, 'TRY_Amount': 2550.60, 'Note': 'Satış: 39 pay x 65,40 TL = 2.550,60 TL'}
    ],

    # 12. FİZİKİ ALTIN / ONS-GRAM
    'GC=F': [
        {'Date': '2025-05-22', 'Action': 'BUY', 'Quantity': 13.15, 'Gross_Amount': 1354.0, 'Fee': 0.0, 'Note': 'Fiziki Altın Alımı (13.15 Gram)'},
        {'Date': '2026-04-29', 'Action': 'SELL', 'Quantity': 13.15, 'Gross_Proceeds': 1920.0, 'Fee': 0.0, 'Note': 'Fiziki Altın Satışı'} 
    ],

    # 13. GRID - NASDAQ CLEAN EDGE SMART GRID ETF
    'GRID': [
        {'Date': '2026-01-26', 'Action': 'BUY', 'Quantity': 2.524859813, 'Gross_Amount': 405.24, 'Fee': 1.50, 'Fee_Type': 'ABD Borsası Komisyonu', 'Note': 'ABD Borsası Alım ($1.50 Komisyon)'},
        {'Date': '2026-02-05', 'Action': 'BUY', 'Quantity': 1.200408824, 'Gross_Amount': 198.49, 'Fee': 1.50, 'Fee_Type': 'ABD Borsası Komisyonu', 'Note': 'ABD Borsası Alım ($1.50 Komisyon)'},
        {'Date': '2026-03-04', 'Action': 'BUY', 'Quantity': 0.866493185, 'Gross_Amount': 148.51, 'Fee': 1.50, 'Fee_Type': 'ABD Borsası Komisyonu', 'Note': 'ABD Borsası Alım ($1.50 Komisyon)'},
        {'Date': '2026-03-31', 'Action': 'DIVIDEND', 'Quantity': 0.0, 'Dividend': 0.37, 'Fee': 0.0, 'Note': 'Nakit Temettü'},
        {'Date': '2026-04-07', 'Action': 'BUY', 'Quantity': 0.599059633, 'Gross_Amount': 98.87, 'Fee': 1.50, 'Fee_Type': 'ABD Borsası Komisyonu', 'Note': 'ABD Borsası Alım ($1.50 Komisyon)'},
        {'Date': '2026-05-15', 'Action': 'BUY', 'Quantity': 2.084745762, 'Gross_Amount': 398.52, 'Fee': 1.50, 'Fee_Type': 'ABD Borsası Komisyonu', 'Note': 'ABD Borsası Alım ($1.50 Komisyon)'},
        {'Date': '2026-05-18', 'Action': 'SELL', 'Quantity': 1.318426326, 'Gross_Proceeds': 249.99, 'Fee': 1.50, 'Fee_Type': 'ABD Borsası Komisyonu', 'Note': 'Kısmi Satış ($1.50 Komisyon)'},
        {'Date': '2026-07-01', 'Action': 'DRIP', 'Quantity': 0.019026478, 'Dividend': 3.60, 'Fee': 0.0, 'Note': 'Temettü Geri Yatırımı (DRIP - Komisyonsuz)'},
        {'Date': '2026-08-11', 'Action': 'SELL', 'Quantity': 1.6055168, 'Gross_Proceeds': 301.49, 'Fee': 1.50, 'Fee_Type': 'ABD Borsası Komisyonu', 'Note': 'Kısmi Satış ($1.50 Komisyon)'},
        {'Date': '2026-09-30', 'Action': 'DRIP', 'Quantity': 0.006980331, 'Dividend': 1.24, 'Fee': 0.0, 'Note': 'Temettü Geri Yatırımı (DRIP - Komisyonsuz x $177.65)'}
    ],

    # 14. ASELSAN
    'ASELS.IS': [
        {'Date': '2026-07-08', 'Action': 'BUY', 'Quantity': 2.0, 'Gross_Amount': 16.17, 'Fee': 0.0, 'TRY_Amount': 758.00, 'Note': '2 adet x 379,00 TL'},
        {'Date': '2026-07-09', 'Action': 'BUY', 'Quantity': 1.0, 'Gross_Amount': 7.72, 'Fee': 0.0, 'TRY_Amount': 361.50, 'Note': '1 adet x 361,50 TL'},
        {'Date': '2026-09-17', 'Action': 'SELL', 'Quantity': 3.0, 'Gross_Proceeds': 24.31, 'Fee': 0.0, 'TRY_Amount': 1139.25, 'Note': 'Satış: 3 pay x 379,75 TL (Komisyonsuz)'}
    ],

    # 15. PUSULA PORTFÖY HİSSE SENEDİ FONU
    'PPS': [
        {'Date': '2026-08-28', 'Action': 'BUY', 'Quantity': 352.0, 'Gross_Amount': 30.60, 'Fee': 0.0, 'TRY_Amount': 1444.47, 'Note': '352 pay x 4.103595 TL'},
        {'Date': '2026-09-07', 'Action': 'SELL', 'Quantity': 352.0, 'Gross_Proceeds': 20.95, 'Fee': 0.0, 'TRY_Amount': 992.16, 'Note': 'Satış: 352 pay x 2.818639 TL'}
    ],

    # 16. MİDAS NEMALANDIRMA GELİRLERİ - USD & TL
    'USD_NEMA': [
        {'Date': '2026-04-30', 'Action': 'DIVIDEND', 'Quantity': 0.0, 'Dividend': 0.04, 'Fee': 0.0, 'Note': 'Nisan 2026 USD Nema (%3 Oran)'},
        {'Date': '2026-05-29', 'Action': 'DIVIDEND', 'Quantity': 0.0, 'Dividend': 0.33, 'Fee': 0.0, 'Note': 'Mayıs 2026 USD Nema (%3 Oran)'},
        {'Date': '2026-08-27', 'Action': 'DIVIDEND', 'Quantity': 0.0, 'Dividend': 0.025, 'Fee': 0.005, 'Fee_TRY': 0.24, 'Fee_Type': 'Stopaj Vergisi', 'TRY_Amount': 1.12, 'Note': 'TL Fon Nema: Brüt 1,36 TL | Stopaj: -0,24 TL | Net: 1,12 TL'},
        {'Date': '2026-08-31', 'Action': 'DIVIDEND', 'Quantity': 0.0, 'Dividend': 0.06, 'Fee': 0.0, 'Note': 'Ağustos 2026 USD Nema (%3 Oran)'}
    ]
}

# ==============================================================================
# OTOMATİK MALİYET VE KÂR HESAPLAMA MOTORU (WEIGHTED AVERAGE COST / AUTO-LEDGER)
# ==============================================================================
def run_accounting_engine(raw_tx_dict):
    processed_dict = {}
    
    for ticker, raw_list in raw_tx_dict.items():
        action_priority = {'BUY': 1, 'DRIP': 2, 'DIVIDEND': 3, 'SELL': 4}
        sorted_txs = sorted(
            raw_list, 
            key=lambda x: (pd.to_datetime(x['Date']), action_priority.get(x.get('Action', 'BUY'), 5))
        )
        
        running_qty = 0.0
        running_cost = 0.0
        processed_list = []
        
        for tx in sorted_txs:
            action = tx.get('Action', 'BUY').upper()
            date_str = tx['Date']
            qty = abs(float(tx.get('Quantity', 0.0)))
            try_amt = tx.get('TRY_Amount', None)
            fee_try = tx.get('Fee_TRY', None)
            fee_type = tx.get('Fee_Type', None)
            note = tx.get('Note', '')
            
            if 'Fee' in tx:
                fee = float(tx['Fee'])
            else:
                if ticker in US_STOCK_TICKERS and action in ('BUY', 'SELL'):
                    fee = US_DEFAULT_FEE
                else:
                    fee = 0.0
                    
            if fee > 0 and not fee_type:
                fee_type = 'ABD Borsası Komisyonu' if ticker in US_STOCK_TICKERS else 'İşlem Komisyonu / Vergi'
                    
            if action == 'BUY':
                gross_amt = float(tx.get('Gross_Amount', tx.get('Total_Cost', 0.0) - fee))
                total_cost_added = round(gross_amt + fee, 4)
                
                running_qty += qty
                running_cost += total_cost_added
                avg_cost_now = running_cost / running_qty if running_qty > 0 else 0.0
                
                processed_list.append({
                    'Date': date_str,
                    'Action': 'BUY',
                    'Quantity': qty,
                    'Total_Cost': total_cost_added,
                    'Realized_Profit': 0.0,
                    'Dividend': 0.0,
                    'Fee': fee,
                    'Fee_TRY': fee_try,
                    'Fee_Type': fee_type,
                    'Sell_Ratio_Pct': 0.0,
                    'Running_Qty': running_qty,
                    'Running_Avg_Cost': avg_cost_now,
                    'TRY_Amount': try_amt,
                    'Note': note
                })
                
            elif action == 'DRIP':
                div_amt = float(tx.get('Dividend', 0.0))
                running_qty += qty
                avg_cost_now = running_cost / running_qty if running_qty > 0 else 0.0
                
                processed_list.append({
                    'Date': date_str,
                    'Action': 'DRIP',
                    'Quantity': qty,
                    'Total_Cost': 0.0,
                    'Realized_Profit': 0.0,
                    'Dividend': div_amt,
                    'Fee': 0.0,
                    'Fee_TRY': None,
                    'Fee_Type': None,
                    'Sell_Ratio_Pct': 0.0,
                    'Running_Qty': running_qty,
                    'Running_Avg_Cost': avg_cost_now,
                    'TRY_Amount': try_amt,
                    'Note': note
                })
                
            elif action == 'SELL':
                avg_cost_before_sale = running_cost / running_qty if running_qty > 0 else 0.0
                sell_ratio = (qty / running_qty) if running_qty > 0 else 1.0
                sell_ratio = min(sell_ratio, 1.0)
                
                if abs(running_qty - qty) < 1e-6:
                    cost_removed = round(running_cost, 2)
                else:
                    cost_removed = round(running_cost * sell_ratio, 2)
                    
                gross_proceeds = float(tx.get('Gross_Proceeds', 0.0))
                net_proceeds = round(gross_proceeds - fee, 2)
                realized_pnl = round(net_proceeds - cost_removed, 2)
                
                running_qty -= qty
                running_cost = round(running_cost - cost_removed, 2)
                if running_qty < 1e-6:
                    running_qty = 0.0
                    running_cost = 0.0
                    
                avg_cost_after = running_cost / running_qty if running_qty > 0 else avg_cost_before_sale
                
                processed_list.append({
                    'Date': date_str,
                    'Action': 'SELL',
                    'Quantity': -qty,
                    'Total_Cost': -cost_removed,
                    'Realized_Profit': realized_pnl,
                    'Dividend': 0.0,
                    'Fee': fee,
                    'Fee_TRY': fee_try,
                    'Fee_Type': fee_type,
                    'Gross_Proceeds': gross_proceeds,
                    'Net_Proceeds': net_proceeds,
                    'Sell_Ratio_Pct': sell_ratio * 100.0,
                    'Running_Qty': running_qty,
                    'Running_Avg_Cost': avg_cost_after,
                    'TRY_Amount': -abs(try_amt) if try_amt is not None else None,
                    'Note': note
                })
                
            elif action == 'DIVIDEND':
                div_amt = round(float(tx.get('Dividend', 0.0)) - fee, 4)
                avg_cost_now = running_cost / running_qty if running_qty > 0 else 0.0
                processed_list.append({
                    'Date': date_str,
                    'Action': 'DIVIDEND',
                    'Quantity': 0.0,
                    'Total_Cost': 0.0,
                    'Realized_Profit': 0.0,
                    'Dividend': div_amt,
                    'Fee': fee,
                    'Fee_TRY': fee_try,
                    'Fee_Type': fee_type,
                    'Sell_Ratio_Pct': 0.0,
                    'Running_Qty': running_qty,
                    'Running_Avg_Cost': avg_cost_now,
                    'TRY_Amount': try_amt,
                    'Note': note
                })
                
        processed_dict[ticker] = processed_list
        
    return processed_dict

portfolio_transactions = run_accounting_engine(raw_portfolio_transactions)

# --- SIDEBAR (TERMİNAL KONTROL PANELİ) ---
with st.sidebar:
    st.markdown("### TERMINAL AYARLARI")
    
    base_currency = st.radio(
        "Para Birimi Bazı",
        options=["USD ($)", "TRY (₺)"],
        index=0,
        horizontal=True
    )
    curr_symbol = "$" if "USD" in base_currency else "₺"
    
    hide_closed = st.checkbox("Kapanan Pozisyonları Gizle", value=False)
    
    benchmark_choice = st.selectbox(
        "Benchmark Karşılaştırması",
        options=["Yok", "S&P 500 (^GSPC)", "NASDAQ 100 (^NDX)", "Altın Ons (GC=F)"]
    )
    
    st.markdown("---")
    auto_refresh = st.toggle("Canlı Veri Akışı (60s)", value=True)
    if st.button("Verileri Senkronize Et", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if auto_refresh:
    st_autorefresh(interval=60000, key="portfolio_update")

def clean_zero(val):
    return 0.0 if abs(float(val)) < 1e-4 else float(val)

# --- PİYASA BANDI VE PORTFÖY VERİ ÇEKME FONKSİYONU ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_portfolio_data(transactions_dict):
    results = []
    errors = []
    
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

    market_Pulse = {'USDTRY': usd_try_rate, 'GOLD_GRAM_USD': 0.0, 'SP500': 0.0, 'BIST100': 0.0}
    try:
        g_fast = yf.Ticker("GC=F").fast_info.last_price
        if g_fast: market_Pulse['GOLD_GRAM_USD'] = float(g_fast) / 31.1035
    except Exception:
        pass
    try:
        sp_fast = yf.Ticker("^GSPC").fast_info.last_price
        if sp_fast: market_Pulse['SP500'] = float(sp_fast)
    except Exception:
        pass
    try:
        xu_fast = yf.Ticker("XU100.IS").fast_info.last_price
        if xu_fast: market_Pulse['BIST100'] = float(xu_fast)
    except Exception:
        pass
            
    for ticker, txs in transactions_dict.items():
        try:
            total_quantity = sum(tx.get('Quantity', 0.0) for tx in txs)
            total_cost_all_tx = sum(tx.get('Total_Cost', 0.0) for tx in txs)
            total_invested_ever = sum(tx.get('Total_Cost', 0.0) for tx in txs if tx.get('Total_Cost', 0.0) > 0)
            realized_profit = sum(tx.get('Realized_Profit', 0.0) for tx in txs)
            dividends = sum(tx.get('Dividend', 0.0) for tx in txs)
            total_fees_paid = sum(tx.get('Fee', 0.0) for tx in txs)
            cash_dividends = sum(tx.get('Dividend', 0.0) for tx in txs if tx.get('Quantity', 0.0) == 0)
            
            is_closed = abs(total_quantity) < 1e-6
            if is_closed:
                total_quantity = 0.0
                total_cost_all_tx = 0.0
            
            avg_cost = total_cost_all_tx / total_quantity if total_quantity > 0 else 0.0
            display_name = ASSET_NAMES.get(ticker, ticker)
            
            if ticker in NON_YF_TICKERS and is_closed:
                total_net_ret = clean_zero(realized_profit + dividends)
                total_roi_pct = clean_zero((total_net_ret / total_invested_ever * 100) if total_invested_ever > 0 else 0.0)
                results.append({
                    'Ticker': ticker,
                    'Asset': display_name,
                    'Status': 'PASİF GELİR' if ticker == 'USD_NEMA' else 'KAPALI',
                    'Quantity': 0.0,
                    'Avg. Cost': 0.0,
                    'Current Price': 0.0,
                    'Daily Change (%)': 0.0,
                    'Daily P/L': 0.0,
                    'Total Cost': 0.0,
                    'Current Value': 0.0,
                    'Unrealized P/L': 0.0,
                    'Unrealized P/L (%)': 0.0,
                    'Realized P/L': clean_zero(realized_profit),
                    'Dividends': clean_zero(dividends),
                    'Fees & Tax': clean_zero(total_fees_paid),
                    'Total Net Return': total_net_ret,
                    'Total ROI (%)': total_roi_pct
                })
                continue

            stock = yf.Ticker(ticker)
            price_data = None
            prev_close = None
            
            hist_data = stock.history(period="5d")
            if not hist_data.empty and not hist_data['Close'].dropna().empty:
                clean_closes = hist_data['Close'].dropna()
                price_data = float(clean_closes.iloc[-1])
                prev_close = float(clean_closes.iloc[-2]) if len(clean_closes) > 1 else price_data
            
            try:
                fast_p = stock.fast_info.last_price
                if fast_p is not None and not pd.isna(fast_p):
                    price_data = float(fast_p)
            except Exception:
                pass
                
            if price_data is None or pd.isna(price_data):
                if is_closed:
                    price_data = 0.0
                    prev_close = 0.0
                else:
                    errors.append(f"{ticker}: Fiyat verisi alınamadı.")
                    continue
            
            if prev_close is None or pd.isna(prev_close):
                prev_close = price_data
                
            if ticker == 'GC=F':
                current_price = price_data / 31.1035
                prev_price_usd = prev_close / 31.1035
            elif ticker.endswith('.IS'):
                current_price = price_data / usd_try_rate
                prev_price_usd = prev_close / usd_try_rate
            else:
                current_price = price_data
                prev_price_usd = prev_close

            current_value = clean_zero(total_quantity * current_price)
            pnl_amount = clean_zero(current_value - total_cost_all_tx)
            pnl_percentage = clean_zero((pnl_amount / total_cost_all_tx) * 100 if total_cost_all_tx > 0 else 0.0)
            
            daily_return_pct = clean_zero(((current_price - prev_price_usd) / prev_price_usd) * 100 if (prev_price_usd > 0 and not is_closed) else 0.0)
            daily_pnl_usd = clean_zero(total_quantity * (current_price - prev_price_usd) if not is_closed else 0.0)
            
            effective_div = dividends if is_closed else cash_dividends
            total_net_ret = clean_zero(pnl_amount + realized_profit + effective_div)
            total_roi_pct = clean_zero((total_net_ret / total_invested_ever * 100) if total_invested_ever > 0 else 0.0)

            results.append({
                'Ticker': ticker,
                'Asset': display_name,
                'Status': 'KAPALI' if is_closed else 'AÇIK',
                'Quantity': clean_zero(total_quantity),
                'Avg. Cost': clean_zero(avg_cost),
                'Current Price': clean_zero(current_price if not is_closed else 0.0),
                'Daily Change (%)': daily_return_pct,
                'Daily P/L': daily_pnl_usd,
                'Total Cost': clean_zero(total_cost_all_tx),
                'Current Value': current_value,
                'Unrealized P/L': pnl_amount,
                'Unrealized P/L (%)': pnl_percentage,
                'Realized P/L': clean_zero(realized_profit),
                'Dividends': clean_zero(dividends),
                'Fees & Tax': clean_zero(total_fees_paid),
                'Total Net Return': total_net_ret,
                'Total ROI (%)': total_roi_pct
            })
            
        except Exception as e:
            errors.append(f"{ticker} hata: {str(e)}")
            continue
            
    return results, errors, usd_try_rate, market_Pulse

# --- GEÇMİŞ PORTFÖY HESAPLAMASI ---
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_historical_chart_data(transactions_dict, benchmark_ticker=None):
    all_tx = []
    for ticker, txs in transactions_dict.items():
        for tx in txs:
            all_tx.append({
                'Ticker': ticker,
                'Date': pd.to_datetime(tx['Date']).tz_localize(None).normalize(),
                'Quantity': tx.get('Quantity', 0.0),
                'Total_Cost': tx.get('Total_Cost', 0.0),
                'Realized_Profit': tx.get('Realized_Profit', 0.0),
                'Dividend': tx.get('Dividend', 0.0)
            })
            
    df_tx = pd.DataFrame(all_tx).sort_values('Date')
    if df_tx.empty:
        return pd.DataFrame()
    
    start_date = df_tx['Date'].min()
    end_date = max(df_tx['Date'].max(), pd.Timestamp.now().normalize())
    full_date_index = pd.date_range(start=start_date, end=end_date, freq='B')
    start_date_str = start_date.strftime('%Y-%m-%d')
    
    try:
        usd_hist = yf.Ticker("USDTRY=X").history(start=start_date_str)['Close']
        usd_hist.index = pd.to_datetime(usd_hist.index).tz_localize(None).normalize()
        usd_hist = usd_hist[~usd_hist.index.duplicated(keep='last')]
    except Exception:
        usd_hist = None
    
    all_prices = {}
    for ticker, txs in transactions_dict.items():
        if ticker == 'USD_NEMA':
            continue
            
        fetched_yf = False
        if ticker not in NON_YF_TICKERS:
            try:
                hist = yf.Ticker(ticker).history(start=start_date_str)
                if not hist.empty and not hist['Close'].dropna().empty:
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
                            
                    all_prices[ticker] = hist['Close'].reindex(full_date_index).ffill().bfill()
                    fetched_yf = True
            except Exception:
                fetched_yf = False
                
        if not fetched_yf:
            pts = {}
            for tx in txs:
                d = pd.to_datetime(tx['Date']).tz_localize(None).normalize()
                q = tx.get('Quantity', 0.0)
                c = tx.get('Total_Cost', 0.0)
                r = tx.get('Realized_Profit', 0.0)
                if q > 0 and c > 0:
                    pts[d] = c / q
                elif q < 0:
                    pts[d] = (abs(c) + r) / abs(q)
            if pts:
                s = pd.Series(pts).sort_index()
                s = s[~s.index.duplicated(keep='last')]
                s_reindexed = s.reindex(full_date_index.union(s.index)).sort_index()
                s_interp = s_reindexed.interpolate(method='time').ffill().bfill()
                all_prices[ticker] = s_interp.reindex(full_date_index)

    if not all_prices:
        return pd.DataFrame()
    
    df_prices = pd.DataFrame(all_prices, index=full_date_index).ffill().bfill()
    
    df_history = pd.DataFrame(index=df_prices.index)
    df_history['Active_Cost'] = 0.0
    df_history['Active_Value'] = 0.0
    df_history['Cum_Realized_PnL'] = 0.0
    df_history['Cum_Cash_Dividends'] = 0.0
    
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
            
        daily_qty = daily_qty.apply(lambda x: 0.0 if abs(x) < 1e-6 else x)
        daily_cost = daily_cost.where(daily_qty > 0, 0.0)
            
        df_history['Active_Value'] += daily_qty * df_prices[ticker]
        df_history['Active_Cost'] += daily_cost

    for _, row in df_tx.iterrows():
        mask = df_history.index >= row['Date']
        df_history.loc[mask, 'Cum_Realized_PnL'] += row['Realized_Profit']
        if row['Quantity'] == 0:
            df_history.loc[mask, 'Cum_Cash_Dividends'] += row['Dividend']

    df_history['Unrealized_PnL'] = df_history['Active_Value'] - df_history['Active_Cost']
    df_history['Total_Net_Profit'] = (
        df_history['Unrealized_PnL'] + 
        df_history['Cum_Realized_PnL'] + 
        df_history['Cum_Cash_Dividends']
    )
    
    df_history['Active_P/L (%)'] = np.where(
        df_history['Active_Cost'] > 0, 
        (df_history['Unrealized_PnL'] / df_history['Active_Cost']) * 100, 
        0.0
    )

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

def fmt_currency(val, sym):
    if abs(val) < 1e-4:
        return f"{sym}0.00"
    sign = "-" if val < 0 else "+"
    return f"{sign}{sym}{abs(val):,.2f}"

def badge_class(val):
    if val > 1e-4:
        return "pos-badge"
    elif val < -1e-4:
        return "neg-badge"
    return "neu-badge"

# Tam Ekran ve Sabit X-Tarzı Grafik Düzeni
def apply_x_smooth_layout(fig, y_title="", show_range_buttons=True, height=420):
    range_selector = dict(
        bgcolor='rgba(21, 25, 36, 0.9)',
        activecolor='#2962FF',
        font=dict(color='#FFFFFF', size=11),
        bordercolor='rgba(132, 142, 156, 0.25)',
        borderwidth=1,
        buttons=list([
            dict(count=1, label="1A", step="month", stepmode="backward"),
            dict(count=3, label="3A", step="month", stepmode="backward"),
            dict(count=6, label="6A", step="month", stepmode="backward"),
            dict(count=1, label="YTD", step="year", stepmode="todate"),
            dict(step="all", label="TÜMÜ")
        ])
    ) if show_range_buttons else None

    fig.update_layout(
        autosize=True,
        height=height,
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            automargin=True,
            showspikes=True, spikemode='across', spikesnap='cursor',
            spikecolor='rgba(132, 142, 156, 0.45)', spikethickness=1, spikedash='solid',
            rangeselector=range_selector
        ),
        yaxis=dict(
            title=y_title,
            side='right',
            automargin=True,
            showgrid=True,
            gridcolor='rgba(132, 142, 156, 0.12)',
            zeroline=False,
            showspikes=True, spikemode='across', spikesnap='cursor',
            spikecolor='rgba(132, 142, 156, 0.45)', spikethickness=1, spikedash='solid'
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=45, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- ANA VERİ ÇAĞRISI VE BAŞLIK ---
results, errors, usd_try_rate, market_pulse = fetch_portfolio_data(portfolio_transactions)
fx_multiplier = 1.0 if "USD" in base_currency else usd_try_rate
guncel_saat = datetime.now(tz_TR).strftime('%H:%M:%S')
total_tx_count = sum(len(v) for v in portfolio_transactions.values())

# ÜST PİYASA BANDI (TICKER BAR)
st.markdown(f"""
<div class="ticker-bar">
    <div class="ticker-item"><span class="ticker-label">TERMINAL</span><span class="ticker-val" style="color:#5282FF;">LIVE PORTFOLIO PRO</span></div>
    <div class="ticker-item"><span class="ticker-label">ENGINE</span><span class="ticker-val" style="color:#00E676;">AUTO-WAC ACTIVE</span></div>
    <div class="ticker-item"><span class="ticker-label">USD/TRY</span><span class="ticker-val">₺{usd_try_rate:,.2f}</span></div>
    <div class="ticker-item"><span class="ticker-label">GRAM ALTIN</span><span class="ticker-val">${market_pulse['GOLD_GRAM_USD']:,.2f} (₺{market_pulse['GOLD_GRAM_USD']*usd_try_rate:,.2f})</span></div>
    <div class="ticker-item"><span class="ticker-label">S&P 500</span><span class="ticker-val">{market_pulse['SP500']:,.2f}</span></div>
    <div class="ticker-item"><span class="ticker-label">BIST 100</span><span class="ticker-val">{market_pulse['BIST100']:,.2f}</span></div>
    <div class="ticker-item" style="margin-left:auto;"><span class="ticker-label">SENKRONİZASYON:</span><span class="ticker-val">{guncel_saat}</span></div>
</div>
""", unsafe_allow_html=True)

if errors:
    for error in errors:
        st.error(error)

if results:
    df = pd.DataFrame(results)
    
    money_cols = [
        'Avg. Cost', 'Current Price', 'Daily P/L', 'Total Cost', 
        'Current Value', 'Unrealized P/L', 'Realized P/L', 'Dividends', 'Fees & Tax', 'Total Net Return'
    ]
    for col in money_cols:
        df[col] = (df[col] * fx_multiplier).apply(clean_zero)

    # --- BÖLÜM 1: ÖZEL BORSA TERMİNALİ KPI KARTLARI ---
    total_invested = df['Total Cost'].sum()
    total_current = df['Current Value'].sum()
    total_unrealized_pnl = df['Unrealized P/L'].sum()
    total_unrealized_pct = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0.0
    
    total_daily_pnl = df['Daily P/L'].sum()
    prev_total_val = total_current - total_daily_pnl
    total_daily_pct = (total_daily_pnl / prev_total_val * 100) if prev_total_val > 0 else 0.0
    
    realized_pnl = df['Realized P/L'].sum()
    total_dividends = df['Dividends'].sum()
    all_time_net_profit = df['Total Net Return'].sum()

    daily_cls = badge_class(total_daily_pnl)
    unreal_cls = badge_class(total_unrealized_pnl)
    real_cls = badge_class(realized_pnl)
    alltime_cls = badge_class(all_time_net_profit)

    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-title">Aktif Portföy Değeri</div>
            <div class="kpi-value">{curr_symbol}{total_current:,.2f}</div>
            <div class="kpi-sub {daily_cls}">{fmt_currency(total_daily_pnl, curr_symbol)} ({total_daily_pct:+.2f}% Bugün)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Aktif Yatırım Maliyeti</div>
            <div class="kpi-value">{curr_symbol}{total_invested:,.2f}</div>
            <div class="kpi-sub neu-badge">Otomatik Ortalama Maliyet</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Açık Kâr / Zarar</div>
            <div class="kpi-value">{fmt_currency(total_unrealized_pnl, curr_symbol)}</div>
            <div class="kpi-sub {unreal_cls}">{total_unrealized_pct:+.2f}% Aktif Getiri</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Realize Kâr (Satışlar)</div>
            <div class="kpi-value">{fmt_currency(realized_pnl, curr_symbol)}</div>
            <div class="kpi-sub {real_cls}">Vergi & Komisyon Sonrası Net</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Temettü & Nema Geliri</div>
            <div class="kpi-value">{curr_symbol}{total_dividends:,.2f}</div>
            <div class="kpi-sub pos-badge">Pasif Nakit & DRIP ($0 Kom.)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Tüm Zamanlar Net Kâr</div>
            <div class="kpi-value">{fmt_currency(all_time_net_profit, curr_symbol)}</div>
            <div class="kpi-sub {alltime_cls}">Kümülatif Toplam Kazanç</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- SEKMELİ GÖRÜNÜM ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "PORTFÖY VE VARLIK ÖZETİ", 
        "PERFORMANS & ISI HARİTASI", 
        "VERGİ, KOMİSYON & PASİF GELİR",
        "TEKNİK ANALİZ TERMİNALİ",
        "MUHASEBE MOTORU & SİMÜLATÖR",
        f"İŞLEM DEFTERİ ({total_tx_count} KAYIT)"
    ])

    pnl_color_cols = [
        'Daily Change (%)', 'Daily P/L', 'Unrealized P/L', 
        'Unrealized P/L (%)', 'Realized P/L', 'Total Net Return', 'Total ROI (%)'
    ]
    
    def style_pnl_cells(val):
        if pd.isna(val):
            return ''
        if val > 1e-4:
            return 'color: #00C853; font-weight: 600;'
        elif val < -1e-4:
            return 'color: #FF1744; font-weight: 600;'
        return 'color: #848E9C;'

    def style_status_cells(val):
        if val == 'AÇIK':
            return 'color: #2962FF; font-weight: 700;'
        return 'color: #848E9C;'

    # ================= SEKME 1: VARLIKLAR VE KAZANÇ GRAFİKLERİ =================
    with tab1:
        df_display = df[df['Status'] == 'AÇIK'].copy() if hide_closed else df.copy()
        df_display = df_display.sort_values(by=['Status', 'Total Net Return'], ascending=[True, False])
        
        st.markdown("#### Portföy ve Geçmiş Yatırımlar Özeti")

        try:
            styled_table = (
                df_display.style
                .map(style_pnl_cells, subset=pnl_color_cols)
                .map(style_status_cells, subset=['Status'])
            )
        except AttributeError:
            styled_table = (
                df_display.style
                .applymap(style_pnl_cells, subset=pnl_color_cols)
                .applymap(style_status_cells, subset=['Status'])
            )

        st.dataframe(
            styled_table,
            use_container_width=True,
            hide_index=True,
            column_order=[
                'Asset', 'Status', 'Quantity', 'Avg. Cost', 'Current Price', 
                'Daily Change (%)', 'Daily P/L', 'Total Cost', 'Current Value', 
                'Unrealized P/L', 'Unrealized P/L (%)', 'Realized P/L', 'Dividends', 
                'Total Net Return', 'Total ROI (%)'
            ],
            column_config={
                'Asset': st.column_config.TextColumn("Varlık"),
                'Status': st.column_config.TextColumn("Durum"),
                'Quantity': st.column_config.NumberColumn("Aktif Adet/Pay", format="%.4f"),
                'Avg. Cost': st.column_config.NumberColumn(f"Ort. Maliyet ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Current Price': st.column_config.NumberColumn(f"Güncel Fiyat ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Daily Change (%)': st.column_config.NumberColumn("Günlük (%)", format="%.2f%%"),
                'Daily P/L': st.column_config.NumberColumn(f"Günlük P/L ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Total Cost': st.column_config.NumberColumn(f"Aktif Maliyet ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Current Value': st.column_config.NumberColumn(f"Güncel Değer ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Unrealized P/L': st.column_config.NumberColumn(f"Açık P/L ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Unrealized P/L (%)': st.column_config.NumberColumn("Açık P/L (%)", format="%.2f%%"),
                'Realized P/L': st.column_config.NumberColumn(f"Realize Kâr ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Dividends': st.column_config.NumberColumn(f"Temettü/Nema ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Total Net Return': st.column_config.NumberColumn(f"Toplam Net Kâr ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Total ROI (%)': st.column_config.NumberColumn("Toplam Kâr (%)", format="%.2f%%"),
            }
        )

        st.markdown("---")
        col_pie, col_bar = st.columns([1, 1.45])
        
        with col_pie:
            st.markdown("#### Aktif Varlık Dağılımı")
            df_pie = df[df['Current Value'] > 0]
            if not df_pie.empty:
                fig_pie = px.pie(
                    df_pie, 
                    values='Current Value', 
                    names='Asset',
                    hole=0.58,
                    color_discrete_sequence=['#2962FF', '#00E676', '#FFAB00', '#00B0FF', '#AA00FF']
                )
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent+label',
                    hovertemplate=f"<b>%{{label}}</b><br>Büyüklük: {curr_symbol}%{{value:,.2f}}<br>Pay: %{{percent}}"
                )
                fig_pie.update_layout(
                    autosize=True,
                    height=520,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5),
                    margin=dict(t=20, b=40, l=10, r=10),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_pie, use_container_width=True, config=PLOTLY_CONFIG)
            else:
                st.info("Açık pozisyon bulunmuyor.")

        with col_bar:
            st.markdown("#### Varlık Bazlı Net Kazanç Katkısı")
            df_bar = df.sort_values('Total Net Return', ascending=True).copy()
            bar_colors = ['#00C853' if v >= 0 else '#FF1744' for v in df_bar['Total Net Return']]
            
            max_v = max(df_bar['Total Net Return'].max(), 10.0)
            min_v = min(df_bar['Total Net Return'].min(), -10.0)
            
            bar_texts = [
                f"  {fmt_currency(v, curr_symbol)} ({r:+.1f}%)" if abs(r) > 0.01 else f"  {fmt_currency(v, curr_symbol)}"
                for v, r in zip(df_bar['Total Net Return'], df_bar['Total ROI (%)'])
            ]
            
            fig_bar = go.Figure(go.Bar(
                x=df_bar['Total Net Return'],
                y=df_bar['Asset'],
                orientation='h',
                marker_color=bar_colors,
                hovertemplate=f"<b>%{{y}}</b><br>Net Kâr: {curr_symbol}%{{x:,.2f}}<extra></extra>"
            ))
            
            fig_bar.add_trace(go.Scatter(
                x=[max(v, 0.0) for v in df_bar['Total Net Return']],
                y=df_bar['Asset'],
                mode='text',
                text=bar_texts,
                textposition='middle right',
                textfont=dict(
                    size=11,
                    family="SF Mono, Roboto Mono, monospace",
                    color=['#FF1744' if v < 0 else '#848E9C' for v in df_bar['Total Net Return']]
                ),
                hoverinfo='skip',
                cliponaxis=False
            ))
            
            fig_bar.update_layout(
                autosize=True,
                height=520,
                showlegend=False,
                bargap=0.26,
                xaxis_title=f"Toplam Net Kâr ({curr_symbol})",
                yaxis_title="",
                margin=dict(t=10, b=20, l=10, r=90),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    range=[min_v * 3.5, max_v * 1.32],
                    gridcolor='rgba(132, 142, 156, 0.15)',
                    zeroline=True,
                    zerolinecolor='rgba(132, 142, 156, 0.4)',
                    zerolinewidth=1.5
                ),
                yaxis=dict(automargin=True)
            )
            st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_CONFIG)

    # ================= SEKME 2: X-TARZI PÜRÜZSÜZ GRAFİKLER VE AYLIK ISI HARİTASI =================
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
            st.caption("Grafiklerin sol üst köşesindeki 1A, 3A, 6A, YTD, TÜMÜ butonlarına tıklayarak zaman aralığını değiştirebilir, çift tıklayarak sıfırlayabilirsiniz.")

            # 1. GRAFİK: Kümülatif Net Kâr Evrimi
            st.markdown("#### Kümülatif Net Kâr Şeması (Realize Kârlar + Açık Kâr + Temettü & Nema)")
            fig_profit = go.Figure()
            fig_profit.add_trace(go.Scatter(
                x=df_history.index,
                y=df_history['Total_Net_Profit'] * fx_multiplier,
                mode='lines',
                name=f'Kümülatif Net Kâr ({curr_symbol})',
                line=dict(color='#00C853', width=2.8, shape='spline', smoothing=0.6),
                fill='tozeroy',
                fillcolor='rgba(0, 200, 83, 0.12)',
                hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>Net Kâr: {curr_symbol}%{{y:,.2f}}<extra></extra>"
            ))
            fig_profit = apply_x_smooth_layout(fig_profit, y_title=f"Net Kâr ({curr_symbol})", height=420)
            st.plotly_chart(fig_profit, use_container_width=True, config=PLOTLY_CONFIG)

            # 2. GRAFİK: Aktif Portföy Büyüklüğü ve Maliyet
            st.markdown("---")
            st.markdown("#### Aktif Portföy Değeri ve Yatırılan Ana Para")
            fig_value = go.Figure()
            fig_value.add_trace(go.Scatter(
                x=df_history.index,
                y=df_history['Active_Value'] * fx_multiplier,
                mode='lines',
                name=f'Portföy Değeri ({curr_symbol})',
                line=dict(color='#2962FF', width=2.8, shape='spline', smoothing=0.6),
                fill='tozeroy',
                fillcolor='rgba(41, 98, 255, 0.12)'
            ))
            fig_value.add_trace(go.Scatter(
                x=df_history.index,
                y=df_history['Active_Cost'] * fx_multiplier,
                mode='lines',
                name=f'Yatırılan Maliyet ({curr_symbol})',
                line=dict(color='#FFAB00', width=2.0, dash='dash', shape='hv')
            ))
            fig_value = apply_x_smooth_layout(fig_value, y_title=f"Büyüklük ({curr_symbol})", height=420)
            st.plotly_chart(fig_value, use_container_width=True, config=PLOTLY_CONFIG)

            # 3. AYLIK KÂR / ZARAR ISI HARİTASI (MONTHLY RETURNS HEATMAP)
            st.markdown("---")
            st.markdown(f"#### Aylık Net Kazanç Isı Haritası ({curr_symbol})")
            st.caption("Her hücre, ilgili ay içinde portföyünüzün ürettiği net kâr/zarar değişimini gösterir.")

            monthly_cum = (df_history['Total_Net_Profit'] * fx_multiplier).resample('ME').last()
            monthly_delta = monthly_cum.diff()
            monthly_delta.iloc[0] = monthly_cum.iloc[0]

            df_hm = pd.DataFrame({
                'Year': monthly_delta.index.year,
                'Month': monthly_delta.index.month,
                'Net_PnL': monthly_delta.values
            })

            month_names = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
            pivot_hm = df_hm.pivot(index='Year', columns='Month', values='Net_PnL')
            for m in range(1, 13):
                if m not in pivot_hm.columns:
                    pivot_hm[m] = np.nan
            pivot_hm = pivot_hm[range(1, 13)]
            pivot_hm.columns = month_names

            z_vals = pivot_hm.values
            text_vals = np.where(
                np.isnan(z_vals), 
                "", 
                np.vectorize(lambda v: f"{fmt_currency(v, curr_symbol)}")(np.nan_to_num(z_vals))
            )

            max_abs = max(abs(np.nanmin(z_vals)), abs(np.nanmax(z_vals)), 1.0)
            fig_hm = go.Figure(data=go.Heatmap(
                z=z_vals,
                x=month_names,
                y=[str(y) for y in pivot_hm.index],
                text=text_vals,
                texttemplate="%{text}",
                textfont={"size": 12, "family": "SF Mono, Roboto Mono, monospace", "color": "#FFFFFF"},
                colorscale=[
                    [0.0, '#D50000'],
                    [0.45, '#5C1A24'],
                    [0.5, '#1E2330'],
                    [0.55, '#144A2E'],
                    [1.0, '#00C853']
                ],
                zmin=-max_abs,
                zmax=max_abs,
                showscale=False,
                xgap=4,
                ygap=4,
                hovertemplate=f"<b>Yıl: %{{y}} | Ay: %{{x}}</b><br>Aylık Net Değişim: %{{text}}<extra></extra>"
            ))
            fig_hm.update_layout(
                autosize=True,
                height=250,
                margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(side='top', showgrid=False, automargin=True),
                yaxis=dict(showgrid=False, autorange='reversed', automargin=True)
            )
            st.plotly_chart(fig_hm, use_container_width=True, config=PLOTLY_CONFIG)

    # ================= SEKME 3: VERGİ (STOPAJ), KOMİSYON & PASİF GELİR ANALİZ PANELİ =================
    with tab3:
        st.markdown("#### Vergi (Stopaj), Borsa Komisyonu ve Pasif Gelir Analizi")

        fee_records = []
        passive_records = []

        for ticker, txs in portfolio_transactions.items():
            asset_label = ASSET_NAMES.get(ticker, ticker)
            for tx in txs:
                f_usd = tx.get('Fee', 0.0)
                f_try = tx.get('Fee_TRY', None)
                f_type = tx.get('Fee_Type', 'Komisyon / Vergi')
                div_usd = tx.get('Dividend', 0.0)

                if f_usd > 0 or (f_try is not None and f_try > 0):
                    fee_records.append({
                        'Tarih': tx['Date'],
                        'Varlık': asset_label,
                        'Kesinti Türü': f_type,
                        'Tutar_USD': f_usd,
                        'Orijinal_TL': f_try if f_try is not None else 0.0,
                        'Detay': tx.get('Note', '')
                    })

                if div_usd > 0:
                    passive_records.append({
                        'Tarih': pd.to_datetime(tx['Date']),
                        'Ay': pd.to_datetime(tx['Date']).strftime('%Y-%m'),
                        'Varlık': asset_label,
                        'Gelir Tipi': 'DRIP (Hisseye Dönüşen)' if tx.get('Action') == 'DRIP' else 'Nakit Temettü / Nema',
                        'Tutar_USD': div_usd,
                        'Not': tx.get('Note', '')
                    })

        df_fees = pd.DataFrame(fee_records)
        df_passive = pd.DataFrame(passive_records)

        total_fees_val = (df_fees['Tutar_USD'].sum() * fx_multiplier) if not df_fees.empty else 0.0
        total_stopaj_try = df_fees[df_fees['Kesinti Türü'] == 'Stopaj Vergisi']['Orijinal_TL'].sum() if not df_fees.empty else 0.0
        total_us_comm_usd = df_fees[df_fees['Kesinti Türü'] == 'ABD Borsası Komisyonu']['Tutar_USD'].sum() if not df_fees.empty else 0.0
        total_aninda_try = df_fees[df_fees['Kesinti Türü'] == 'Anında Nakit & Komisyon']['Orijinal_TL'].sum() if not df_fees.empty else 0.0

        gross_profit_before_fees = all_time_net_profit + total_fees_val
        fee_drag_pct = (total_fees_val / gross_profit_before_fees * 100) if gross_profit_before_fees > 0 else 0.0

        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Brüt Kazanç (Kesinti Öncesi)</div>
                <div class="kpi-value">{curr_symbol}{gross_profit_before_fees:,.2f}</div>
                <div class="kpi-sub pos-badge">Tüm Zamanlar Brüt Üretim</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Toplam Stopaj & Komisyon</div>
                <div class="kpi-value">-{curr_symbol}{total_fees_val:,.2f}</div>
                <div class="kpi-sub neg-badge">Brüt Kârın %{fee_drag_pct:.2f}'si Kesildi</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Ödenen Fon/Nema Stopajı</div>
                <div class="kpi-value">₺{total_stopaj_try:,.2f}</div>
                <div class="kpi-sub neu-badge">Resmi Stopaj Kesintileri Toplamı</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">ABD Borsa & Anında Nakit Kom.</div>
                <div class="kpi-value">${total_us_comm_usd:,.2f} + ₺{total_aninda_try:,.2f}</div>
                <div class="kpi-sub neu-badge">Midas İşlem & Takas Masrafları</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_tax1, col_tax2 = st.columns([1, 1.2])

        with col_tax1:
            st.markdown("#### Kesinti ve Vergi Kırılımı")
            if not df_fees.empty:
                df_fee_grp = df_fees.groupby('Kesinti Türü', as_index=False)['Tutar_USD'].sum()
                df_fee_grp['Tutar_Display'] = df_fee_grp['Tutar_USD'] * fx_multiplier
                fig_tax = px.pie(
                    df_fee_grp,
                    values='Tutar_Display',
                    names='Kesinti Türü',
                    hole=0.58,
                    color_discrete_sequence=['#FF3B69', '#FFAB00', '#AA00FF', '#00B0FF']
                )
                fig_tax.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    hovertemplate=f"<b>%{{label}}</b><br>Tutar: {curr_symbol}%{{value:,.2f}}<br>Oran: %{{percent}}"
                )
                fig_tax.update_layout(
                    autosize=True,
                    height=380,
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                    margin=dict(t=15, b=35, l=10, r=10),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_tax, use_container_width=True, config=PLOTLY_CONFIG)

        with col_tax2:
            st.markdown("#### Aylık Pasif Gelir Akışı (Temettü, DRIP & Nema)")
            if not df_passive.empty:
                df_passive['Tutar_Display'] = df_passive['Tutar_USD'] * fx_multiplier
                fig_pas = px.bar(
                    df_passive,
                    x='Ay',
                    y='Tutar_Display',
                    color='Gelir Tipi',
                    barmode='stack',
                    text_auto='.2f',
                    color_discrete_map={
                        'DRIP (Hisseye Dönüşen)': '#00C853',
                        'Nakit Temettü / Nema': '#2962FF'
                    }
                )
                fig_pas.update_layout(
                    autosize=True,
                    height=380,
                    xaxis_title="Dönem",
                    yaxis_title=f"Pasif Gelir ({curr_symbol})",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(t=30, b=10, l=10, r=10),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_pas, use_container_width=True, config=PLOTLY_CONFIG)

        st.markdown("---")
        st.markdown("#### Kesilen Tüm Vergi (Stopaj) ve Komisyonların Detaylı Listesi")
        if not df_fees.empty:
            df_fees_disp = df_fees.sort_values('Tarih', ascending=False).copy()
            df_fees_disp[f'Tutar ({curr_symbol})'] = df_fees_disp['Tutar_USD'] * fx_multiplier
            df_fees_disp['Orijinal TL Kesintisi'] = df_fees_disp['Orijinal_TL'].apply(lambda x: f"₺{x:,.2f}" if x > 0 else "-")
            st.dataframe(
                df_fees_disp[['Tarih', 'Varlık', 'Kesinti Türü', f'Tutar ({curr_symbol})', 'Orijinal TL Kesintisi', 'Detay']],
                use_container_width=True,
                hide_index=True
            )

    # ================= SEKME 4: TEKNİK ANALİZ TERMİNALİ =================
    with tab4:
        st.markdown("#### Canlı Piyasa & Teknik Analiz Terminali")
        
        yf_supported_tickers = ['GRID', 'GC=F', 'ASELS.IS', 'CCOLA.IS', 'CGCAM.IS', 'ALTIN.IS']
        c_sel1, c_sel2, c_sel3, c_sel4 = st.columns([2, 1.2, 1.2, 1.6])
        
        with c_sel1:
            selected_ta_ticker = st.selectbox(
                "Enstrüman Seçimi",
                options=yf_supported_tickers,
                format_func=lambda x: ASSET_NAMES.get(x, x)
            )
        with c_sel2:
            ta_period = st.selectbox("Periyot", options=["1mo", "3mo", "6mo", "1y", "2y"], index=3)
        with c_sel3:
            ta_chart_type = st.radio("Grafik Tipi", options=["X-Tarzı Eğri (Spline)", "Mum (Candlestick)"], horizontal=True)
        with c_sel4:
            show_sma = st.multiselect("Teknik Katmanlar", options=["SMA 20", "SMA 50", "İşlem Noktalarım"], default=["SMA 20", "İşlem Noktalarım"])

        try:
            ta_df = yf.Ticker(selected_ta_ticker).history(period=ta_period)
            if not ta_df.empty:
                ta_df.index = pd.to_datetime(ta_df.index).tz_localize(None)
                if selected_ta_ticker == 'GC=F':
                    for col in ['Open', 'High', 'Low', 'Close']:
                        ta_df[col] = ta_df[col] / 31.1035
                    unit_label = "USD / Gram"
                elif selected_ta_ticker.endswith('.IS'):
                    unit_label = "TRY (₺)"
                else:
                    unit_label = "USD ($)"

                ta_df['SMA20'] = ta_df['Close'].rolling(window=20).mean()
                ta_df['SMA50'] = ta_df['Close'].rolling(window=50).mean()

                fig_ta = go.Figure()
                if "Mum" in ta_chart_type:
                    fig_ta.add_trace(go.Candlestick(
                        x=ta_df.index,
                        open=ta_df['Open'],
                        high=ta_df['High'],
                        low=ta_df['Low'],
                        close=ta_df['Close'],
                        name=selected_ta_ticker,
                        increasing_line_color='#00C853',
                        decreasing_line_color='#FF1744'
                    ))
                else:
                    is_up = ta_df['Close'].iloc[-1] >= ta_df['Close'].iloc[0]
                    s_color = '#00C853' if is_up else '#FF1744'
                    s_fill = 'rgba(0, 200, 83, 0.12)' if is_up else 'rgba(255, 23, 68, 0.12)'
                    fig_ta.add_trace(go.Scatter(
                        x=ta_df.index,
                        y=ta_df['Close'],
                        mode='lines',
                        name=selected_ta_ticker,
                        line=dict(color=s_color, width=2.8, shape='spline', smoothing=0.6),
                        fill='tozeroy',
                        fillcolor=s_fill
                    ))

                if "SMA 20" in show_sma:
                    fig_ta.add_trace(go.Scatter(
                        x=ta_df.index, y=ta_df['SMA20'], mode='lines', 
                        name='SMA 20', line=dict(color='#FFAB00', width=1.6, shape='spline')
                    ))
                if "SMA 50" in show_sma:
                    fig_ta.add_trace(go.Scatter(
                        x=ta_df.index, y=ta_df['SMA50'], mode='lines', 
                        name='SMA 50', line=dict(color='#00B0FF', width=1.6, shape='spline')
                    ))

                if "İşlem Noktalarım" in show_sma and selected_ta_ticker in portfolio_transactions:
                    buy_dates, buy_prices = [], []
                    sell_dates, sell_prices = [], []
                    for tx in portfolio_transactions[selected_ta_ticker]:
                        tx_dt = pd.to_datetime(tx['Date']).tz_localize(None)
                        if tx_dt >= ta_df.index.min():
                            closest_idx = ta_df.index.get_indexer([tx_dt], method='nearest')[0]
                            px_val = ta_df['Close'].iloc[closest_idx]
                            if tx.get('Quantity', 0) > 0:
                                buy_dates.append(ta_df.index[closest_idx])
                                buy_prices.append(px_val)
                            elif tx.get('Quantity', 0) < 0:
                                sell_dates.append(ta_df.index[closest_idx])
                                sell_prices.append(px_val)

                    if buy_dates:
                        fig_ta.add_trace(go.Scatter(
                            x=buy_dates, y=buy_prices, mode='markers', name='ALIM (BUY/DRIP)',
                            marker=dict(symbol='triangle-up', size=13, color='#00C853', line=dict(width=1, color='#000000'))
                        ))
                    if sell_dates:
                        fig_ta.add_trace(go.Scatter(
                            x=sell_dates, y=sell_prices, mode='markers', name='SATIM (SELL)',
                            marker=dict(symbol='triangle-down', size=13, color='#FF1744', line=dict(width=1, color='#000000'))
                        ))

                fig_ta.update_layout(xaxis_rangeslider_visible=False)
                fig_ta = apply_x_smooth_layout(fig_ta, y_title=f"Fiyat ({unit_label})", show_range_buttons=False, height=500)
                st.plotly_chart(fig_ta, use_container_width=True, config=PLOTLY_CONFIG)
            else:
                st.warning("Seçilen enstrüman için tarihsel grafik verisi bulunamadı.")
        except Exception as e:
            st.error(f"Teknik analiz grafiği yüklenirken hata: {str(e)}")

    # ================= SEKME 5: OTOMATİK MUHASEBE MOTORU & KOD ÜRETİCİ =================
    with tab5:
        st.markdown("#### Otomatik Maliyet Simülatörü & Yeni İşlem Kod Üretici")
        st.caption("Sol taraftan herhangi bir hisse/fon seçip işlem simülasyonu yapabilir, sağ tarafta otomatik oluşan kod satırını kopyalayıp canli.py dosyanıza yapıştırabilirsiniz.")

        sim_col1, sim_col2 = st.columns([1.15, 1.25])

        with sim_col1:
            st.markdown("##### 1. İşlem Detaylarını Girin / Test Edin")
            
            asset_options = list(portfolio_transactions.keys()) + ["+ YENİ VARLIK EKLE"]
            selected_sim_ticker = st.selectbox(
                "Varlık Seçin",
                options=asset_options,
                index=asset_options.index('GRID') if 'GRID' in asset_options else 0,
                format_func=lambda x: ASSET_NAMES.get(x, x) if x != "+ YENİ VARLIK EKLE" else "+ Yeni Hisse / Fon Kodu Gir"
            )

            if selected_sim_ticker == "+ YENİ VARLIK EKLE":
                custom_ticker = st.text_input("Yeni Sembol Kodu (Örn: AAPL, THYAO.IS, TLY)", value="NVDA").upper().strip()
                active_ticker = custom_ticker if custom_ticker else "YENI"
                cur_qty, cur_cost_usd, cur_avg_usd, cur_price_usd = 0.0, 0.0, 0.0, 100.0
            else:
                active_ticker = selected_sim_ticker
                row_match = df[df['Ticker'] == active_ticker]
                if not row_match.empty:
                    r_data = row_match.iloc[0]
                    cur_qty = float(r_data['Quantity'])
                    cur_cost_usd = float(r_data['Total Cost']) / fx_multiplier
                    cur_avg_usd = float(r_data['Avg. Cost']) / fx_multiplier
                    cur_price_usd = float(r_data['Current Price']) / fx_multiplier
                else:
                    cur_qty, cur_cost_usd, cur_avg_usd, cur_price_usd = 0.0, 0.0, 0.0, 0.0

            sim_date = st.date_input("İşlem Tarihi", value=datetime.now(tz_TR).date())
            sim_action = st.radio(
                "İşlem Tipi",
                options=["Yeni Alım (BUY)", "Kısmi / Tam Satış (SELL)", "Temettü Geri Yatırımı (DRIP)", "Nakit Temettü / Nema (DIVIDEND)"],
                horizontal=True
            )

            default_fee = 1.50 if (active_ticker in US_STOCK_TICKERS and ("BUY" in sim_action or "SELL" in sim_action)) else 0.0
            sim_note = st.text_input("İşlem Notu (İsteğe Bağlı)", value="")

            if "BUY" in sim_action:
                c1, c2, c3 = st.columns(3)
                sim_qty = c1.number_input("Alınan Adet / Pay", min_value=0.000001, value=1.0, step=0.1, format="%.6f")
                sim_gross = c2.number_input("Brüt Alım Tutarı ($)", min_value=0.01, value=round(max(cur_price_usd, 10.0), 2), step=10.0)
                sim_fee = c3.number_input("Komisyon ($)", min_value=0.0, value=default_fee, step=0.50)

                total_added = sim_gross + sim_fee
                new_qty = cur_qty + sim_qty
                new_cost = cur_cost_usd + total_added
                new_avg = new_cost / new_qty if new_qty > 0 else 0.0

                st.info(
                    f"**Alım Simülasyonu Özeti ({active_ticker}):**\n"
                    f"- **Maliyete Eklenecek Tutar (Komisyon Dahil):** `+${total_added:,.2f}`\n"
                    f"- **Önceki Adet:** `{cur_qty:.4f}` -> **Yeni Toplam Adet:** `{new_qty:.4f}`\n"
                    f"- **Önceki Ort. Maliyet:** `${cur_avg_usd:,.2f}` -> **Yeni Ort. Maliyet:** **`${new_avg:,.2f}`**"
                )
                generated_line = f"{{'Date': '{sim_date}', 'Action': 'BUY', 'Quantity': {sim_qty}, 'Gross_Amount': {sim_gross:.2f}, 'Fee': {sim_fee:.2f}, 'Note': '{sim_note or 'Alım İşlemi'}'}},"

            elif "SELL" in sim_action:
                if cur_qty > 0:
                    sell_mode = st.radio("Satış Miktarı Belirleme", ["Yüzde (%) ile Seç", "Adet Yazarak Seç"], horizontal=True)
                    if sell_mode == "Yüzde (%) ile Seç":
                        sell_pct = st.slider("Satılacak Pozisyon Oranı (%)", min_value=1, max_value=100, value=25)
                        sim_qty = round(cur_qty * (sell_pct / 100.0), 8)
                    else:
                        sim_qty = st.number_input("Satılacak Adet", min_value=0.000001, max_value=float(cur_qty), value=float(cur_qty), format="%.6f")
                        sell_pct = (sim_qty / cur_qty) * 100.0
                else:
                    st.warning(f"{active_ticker} için şu an açık pozisyonunuz (0 adet) bulunmuyor, yine de geçmiş satış kodu üretebilirsiniz.")
                    sim_qty = st.number_input("Satılan Adet", min_value=0.000001, value=1.0, format="%.6f")
                    sell_pct = 100.0

                c1, c2 = st.columns(2)
                default_sell_gross = round(sim_qty * cur_price_usd, 2) if cur_price_usd > 0 else 100.0
                sim_gross_proc = c1.number_input("Toplam Brüt Satış Tutarı ($)", min_value=0.01, value=max(default_sell_gross, 0.01), step=10.0)
                sim_fee = c2.number_input("Komisyon / Stopaj ($)", min_value=0.0, value=default_fee, step=0.50)

                net_proc = sim_gross_proc - sim_fee
                cost_removed = cur_cost_usd * (sell_pct / 100.0) if cur_qty > 0 else 0.0
                realized_pnl = net_proc - cost_removed
                rem_qty = max(0.0, cur_qty - sim_qty)
                rem_cost = max(0.0, cur_cost_usd - cost_removed)

                st.info(
                    f"**Satış Simülasyonu Özeti ({active_ticker} - %{sell_pct:.1f} Satış):**\n"
                    f"- **Satılacak Adet:** `{sim_qty:.6f} pay` | **Net Ele Geçen:** `${net_proc:,.2f}`\n"
                    f"- **Otomatik Düşülecek Maliyet:** `-${cost_removed:,.2f}` (Pay başı `${cur_avg_usd:,.2f}` ortalamadan)\n"
                    f"- **Bu Satıştan Yazılacak Net Kâr/Zarar:** **`{fmt_currency(realized_pnl, '$')}`**\n"
                    f"- **Satış Sonrası Kalan:** `{rem_qty:.4f} pay` (`${rem_cost:,.2f}` aktif maliyet)"
                )
                generated_line = f"{{'Date': '{sim_date}', 'Action': 'SELL', 'Quantity': {sim_qty}, 'Gross_Proceeds': {sim_gross_proc:.2f}, 'Fee': {sim_fee:.2f}, 'Note': '{sim_note or 'Satış İşlemi'}'}},"

            elif "DRIP" in sim_action:
                c1, c2 = st.columns(2)
                sim_qty = c1.number_input("Eklenecek Bedelsiz Pay Adedi", min_value=0.000001, value=0.015000, format="%.8f")
                sim_div = c2.number_input("Yatan Temettü Tutarı ($)", min_value=0.01, value=2.50, step=0.50)

                new_qty = cur_qty + sim_qty
                new_avg = cur_cost_usd / new_qty if new_qty > 0 else 0.0

                st.info(
                    f"**DRIP Simülasyonu Özeti ({active_ticker} - Komisyonsuz):**\n"
                    f"- **Yeni Toplam Pay:** `{cur_qty:.4f}` -> `{new_qty:.6f} pay`\n"
                    f"- **Eski Ort. Maliyet:** `${cur_avg_usd:,.2f}` -> **Yeni Düşürülmüş Ort. Maliyet:** **`${new_avg:,.2f}`**"
                )
                generated_line = f"{{'Date': '{sim_date}', 'Action': 'DRIP', 'Quantity': {sim_qty}, 'Dividend': {sim_div:.2f}, 'Fee': 0.0, 'Note': '{sim_note or 'Temettü Geri Yatırımı (DRIP)'}'}},"

            else:
                c1, c2 = st.columns(2)
                sim_div = c1.number_input("Net Temettü / Nema Tutarı ($)", min_value=0.01, value=1.00, step=0.25)
                sim_fee = c2.number_input("Varsa Stopaj Kesintisi ($)", min_value=0.0, value=0.0, step=0.10)
                generated_line = f"{{'Date': '{sim_date}', 'Action': 'DIVIDEND', 'Quantity': 0.0, 'Dividend': {sim_div:.2f}, 'Fee': {sim_fee:.2f}, 'Note': '{sim_note or 'Nakit Temettü / Nema'}'}},"

        with sim_col2:
            st.markdown("##### 2. Otomatik Üretilen Kod Satırı (Kopyala & Yapıştır)")
            st.success(f"Aşağıdaki satırı kopyalayıp `canli.py` dosyanızdaki `'{active_ticker}'` listesinin en altına yapıştırmanız yeterlidir:")
            
            st.code(f"# '{active_ticker}' listesine eklenecek hazır satır:\n{generated_line}", language="python")
            
            st.markdown("---")
            st.markdown("##### Nasıl Çalışır?")
            st.markdown(
                "1. **İşlem Öncesi Test:** Midas'ta alım veya satım yapmadan önce sol tarafta rakamları değiştirerek ortalama maliyetinizin nasıl değişeceğini ve kaç dolar net kâr/zarar yazacağını görün.\n"
                "2. **İşlem Sonrası Kayıt:** İşlemi gerçekleştirdiğinizde sol taraftaki kutulara gerçekleşen adedi ve tutarı yazın.\n"
                "3. **Tek Tıkla Kopyala:** Sağ üstteki kod kutusunun köşesindeki **Kopyala** ikonuna tıklayıp GitHub'daki `canli.py` dosyanıza yapıştırın. Maliyet düşümü ve kâr hesabını motor otomatik yapacaktır."
            )

    # ================= SEKME 6: İŞLEM GEÇMİŞİ LOGU =================
    with tab6:
        st.markdown("#### Muhasebe Motoru İşlem Defteri (Otomatik Maliyet & Kâr Dökümü)")
        
        filter_asset = st.selectbox(
            "Varlığa Göre Filtrele",
            options=["Tümü"] + [ASSET_NAMES.get(k, k) for k in portfolio_transactions.keys()]
        )
        
        tx_rows = []
        for ticker, txs in portfolio_transactions.items():
            asset_label = ASSET_NAMES.get(ticker, ticker)
            if filter_asset != "Tümü" and asset_label != filter_asset:
                continue
                
            for tx in txs:
                action = tx.get('Action', 'BUY')
                q = clean_zero(tx.get('Quantity', 0.0))
                c = clean_zero(tx.get('Total_Cost', 0.0) * fx_multiplier)
                r = clean_zero(tx.get('Realized_Profit', 0.0) * fx_multiplier)
                d = clean_zero(tx.get('Dividend', 0.0) * fx_multiplier)
                fee = clean_zero(tx.get('Fee', 0.0) * fx_multiplier)
                sell_ratio = tx.get('Sell_Ratio_Pct', 0.0)
                running_avg = clean_zero(tx.get('Running_Avg_Cost', 0.0) * fx_multiplier)
                try_amt = tx.get('TRY_Amount', None)
                note = tx.get('Note', '')
                
                if action == 'DIVIDEND':
                    tx_type = "DIVIDEND / NEMA"
                elif action == 'DRIP':
                    tx_type = "DRIP (TEMETTÜ YATIRIMI)"
                elif action == 'BUY':
                    tx_type = "BUY (ALIM)"
                else:
                    tx_type = f"SELL (%{sell_ratio:.1f} SATIŞ)"
                    
                tx_rows.append({
                    'Tarih': tx['Date'],
                    'Varlık': asset_label,
                    'İşlem Tipi': tx_type,
                    'Miktar / Pay': q,
                    f'Maliyet Değişimi ({curr_symbol})': c,
                    f'İşlem Sonrası Ort. Maliyet ({curr_symbol})': running_avg,
                    f'Komisyon / Stopaj ({curr_symbol})': fee,
                    f'Otomatik Realize Kâr ({curr_symbol})': r,
                    f'Temettü/Nema ({curr_symbol})': d,
                    'Orijinal TL (₺)': f"₺{abs(try_amt):,.2f}" if try_amt is not None else "-",
                    'Not': note
                })
        
        df_tx_log = pd.DataFrame(tx_rows).sort_values('Tarih', ascending=False)
        
        def style_tx_type(val):
            if "BUY" in val:
                return 'color: #00C853; font-weight: 600;'
            elif "SELL" in val:
                return 'color: #FF1744; font-weight: 600;'
            elif "DRIP" in val or "DIVIDEND" in val:
                return 'color: #2962FF; font-weight: 600;'
            return ''

        try:
            styled_log = (
                df_tx_log.style
                .map(style_tx_type, subset=['İşlem Tipi'])
                .map(style_pnl_cells, subset=[f'Otomatik Realize Kâr ({curr_symbol})'])
            )
        except AttributeError:
            styled_log = (
                df_tx_log.style
                .applymap(style_tx_type, subset=['İşlem Tipi'])
                .applymap(style_pnl_cells, subset=[f'Otomatik Realize Kâr ({curr_symbol})'])
            )

        st.dataframe(styled_log, use_container_width=True, hide_index=True)

else:
    st.warning("Ekranda listelenecek geçerli bir veri bulunamadı.")

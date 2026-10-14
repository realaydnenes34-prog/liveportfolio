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

# --- PROFESYONEL BORSA TERMİNALİ CSS STİLİ ---
st.markdown("""
<style>
    /* Genel Arka Plan ve Tipografi */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    
    /* Üst Piyasa Bandı (Ticker Tape) */
    .ticker-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 24px;
        background: rgba(21, 25, 36, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 6px;
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
        color: #848E9C;
        font-weight: 600;
    }
    .ticker-val {
        color: #EAECEF;
        font-weight: 700;
    }

    /* Özel KPI Metrik Kartları */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 14px;
        margin-bottom: 20px;
    }
    .kpi-card {
        background: rgba(21, 25, 36, 0.75);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 16px 18px;
        transition: border-color 0.2s ease;
    }
    .kpi-card:hover {
        border-color: rgba(255, 255, 255, 0.22);
    }
    .kpi-title {
        color: #848E9C;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 8px;
    }
    .kpi-value {
        color: #EAECEF;
        font-size: 1.45rem;
        font-weight: 700;
        font-family: 'SF Mono', 'Roboto Mono', monospace;
        line-height: 1.2;
        margin-bottom: 8px;
    }
    .kpi-sub {
        display: inline-block;
        font-size: 0.76rem;
        font-weight: 600;
        font-family: 'SF Mono', 'Roboto Mono', monospace;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .pos-badge {
        color: #00E676;
        background: rgba(0, 230, 118, 0.12);
    }
    .neg-badge {
        color: #FF3B69;
        background: rgba(255, 59, 105, 0.12);
    }
    .neu-badge {
        color: #848E9C;
        background: rgba(132, 142, 156, 0.12);
    }

    /* Sekme (Tab) Stilleri */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.04em;
    }
</style>
""", unsafe_allow_html=True)

# Türkiye Saat Dilimi (UTC+3)
tz_TR = timezone(timedelta(hours=3))

# Kurumsal Varlık İsimlendirmeleri (Emojisiz)
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

# --- YATIRIM PORTFÖYÜ (TÜM İŞLEM GEÇMİŞİ - GÜN GÜN SIRALI 102 İŞLEM) ---
portfolio_transactions = {
    # 1. İŞ PORTFÖY GÜMÜŞ SERBEST FON (15 Alış, 1 Satış = 16 İşlem)
    'IOG': [
        {'Date': '2024-10-31', 'Quantity': 8.0, 'Total_Cost': 1.29, 'TRY_Amount': 44.33, 'Note': '8 pay x 5.5410 TL'},
        {'Date': '2024-11-06', 'Quantity': 1.0, 'Total_Cost': 0.16, 'TRY_Amount': 5.37, 'Note': '1 pay x 5.3693 TL'},
        {'Date': '2024-11-19', 'Quantity': 3.0, 'Total_Cost': 0.44, 'TRY_Amount': 15.22, 'Note': '3 pay x 5.0743 TL'},
        {'Date': '2025-01-02', 'Quantity': 4.0, 'Total_Cost': 0.55, 'TRY_Amount': 19.34, 'Note': '4 pay x 4.8354 TL'},
        {'Date': '2025-04-07', 'Quantity': 18.0, 'Total_Cost': 2.56, 'TRY_Amount': 97.41, 'Note': '18 pay x 5.4115 TL'},
        {'Date': '2025-04-25', 'Quantity': 16.0, 'Total_Cost': 2.49, 'TRY_Amount': 95.63, 'Note': '16 pay x 5.9771 TL'},
        {'Date': '2025-06-11', 'Quantity': 14.0, 'Total_Cost': 2.40, 'TRY_Amount': 94.37, 'Note': '14 pay x 6.7404 TL'},
        {'Date': '2025-07-10', 'Quantity': 28.0, 'Total_Cost': 4.81, 'TRY_Amount': 192.35, 'Note': '28 pay x 6.8695 TL'},
        {'Date': '2025-07-22', 'Quantity': 19.0, 'Total_Cost': 3.45, 'TRY_Amount': 139.36, 'Note': '19 pay x 7.3350 TL'},
        {'Date': '2025-07-25', 'Quantity': 53.0, 'Total_Cost': 9.71, 'TRY_Amount': 393.25, 'Note': '53 pay x 7.4198 TL'},
        {'Date': '2025-08-15', 'Quantity': 68.0, 'Total_Cost': 12.23, 'TRY_Amount': 499.66, 'Note': '68 pay x 7.3479 TL'},
        {'Date': '2025-08-18', 'Quantity': 23.0, 'Total_Cost': 4.11, 'TRY_Amount': 168.19, 'Note': '23 pay x 7.3125 TL'},
        {'Date': '2025-09-30', 'Quantity': 111.0, 'Total_Cost': 24.26, 'TRY_Amount': 1007.86, 'Note': '111 pay x 9.0798 TL'},
        {'Date': '2025-10-06', 'Quantity': 114.0, 'Total_Cost': 25.31, 'TRY_Amount': 1054.73, 'Note': '114 pay x 9.2520 TL'},
        {'Date': '2025-10-08', 'Quantity': 321.0, 'Total_Cost': 72.01, 'TRY_Amount': 3004.23, 'Note': '321 pay x 9.3590 TL'},
        {'Date': '2026-01-07', 'Quantity': -801.0, 'Total_Cost': -165.78, 'Realized_Profit': 93.26, 'TRY_Amount': -11671.98, 'Note': 'Brüt Satış: 11.671,98 TL | Stopaj (06.01): -825,64 TL | Net Kâr: +4.015,04 TL'}
    ],

    # 2. YAPI KREDİ PORTFÖY ALTIN FONU (4 Alış, 1 Satış = 5 İşlem)
    'YKT': [
        {'Date': '2024-10-31', 'Quantity': 114.0, 'Total_Cost': 1.46, 'TRY_Amount': 49.97, 'Note': '114 pay x 0.4383 TL'},
        {'Date': '2024-11-05', 'Quantity': 69.0, 'Total_Cost': 0.87, 'TRY_Amount': 29.85, 'Note': '69 pay x 0.4325 TL'},
        {'Date': '2024-11-19', 'Quantity': 46.0, 'Total_Cost': 0.57, 'TRY_Amount': 19.62, 'Note': '46 pay x 0.4266 TL'},
        {'Date': '2025-04-07', 'Quantity': 191.0, 'Total_Cost': 2.62, 'TRY_Amount': 99.69, 'Note': '191 pay x 0.5219 TL'},
        {'Date': '2025-04-15', 'Quantity': -420.0, 'Total_Cost': -5.52, 'Realized_Profit': 0.66, 'TRY_Amount': -226.86, 'Note': 'Brüt Satış: 226,86 TL | Stopaj (14.04): -2,52 TL | Net Kâr: +25,21 TL'}
    ],

    # 3. İSTANBUL PORTFÖY BLOCKCHAIN FONU (2 Alış, 1 Satış = 3 İşlem)
    'IVY': [
        {'Date': '2024-11-04', 'Quantity': 17.0, 'Total_Cost': 1.43, 'TRY_Amount': 49.22, 'Note': '17 pay x 2.8954 TL'},
        {'Date': '2024-11-19', 'Quantity': 9.0, 'Total_Cost': 0.85, 'TRY_Amount': 29.49, 'Note': '9 pay x 3.2769 TL'},
        {'Date': '2025-05-02', 'Quantity': -26.0, 'Total_Cost': -2.28, 'Realized_Profit': 0.14, 'TRY_Amount': -84.85, 'Note': 'Brüt Satış: 84,85 TL | Stopaj (01.05): -0,62 TL | Net Kâr: +5,51 TL'}
    ],

    # 4. YAPI KREDİ KOÇ HOLDİNG İŞTİRAK FONU (2 Alış, 1 Satış = 3 İşlem)
    'YAS': [
        {'Date': '2024-11-04', 'Quantity': 6.0, 'Total_Cost': 1.96, 'TRY_Amount': 67.41, 'Note': '6 pay x 11.2342 TL'},
        {'Date': '2024-11-19', 'Quantity': 2.0, 'Total_Cost': 0.71, 'TRY_Amount': 24.44, 'Note': '2 pay x 12.2191 TL'},
        {'Date': '2025-03-28', 'Quantity': -8.0, 'Total_Cost': -2.67, 'Realized_Profit': 0.10, 'TRY_Amount': -95.66, 'Note': 'Satış: 95,66 TL (%0 Stopaj) | Net Kâr: +3,81 TL'}
    ],

    # 5. İŞ PORTFÖY YABANCI HİSSE SENEDİ FONU (2 Alış, 1 Satış = 3 İşlem)
    'TMG': [
        {'Date': '2024-12-06', 'Quantity': 18.0, 'Total_Cost': 0.42, 'TRY_Amount': 14.52, 'Note': '18 pay x 0.8065 TL'},
        {'Date': '2024-12-09', 'Quantity': 61.0, 'Total_Cost': 1.42, 'TRY_Amount': 49.22, 'Note': '61 pay x 0.8070 TL'},
        {'Date': '2025-01-30', 'Quantity': -79.0, 'Total_Cost': -1.84, 'Realized_Profit': -0.04, 'TRY_Amount': -62.46, 'Note': 'Satış: 62,46 TL | Net Zarar: -1,28 TL'}
    ],

    # 6. ÇAĞDAŞ CAM SAN. VE TİC. A.Ş. (1 Halka Arz, 3 Satış = 4 İşlem)
    'CGCAM.IS': [
        {'Date': '2024-12-12', 'Quantity': 4.0, 'Total_Cost': 2.29, 'TRY_Amount': 80.04, 'Note': 'Halka Arz: 4 adet x 20,00 TL (+0,03 TL Komisyon)'},
        {'Date': '2024-12-19', 'Quantity': -2.0, 'Total_Cost': -1.15, 'Realized_Profit': 0.36, 'TRY_Amount': -52.70, 'Note': '2 adet x 26,62 TL | Anında Nakit Kom: -0,51 TL | Net: 52,70 TL'},
        {'Date': '2024-12-30', 'Quantity': -1.0, 'Total_Cost': -0.57, 'Realized_Profit': 0.43, 'TRY_Amount': -35.05, 'Note': '1 adet x 35,24 TL | Anında Nakit Kom (31.12): -0,17 TL | Net: 35,05 TL'},
        {'Date': '2025-03-03', 'Quantity': -1.0, 'Total_Cost': -0.57, 'Realized_Profit': 0.17, 'TRY_Amount': -26.30, 'Note': '1 adet x 26,30 TL | Komisyonsuz Satış'}
    ],

    # 7. AK PORTFÖY AMERİKA YABANCI HİSSE SENEDİ FONU (13 Alış, 2 Satış = 15 İşlem)
    'AFA': [
        {'Date': '2024-12-13', 'Quantity': 27.0, 'Total_Cost': 0.56, 'TRY_Amount': 19.39, 'Note': '27 pay x 0.7182 TL'},
        {'Date': '2024-12-20', 'Quantity': 70.0, 'Total_Cost': 1.41, 'TRY_Amount': 49.68, 'Note': '70 pay x 0.7096 TL'},
        {'Date': '2025-01-02', 'Quantity': 27.0, 'Total_Cost': 0.55, 'TRY_Amount': 19.29, 'Note': '27 pay x 0.7145 TL'},
        {'Date': '2025-02-04', 'Quantity': 82.0, 'Total_Cost': 1.66, 'TRY_Amount': 59.72, 'Note': '82 pay x 0.7283 TL'},
        {'Date': '2025-04-03', 'Quantity': 178.0, 'Total_Cost': 3.32, 'TRY_Amount': 125.94, 'Note': '178 pay x 0.7075 TL'},
        {'Date': '2025-04-07', 'Quantity': 309.0, 'Total_Cost': 5.26, 'TRY_Amount': 200.00, 'Note': '309 pay x 0.6472 TL'},
        {'Date': '2025-04-17', 'Quantity': 147.0, 'Total_Cost': 2.60, 'TRY_Amount': 99.42, 'Note': '147 pay x 0.6763 TL'},
        {'Date': '2025-04-25', 'Quantity': 158.0, 'Total_Cost': 2.85, 'TRY_Amount': 109.68, 'Note': '158 pay x 0.6941 TL'},
        {'Date': '2025-05-20', 'Quantity': 151.0, 'Total_Cost': 3.06, 'TRY_Amount': 118.95, 'Note': '151 pay x 0.7878 TL'},
        {'Date': '2025-06-11', 'Quantity': 225.0, 'Total_Cost': 4.59, 'TRY_Amount': 180.28, 'Note': '225 pay x 0.8012 TL'},
        {'Date': '2025-07-25', 'Quantity': 455.0, 'Total_Cost': 9.87, 'TRY_Amount': 399.40, 'Note': '455 pay x 0.8778 TL'},
        {'Date': '2025-08-18', 'Quantity': 111.0, 'Total_Cost': 2.44, 'TRY_Amount': 99.83, 'Note': '111 pay x 0.8993 TL'},
        {'Date': '2025-08-27', 'Quantity': 334.0, 'Total_Cost': 7.32, 'TRY_Amount': 300.34, 'Note': '334 pay x 0.8992 TL'},
        {'Date': '2025-09-25', 'Quantity': -1137.0, 'Total_Cost': -22.75, 'Realized_Profit': 2.94, 'TRY_Amount': -1049.92, 'Note': '1. Satış: 1.049,92 TL | Stopaj (24.09): -37,28 TL | Net Kâr: +121,68 TL'},
        {'Date': '2025-10-02', 'Quantity': -1137.0, 'Total_Cost': -22.74, 'Realized_Profit': 3.94, 'TRY_Amount': -1067.73, 'Note': '2. Satış: 1.067,73 TL | Stopaj (01.10): -12,90 TL | Net Kâr: +163,87 TL'}
    ],

    # 8. HSBC MUTLAK GETİRİ HİSSE SENEDİ SERBEST FON (5 Alış, 2 Satış = 7 İşlem)
    'HMG': [
        {'Date': '2025-01-10', 'Quantity': 6914.0, 'Total_Cost': 8.46, 'TRY_Amount': 299.96, 'Note': '6.914 pay x 0.0434 TL'},
        {'Date': '2025-02-10', 'Quantity': 6487.0, 'Total_Cost': 8.33, 'TRY_Amount': 299.98, 'Note': '6.487 pay x 0.0462 TL'},
        {'Date': '2025-04-17', 'Quantity': 3062.0, 'Total_Cost': 3.93, 'TRY_Amount': 149.96, 'Note': '3.062 pay x 0.0490 TL'},
        {'Date': '2025-04-24', 'Quantity': 4037.0, 'Total_Cost': 5.21, 'TRY_Amount': 200.00, 'Note': '4.037 pay x 0.0495 TL'},
        {'Date': '2025-04-25', 'Quantity': 10073.0, 'Total_Cost': 13.01, 'TRY_Amount': 499.96, 'Note': '10.073 pay x 0.0496 TL'},
        {'Date': '2025-06-24', 'Quantity': -10000.0, 'Total_Cost': -12.74, 'Realized_Profit': 0.78, 'TRY_Amount': -505.13, 'Note': '1. Satış: 10.000 pay = 505,13 TL (%0 Stopaj)'},
        {'Date': '2025-07-07', 'Quantity': -20573.0, 'Total_Cost': -26.20, 'Realized_Profit': 1.90, 'TRY_Amount': -1051.49, 'Note': '2. Satış: 20.573 pay = 1.051,49 TL (%0 Stopaj)'}
    ],

    # 9. HSBC PORTFÖY PARA PİYASASI FONU (8 Alış, 1 Satış = 9 İşlem)
    'HSL': [
        {'Date': '2025-04-18', 'Quantity': 8.0, 'Total_Cost': 50.43, 'TRY_Amount': 1926.43, 'Note': '8 pay x 240.8033 TL'},
        {'Date': '2025-04-22', 'Quantity': 8.0, 'Total_Cost': 50.62, 'TRY_Amount': 1937.59, 'Note': '8 pay x 242.1987 TL'},
        {'Date': '2025-04-24', 'Quantity': 26.0, 'Total_Cost': 164.49, 'TRY_Amount': 6313.22, 'Note': '26 pay x 242.8162 TL'},
        {'Date': '2025-05-08', 'Quantity': 12.0, 'Total_Cost': 76.75, 'TRY_Amount': 2966.56, 'Note': '12 pay x 247.2131 TL'},
        {'Date': '2025-05-14', 'Quantity': 11.0, 'Total_Cost': 70.72, 'TRY_Amount': 2740.30, 'Note': '11 pay x 249.1178 TL'},
        {'Date': '2025-06-10', 'Quantity': 5.0, 'Total_Cost': 32.89, 'TRY_Amount': 1289.94, 'Note': '5 pay x 257.9887 TL'},
        {'Date': '2025-07-21', 'Quantity': 1.0, 'Total_Cost': 6.74, 'TRY_Amount': 271.71, 'Note': '1 pay x 271.7117 TL'},
        {'Date': '2025-08-14', 'Quantity': 2.0, 'Total_Cost': 13.69, 'TRY_Amount': 558.63, 'Note': '2 pay x 279.3153 TL'},
        {'Date': '2025-09-17', 'Quantity': -73.0, 'Total_Cost': -466.33, 'Realized_Profit': 65.53, 'TRY_Amount': -21188.02, 'Note': 'Brüt Satış: 21.188,02 TL | Stopaj (16.09): -478,55 TL | Net Kâr: +2.705,10 TL'}
    ],

    # 10. DARPHANE ALTIN SERTİFİKASI • 0,01 GR ALTIN (11 Alış, 1 Satış = 12 İşlem)
    'ALTIN.IS': [
        {'Date': '2025-04-24', 'Quantity': 3.0, 'Total_Cost': 3.72, 'TRY_Amount': 142.95, 'Note': '3 adet x 47,65 TL'},
        {'Date': '2025-04-25', 'Quantity': 1.0, 'Total_Cost': 1.19, 'TRY_Amount': 45.82, 'Note': '1 adet x 45,82 TL'},
        {'Date': '2025-05-02', 'Quantity': 1.0, 'Total_Cost': 1.17, 'TRY_Amount': 44.92, 'Note': '1 adet x 44,92 TL'},
        {'Date': '2025-05-08', 'Quantity': 1.0, 'Total_Cost': 1.22, 'TRY_Amount': 47.08, 'Note': '1 adet x 47,08 TL'},
        {'Date': '2025-05-14', 'Quantity': 1.0, 'Total_Cost': 1.14, 'TRY_Amount': 44.14, 'Note': '1 adet x 44,14 TL'},
        {'Date': '2025-05-15', 'Quantity': 3.0, 'Total_Cost': 3.32, 'TRY_Amount': 128.61, 'Note': '3 adet x 42,87 TL'},
        {'Date': '2025-06-10', 'Quantity': 1.0, 'Total_Cost': 1.20, 'TRY_Amount': 47.07, 'Note': '1 adet x 47,07 TL'},
        {'Date': '2025-06-24', 'Quantity': 1.0, 'Total_Cost': 1.20, 'TRY_Amount': 47.76, 'Note': '1 adet x 47,76 TL'},
        {'Date': '2025-07-07', 'Quantity': 5.0, 'Total_Cost': 5.84, 'TRY_Amount': 232.60, 'Note': '5 adet x 46,52 TL'},
        {'Date': '2025-07-09', 'Quantity': 2.0, 'Total_Cost': 2.31, 'TRY_Amount': 92.32, 'Note': '2 adet x 46,16 TL (Limit)'},
        {'Date': '2025-08-14', 'Quantity': 6.0, 'Total_Cost': 7.00, 'TRY_Amount': 285.90, 'Note': '6 adet x 47,65 TL (Limit)'},
        {'Date': '2025-09-18', 'Quantity': -25.0, 'Total_Cost': -29.31, 'Realized_Profit': 6.56, 'TRY_Amount': -1430.00, 'Note': 'Brüt: 1.448,25 TL | Anında Nakit Kom: -18,25 TL | Net: 1.430,00 TL (+270,83 TL Kâr)'}
    ],

    # 11. COCA-COLA İÇECEK A.Ş. (4 Alış, 1 Satış = 5 İşlem)
    'CCOLA.IS': [
        {'Date': '2025-06-24', 'Quantity': 10.0, 'Total_Cost': 12.21, 'TRY_Amount': 484.00, 'Note': '10 pay x 48,40 TL'},
        {'Date': '2025-07-07', 'Quantity': 15.0, 'Total_Cost': 19.48, 'TRY_Amount': 776.25, 'Note': '15 pay x 51,75 TL'},
        {'Date': '2025-07-09', 'Quantity': 2.0, 'Total_Cost': 2.50, 'TRY_Amount': 99.64, 'Note': '2 pay x 49,82 TL (Limit)'},
        {'Date': '2025-08-14', 'Quantity': 12.0, 'Total_Cost': 14.73, 'TRY_Amount': 601.20, 'Note': '12 pay x 50,10 TL (Limit)'},
        {'Date': '2026-01-14', 'Quantity': -39.0, 'Total_Cost': -48.92, 'Realized_Profit': 13.65, 'TRY_Amount': -2550.60, 'Note': 'Satış: 39 pay x 65,40 TL = 2.550,60 TL | Net Kâr: +589,51 TL'}
    ],

    # 12. FİZİKİ ALTIN / ONS-GRAM (2 İşlem)
    'GC=F': [
        {'Date': '2025-05-22', 'Quantity': 13.15, 'Total_Cost': 1354.0, 'Note': 'Fiziki Altın Alımı (13.15 Gram)'},
        {'Date': '2026-04-29', 'Quantity': -13.15, 'Total_Cost': -1354.0, 'Realized_Profit': 566.0, 'Note': 'Fiziki Altın Satışı (+566.00$ Realize Kâr)'} 
    ],

    # 13. GRID - NASDAQ CLEAN EDGE SMART GRID ETF (10 İşlem)
    'GRID': [
        {'Date': '2026-01-26', 'Quantity': 2.524859813, 'Total_Cost': 406.74, 'Note': 'ABD Borsası Alım (Komisyon Dahil)'},
        {'Date': '2026-02-05', 'Quantity': 1.200408824, 'Total_Cost': 199.99, 'Note': 'ABD Borsası Alım (Komisyon Dahil)'},
        {'Date': '2026-03-04', 'Quantity': 0.866493185, 'Total_Cost': 150.01, 'Note': 'ABD Borsası Alım (Komisyon Dahil)'},
        {'Date': '2026-03-31', 'Quantity': 0.0, 'Total_Cost': 0.0, 'Dividend': 0.37, 'Note': 'Nakit Temettü'},
        {'Date': '2026-04-07', 'Quantity': 0.599059633, 'Total_Cost': 100.37, 'Note': 'ABD Borsası Alım (Komisyon Dahil)'},
        {'Date': '2026-05-15', 'Quantity': 2.084745762, 'Total_Cost': 400.02, 'Note': 'ABD Borsası Alım (Komisyon Dahil)'},
        {'Date': '2026-05-18', 'Quantity': -1.318426326, 'Total_Cost': -227.81, 'Realized_Profit': 20.68, 'Note': 'Kısmi Satış (+20.68$ Net Kâr)'},
        {'Date': '2026-07-01', 'Quantity': 0.019026478, 'Total_Cost': 0.0, 'Dividend': 3.60, 'Note': 'Temettü Yeniden Yatırım (DRIP - 0.019026478 pay)'},
        {'Date': '2026-08-11', 'Quantity': -1.6055168, 'Total_Cost': -276.53, 'Realized_Profit': 23.46, 'Note': 'Kısmi Satış (+23.46$ Net Kâr)'},
        {'Date': '2026-09-30', 'Quantity': 0.006980331, 'Total_Cost': 0.0, 'Dividend': 1.24, 'Note': 'Temettü Yeniden Yatırım (DRIP - 0.006980331 pay x $177.65)'}
    ],

    # 14. ASELSAN (2 Alış, 1 Satış = 3 İşlem)
    'ASELS.IS': [
        {'Date': '2026-07-08', 'Quantity': 2.0, 'Total_Cost': 16.17, 'TRY_Amount': 758.00, 'Note': '2 adet x 379,00 TL'},
        {'Date': '2026-07-09', 'Quantity': 1.0, 'Total_Cost': 7.72, 'TRY_Amount': 361.50, 'Note': '1 adet x 361,50 TL'},
        {'Date': '2026-09-17', 'Quantity': -3.0, 'Total_Cost': -23.89, 'Realized_Profit': 0.42, 'TRY_Amount': -1139.25, 'Note': 'Satış: 3 pay x 379,75 TL = 1.139,25 TL (Komisyonsuz) | Net Kâr: +19,75 TL'}
    ],

    # 15. PUSULA PORTFÖY HİSSE SENEDİ FONU (1 Alış, 1 Satış = 2 İşlem)
    'PPS': [
        {'Date': '2026-08-28', 'Quantity': 352.0, 'Total_Cost': 30.60, 'TRY_Amount': 1444.47, 'Note': '352 pay x 4.103595 TL'},
        {'Date': '2026-09-07', 'Quantity': -352.0, 'Total_Cost': -30.60, 'Realized_Profit': -9.65, 'TRY_Amount': -992.16, 'Note': 'Satış: 352 pay x 2.818639 TL = 992,16 TL | Net Zarar: -452,30 TL (-%31.31)'}
    ],

    # 16. MİDAS NEMALANDIRMA GELİRLERİ - USD & TL (4 İşlem)
    'USD_NEMA': [
        {'Date': '2026-04-30', 'Quantity': 0.0, 'Total_Cost': 0.0, 'Dividend': 0.04, 'Note': 'Nisan 2026 USD Nema (%3 Oran)'},
        {'Date': '2026-05-29', 'Quantity': 0.0, 'Total_Cost': 0.0, 'Dividend': 0.33, 'Note': 'Mayıs 2026 USD Nema (%3 Oran)'},
        {'Date': '2026-08-27', 'Quantity': 0.0, 'Total_Cost': 0.0, 'Dividend': 0.02, 'TRY_Amount': 1.12, 'Note': 'TL Fon Nema: Brüt 1,36 TL | Stopaj: -0,24 TL | Net: 1,12 TL (Günlük %0,09)'},
        {'Date': '2026-08-31', 'Quantity': 0.0, 'Total_Cost': 0.0, 'Dividend': 0.06, 'Note': 'Ağustos 2026 USD Nema (%3 Oran)'}
    ]
}

NON_YF_TICKERS = {'IOG', 'YKT', 'IVY', 'YAS', 'TMG', 'AFA', 'HMG', 'HSL', 'PPS', 'USD_NEMA'}

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

# --- PİYASA BANDI VE PORTFÖY VERİ ÇEKME FONKSİYONU ---
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

    # Piyasa Bandı (Market Ticker) İçin Endeks Fiyatları
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
            cash_dividends = sum(tx.get('Dividend', 0.0) for tx in txs if tx.get('Quantity', 0.0) == 0)
            
            is_closed = abs(total_quantity) < 1e-6
            if is_closed:
                total_quantity = 0.0
                total_cost_all_tx = 0.0
            
            avg_cost = total_cost_all_tx / total_quantity if total_quantity > 0 else 0.0
            display_name = ASSET_NAMES.get(ticker, ticker)
            
            if ticker in NON_YF_TICKERS and is_closed:
                total_net_ret = float(realized_profit + dividends)
                total_roi_pct = (total_net_ret / total_invested_ever * 100) if total_invested_ever > 0 else 0.0
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
                    'Realized P/L': float(realized_profit),
                    'Dividends': float(dividends),
                    'Total Net Return': total_net_ret,
                    'Total ROI (%)': float(total_roi_pct)
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

            current_value = total_quantity * current_price
            pnl_amount = current_value - total_cost_all_tx
            pnl_percentage = (pnl_amount / total_cost_all_tx) * 100 if total_cost_all_tx > 0 else 0.0
            
            daily_return_pct = ((current_price - prev_price_usd) / prev_price_usd) * 100 if (prev_price_usd > 0 and not is_closed) else 0.0
            daily_pnl_usd = total_quantity * (current_price - prev_price_usd) if not is_closed else 0.0
            
            effective_div = dividends if is_closed else cash_dividends
            total_net_ret = float(pnl_amount + realized_profit + effective_div)
            total_roi_pct = (total_net_ret / total_invested_ever * 100) if total_invested_ever > 0 else 0.0

            results.append({
                'Ticker': ticker,
                'Asset': display_name,
                'Status': 'KAPALI' if is_closed else 'AÇIK',
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
                'Total Net Return': total_net_ret,
                'Total ROI (%)': float(total_roi_pct)
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

# --- YARDIMCI FORMAT FONKSİYONU ---
def fmt_currency(val, sym):
    sign = "-" if val < -1e-6 else ("+" if val > 1e-6 else "")
    return f"{sign}{sym}{abs(val):,.2f}"

def badge_class(val):
    if val > 1e-6:
        return "pos-badge"
    elif val < -1e-6:
        return "neg-badge"
    return "neu-badge"

# --- ANA VERİ ÇAĞRISI VE BAŞLIK ---
results, errors, usd_try_rate, market_pulse = fetch_portfolio_data(portfolio_transactions)
fx_multiplier = 1.0 if "USD" in base_currency else usd_try_rate
guncel_saat = datetime.now(tz_TR).strftime('%H:%M:%S')
total_tx_count = sum(len(v) for v in portfolio_transactions.values())

# ÜST PİYASA BANDI (TICKER BAR)
st.markdown(f"""
<div class="ticker-bar">
    <div class="ticker-item"><span class="ticker-label">TERMINAL</span><span class="ticker-val" style="color:#2962FF;">LIVE PORTFOLIO PRO</span></div>
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
        'Current Value', 'Unrealized P/L', 'Realized P/L', 'Dividends', 'Total Net Return'
    ]
    for col in money_cols:
        df[col] = df[col] * fx_multiplier

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
            <div class="kpi-sub neu-badge">Açık Pozisyon Ana Parası</div>
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
            <div class="kpi-sub pos-badge">Pasif Nakit & DRIP</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-title">Tüm Zamanlar Net Kâr</div>
            <div class="kpi-value">{fmt_currency(all_time_net_profit, curr_symbol)}</div>
            <div class="kpi-sub {alltime_cls}">Kümülatif Toplam Kazanç</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- SEKMELİ GÖRÜNÜM (EMOJİSİZ KURUMSAL BAŞLIKLAR) ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "PORTFÖY VE VARLIK ÖZETİ", 
        "PERFORMANS VE ANALİTİK", 
        "TEKNİK ANALİZ TERMİNALİ",
        f"İŞLEM DEFTERİ ({total_tx_count} KAYIT)"
    ])

    # ================= SEKME 1: VARLIKLAR VE PASTA GRAFİĞİ =================
    with tab1:
        df_display = df[df['Status'] == 'AÇIK'].copy() if hide_closed else df.copy()
        df_display = df_display.sort_values(by=['Status', 'Total Net Return'], ascending=[True, False])
        
        st.markdown("#### Portföy ve Geçmiş Yatırımlar Özeti")
        
        # Tablo içi Yeşil / Kırmızı Koşullu Renklendirme Fonksiyonu
        pnl_color_cols = [
            'Daily Change (%)', 'Daily P/L', 'Unrealized P/L', 
            'Unrealized P/L (%)', 'Realized P/L', 'Total Net Return', 'Total ROI (%)'
        ]
        
        def style_pnl_cells(val):
            if pd.isna(val):
                return ''
            if val > 1e-6:
                return 'color: #00E676; font-weight: 600;'
            elif val < -1e-6:
                return 'color: #FF3B69; font-weight: 600;'
            return 'color: #848E9C;'

        def style_status_cells(val):
            if val == 'AÇIK':
                return 'color: #2962FF; font-weight: 700;'
            return 'color: #848E9C;'

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
                'Daily Change (%)': st.column_config.NumberColumn("Günlük (%)", format="%+.2f%%"),
                'Daily P/L': st.column_config.NumberColumn(f"Günlük P/L ({curr_symbol})", format=f"{curr_symbol}%+.2f"),
                'Total Cost': st.column_config.NumberColumn(f"Aktif Maliyet ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Current Value': st.column_config.NumberColumn(f"Güncel Değer ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Unrealized P/L': st.column_config.NumberColumn(f"Açık P/L ({curr_symbol})", format=f"{curr_symbol}%+.2f"),
                'Unrealized P/L (%)': st.column_config.NumberColumn("Açık P/L (%)", format="%+.2f%%"),
                'Realized P/L': st.column_config.NumberColumn(f"Realize Kâr ({curr_symbol})", format=f"{curr_symbol}%+.2f"),
                'Dividends': st.column_config.NumberColumn(f"Temettü/Nema ({curr_symbol})", format=f"{curr_symbol}%.2f"),
                'Total Net Return': st.column_config.NumberColumn(f"Toplam Net Kâr ({curr_symbol})", format=f"{curr_symbol}%+.2f"),
                'Total ROI (%)': st.column_config.NumberColumn("Toplam Kâr (%)", format="%+.2f%%"),
            }
        )

        st.markdown("---")
        col_pie, col_bar = st.columns([1, 1.35])
        
        with col_pie:
            st.markdown("#### Aktif Varlık Dağılımı")
            df_pie = df[df['Current Value'] > 0]
            if not df_pie.empty:
                fig_pie = px.pie(
                    df_pie, 
                    values='Current Value', 
                    names='Asset',
                    hole=0.55,
                    color_discrete_sequence=['#2962FF', '#00E676', '#FFAB00', '#00B0FF', '#AA00FF']
                )
                fig_pie.update_traces(
                    textposition='inside', 
                    textinfo='percent+label',
                    hovertemplate=f"<b>%{{label}}</b><br>Büyüklük: {curr_symbol}%{{value:,.2f}}<br>Pay: %{{percent}}"
                )
                fig_pie.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                    margin=dict(t=20, b=40, l=10, r=10),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Açık pozisyon bulunmuyor.")

        with col_bar:
            st.markdown("#### Varlık Bazlı Net Kazanç Katkısı")
            df_bar = df.sort_values('Total Net Return', ascending=True).copy()
            bar_colors = ['#00E676' if v >= 0 else '#FF3B69' for v in df_bar['Total Net Return']]
            
            fig_bar = go.Figure(go.Bar(
                x=df_bar['Total Net Return'],
                y=df_bar['Asset'],
                orientation='h',
                marker_color=bar_colors,
                text=[f"{fmt_currency(v, curr_symbol)} ({r:+.1f}%)" for v, r in zip(df_bar['Total Net Return'], df_bar['Total ROI (%)'])],
                textposition='auto'
            ))
            fig_bar.update_layout(
                xaxis_title=f"Toplam Net Kâr ({curr_symbol})",
                yaxis_title="",
                margin=dict(t=10, b=10, l=10, r=10),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(gridcolor='rgba(255,255,255,0.06)', zerolinecolor='rgba(255,255,255,0.2)')
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
            time_filter = st.radio(
                "Zaman Aralığı",
                options=["1A", "3A", "6A", "YTD (Yılbaşı)", "TÜMÜ (2024'ten Beri)"],
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

            # TradingView Crosshair Ayarı
            tv_xaxis = dict(
                showspikes=True, spikemode='across', spikesnap='cursor', 
                spikecolor='#848E9C', spikethickness=1, spikedash='dash',
                gridcolor='rgba(255,255,255,0.05)'
            )
            tv_yaxis = dict(
                showspikes=True, spikemode='across', spikesnap='cursor', 
                spikecolor='#848E9C', spikethickness=1, spikedash='dash',
                gridcolor='rgba(255,255,255,0.05)'
            )

            # 1. GRAFİK: Varlık Büyüklüğü vs Yatırılan Maliyet
            st.markdown("#### Aktif Portföy Değeri ve Yatırılan Ana Para")
            fig_value = go.Figure()
            fig_value.add_trace(go.Scatter(
                x=df_hist_filtered.index,
                y=df_hist_filtered['Active_Value'] * fx_multiplier,
                mode='lines',
                name=f'Portföy Değeri ({curr_symbol})',
                line=dict(color='#2962FF', width=2.5),
                fill='tozeroy',
                fillcolor='rgba(41, 98, 255, 0.14)'
            ))
            fig_value.add_trace(go.Scatter(
                x=df_hist_filtered.index,
                y=df_hist_filtered['Active_Cost'] * fx_multiplier,
                mode='lines',
                name=f'Yatırılan Maliyet ({curr_symbol})',
                line=dict(color='#FFAB00', width=1.8, dash='dash')
            ))
            fig_value.update_layout(
                hovermode="x unified",
                xaxis=tv_xaxis,
                yaxis=tv_yaxis,
                yaxis_title=f"Büyüklük ({curr_symbol})",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=30, b=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_value, use_container_width=True)

            # 2. GRAFİK: Kümülatif Net Kâr Evrimi
            st.markdown("---")
            st.markdown("#### Kümülatif Net Kâr Evrimi (Realize Kârlar + Açık Kâr + Temettü & Nema)")
            fig_profit = go.Figure()
            fig_profit.add_trace(go.Scatter(
                x=df_hist_filtered.index,
                y=df_hist_filtered['Total_Net_Profit'] * fx_multiplier,
                mode='lines',
                name=f'Kümülatif Net Kâr ({curr_symbol})',
                line=dict(color='#00E676', width=2.5),
                fill='tozeroy',
                fillcolor='rgba(0, 230, 118, 0.14)'
            ))
            fig_profit.update_layout(
                hovermode="x unified",
                xaxis=tv_xaxis,
                yaxis=tv_yaxis,
                yaxis_title=f"Net Kâr ({curr_symbol})",
                margin=dict(l=0, r=0, t=20, b=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_profit, use_container_width=True)

            # 3. GRAFİK: Yüzdelik Getiri
            st.markdown("---")
            st.markdown("#### Aktif Portföy Getirisi (%) ve Benchmark Kıyaslaması")
            fig_pct = go.Figure()
            
            line_color = '#00E676' if df_hist_filtered['Active_P/L (%)'].iloc[-1] >= 0 else '#FF3B69'
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

            fig_pct.add_hline(y=0, line_dash="dash", line_color="#848E9C", annotation_text="Başabaş (0%)")
            fig_pct.update_layout(
                hovermode="x unified",
                xaxis=tv_xaxis,
                yaxis=tv_yaxis,
                yaxis_title="Getiri (%)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=30, b=0),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_pct, use_container_width=True)

    # ================= SEKME 3: TEKNİK ANALİZ TERMİNALİ =================
    with tab3:
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
            ta_chart_type = st.radio("Grafik Tipi", options=["Mum (Candlestick)", "Çizgi (Line)"], horizontal=True)
        with c_sel4:
            show_sma = st.multiselect("Teknik İndikatörler", options=["SMA 20", "SMA 50", "İşlem Noktalarım"], default=["SMA 20", "İşlem Noktalarım"])

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
                        increasing_line_color='#00E676',
                        decreasing_line_color='#FF3B69'
                    ))
                else:
                    fig_ta.add_trace(go.Scatter(
                        x=ta_df.index,
                        y=ta_df['Close'],
                        mode='lines',
                        name=selected_ta_ticker,
                        line=dict(color='#2962FF', width=2.5),
                        fill='tozeroy',
                        fillcolor='rgba(41, 98, 255, 0.12)'
                    ))

                if "SMA 20" in show_sma:
                    fig_ta.add_trace(go.Scatter(
                        x=ta_df.index, y=ta_df['SMA20'], mode='lines', 
                        name='SMA 20', line=dict(color='#FFAB00', width=1.5)
                    ))
                if "SMA 50" in show_sma:
                    fig_ta.add_trace(go.Scatter(
                        x=ta_df.index, y=ta_df['SMA50'], mode='lines', 
                        name='SMA 50', line=dict(color='#00B0FF', width=1.5)
                    ))

                # Kullanıcının Gerçek Alım/Satım Noktalarını Grafik Üzerinde Göster
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
                            x=buy_dates, y=buy_prices, mode='markers', name='ALIM (BUY)',
                            marker=dict(symbol='triangle-up', size=13, color='#00E676', line=dict(width=1, color='#000000'))
                        ))
                    if sell_dates:
                        fig_ta.add_trace(go.Scatter(
                            x=sell_dates, y=sell_prices, mode='markers', name='SATIM (SELL)',
                            marker=dict(symbol='triangle-down', size=13, color='#FF3B69', line=dict(width=1, color='#000000'))
                        ))

                fig_ta.update_layout(
                    xaxis_rangeslider_visible=False,
                    hovermode="x unified",
                    height=520,
                    yaxis_title=f"Fiyat ({unit_label})",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=0, r=0, t=30, b=0),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showspikes=True, spikemode='across', spikecolor='#848E9C', spikethickness=1, gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(showspikes=True, spikemode='across', spikecolor='#848E9C', spikethickness=1, gridcolor='rgba(255,255,255,0.05)')
                )
                st.plotly_chart(fig_ta, use_container_width=True)
            else:
                st.warning("Seçilen enstrüman için tarihsel grafik verisi bulunamadı.")
        except Exception as e:
            st.error(f"Teknik analiz grafiği yüklenirken hata: {str(e)}")

    # ================= SEKME 4: İŞLEM GEÇMİŞİ LOGU =================
    with tab4:
        st.markdown("#### Tüm İşlem Kayıtları (Tarih Sıralı Muhasebe Dökümü)")
        
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
                q = tx.get('Quantity', 0.0)
                c = tx.get('Total_Cost', 0.0)
                r = tx.get('Realized_Profit', 0.0)
                d = tx.get('Dividend', 0.0)
                try_amt = tx.get('TRY_Amount', None)
                note = tx.get('Note', '')
                
                if d > 0 and q == 0:
                    tx_type = "DIVIDEND / NEMA"
                elif d > 0 and q > 0:
                    tx_type = "DRIP (TEMETTÜ YATIRIMI)"
                elif q > 0:
                    tx_type = "BUY (ALIM)"
                else:
                    tx_type = "SELL (SATIM)"
                    
                tx_rows.append({
                    'Tarih': tx['Date'],
                    'Varlık': asset_label,
                    'İşlem Tipi': tx_type,
                    'Miktar / Pay': q,
                    f'Tutar ({curr_symbol})': c * fx_multiplier,
                    'Orijinal TL Tutarı (₺)': f"₺{abs(try_amt):,.2f}" if try_amt is not None else "-",
                    f'Realize Net Kâr ({curr_symbol})': r * fx_multiplier,
                    f'Temettü/Nema ({curr_symbol})': d * fx_multiplier,
                    'İşlem Detayı & Vergi/Komisyon Notu': note
                })
        
        df_tx_log = pd.DataFrame(tx_rows).sort_values('Tarih', ascending=False)
        
        def style_tx_type(val):
            if "BUY" in val:
                return 'color: #00E676; font-weight: 600;'
            elif "SELL" in val:
                return 'color: #FF3B69; font-weight: 600;'
            elif "DRIP" in val or "DIVIDEND" in val:
                return 'color: #00B0FF; font-weight: 600;'
            return ''

        try:
            styled_log = (
                df_tx_log.style
                .map(style_tx_type, subset=['İşlem Tipi'])
                .map(style_pnl_cells, subset=[f'Realize Net Kâr ({curr_symbol})'])
            )
        except AttributeError:
            styled_log = (
                df_tx_log.style
                .applymap(style_tx_type, subset=['İşlem Tipi'])
                .applymap(style_pnl_cells, subset=[f'Realize Net Kâr ({curr_symbol})'])
            )

        st.dataframe(styled_log, use_container_width=True, hide_index=True)

else:
    st.warning("Ekranda listelenecek geçerli bir veri bulunamadı.")

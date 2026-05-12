# app.py
# MILANO 5Y SCREENER - Screener Borsa Italiana
# Filtra titoli .MI con volume medio 90gg >= soglia E prezzo attuale <= prezzo 5 anni fa
# Pattern: dark theme, mobile-first, JetBrains Mono + Syne, cache TTL

import streamlit as st
import pandas as pd
from datetime import datetime

from universe import get_milan_universe, get_universe_stats
from data_engine import (
    run_screening,
    results_to_dataframe,
    errors_to_dataframe,
)

# === CONFIG PAGINA ===
st.set_page_config(
    page_title="Milano 5Y Screener",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="collapsed",  # Mobile-first
)

# === CSS PERSONALIZZATO ===
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Syne:wght@600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #000000 !important;
    }

    h1, h2, h3 {
        font-family: 'Syne', sans-serif !important;
        color: #ffffff !important;
        letter-spacing: -0.02em;
    }

    .stApp {
        background-color: #000000;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background-color: #0a0a0a;
        border: 1px solid #1a1a1a;
        border-radius: 8px;
        padding: 12px;
    }
    [data-testid="stMetricLabel"] {
        color: #7aa8c8 !important;
        font-size: 0.75rem !important;
    }
    [data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 1.5rem !important;
    }

    /* Bottoni */
    .stButton > button {
        background-color: #0099ff;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #38bdf8;
    }

    /* Download button */
    .stDownloadButton > button {
        background-color: #1a1a1a;
        color: #38bdf8;
        border: 1px solid #38bdf8;
        font-family: 'JetBrains Mono', monospace;
    }

    /* DataFrame */
    [data-testid="stDataFrame"] {
        background-color: #0a0a0a;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #050505;
    }

    /* Riduci padding mobile */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }

    /* Caption / testo secondario */
    .caption-muted {
        color: #7aa8c8;
        font-size: 0.8rem;
    }

    /* Badge */
    .badge-ok {
        background-color: #0099ff;
        color: #ffffff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-ko {
        background-color: #ef4444;
        color: #ffffff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# === HEADER ===
st.markdown("# 📉 MILANO 5Y SCREENER")
st.markdown(
    '<p class="caption-muted">Screening titoli Borsa Italiana — '
    'Prezzo attuale ≤ Prezzo 5 anni fa + Volume liquido</p>',
    unsafe_allow_html=True,
)


# === SIDEBAR PARAMETRI ===
with st.sidebar:
    st.markdown("## ⚙️ Parametri")

    min_volume = st.slider(
        "Volume minimo medio (90gg)",
        min_value=50_000,
        max_value=2_000_000,
        value=200_000,
        step=50_000,
        format="%d",
        help="Soglia minima sulla media mobile a 90 giorni del volume scambiato",
    )

    years_lookback = st.slider(
        "Anni di lookback prezzo",
        min_value=1,
        max_value=10,
        value=5,
        step=1,
        help="Confronta il prezzo attuale con quello di N anni fa",
    )

    volume_window = st.slider(
        "Finestra media volume (gg)",
        min_value=30,
        max_value=180,
        value=90,
        step=10,
    )

    max_workers = st.slider(
        "Worker paralleli",
        min_value=1,
        max_value=20,
        value=10,
        step=1,
        help="Più worker = più veloce, ma rischio rate-limit Yahoo",
    )

    st.markdown("---")
    st.markdown("### 📊 Universo")
    stats = get_universe_stats()
    for k, v in stats.items():
        st.markdown(f"**{k}**: `{v}`")

    st.markdown("---")
    if st.button("🔄 Pulisci cache"):
        st.cache_data.clear()
        st.success("Cache pulita")


# === STATO SESSIONE ===
if "results_ok" not in st.session_state:
    st.session_state.results_ok = []
if "results_err" not in st.session_state:
    st.session_state.results_err = []
if "last_run" not in st.session_state:
    st.session_state.last_run = None


# === ESECUZIONE SCREENING ===
col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    run_clicked = st.button("▶️ ESEGUI SCREENING", use_container_width=True)
with col_btn2:
    if st.session_state.last_run:
        st.markdown(
            f'<p class="caption-muted" style="text-align:right; margin-top:8px;">'
            f'Ultimo: {st.session_state.last_run.strftime("%H:%M:%S")}</p>',
            unsafe_allow_html=True,
        )

if run_clicked:
    universe = get_milan_universe()

    progress_bar = st.progress(0.0, text=f"Analisi 0/{len(universe)} ticker...")

    def update_progress(done: int, total: int):
        progress_bar.progress(done / total, text=f"Analisi {done}/{total} ticker...")

    with st.spinner("Download e calcolo in corso..."):
        ok, err = run_screening(
            tickers=universe,
            years_lookback=years_lookback,
            min_volume=min_volume,
            volume_window=volume_window,
            max_workers=max_workers,
            progress_callback=update_progress,
        )

    progress_bar.empty()
    st.session_state.results_ok = ok
    st.session_state.results_err = err
    st.session_state.last_run = datetime.now()
    st.rerun()


# === RISULTATI ===
results_ok = st.session_state.results_ok
results_err = st.session_state.results_err

if results_ok or results_err:
    # Statistiche
    totale_analizzati = len(results_ok) + len(results_err)
    qualificati = [r for r in results_ok if r.passa_screening]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Analizzati", f"{totale_analizzati}")
    c2.metric("Validi", f"{len(results_ok)}")
    c3.metric("Errori", f"{len(results_err)}")
    c4.metric("✓ Filtri", f"{len(qualificati)}")

    st.markdown("---")

    # Tabella titoli che passano tutti i filtri
    st.markdown("## 🎯 Titoli Qualificati")
    if qualificati:
        df_qual = results_to_dataframe(qualificati)
        st.dataframe(
            df_qual,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Prezzo Attuale (€)": st.column_config.NumberColumn(format="%.4f"),
                "Prezzo 5y fa (€)": st.column_config.NumberColumn(format="%.4f"),
                "Variazione %": st.column_config.NumberColumn(format="%.2f%%"),
                "Vol. Medio 90gg": st.column_config.NumberColumn(format="%d"),
            },
        )

        # Download CSV
        csv = df_qual.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Scarica CSV Qualificati",
            data=csv,
            file_name=f"milano_5y_screener_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Nessun titolo passa entrambi i filtri con i parametri attuali.")

    # Tabella tutti gli analizzati (espandibile)
    with st.expander(f"📋 Tutti i titoli analizzati ({len(results_ok)})"):
        df_all = results_to_dataframe(results_ok)
        st.dataframe(
            df_all,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Prezzo Attuale (€)": st.column_config.NumberColumn(format="%.4f"),
                "Prezzo 5y fa (€)": st.column_config.NumberColumn(format="%.4f"),
                "Variazione %": st.column_config.NumberColumn(format="%.2f%%"),
                "Vol. Medio 90gg": st.column_config.NumberColumn(format="%d"),
            },
        )

        csv_all = df_all.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Scarica CSV Completo",
            data=csv_all,
            file_name=f"milano_5y_full_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Debug errori
    with st.expander(f"🐛 Debug — Errori ({len(results_err)})"):
        if results_err:
            df_err = errors_to_dataframe(results_err)
            st.dataframe(df_err, use_container_width=True, hide_index=True)
        else:
            st.success("Nessun errore registrato.")

else:
    st.info(
        "👆 Premi **ESEGUI SCREENING** per avviare l'analisi sull'intero universo "
        "di Borsa Italiana. La prima esecuzione richiede ~1-2 minuti "
        "(le successive sono in cache per 1h)."
    )

# === FOOTER ===
st.markdown("---")
st.markdown(
    '<p class="caption-muted" style="text-align:center;">'
    'Dati: Yahoo Finance · Cache: 1h · '
    f'© {datetime.now().year} Milano 5Y Screener</p>',
    unsafe_allow_html=True,
)

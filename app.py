# app.py
# MILANO SCREENER - Screener Borsa Italiana
# v3: filtro nazionalità ISIN (solo IT vs tutti)

import streamlit as st
import pandas as pd
from datetime import datetime

from universe import get_milan_universe, get_metadata, get_universe_stats
from data_engine import (
    run_screening,
    results_to_dataframe,
    errors_to_dataframe,
)

# === CONFIG PAGINA ===
st.set_page_config(
    page_title="Milano Screener",
    page_icon="📉",
    layout="wide",
    initial_sidebar_state="collapsed",
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

    .stApp { background-color: #000000; }

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

    .stButton > button {
        background-color: #0099ff;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        width: 100%;
    }
    .stButton > button:hover { background-color: #38bdf8; }

    .stDownloadButton > button {
        background-color: #1a1a1a;
        color: #38bdf8;
        border: 1px solid #38bdf8;
        font-family: 'JetBrains Mono', monospace;
    }

    [data-testid="stDataFrame"] { background-color: #0a0a0a; }
    [data-testid="stSidebar"] { background-color: #050505; }

    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }

    .caption-muted {
        color: #7aa8c8;
        font-size: 0.8rem;
    }

    div[role="radiogroup"] > label {
        background-color: #0a0a0a;
        border: 1px solid #1a1a1a;
        border-radius: 6px;
        padding: 6px 12px;
        margin: 2px;
    }
    div[role="radiogroup"] > label:hover {
        border-color: #38bdf8;
    }

    /* Banner info nazionalità */
    .info-it {
        background-color: #0a1a0a;
        border-left: 3px solid #0099ff;
        padding: 8px 12px;
        border-radius: 4px;
        color: #7aa8c8;
        font-size: 0.8rem;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# === HEADER ===
st.markdown("# 📉 MILANO SCREENER")
st.markdown(
    '<p class="caption-muted">Screening Borsa Italiana — '
    'Prezzo attuale ≤ Prezzo N anni fa + Volume liquido</p>',
    unsafe_allow_html=True,
)


# === SIDEBAR PARAMETRI ===
with st.sidebar:
    st.markdown("## ⚙️ Parametri")

    min_volume = st.slider(
        "Volume minimo medio",
        min_value=50_000,
        max_value=2_000_000,
        value=200_000,
        step=50_000,
        format="%d",
        help="Soglia minima sulla media mobile del volume scambiato",
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


# === FILTRO NAZIONALITÀ ===
st.markdown("### 🇮🇹 Nazionalità emittente")
solo_italiani = st.toggle(
    "**Solo società di diritto italiano** (ISIN IT)",
    value=True,
    help=(
        "Se attivo, esclude società di diritto estero quotate a Milano "
        "(Stellantis, Ferrari, STMicro, Tenaris, Iveco, Brembo, Cementir, "
        "Campari, MFE). Evita doppia tassazione su dividendi e complessità fiscale."
    ),
)

if solo_italiani:
    st.markdown(
        '<div class="info-it">✓ Filtro attivo: solo emittenti con ISIN <code>IT*</code> '
        '(no doppia ritenuta dividendi, no quadro RW estero)</div>',
        unsafe_allow_html=True,
    )


# === SELETTORE LOOKBACK ===
st.markdown("### 📅 Periodo di confronto")
col_lb1, col_lb2 = st.columns([3, 2])

with col_lb1:
    lookback_preset = st.radio(
        "Minimi di quanti anni?",
        options=[3, 5, 7, "Custom"],
        horizontal=True,
        index=1,
        label_visibility="collapsed",
    )

with col_lb2:
    if lookback_preset == "Custom":
        years_lookback = st.slider(
            "Anni custom",
            min_value=1,
            max_value=15,
            value=5,
            step=1,
            label_visibility="collapsed",
        )
    else:
        years_lookback = int(lookback_preset)
        st.markdown(
            f'<p style="color:#38bdf8; font-weight:700; margin-top:8px;">'
            f'→ Lookback: {years_lookback} anni</p>',
            unsafe_allow_html=True,
        )


# === STATO SESSIONE ===
if "results_ok" not in st.session_state:
    st.session_state.results_ok = []
if "results_err" not in st.session_state:
    st.session_state.results_err = []
if "last_run" not in st.session_state:
    st.session_state.last_run = None
if "last_lookback" not in st.session_state:
    st.session_state.last_lookback = None
if "last_solo_it" not in st.session_state:
    st.session_state.last_solo_it = None


# === ESECUZIONE SCREENING ===
# Pre-filtraggio universo in base a nazionalità
universe_full = get_milan_universe()
if solo_italiani:
    universe = [t for t in universe_full if get_metadata(t)[1].startswith("IT")]
else:
    universe = universe_full

col_btn1, col_btn2 = st.columns([3, 1])
with col_btn1:
    flag_naz = "🇮🇹" if solo_italiani else "🌍"
    run_clicked = st.button(
        f"▶️ ESEGUI SCREENING ({years_lookback}Y · {flag_naz} {len(universe)} titoli)",
        use_container_width=True,
    )
with col_btn2:
    if st.session_state.last_run:
        flag_prev = "🇮🇹" if st.session_state.last_solo_it else "🌍"
        st.markdown(
            f'<p class="caption-muted" style="text-align:right; margin-top:8px;">'
            f'Ultimo: {st.session_state.last_run.strftime("%H:%M:%S")}<br>'
            f'({st.session_state.last_lookback}Y {flag_prev})</p>',
            unsafe_allow_html=True,
        )

if run_clicked:
    progress_bar = st.progress(0.0, text=f"Analisi 0/{len(universe)} ticker...")

    def update_progress(done: int, total: int):
        progress_bar.progress(done / total, text=f"Analisi {done}/{total} ticker...")

    with st.spinner(f"Download e calcolo lookback {years_lookback} anni..."):
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
    st.session_state.last_lookback = years_lookback
    st.session_state.last_solo_it = solo_italiani
    st.rerun()


# === RISULTATI ===
results_ok = st.session_state.results_ok
results_err = st.session_state.results_err
last_lb = st.session_state.last_lookback
last_solo_it = st.session_state.last_solo_it

if results_ok or results_err:
    totale_analizzati = len(results_ok) + len(results_err)
    qualificati = [r for r in results_ok if r.passa_screening]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Analizzati", f"{totale_analizzati}")
    c2.metric("Validi", f"{len(results_ok)}")
    c3.metric("Errori", f"{len(results_err)}")
    c4.metric("✓ Filtri", f"{len(qualificati)}")

    naz_label = "🇮🇹 Solo IT" if last_solo_it else "🌍 Tutti"
    st.caption(f"Run: lookback **{last_lb}Y** · Nazionalità **{naz_label}**")

    st.markdown("---")

    # === TABELLA TITOLI QUALIFICATI ===
    st.markdown(f"## 🎯 Titoli Qualificati ({last_lb}Y)")
    if qualificati:
        df_qual = results_to_dataframe(qualificati)
        prezzo_storico_col = f"Prezzo {last_lb}y fa (€)"

        st.dataframe(
            df_qual,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ticker": st.column_config.TextColumn(width="small"),
                "Nome": st.column_config.TextColumn(width="medium"),
                "ISIN": st.column_config.TextColumn(width="medium"),
                "Prezzo Attuale (€)": st.column_config.NumberColumn(format="%.4f"),
                prezzo_storico_col: st.column_config.NumberColumn(format="%.4f"),
                "Variazione %": st.column_config.NumberColumn(format="%.2f%%"),
                "Vol. Medio": st.column_config.NumberColumn(format="%d"),
            },
        )

        csv = df_qual.to_csv(index=False).encode("utf-8")
        suffix_naz = "IT" if last_solo_it else "ALL"
        st.download_button(
            label="📥 Scarica CSV Qualificati",
            data=csv,
            file_name=f"milano_{last_lb}y_{suffix_naz}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.info("Nessun titolo passa entrambi i filtri con i parametri attuali.")

    # === TABELLA COMPLETA ===
    with st.expander(f"📋 Tutti i titoli analizzati ({len(results_ok)})"):
        df_all = results_to_dataframe(results_ok)
        prezzo_storico_col = f"Prezzo {last_lb}y fa (€)"

        st.dataframe(
            df_all,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Prezzo Attuale (€)": st.column_config.NumberColumn(format="%.4f"),
                prezzo_storico_col: st.column_config.NumberColumn(format="%.4f"),
                "Variazione %": st.column_config.NumberColumn(format="%.2f%%"),
                "Vol. Medio": st.column_config.NumberColumn(format="%d"),
            },
        )

        csv_all = df_all.to_csv(index=False).encode("utf-8")
        suffix_naz = "IT" if last_solo_it else "ALL"
        st.download_button(
            label="📥 Scarica CSV Completo",
            data=csv_all,
            file_name=f"milano_{last_lb}y_full_{suffix_naz}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # === DEBUG ===
    with st.expander(f"🐛 Debug — Errori ({len(results_err)})"):
        if results_err:
            df_err = errors_to_dataframe(results_err)
            st.dataframe(df_err, use_container_width=True, hide_index=True)
            st.caption(
                "💡 Ticker con 'Storico insufficiente' sono titoli quotati di recente. "
                "Per testarli, riduci il lookback (es. 3 anni)."
            )
        else:
            st.success("Nessun errore registrato.")

else:
    st.info(
        "👆 Premi **ESEGUI SCREENING** per avviare l'analisi. "
        f"Attualmente in coda: **{len(universe)} ticker** "
        f"({'solo IT' if solo_italiani else 'IT + esteri quotati a Milano'})."
    )

# === FOOTER ===
st.markdown("---")
st.markdown(
    '<p class="caption-muted" style="text-align:center;">'
    'Dati: Yahoo Finance · Cache: 1h · '
    f'© {datetime.now().year} Milano Screener</p>',
    unsafe_allow_html=True,
)

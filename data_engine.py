# data_engine.py
# Engine per download dati Yahoo Finance, calcolo filtri e screening
# Pattern: ThreadPoolExecutor + cache TTL + gestione errori robusta

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional
import streamlit as st


@dataclass
class TickerResult:
    """Risultato analisi singolo ticker."""
    ticker: str
    nome: Optional[str] = None
    prezzo_attuale: Optional[float] = None
    prezzo_5y_ago: Optional[float] = None
    variazione_pct: Optional[float] = None
    volume_medio_90d: Optional[float] = None
    passa_volume: bool = False
    passa_prezzo: bool = False
    passa_screening: bool = False
    errore: Optional[str] = None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ticker_history(ticker: str, years_lookback: int = 5) -> Optional[pd.DataFrame]:
    """
    Scarica lo storico OHLCV per un singolo ticker.
    Cache 1h per evitare rate-limit Yahoo Finance.
    Restituisce None se i dati sono insufficienti o errore.
    """
    try:
        # Margine di sicurezza: +30 giorni per gestire weekend/festivi
        end = datetime.now()
        start = end - timedelta(days=years_lookback * 365 + 30)

        df = yf.download(
            ticker,
            start=start,
            end=end,
            progress=False,
            auto_adjust=False,  # Vogliamo sia Close che Adj Close
            threads=False,      # Parallelismo gestito da noi
        )

        if df is None or df.empty:
            return None

        # yfinance recente restituisce MultiIndex columns: appiattiamo
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Validazione storico minimo (almeno years_lookback anni)
        if len(df) < years_lookback * 200:  # ~200 giorni di trading/anno conservativo
            return None

        return df
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_ticker_name(ticker: str) -> str:
    """Recupera il nome esteso del titolo. Cache 24h."""
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker


def analyze_ticker(
    ticker: str,
    years_lookback: int = 5,
    min_volume: int = 200_000,
    volume_window: int = 90,
) -> TickerResult:
    """
    Analizza un singolo ticker applicando i filtri di screening:
    - Volume medio sugli ultimi `volume_window` giorni >= min_volume
    - Prezzo attuale <= Adj Close di `years_lookback` anni fa (ffill su festivi)
    """
    result = TickerResult(ticker=ticker)

    df = fetch_ticker_history(ticker, years_lookback=years_lookback)
    if df is None:
        result.errore = "Dati insufficienti o errore download"
        return result

    try:
        # === FILTRO VOLUME ===
        if "Volume" not in df.columns:
            result.errore = "Colonna Volume mancante"
            return result

        vol_recente = df["Volume"].tail(volume_window)
        if len(vol_recente) < volume_window:
            result.errore = f"Storico volumi < {volume_window}gg"
            return result

        vol_medio = float(vol_recente.mean())
        result.volume_medio_90d = vol_medio
        result.passa_volume = vol_medio >= min_volume

        # === FILTRO PREZZO STORICO ===
        if "Adj Close" not in df.columns or "Close" not in df.columns:
            result.errore = "Colonne prezzo mancanti"
            return result

        # Forward-fill per gestire festivi/weekend nella data target
        df_filled = df[["Close", "Adj Close"]].ffill()

        prezzo_attuale = float(df_filled["Close"].iloc[-1])
        result.prezzo_attuale = prezzo_attuale

        # Data esattamente N anni fa
        oggi = df_filled.index[-1]
        target_date = oggi - pd.DateOffset(years=years_lookback)

        # Reindex con ffill per ottenere il valore al target_date anche se festivo
        df_reindexed = df_filled.reindex(
            df_filled.index.union([target_date])
        ).ffill()

        if target_date not in df_reindexed.index:
            result.errore = "Data target non disponibile"
            return result

        prezzo_5y = df_reindexed.loc[target_date, "Adj Close"]
        if pd.isna(prezzo_5y):
            result.errore = f"Prezzo {years_lookback}y fa NaN"
            return result

        prezzo_5y = float(prezzo_5y)
        result.prezzo_5y_ago = prezzo_5y
        result.variazione_pct = ((prezzo_attuale - prezzo_5y) / prezzo_5y) * 100
        result.passa_prezzo = prezzo_attuale <= prezzo_5y

        # === ESITO COMPLESSIVO ===
        result.passa_screening = result.passa_volume and result.passa_prezzo

        return result

    except Exception as e:
        result.errore = f"Errore analisi: {type(e).__name__}: {str(e)[:80]}"
        return result


def run_screening(
    tickers: list[str],
    years_lookback: int = 5,
    min_volume: int = 200_000,
    volume_window: int = 90,
    max_workers: int = 10,
    progress_callback=None,
) -> tuple[list[TickerResult], list[TickerResult]]:
    """
    Esegue lo screening in parallelo su tutta la lista di ticker.
    Restituisce (risultati_ok, risultati_errore).
    """
    risultati_ok: list[TickerResult] = []
    risultati_errore: list[TickerResult] = []

    completati = 0
    totale = len(tickers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(
                analyze_ticker, t, years_lookback, min_volume, volume_window
            ): t
            for t in tickers
        }

        for future in as_completed(future_to_ticker):
            res = future.result()
            if res.errore:
                risultati_errore.append(res)
            else:
                risultati_ok.append(res)

            completati += 1
            if progress_callback:
                progress_callback(completati, totale)

    return risultati_ok, risultati_errore


def results_to_dataframe(results: list[TickerResult]) -> pd.DataFrame:
    """Converte i risultati in DataFrame pronto per st.dataframe."""
    if not results:
        return pd.DataFrame()

    rows = []
    for r in results:
        rows.append({
            "Ticker": r.ticker.replace(".MI", ""),
            "Prezzo Attuale (€)": r.prezzo_attuale,
            "Prezzo 5y fa (€)": r.prezzo_5y_ago,
            "Variazione %": r.variazione_pct,
            "Vol. Medio 90gg": r.volume_medio_90d,
            "Filtro Volume": "✓" if r.passa_volume else "✗",
            "Filtro Prezzo": "✓" if r.passa_prezzo else "✗",
        })

    df = pd.DataFrame(rows)
    # Ordina per variazione % crescente (i più negativi in cima)
    df = df.sort_values("Variazione %", ascending=True).reset_index(drop=True)
    return df


def errors_to_dataframe(errors: list[TickerResult]) -> pd.DataFrame:
    """DataFrame degli errori per la sezione Debug."""
    if not errors:
        return pd.DataFrame()
    return pd.DataFrame([
        {"Ticker": r.ticker, "Errore": r.errore} for r in errors
    ])

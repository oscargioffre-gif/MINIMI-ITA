# data_engine.py
# Engine per download dati Yahoo Finance, calcolo filtri e screening
# v2: fix logica NaN 5y, aggiunta ISIN, lookback flessibile

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional
import streamlit as st


@dataclass
class TickerResult:
    """Risultato analisi singolo ticker."""
    ticker: str
    nome: Optional[str] = None
    isin: Optional[str] = None
    prezzo_attuale: Optional[float] = None
    prezzo_storico: Optional[float] = None
    variazione_pct: Optional[float] = None
    volume_medio: Optional[float] = None
    anni_lookback: int = 5
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
        # Margine di sicurezza: +60 giorni per gestire weekend/festivi e calcolo volume
        end = datetime.now()
        start = end - timedelta(days=years_lookback * 365 + 60)

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

        return df
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_ticker_metadata(ticker: str) -> dict:
    """
    Recupera nome esteso e ISIN. Cache 24h (dati statici).
    Restituisce dict con 'nome' e 'isin' (entrambi possono essere None).
    """
    result = {"nome": None, "isin": None}
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        result["nome"] = info.get("longName") or info.get("shortName") or ticker

        # Tenta prima con il campo info, poi con il metodo dedicato isin()
        isin = info.get("isin")
        if not isin:
            try:
                isin = tk.isin
            except Exception:
                isin = None

        # yfinance può restituire "-" se non disponibile
        if isin and isin != "-":
            result["isin"] = isin
    except Exception:
        pass

    if not result["nome"]:
        result["nome"] = ticker
    return result


def analyze_ticker(
    ticker: str,
    years_lookback: int = 5,
    min_volume: int = 200_000,
    volume_window: int = 90,
    fetch_meta: bool = True,
) -> TickerResult:
    """
    Analizza un singolo ticker applicando i filtri di screening.
    - Volume medio sugli ultimi `volume_window` giorni >= min_volume
    - Prezzo attuale <= Adj Close di `years_lookback` anni fa (ffill su festivi)
    """
    result = TickerResult(ticker=ticker, anni_lookback=years_lookback)

    df = fetch_ticker_history(ticker, years_lookback=years_lookback)
    if df is None:
        result.errore = "Ticker non trovato su Yahoo Finance"
        return result

    try:
        # === VALIDAZIONE COLONNE ===
        for col in ("Volume", "Close", "Adj Close"):
            if col not in df.columns:
                result.errore = f"Colonna {col} mancante"
                return result

        # === FILTRO VOLUME ===
        vol_recente = df["Volume"].tail(volume_window)
        if len(vol_recente) < volume_window:
            result.errore = f"Storico volumi < {volume_window}gg (solo {len(vol_recente)}gg)"
            return result

        vol_medio = float(vol_recente.mean())
        result.volume_medio = vol_medio
        result.passa_volume = vol_medio >= min_volume

        # === VALIDAZIONE STORICO MINIMO ===
        # Verifica esplicita che lo storico copra il periodo di lookback richiesto
        prima_data = df.index[0]
        ultima_data = df.index[-1]
        target_date = ultima_data - pd.DateOffset(years=years_lookback)

        # Margine: se la prima data disponibile è DOPO la target_date, niente da fare
        if prima_data > target_date:
            anni_disponibili = (ultima_data - prima_data).days / 365.25
            result.errore = (
                f"Storico insufficiente: solo {anni_disponibili:.1f} anni "
                f"(richiesti {years_lookback})"
            )
            return result

        # === CALCOLO PREZZO STORICO ===
        df_filled = df[["Close", "Adj Close"]].ffill()

        prezzo_attuale = float(df_filled["Close"].iloc[-1])
        if pd.isna(prezzo_attuale):
            result.errore = "Prezzo attuale NaN"
            return result
        result.prezzo_attuale = prezzo_attuale

        # Reindex con ffill per ottenere il valore al target_date anche se festivo
        df_reindexed = df_filled.reindex(
            df_filled.index.union([target_date])
        ).ffill()

        prezzo_storico = df_reindexed.loc[target_date, "Adj Close"]
        if pd.isna(prezzo_storico):
            result.errore = f"Prezzo {years_lookback}y fa non calcolabile"
            return result

        prezzo_storico = float(prezzo_storico)
        result.prezzo_storico = prezzo_storico
        result.variazione_pct = ((prezzo_attuale - prezzo_storico) / prezzo_storico) * 100
        result.passa_prezzo = prezzo_attuale <= prezzo_storico

        # === ESITO COMPLESSIVO ===
        result.passa_screening = result.passa_volume and result.passa_prezzo

        # === METADATA (nome + ISIN) - solo se il ticker passa il filtro ===
        # Evitiamo chiamate .info inutili sui ticker scartati per non triggerare rate-limit
        if fetch_meta and result.passa_screening:
            meta = fetch_ticker_metadata(ticker)
            result.nome = meta["nome"]
            result.isin = meta["isin"]

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
                analyze_ticker, t, years_lookback, min_volume, volume_window, True
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
            "Nome": r.nome or "—",
            "ISIN": r.isin or "—",
            "Prezzo Attuale (€)": r.prezzo_attuale,
            f"Prezzo {r.anni_lookback}y fa (€)": r.prezzo_storico,
            "Variazione %": r.variazione_pct,
            "Vol. Medio": r.volume_medio,
            "Filtro Volume": "✓" if r.passa_volume else "✗",
            "Filtro Prezzo": "✓" if r.passa_prezzo else "✗",
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("Variazione %", ascending=True).reset_index(drop=True)
    return df


def errors_to_dataframe(errors: list[TickerResult]) -> pd.DataFrame:
    """DataFrame degli errori per la sezione Debug."""
    if not errors:
        return pd.DataFrame()
    return pd.DataFrame([
        {"Ticker": r.ticker, "Errore": r.errore} for r in errors
    ])

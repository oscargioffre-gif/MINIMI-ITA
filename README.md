# 📉 Milano 5Y Screener

Screener real-time per Borsa Italiana che identifica titoli con:
- **Volume**: media mobile 90gg ≥ 200.000 azioni/giorno
- **Prezzo**: prezzo attuale ≤ prezzo (Adj Close) di 5 anni fa

## Stack
- Python 3.10+
- Streamlit
- yfinance
- pandas

## Struttura
```
.
├── app.py              # UI Streamlit
├── data_engine.py      # Download dati, calcoli, screening parallelo
├── universe.py         # Universo investibile (FTSE MIB + MidCap + Small Cap)
├── requirements.txt
└── .streamlit/
    └── config.toml     # Dark theme
```

## Logica
1. Per ogni ticker dell'universo `.MI`:
   - Scarica 5 anni di storico OHLCV (yfinance, `auto_adjust=False`)
   - Calcola media volume ultimi 90gg
   - Calcola Adj Close esattamente N anni fa (con `ffill` per festivi)
2. Filtra titoli che soddisfano entrambe le condizioni
3. Cache 1h via `@st.cache_data` per evitare rate-limit
4. Parallelismo con `ThreadPoolExecutor` (10 worker default)

## Deploy su Streamlit Community Cloud
1. Pusha su GitHub
2. Connetti il repo su https://share.streamlit.io
3. Main file: `app.py`
4. Python: 3.10+

## Sviluppo locale
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Parametri configurabili (sidebar)
- Volume minimo medio (50k–2M)
- Anni di lookback (1–10)
- Finestra media volume (30–180 gg)
- Worker paralleli (1–20)

## Note
- I dati storici di yfinance includono già il rettifico per split/dividendi (`Adj Close`)
- L'universo è curato manualmente; aggiornare `universe.py` quando ci sono variazioni negli indici
- Pulsante "Pulisci cache" nella sidebar per forzare refresh dati

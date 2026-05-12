# universe.py
# Universo investibile Borsa Italiana - suffisso .MI per yfinance
# Lista curata: FTSE MIB (40) + FTSE Italia Mid Cap (60) + selezione Small Cap liquide
# Aggiornare manualmente in caso di nuovi ingressi/uscite dagli indici

FTSE_MIB = [
    "A2A.MI", "AMP.MI", "AZM.MI", "BAMI.MI", "BMED.MI", "BPE.MI", "BPSO.MI",
    "BGN.MI", "CPR.MI", "DIA.MI", "ENEL.MI", "ENI.MI", "RACE.MI", "FBK.MI",
    "G.MI", "HER.MI", "IP.MI", "ISP.MI", "IVG.MI", "LDO.MI", "MB.MI",
    "MONC.MI", "NEXI.MI", "PIRC.MI", "PRY.MI", "PST.MI", "REC.MI", "SPM.MI",
    "SRG.MI", "STLAM.MI", "STMMI.MI", "TRN.MI", "TEN.MI", "TIT.MI", "TGYM.MI",
    "TGAGM.MI", "UCG.MI", "UNI.MI", "US.MI", "ERG.MI",
]

FTSE_MID_CAP = [
    "ACE.MI", "ALK.MI", "AMP.MI", "ANIM.MI", "ARN.MI", "AUTME.MI", "BC.MI",
    "BFF.MI", "BPSO.MI", "BRE.MI", "BZU.MI", "CE.MI", "CEM.MI", "CFL.MI",
    "DAN.MI", "DAL.MI", "DLG.MI", "ELC.MI", "EM.MI", "EGPW.MI", "EQUI.MI",
    "FCT.MI", "FNM.MI", "FILA.MI", "GHC.MI", "GVS.MI", "IF.MI", "IGD.MI",
    "ILTY.MI", "IRE.MI", "JUVE.MI", "LDB.MI", "LUVE.MI", "MARR.MI", "MAIRE.MI",
    "MN.MI", "MFEA.MI", "MFEB.MI", "OVS.MI", "PHN.MI", "PIA.MI", "PININ.MI",
    "RWAY.MI", "SFL.MI", "SAB.MI", "SL.MI", "SES.MI", "SCF.MI", "SOL.MI",
    "SSL.MI", "TES.MI", "TXT.MI", "TPRO.MI", "TIP.MI", "WBD.MI", "ZV.MI",
]

SMALL_CAP_LIQUIDE = [
    "ALA.MI", "ARIS.MI", "BAS.MI", "BFG.MI", "CIA.MI", "CIR.MI", "CY4.MI",
    "DAN.MI", "DIB.MI", "ELN.MI", "ENV.MI", "EXP.MI", "FOS.MI", "GE.MI",
    "GPI.MI", "INW.MI", "IOL.MI", "ITM.MI", "ITW.MI", "LR.MI", "LUX.MI",
    "MAR.MI", "NWL.MI", "ORS.MI", "PRL.MI", "RAT.MI", "RDF.MI", "SRI.MI",
    "TKA.MI", "TNXT.MI", "VLS.MI", "WIIT.MI",
]


def get_milan_universe() -> list[str]:
    """Restituisce la lista deduplicata dei ticker di Borsa Italiana."""
    combined = FTSE_MIB + FTSE_MID_CAP + SMALL_CAP_LIQUIDE
    # Deduplicazione preservando l'ordine
    seen = set()
    universe = []
    for ticker in combined:
        if ticker not in seen:
            seen.add(ticker)
            universe.append(ticker)
    return universe


def get_universe_stats() -> dict:
    """Statistiche sull'universo per UI."""
    return {
        "FTSE MIB": len(set(FTSE_MIB)),
        "FTSE Mid Cap": len(set(FTSE_MID_CAP)),
        "Small Cap": len(set(SMALL_CAP_LIQUIDE)),
        "Totale (dedup)": len(get_milan_universe()),
    }

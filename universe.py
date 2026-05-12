# universe.py
# Universo investibile Borsa Italiana - suffisso .MI per yfinance
# Mappa statica ticker -> (nome, ISIN) per evitare rate-limit su yf.Ticker().info
# ISIN verificati da Borsa Italiana ufficiale

# Mappa: ticker -> (nome_esteso, ISIN)
# Aggiornare manualmente in caso di fusioni/cambi denominazione/nuovi ingressi
TICKER_METADATA: dict[str, tuple[str, str]] = {
    # === FTSE MIB ===
    "A2A.MI":    ("A2A S.p.A.",                       "IT0001233417"),
    "AMP.MI":    ("Amplifon S.p.A.",                  "IT0004056880"),
    "AZM.MI":    ("Azimut Holding S.p.A.",            "IT0003261697"),
    "BAMI.MI":   ("Banco BPM S.p.A.",                 "IT0005218380"),
    "BMED.MI":   ("Banca Mediolanum S.p.A.",          "IT0004776628"),
    "BPE.MI":    ("BPER Banca S.p.A.",                "IT0000066123"),
    "BPSO.MI":   ("Banca Popolare di Sondrio S.p.A.", "IT0000784196"),
    "BGN.MI":    ("Banca Generali S.p.A.",            "IT0001031084"),
    "CPR.MI":    ("Davide Campari-Milano N.V.",       "NL0015435975"),
    "DIA.MI":    ("DiaSorin S.p.A.",                  "IT0003492391"),
    "ENEL.MI":   ("Enel S.p.A.",                      "IT0003128367"),
    "ENI.MI":    ("Eni S.p.A.",                       "IT0003132476"),
    "RACE.MI":   ("Ferrari N.V.",                     "NL0011585146"),
    "FBK.MI":    ("FinecoBank S.p.A.",                "IT0000072170"),
    "G.MI":      ("Assicurazioni Generali S.p.A.",    "IT0000062072"),
    "HER.MI":    ("Hera S.p.A.",                      "IT0001250932"),
    "IP.MI":     ("Interpump Group S.p.A.",           "IT0001078911"),
    "ISP.MI":    ("Intesa Sanpaolo S.p.A.",           "IT0000072618"),
    "IVG.MI":    ("Iveco Group N.V.",                 "NL0015000LU4"),
    "LDO.MI":    ("Leonardo S.p.A.",                  "IT0003856405"),
    "MB.MI":     ("Mediobanca S.p.A.",                "IT0000062957"),
    "MONC.MI":   ("Moncler S.p.A.",                   "IT0004965148"),
    "NEXI.MI":   ("Nexi S.p.A.",                      "IT0005366767"),
    "PIRC.MI":   ("Pirelli & C. S.p.A.",              "IT0005278236"),
    "PRY.MI":    ("Prysmian S.p.A.",                  "IT0004176001"),
    "PST.MI":    ("Poste Italiane S.p.A.",            "IT0003796171"),
    "REC.MI":    ("Recordati Industria Chimica e Farmaceutica S.p.A.", "IT0003828271"),
    "SPM.MI":    ("Saipem S.p.A.",                    "IT0005252140"),
    "SRG.MI":    ("Snam S.p.A.",                      "IT0003153415"),
    "STLAM.MI":  ("Stellantis N.V.",                  "NL00150001Q9"),
    "STMMI.MI":  ("STMicroelectronics N.V.",          "NL0000226223"),
    "TRN.MI":    ("Terna S.p.A.",                     "IT0003242622"),
    "TEN.MI":    ("Tenaris S.A.",                     "LU0156801721"),
    "TIT.MI":    ("Telecom Italia S.p.A.",            "IT0003497168"),
    "TITR.MI":   ("Telecom Italia Risparmio",         "IT0003497176"),
    "TGYM.MI":   ("Technogym S.p.A.",                 "IT0005162406"),
    "UCG.MI":    ("UniCredit S.p.A.",                 "IT0005239360"),
    "UNI.MI":    ("Unipol Gruppo S.p.A.",             "IT0004810054"),
    "ERG.MI":    ("ERG S.p.A.",                       "IT0001157020"),
    "INW.MI":    ("INWIT S.p.A.",                     "IT0005090300"),

    # === FTSE MID CAP ===
    "ACE.MI":    ("ACEA S.p.A.",                      "IT0001207098"),
    "ANIM.MI":   ("Anima Holding S.p.A.",             "IT0004998065"),
    "ARN.MI":    ("Aeroporto Guglielmo Marconi di Bologna S.p.A.", "IT0005327657"),
    "BC.MI":     ("Brunello Cucinelli S.p.A.",        "IT0004764699"),
    "BFF.MI":    ("BFF Bank S.p.A.",                  "IT0005244402"),
    "BRE.MI":    ("Brembo N.V.",                      "NL0015000W43"),
    "BZU.MI":    ("Buzzi S.p.A.",                     "IT0001347308"),
    "CE.MI":     ("Credito Emiliano S.p.A.",          "IT0003121677"),
    "CEM.MI":    ("Cementir Holding N.V.",            "NL0012609421"),
    "DAN.MI":    ("Danieli & C. S.p.A.",              "IT0000076486"),
    "DAL.MI":    ("Danieli & C. Risparmio",           "IT0000076478"),
    "DLG.MI":    ("De' Longhi S.p.A.",                "IT0003115950"),
    "ELC.MI":    ("Elica S.p.A.",                     "IT0003487029"),
    "EM.MI":     ("Emak S.p.A.",                      "IT0005453250"),
    "EQUI.MI":   ("Equita Group S.p.A.",              "IT0005312027"),
    "FCT.MI":    ("Fincantieri S.p.A.",               "IT0004854496"),
    "FNM.MI":    ("FNM S.p.A.",                       "IT0000060886"),
    "FILA.MI":   ("F.I.L.A. - Fabbrica Italiana Lapis ed Affini", "IT0004967292"),
    "GHC.MI":    ("Garofalo Health Care S.p.A.",      "IT0005351496"),
    "GVS.MI":    ("GVS S.p.A.",                       "IT0005393290"),
    "IF.MI":     ("Banca IFIS S.p.A.",                "IT0003188064"),
    "IGD.MI":    ("Immobiliare Grande Distribuzione SIIQ", "IT0003745889"),
    "IRE.MI":    ("Iren S.p.A.",                      "IT0003027817"),
    "JUVE.MI":   ("Juventus Football Club S.p.A.",    "IT0005572778"),
    "LUVE.MI":   ("LU-VE S.p.A.",                     "IT0005045354"),
    "MARR.MI":   ("MARR S.p.A.",                      "IT0001005010"),
    "MAIRE.MI":  ("MAIRE S.p.A.",                     "IT0004931058"),
    "MN.MI":     ("Mondadori Editore S.p.A.",         "IT0001469383"),
    "MFEA.MI":   ("MFE-MediaForEurope N.V. A",        "NL0015001OJ8"),
    "MFEB.MI":   ("MFE-MediaForEurope N.V. B",        "NL0015001OK6"),
    "OVS.MI":    ("OVS S.p.A.",                       "IT0005043507"),
    "PHN.MI":    ("Philogen S.p.A.",                  "IT0005419554"),
    "PIA.MI":    ("Piaggio & C. S.p.A.",              "IT0003073266"),
    "RWAY.MI":   ("Reply S.p.A.",                     "IT0001499620"),
    "SFL.MI":    ("Safilo Group S.p.A.",              "IT0004604762"),
    "SAB.MI":    ("Sabaf S.p.A.",                     "IT0001210050"),
    "SL.MI":     ("Saes Getters S.p.A.",              "IT0000076569"),
    "SES.MI":    ("Sesa S.p.A.",                      "IT0005122370"),
    "SOL.MI":    ("Sol S.p.A.",                       "IT0000076536"),
    "SSL.MI":    ("Salvatore Ferragamo S.p.A.",       "IT0004712375"),
    "TES.MI":    ("Tessellis S.p.A.",                 "IT0005108488"),
    "TXT.MI":    ("TXT e-solutions S.p.A.",           "IT0001454435"),
    "TIP.MI":    ("Tamburi Investment Partners S.p.A.", "IT0003153621"),
    "WBD.MI":    ("Webuild S.p.A.",                   "IT0003865570"),
    "ZV.MI":     ("Zignago Vetro S.p.A.",             "IT0004171440"),
    "DIB.MI":    ("Digital Bros S.p.A.",              "IT0001469995"),
    "WIIT.MI":   ("WIIT S.p.A.",                      "IT0005440893"),
    "GE.MI":     ("Generalfinance S.p.A.",            "IT0005227510"),
    "CY4.MI":    ("Cy4Gate S.p.A.",                   "IT0005412504"),
    "BFG.MI":    ("BasicNet S.p.A.",                  "IT0001049623"),
    "CIR.MI":    ("CIR S.p.A.",                       "IT0000070786"),
    "ELN.MI":    ("El.En. S.p.A.",                    "IT0003480546"),
    "ENV.MI":    ("Enav S.p.A.",                      "IT0005176406"),
    "MAR.MI":    ("Marr S.p.A.",                      "IT0001005010"),
    "RAT.MI":    ("Ratti S.p.A.",                     "IT0001029492"),
    "RDF.MI":    ("Reno De Medici S.p.A.",            "IT0005327989"),
    "TKA.MI":    ("Tinexta S.p.A.",                   "IT0005354256"),
    "TNXT.MI":   ("Tinexta S.p.A.",                   "IT0005354256"),
    "VLS.MI":    ("Valsoia S.p.A.",                   "IT0001454238"),

    # === SMALL CAP ===
    "ALA.MI":    ("Alkemy S.p.A.",                    "IT0005314420"),
    "EXP.MI":    ("Expert.ai S.p.A.",                 "IT0005384248"),
    "GPI.MI":    ("GPI S.p.A.",                       "IT0005221004"),
    "ITM.MI":    ("Italmobiliare S.p.A.",             "IT0005239881"),
    "ITW.MI":    ("Italian Wine Brands S.p.A.",       "IT0005386131"),
    "LR.MI":     ("LVenture Group S.p.A.",            "IT0004982850"),
    "NWL.MI":    ("Newlat Food S.p.A.",               "IT0005379302"),
    "ORS.MI":    ("Orsero S.p.A.",                    "IT0005138703"),
    "PRL.MI":    ("Pierrel S.p.A.",                   "IT0004991573"),
}


def get_milan_universe() -> list[str]:
    """Restituisce la lista dei ticker validi (chiavi della mappa)."""
    return list(TICKER_METADATA.keys())


def get_metadata(ticker: str) -> tuple[str, str]:
    """
    Restituisce (nome, ISIN) per un ticker.
    Fallback: (ticker, '—') se non in mappa.
    """
    meta = TICKER_METADATA.get(ticker)
    if meta is None:
        return (ticker, "—")
    return meta


def get_universe_stats() -> dict:
    """Statistiche sull'universo per UI con breakdown per nazionalità ISIN."""
    italiani = sum(1 for _, isin in TICKER_METADATA.values() if isin.startswith("IT"))
    olandesi = sum(1 for _, isin in TICKER_METADATA.values() if isin.startswith("NL"))
    lussemb = sum(1 for _, isin in TICKER_METADATA.values() if isin.startswith("LU"))
    return {
        "Totali": len(TICKER_METADATA),
        "🇮🇹 Italia": italiani,
        "🇳🇱 Olanda": olandesi,
        "🇱🇺 Lussemb.": lussemb,
    }

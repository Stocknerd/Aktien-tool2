import pandas as pd
from pathlib import Path
import sys

# Configure stdout for utf-8 if possible
# sys.stdout.reconfigure(encoding='utf-8') # Might fail on some windows shells, safer to avoiding emojis

BASE_DIR = Path(__file__).resolve().parent
FILE_OUTPUT = BASE_DIR / "ticker_resolved.csv"

def get_manual_sdax():
    print("Generating manual SDAX list...")
    # Top SDAX / known SDAX tickers
    data = [
        ("FIE.DE", "Fielmann", "Consumer Discretionary", "SDAX"),
        ("DEZ.DE", "Deutz", "Industrials", "SDAX"),
        ("SWA.DE", "SMA Solar", "Technology", "SDAX"),
        ("HDD.DE", "Heidelberger Druckmaschinen", "Industrials", "SDAX"),
        ("JJU.DE", "Jungheinrich", "Industrials", "SDAX"),
        ("KRN.DE", "Krones", "Industrials", "SDAX"),
        ("NDX1.DE", "Nordex", "Energy", "SDAX"),
        ("EVT.DE", "Evotec", "Health Care", "SDAX"),
        ("WAF.DE", "Siltronic", "Technology", "SDAX"),
        ("PFV.DE", "Pfeiffer Vacuum", "Industrials", "SDAX"),
        ("GFT.DE", "GFT Technologies", "Technology", "SDAX"),
        ("GIL.DE", "Wacker Neuson", "Industrials", "SDAX"),
        ("HLE.DE", "Hella", "Consumer Discretionary", "SDAX"),
        ("BOSS.DE", "Hugo Boss", "Consumer Discretionary", "SDAX"), # Often MDAX?
        ("SIX2.DE", "Sixt Vz", "Consumer Discretionary", "SDAX"),
        ("DUE.DE", "Duerr", "Industrials", "SDAX"),
        ("BIO3.DE", "Biotest", "Health Care", "SDAX"),
        ("ZAL.DE", "Zalando", "Consumer Discretionary", "SDAX") # Was DAX, then MDAX/SDAX?
    ]
    return pd.DataFrame(data, columns=["valid_yahoo_ticker", "resolved_name", "Sektor", "SourceIndex"])

def get_manual_msci_world_top_non_us():
    print("Generating manual MSCI World Top Non-US list...")
    # Selection of largest non-US components
    data = [
        # Switzerland
        ("NESN.SW", "Nestle", "Consumer Staples", "MSCI World"),
        ("ROG.SW", "Roche", "Health Care", "MSCI World"),
        ("NOVN.SW", "Novartis", "Health Care", "MSCI World"),
        ("CFR.SW", "Richemont", "Consumer Discretionary", "MSCI World"),
        ("UBSG.SW", "UBS Group", "Financials", "MSCI World"),
        ("ABBN.SW", "ABB", "Industrials", "MSCI World"),
        ("ZURN.SW", "Zurich Insurance", "Financials", "MSCI World"),
        # UK
        ("SHEL.L", "Shell", "Energy", "MSCI World"),
        ("AZN.L", "AstraZeneca", "Health Care", "MSCI World"),
        ("HSBA.L", "HSBC", "Financials", "MSCI World"),
        ("ULVR.L", "Unilever", "Consumer Staples", "MSCI World"),
        ("BP.L", "BP", "Energy", "MSCI World"),
        ("RIO.L", "Rio Tinto", "Materials", "MSCI World"),
        ("GSK.L", "GSK", "Health Care", "MSCI World"),
        ("BATS.L", "British American Tobacco", "Consumer Staples", "MSCI World"),
        ("REL.L", "RELX", "Industrials", "MSCI World"),
        ("DGE.L", "Diageo", "Consumer Staples", "MSCI World"),
        # France / EU
        ("ASML.AS", "ASML", "Technology", "MSCI World"),
        ("MC.PA", "LVMH", "Consumer Discretionary", "MSCI World"),
        ("OR.PA", "L'Oreal", "Consumer Staples", "MSCI World"),
        ("TTE.PA", "TotalEnergies", "Energy", "MSCI World"),
        ("AIR.PA", "Airbus", "Industrials", "MSCI World"),
        ("RMS.PA", "Hermes", "Consumer Discretionary", "MSCI World"),
        ("SAN.MC", "Banco Santander", "Financials", "MSCI World"),
        ("IBE.MC", "Iberdrola", "Utilities", "MSCI World"),
        ("ITX.MC", "Inditex", "Consumer Discretionary", "MSCI World"),
        ("INGA.AS", "ING Group", "Financials", "MSCI World"),
        ("CS.PA", "AXA", "Financials", "MSCI World"),
        ("BNP.PA", "BNP Paribas", "Financials", "MSCI World"),
        ("SU.PA", "Schneider Electric", "Industrials", "MSCI World"),
        ("AI.PA", "Air Liquide", "Materials", "MSCI World"),
        # Denmark
        ("NOVO-B.CO", "Novo Nordisk", "Health Care", "MSCI World"),
        # Japan
        ("7203.T", "Toyota Motor", "Consumer Discretionary", "MSCI World"),
        ("6758.T", "Sony Group", "Consumer Discretionary", "MSCI World"),
        ("8306.T", "Mitsubishi UFJ", "Financials", "MSCI World"),
        ("9984.T", "Softbank Group", "Communication", "MSCI World"),
        ("6861.T", "Keyence", "Technology", "MSCI World"),
        ("4063.T", "Shin-Etsu Chemical", "Materials", "MSCI World"),
        # Canada
        ("RY.TO", "Royal Bank of Canada", "Financials", "MSCI World"),
        ("TD.TO", "Toronto-Dominion Bank", "Financials", "MSCI World"),
        ("CNR.TO", "Canadian National Railway", "Industrials", "MSCI World"),
        ("CP.TO", "Canadian Pacific", "Industrials", "MSCI World"),
        ("CNQ.TO", "Canadian Natural Resources", "Energy", "MSCI World"),
        ("ENB.TO", "Enbridge", "Energy", "MSCI World"),
        # Australia
        ("BHP.AX", "BHP Group", "Materials", "MSCI World"),
        ("CBA.AX", "CommBank Australia", "Financials", "MSCI World"),
        ("CSL.AX", "CSL", "Health Care", "MSCI World"),
        ("NAB.AX", "National Australia Bank", "Financials", "MSCI World")
    ]
    return pd.DataFrame(data, columns=["valid_yahoo_ticker", "resolved_name", "Sektor", "SourceIndex"])

def main():
    print("Starting manual ticker add...")
    
    df_new = pd.concat([get_manual_sdax(), get_manual_msci_world_top_non_us()], ignore_index=True)
    
    print(f"Prepared {len(df_new)} manual tickers.")

    if FILE_OUTPUT.exists():
        print(f"Loading existing {FILE_OUTPUT.name}...")
        df_old = pd.read_csv(FILE_OUTPUT)
        
        # Merge SourceIndex
        idx_map = df_new.set_index("valid_yahoo_ticker")["SourceIndex"].to_dict()
        if "SourceIndex" not in df_old.columns: df_old["SourceIndex"] = None
        df_old["SourceIndex"] = df_old["valid_yahoo_ticker"].map(idx_map).combine_first(df_old["SourceIndex"])
        
        # Append missing
        existing_set = set(df_old["valid_yahoo_ticker"].astype(str))
        to_add = df_new[~df_new["valid_yahoo_ticker"].isin(existing_set)]
        
        if not to_add.empty:
            print(f"Appending {len(to_add)} NEW tickers:")
            print(to_add["resolved_name"].tolist())
            df_combined = pd.concat([df_old, to_add], ignore_index=True)
        else:
            print("All manual tickers already exist (SourceIndex updated).")
            df_combined = df_old
    else:
        df_combined = df_new

    # Drop duplicates
    df_combined = df_combined.drop_duplicates(subset=["valid_yahoo_ticker"], keep="last")
    
    df_combined.to_csv(FILE_OUTPUT, index=False, encoding="utf-8-sig")
    print(f"Saved {len(df_combined)} rows to {FILE_OUTPUT}.")

if __name__ == "__main__":
    main()

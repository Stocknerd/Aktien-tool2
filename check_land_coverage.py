import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FILE_DATA = BASE_DIR / "stock_data.csv"

def check():
    if not FILE_DATA.exists():
        print("Datei nicht gefunden.")
        return

    df = pd.read_csv(FILE_DATA)
    total = len(df)
    
    # Check coverage of new columns
    has_land = df["Land"].notna().sum()
    has_name = df["Langname"].notna().sum()
    
    print(f"Total Rows: {total}")
    print(f"Rows with 'Land': {has_land} ({has_land/total*100:.1f}%)")
    print(f"Rows with 'Langname': {has_name} ({has_name/total*100:.1f}%)")
    
    print("\nTop 10 Countries by count:")
    print(df["Land"].value_counts().head(10))

if __name__ == "__main__":
    check()

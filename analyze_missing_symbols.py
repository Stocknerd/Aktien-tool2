import pandas as pd

# CSV laden
df = pd.read_csv('stock_data.csv')

# Zeilen ohne Symbol filtern
missing_symbols = df[df['Symbol'].isna() | (df['Symbol'] == '')]

print(f"Gesamtanzahl Zeilen ohne Symbol: {len(missing_symbols)}")
print("\nBeispiel-Unternehmen ohne Symbol:")
# Zeige die ersten 20 Treffer mit relevanten Spalten
cols_to_show = ['Security', 'Langname', 'Land', 'Branche']
# Nur vorhandene Spalten anzeigen
existing_cols = [c for c in cols_to_show if c in df.columns]
print(missing_symbols[existing_cols].head(20).to_string())

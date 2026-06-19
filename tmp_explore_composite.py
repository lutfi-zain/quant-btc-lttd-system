import pandas as pd
import requests

# Fetch composite oscillator data
url = "http://localhost:5173/api/composite"
response = requests.get(url)
data = response.json()

df_comp = pd.DataFrame(data)
df_comp['date'] = pd.to_datetime(df_comp['date']).dt.tz_localize(None)
df_comp.set_index('date', inplace=True)

tops = [
    ("2017 Top", "2017-11-01", "2018-01-15"),
    ("2021 Spring Top", "2021-03-01", "2021-05-15"),
    ("2021 Fall Top", "2021-10-01", "2021-11-30"),
    ("2024 Spring Top", "2024-02-15", "2024-04-15")
]

for name, start, end in tops:
    mask = (df_comp.index >= start) & (df_comp.index <= end)
    top_window = df_comp[mask]
    if not top_window.empty:
        max_price_idx = top_window["btc_price"].idxmax()
        peak_row = top_window.loc[max_price_idx]
        max_composite = top_window["composite_value"].max()
        
        print(f"=== {name} ===")
        print(f"Peak Price Date: {max_price_idx.strftime('%Y-%m-%d')} | Price: ${peak_row['btc_price']:,.0f}")
        print(f"Composite at Peak : {peak_row['composite_value']:.2f}")
        print(f"Max Composite in Window: {max_composite:.2f}")
        print("")

# Also check what the min/max overall are
print(f"Overall Max Composite: {df_comp['composite_value'].max():.2f}")
print(f"Overall Min Composite: {df_comp['composite_value'].min():.2f}")


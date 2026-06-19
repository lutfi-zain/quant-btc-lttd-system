import pandas as pd
df = pd.read_csv("docs/isps/isp-signals-btcusd-2026-06-13.csv")
df["Date"] = pd.to_datetime(df["Date"])
years = (df["Date"].max() - df["Date"].min()).days / 365.25
eq_start = df["TotalEquity"].iloc[0]
eq_end = df["TotalEquity"].iloc[-1]
cagr = (eq_end / eq_start) ** (1/years) - 1
print(f"Target CAGR: {cagr*100:.2f}%")

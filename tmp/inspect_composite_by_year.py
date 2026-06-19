import requests
import pandas as pd
import numpy as np

def main():
    r = requests.get("http://localhost:5173/api/composite", timeout=10)
    data = r.json()
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    if df['date'].dt.tz is not None:
        df['date'] = df['date'].dt.tz_convert(None)
    df.set_index('date', inplace=True)
    df['year'] = df.index.year
    
    print("Composite value summary by year:")
    print("="*60)
    summary = df.groupby('year')['composite_value'].agg(['count', 'mean', 'min', 'max', 'std'])
    print(summary)
    
    print("\nQuantiles by year:")
    print("="*60)
    for yr in sorted(df['year'].unique()):
        yr_df = df[df['year'] == yr]
        q = yr_df['composite_value'].quantile([0.1, 0.25, 0.5, 0.75, 0.9])
        print(f"Year {yr}: p10={q[0.1]:.3f} | p25={q[0.25]:.3f} | p50={q[0.5]:.3f} | p75={q[0.75]:.3f} | p90={q[0.9]:.3f}")

if __name__ == '__main__':
    main()

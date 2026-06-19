import requests
import pandas as pd

def main():
    try:
        # Let's try port 5173
        r = requests.get("http://localhost:5173/api/composite", timeout=5)
        print("Port 5173 returned status:", r.status_code)
        data = r.json()
        print("Data size:", len(data))
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        print("Date range on 5173:", df['date'].min(), "to", df['date'].max())
        print("Sample 2018 data on 5173:")
        print(df[df['date'].dt.year == 2018].head())
    except Exception as e:
        print("Failed to query 5173:", e)
        
    try:
        # Let's try port 8765
        r = requests.get("http://localhost:8765/api/composite", timeout=5)
        print("Port 8765 returned status:", r.status_code)
        data = r.json()
        print("Data size:", len(data))
    except Exception as e:
        print("Failed to query 8765:", e)

if __name__ == '__main__':
    main()

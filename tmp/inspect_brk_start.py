import requests

def main():
    # Fetch from bitview API
    url = "https://bitview.space/api/series/price_ohlc/day?start=2009-01-01"
    resp = requests.get(url).json()
    
    start_idx = resp["start"]
    print("API start index:", start_idx)
    print("First 5 data points:", resp["data"][:5])
    
    # Check if there is data on Jan 3, 2009 or if it's the genesis block.
    # Note that BTC's genesis block was on Jan 3, 2009.
    # If the API starts at index 0, and index 0 is Jan 3, 2009:
    # then start_idx = 2 means Jan 5, 2009.
    # Let's inspect the actual start date on the Bitview website or API.
    # Let's fetch bulk price data for the first index
    url_bulk = "https://bitview.space/api/series/bulk?series=price_ohlc&index=day1&start=0"
    resp_bulk = requests.get(url_bulk).json()
    print("Bulk API start index:", resp_bulk["start"])
    print("Bulk API data length:", len(resp_bulk["data"]))
    print("Bulk API first 5 data points:", resp_bulk["data"][:5])

if __name__ == '__main__':
    main()

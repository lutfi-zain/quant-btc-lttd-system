import requests

def main():
    url_bulk = "https://bitview.space/api/series/bulk?series=price_ohlc&index=day1&start=0"
    resp_bulk = requests.get(url_bulk).json()
    data = resp_bulk["data"]
    
    # Find first index where close > 0
    first_non_zero_idx = -1
    for i, row in enumerate(data):
        if row[3] > 0:  # close is index 3
            first_non_zero_idx = i
            break
            
    print("First non-zero index:", first_non_zero_idx)
    print("Row at that index:", data[first_non_zero_idx])
    print("Next 5 rows:", data[first_non_zero_idx:first_non_zero_idx+5])

if __name__ == '__main__':
    main()

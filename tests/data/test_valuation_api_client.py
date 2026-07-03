import pytest
from unittest.mock import patch, MagicMock
from src.data.valuation_api_client import ValuationApiClient
import pandas as pd
import requests

def test_get_latest_composite_value_success():
    from datetime import datetime
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    client = ValuationApiClient()
    mock_response = MagicMock()
    mock_response.json.return_value = [{"date": today_str, "composite_value": -1.5}]
    
    with patch("requests.get", return_value=mock_response):
        value = client.get_latest_composite_value()
        assert value == -1.5
        
        # Test caching
        mock_response.json.side_effect = Exception("Should not hit API again")
        cached_value = client.get_latest_composite_value()
        assert cached_value == -1.5

def test_get_latest_composite_value_failure():
    client = ValuationApiClient()
    with patch("requests.get", side_effect=requests.exceptions.RequestException("API down")):
        value = client.get_latest_composite_value()
        assert value == 0.0

def test_get_composite_value_for_date():
    client = ValuationApiClient()
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"date": "2024-01-01T00:00:00Z", "composite_value": 0.5},
        {"date": "2024-01-02T00:00:00Z", "composite_value": -1.2}
    ]
    
    with patch("requests.get", return_value=mock_response):
        val1 = client.get_composite_value_for_date(pd.Timestamp("2024-01-01", tz="UTC"))
        assert val1 == 0.5
        
        val2 = client.get_composite_value_for_date(pd.Timestamp("2024-01-03", tz="UTC"))
        assert val2 == -1.2


def test_get_latest_composite_value_stale(caplog):
    import logging
    client = ValuationApiClient()
    mock_response = MagicMock()
    # 3 days ago
    stale_date = (pd.Timestamp.utcnow() - pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    mock_response.json.return_value = [{"date": stale_date, "composite_value": 0.8}]
    
    with caplog.at_level(logging.WARNING):
        with patch("requests.get", return_value=mock_response):
            value = client.get_latest_composite_value()
            assert value == 0.0
            assert any("STALE" in record.message for record in caplog.records)


def test_get_composite_value_for_date_stale(caplog):
    import logging
    client = ValuationApiClient()
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"date": "2024-01-01T00:00:00Z", "composite_value": 0.5},
        {"date": "2024-01-02T00:00:00Z", "composite_value": -1.2}
    ]
    
    # Target date is 3 days after latest record (2024-01-02)
    target_date = pd.Timestamp("2024-01-05", tz="UTC")
    
    with caplog.at_level(logging.WARNING):
        with patch("requests.get", return_value=mock_response):
            value = client.get_composite_value_for_date(target_date)
            assert value == 0.0
            assert any("STALE" in record.message for record in caplog.records)


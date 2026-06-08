from unittest.mock import MagicMock
from src.ensemble.wfo import WFOEnsemble


def test_fetch_deep_matrices():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_historical_bulk.return_value = [{"index": "day1", "data": [1]}]

    ensemble = WFOEnsemble(fetcher=mock_fetcher)
    res = ensemble.fetch_deep_matrices(start=-500)

    assert res == [{"index": "day1", "data": [1]}]
    mock_fetcher.fetch_historical_bulk.assert_called_once_with(
        ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"], start=-500
    )

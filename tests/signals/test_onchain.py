from unittest.mock import MagicMock
from src.signals.onchain import OnChainSignalEngine


def test_get_realtime_signals():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_latest.side_effect = lambda series: {
        "value": 0.5,
        "stamp": "2026-06-08",
    }

    engine = OnChainSignalEngine(fetcher=mock_fetcher)
    signals = engine.get_realtime_signals()

    assert signals["sth_mvrv"] == 0.5
    assert signals["sth_nupl"] == 0.5
    assert signals["sth_sopr_24h"] == 0.5
    assert signals["sth_supply_in_profit"] == 0.5
    assert mock_fetcher.fetch_latest.call_count == 4

from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from src.signals.onchain import OnChainSignalEngine, OnChainFeed


def test_get_realtime_signals():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_latest.side_effect = lambda series: {
        "value": 0.5,
        "stamp": datetime.now(timezone.utc),
    }

    engine = OnChainSignalEngine(fetcher=mock_fetcher)
    signals = engine.get_realtime_signals()

    assert signals["sth_mvrv"] == 0.5
    assert signals["sth_nupl"] == 0.5
    assert signals["sth_sopr_24h"] == 0.5
    assert signals["sth_supply_in_profit"] == 0.5


def test_onchain_feed_causal_validation():
    mock_fetcher = MagicMock()
    feed = OnChainFeed(fetcher=mock_fetcher)

    current_bar_time = datetime(2026, 6, 10, 10, 0, 0, tzinfo=timezone.utc)

    # 1. Normal case: stamp is causal (e.g. 1 day ago) and within 3 days
    mock_fetcher.fetch_latest.side_effect = lambda series: {
        "value": 1.2,
        "stamp": current_bar_time - timedelta(days=1),
    }
    signals = feed.fetch_latest_causal(current_bar_time)
    assert signals["sth_mvrv"] == 1.2
    assert signals["sth_nupl"] == 1.2

    # 2. Lookahead case: stamp is in future (e.g. current_bar_time + 1 hour)
    # This should trigger lookahead detection and fall back to 0.0
    mock_fetcher.fetch_latest.side_effect = lambda series: {
        "value": 1.2,
        "stamp": current_bar_time + timedelta(hours=1),
    }
    signals_lookahead = feed.fetch_latest_causal(current_bar_time)
    assert signals_lookahead["sth_mvrv"] == 0.0

    # 3. Stale case: stamp is 4 days old
    # This should trigger staleness detection and fall back to 0.0
    mock_fetcher.fetch_latest.side_effect = lambda series: {
        "value": 1.2,
        "stamp": current_bar_time - timedelta(days=4),
    }
    signals_stale = feed.fetch_latest_causal(current_bar_time)
    assert signals_stale["sth_mvrv"] == 0.0

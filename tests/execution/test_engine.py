from unittest.mock import MagicMock
from src.execution.engine import ExecutionEngine
from src.data.brk_fetcher import StaleOnChainDataError


def test_run_daily_success():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_latest.side_effect = lambda series: {
        "value": 0.8,
        "stamp": "2026-06-08",
    }

    engine = ExecutionEngine(fetcher=mock_fetcher)
    res = engine.run_daily()

    assert res["status"] == "success"
    assert res["metrics"]["mvrv"] == 0.8
    assert res["metrics"]["nupl"] == 0.8


def test_run_daily_stale():
    mock_fetcher = MagicMock()
    mock_fetcher.fetch_latest.side_effect = StaleOnChainDataError("Stale data")

    engine = ExecutionEngine(fetcher=mock_fetcher)
    res = engine.run_daily()

    assert res["status"] == "paused"
    assert "Stale data" in res["error"]

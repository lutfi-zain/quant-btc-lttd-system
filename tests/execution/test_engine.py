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


def test_persist_features(tmp_path):
    db_path = str(tmp_path / "test_engine_persist.db")
    from src.execution.db import init_db, get_connection
    init_db(db_path)

    engine = ExecutionEngine()
    engine.persist_features(
        date_str="2023-01-01",
        indicator_scores={"rsi": 1, "macd": -1},
        pca_components={"PC1": 0.5, "PC2": -0.3},
        db_path=db_path
    )

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM indicator_scores WHERE date = '2023-01-01' ORDER BY indicator_name")
        rows_ind = cursor.fetchall()
        assert len(rows_ind) == 2
        assert rows_ind[0]["indicator_name"] == "macd"
        assert rows_ind[0]["score"] == -1
        assert rows_ind[1]["indicator_name"] == "rsi"
        assert rows_ind[1]["score"] == 1

        cursor.execute("SELECT * FROM pca_components WHERE date = '2023-01-01' ORDER BY component_name")
        rows_pca = cursor.fetchall()
        assert len(rows_pca) == 2
        assert rows_pca[0]["component_name"] == "PC1"
        assert rows_pca[0]["value"] == 0.5
        assert rows_pca[1]["component_name"] == "PC2"
        assert rows_pca[1]["value"] == -0.3


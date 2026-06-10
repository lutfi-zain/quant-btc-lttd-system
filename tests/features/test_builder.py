import pandas as pd
import numpy as np
import pytest
from src.features.builder import FeatureMatrixBuilder
from src.features.vif import calculate_vif, prune_multicollinear_indicators


@pytest.fixture
def sample_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=600)
    closes = np.cumsum(np.random.randn(600)) + 100
    highs = closes + np.random.rand(600) * 2.0
    lows = closes - np.random.rand(600) * 2.0
    volumes = np.random.rand(600) * 1000.0 + 100.0
    return pd.DataFrame(
        {"close": closes, "high": highs, "low": lows, "volume": volumes}, index=dates
    )


def test_feature_matrix_builder_shape(sample_data):
    builder = FeatureMatrixBuilder()
    matrix = builder.build_matrix(sample_data)

    assert isinstance(matrix, pd.DataFrame)
    assert len(matrix) == len(sample_data)
    assert sorted(list(matrix.columns)) == sorted(
        [
            "FDI",
            "QuantileDEMA",
            "AdvancedStochastic",
            "KalmanRSI",
            "FourierSupertrend",
            "TrendStrengthIndex",
        ]
    )
    # Check no NaN values are present at the end of the series
    non_nan_part = matrix.dropna()
    assert len(non_nan_part) > 200


def test_feature_matrix_vif_and_pruning(sample_data):
    builder = FeatureMatrixBuilder()
    matrix = builder.build_matrix(sample_data).dropna()

    # Calculate VIF on the built feature matrix
    vifs = calculate_vif(matrix)

    # All Batch 3 indicators must have VIF < 10 since they are mathematically diverse
    for col in matrix.columns:
        assert vifs[col] < 10.0, f"Indicator {col} has VIF >= 10: {vifs[col]}"

    # Artificially inject a highly correlated column to test Pratt's Measure pruning
    collinear_matrix = matrix.copy()
    # Adding a column that is almost identical to FDI
    collinear_matrix["FDI_collinear"] = collinear_matrix["FDI"] + np.random.normal(
        0, 0.001, len(collinear_matrix)
    )

    # Calculate VIF on the collinear matrix
    vifs_collinear = calculate_vif(collinear_matrix)
    assert vifs_collinear["FDI"] > 10.0
    assert vifs_collinear["FDI_collinear"] > 10.0

    # Run pruning
    # Create a dummy target y
    y = collinear_matrix["FDI"] * 2.0 + np.random.normal(0, 0.1, len(collinear_matrix))
    pruned_matrix = prune_multicollinear_indicators(
        collinear_matrix, y, vif_threshold=10.0
    )

    # Verify that the collinear column is pruned and VIF is restored to < 10
    vifs_pruned = calculate_vif(pruned_matrix)
    for col in pruned_matrix.columns:
        assert vifs_pruned[col] <= 10.0
    # Ensure one of FDI or FDI_collinear was dropped
    assert not (
        "FDI" in pruned_matrix.columns and "FDI_collinear" in pruned_matrix.columns
    )


def test_feature_matrix_onchain_momentum_pruning(sample_data):
    # Add on-chain columns to sample_data
    data = sample_data.copy()
    data["sth_mvrv"] = 1.2
    data["sth_nupl"] = 0.6
    data["sth_sopr_24h"] = 1.0
    # Make sth_supply_in_profit identical to sth_sopr_24h to trigger high VIF
    data["sth_supply_in_profit"] = data["sth_sopr_24h"]

    builder = FeatureMatrixBuilder()
    matrix = builder.build_matrix(data)

    assert "sth_mvrv_roc_7" in matrix.columns
    assert "sth_nupl_roc_7" in matrix.columns
    assert "sth_sopr_24h_roc_7" in matrix.columns
    assert "sth_supply_in_profit_roc_7" in matrix.columns

    # Since they are constant/collinear, VIF will be high or infinite
    vifs = calculate_vif(matrix)
    # At least one of the collinear ones should be infinite
    assert vifs["sth_sopr_24h_roc_7"] == float("inf")

    # Target y
    y = pd.Series(np.random.randn(len(matrix)), index=matrix.index)
    pruned = prune_multicollinear_indicators(matrix, y, vif_threshold=10.0)

    # VIF should be under 10.0 after pruning
    pruned_vifs = calculate_vif(pruned)
    for col in pruned.columns:
        assert pruned_vifs[col] <= 10.0

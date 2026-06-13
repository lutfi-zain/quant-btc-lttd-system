import numpy as np
import pandas as pd
import pytest
from src.features.processor import FeatureProcessor


def test_feature_processor_orchestration():
    np.random.seed(42)
    # Generate 6 core technical indicators (some collinear)
    fdi = np.random.randn(100)
    qdema = fdi + np.random.normal(0, 0.01, 100) # highly collinear
    stoch = np.random.randn(100)
    krsi = np.random.randn(100)
    fourier = np.random.randn(100)
    tsi = np.random.randn(100)

    # Onchain metrics
    mvrv = np.random.randn(100)
    nupl = np.random.randn(100)

    df = pd.DataFrame({
        "FDI": fdi,
        "QuantileDEMA": qdema,
        "AdvancedStochastic": stoch,
        "KalmanRSI": krsi,
        "FourierSupertrend": fourier,
        "TrendStrengthIndex": tsi,
        "sth_mvrv_roc_7": mvrv,
        "sth_nupl_roc_7": nupl
    })

    processor = FeatureProcessor(vif_threshold=10.0)
    processor.fit(df)

    # 1. Verify kept columns
    # FDI and QuantileDEMA are collinear, so one of them should be pruned
    assert not ("FDI" in processor.kept_tech_cols and "QuantileDEMA" in processor.kept_tech_cols)
    assert len(processor.kept_tech_cols) < 6

    # 2. Verify transform output
    df_transformed = processor.transform(df)
    
    # Check that columns in transformed output are PC components + onchain columns
    cols = df_transformed.columns.tolist()
    # PC columns should exist
    assert any(c.startswith("PC") for c in cols)
    # Onchain columns must bypass PCA and be present directly
    assert "sth_mvrv_roc_7" in cols
    assert "sth_nupl_roc_7" in cols
    
    # Check shape
    assert len(df_transformed) == 100


def test_feature_processor_no_lookahead():
    np.random.seed(42)
    df = pd.DataFrame({
        "FDI": np.random.randn(200),
        "QuantileDEMA": np.random.randn(200),
        "AdvancedStochastic": np.random.randn(200),
        "KalmanRSI": np.random.randn(200),
        "FourierSupertrend": np.random.randn(200),
        "TrendStrengthIndex": np.random.randn(200),
        "sth_mvrv_roc_7": np.random.randn(200)
    })

    df_train = df.iloc[:150]
    df_test = df.iloc[150:]

    processor = FeatureProcessor()
    processor.fit(df_train)

    # Transform test set as a block
    trans_test_block = processor.transform(df_test)

    # Transform test set incrementally
    trans_test_incremental = []
    for i in range(len(df_test)):
        row = df_test.iloc[[i]]
        trans_row = processor.transform(row)
        trans_test_incremental.append(trans_row.iloc[0])

    df_incremental = pd.DataFrame(trans_test_incremental, index=df_test.index)

    # Assert block transform matches step-by-step transform
    pd.testing.assert_frame_equal(trans_test_block, df_incremental)


def test_feature_processor_segregated_vif():
    np.random.seed(42)
    # FDI and QuantileDEMA are collinear
    fdi = np.random.randn(100)
    qdema = fdi + np.random.normal(0, 0.01, 100)
    stoch = np.random.randn(100)
    krsi = np.random.randn(100)
    fourier = np.random.randn(100)
    tsi = np.random.randn(100)

    # Create an on-chain feature highly collinear with stoch
    mvrv = stoch + np.random.normal(0, 0.001, 100) # extremely collinear (VIF will be huge)

    df = pd.DataFrame({
        "FDI": fdi,
        "QuantileDEMA": qdema,
        "AdvancedStochastic": stoch,
        "KalmanRSI": krsi,
        "FourierSupertrend": fourier,
        "TrendStrengthIndex": tsi,
        "sth_mvrv_roc_7": mvrv
    })

    processor = FeatureProcessor(vif_threshold=5.0) # low threshold to trigger pruning
    processor.fit(df)

    # Verify that the on-chain feature is NOT pruned (meaning it's not in kept_tech_cols,
    # and continues to bypass VIF pruning and PCA entirely)
    assert "sth_mvrv_roc_7" not in processor.kept_tech_cols
    
    df_transformed = processor.transform(df)
    assert "sth_mvrv_roc_7" in df_transformed.columns

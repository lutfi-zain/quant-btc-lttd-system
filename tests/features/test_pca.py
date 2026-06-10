import numpy as np
import pandas as pd
import pytest
from src.features.pca import CausalPCA


def test_pca_orthogonality_and_variance():
    np.random.seed(42)
    # Create collinear features
    x1 = np.random.randn(200)
    x2 = x1 + np.random.normal(0, 0.1, 200)
    x3 = x1 + np.random.normal(0, 0.2, 200)
    x4 = np.random.randn(200)
    x5 = x4 + np.random.normal(0, 0.1, 200)

    df = pd.DataFrame({"x1": x1, "x2": x2, "x3": x3, "x4": x4, "x5": x5})

    pca = CausalPCA(variance_threshold=0.85)
    pca.fit(df)
    
    # 1. Variance retention threshold: check n_components is less than 5
    assert pca.n_components_ < 5
    
    # 2. Orthogonality: project training data and check correlation
    df_transformed = pca.transform(df)
    corr = df_transformed.corr()
    
    # Off-diagonal elements should be extremely close to 0
    for i in range(pca.n_components_):
        for j in range(pca.n_components_):
            if i != j:
                assert np.isclose(corr.iloc[i, j], 0.0, atol=1e-12)


def test_pca_sign_alignment():
    np.random.seed(42)
    # Generate data with positive trend
    x1 = np.linspace(-10, 10, 100) + np.random.randn(100)
    x2 = x1 + np.random.normal(0, 0.5, 100)
    df1 = pd.DataFrame({"x1": x1, "x2": x2})

    pca1 = CausalPCA()
    pca1.fit(df1)
    df_trans1 = pca1.transform(df1)

    # Now generate negative trend (opposite signs)
    df2 = -df1.copy()
    pca2 = CausalPCA()
    pca2.fit(df2)
    df_trans2 = pca2.transform(df2)

    # In standard PCA, components can flip arbitrarily.
    # With our sign alignment heuristic, they should maintain the same sign relationship
    # with the input mean. Thus, the correlation of PC1 with baseline should be positive in both.
    corr1 = np.corrcoef(df_trans1["PC1"].values, df1.mean(axis=1).values)[0, 1]
    corr2 = np.corrcoef(df_trans2["PC1"].values, df2.mean(axis=1).values)[0, 1]
    
    assert corr1 > 0
    assert corr2 > 0


def test_pca_causality_no_lookahead():
    np.random.seed(42)
    x1 = np.random.randn(200)
    x2 = x1 + np.random.normal(0, 0.1, 200)
    df = pd.DataFrame({"x1": x1, "x2": x2})

    # Split into train (150) and test (50)
    df_train = df.iloc[:150]
    df_test = df.iloc[150:]

    pca = CausalPCA()
    pca.fit(df_train)

    # Transform the test set as a block
    trans_test_block = pca.transform(df_test)

    # Transform the test set step-by-step
    trans_test_incremental = []
    for idx in range(len(df_test)):
        row = df_test.iloc[[idx]]
        trans_row = pca.transform(row)
        trans_test_incremental.append(trans_row.iloc[0])

    df_incremental = pd.DataFrame(trans_test_incremental, index=df_test.index)

    # Assert block transform equals incremental transform (ensures no leakage)
    pd.testing.assert_frame_equal(trans_test_block, df_incremental)

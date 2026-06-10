import pandas as pd
from src.data.brk_fetcher import BRKDataFetcher
from src.features.ou_calibration import estimate_ou_halflife


class WFOEnsemble:
    def __init__(self, fetcher: BRKDataFetcher = None):
        self.fetcher = fetcher or BRKDataFetcher()
        self.ou_halflives = {}

    def fetch_deep_matrices(self, start=-1000):
        series_list = ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"]
        return self.fetcher.fetch_historical_bulk(series_list, start=start)

    def recalibrate_ou_halflife(
        self,
        log_returns: pd.Series,
        train_end: pd.Timestamp,
        train_window_days: int = 1095,
    ) -> float:
        """
        Recalibrate the OU Half-Life strictly using purged in-sample data.
        In-sample data starts at (train_end - train_window_days) and ends at train_end.
        """
        train_start = train_end - pd.Timedelta(days=train_window_days)
        in_sample = log_returns.loc[train_start:train_end]

        # Recalibrate
        hl = estimate_ou_halflife(in_sample, min_bars=250)
        return hl

    def run_wfo_calibration(
        self,
        log_returns: pd.Series,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        legacy_fixed_window: bool = False,
    ) -> pd.Series:
        """
        Runs quarterly recalibration of OU half-life over the dataset.
        If legacy_fixed_window is True, forces a static 200-day window.
        """
        target_index = log_returns.loc[start_date:end_date].index
        if legacy_fixed_window:
            return pd.Series(200.0, index=target_index)

        # Generate quarterly dates
        quarterly_dates = pd.date_range(start=start_date, end=end_date, freq="QS")

        # Calculate half-life for each quarter using in-sample (past 3-year) data
        for q_date in quarterly_dates:
            # Training data ends exactly before the quarter starts
            train_end = q_date - pd.Timedelta(days=1)
            hl = self.recalibrate_ou_halflife(log_returns, train_end)
            self.ou_halflives[q_date] = hl

        # Create a series mapped to daily index
        daily_hl = pd.Series(350.0, index=target_index)

        for i, date in enumerate(daily_hl.index):
            prev_quarters = [q for q in quarterly_dates if q <= date]
            if prev_quarters:
                prev_q = max(prev_quarters)
                daily_hl.iloc[i] = self.ou_halflives[prev_q]
            else:
                daily_hl.iloc[i] = 350.0

        return daily_hl

    def merge_onchain_data(
        self, ohlcv_df: pd.DataFrame, onchain_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge OHLCV data and on-chain historical bulk data via causal asof merge.
        """
        if not isinstance(ohlcv_df.index, pd.DatetimeIndex):
            ohlcv_df.index = pd.to_datetime(ohlcv_df.index)
        if not isinstance(onchain_df.index, pd.DatetimeIndex):
            onchain_df.index = pd.to_datetime(onchain_df.index)

        ohlcv_sorted = ohlcv_df.sort_index()
        onchain_sorted = onchain_df.sort_index()

        merged = pd.merge_asof(
            ohlcv_sorted,
            onchain_sorted,
            left_index=True,
            right_index=True,
            direction="backward",
        )
        return merged

    def process_features(
        self, train_data: pd.DataFrame, test_data: pd.DataFrame, y_train: pd.Series = None
    ) -> tuple:
        """
        Orchestrate VIF pruning and PCA transformation causally across WFO folds.
        Fits FeatureProcessor on train_data and transforms both train_data and test_data.
        """
        from src.features.processor import FeatureProcessor
        
        processor = FeatureProcessor()
        processor.fit(train_data, y_train)
        
        train_processed = processor.transform(train_data)
        test_processed = processor.transform(test_data)
        
        return train_processed, test_processed

    def purge_train_set(
        self, train_index: pd.DatetimeIndex, test_intervals: list, purge_days: int = 7
    ) -> pd.DatetimeIndex:
        """
        Purges training indices that fall within `purge_days` of any test interval
        to prevent overlap and serial correlation leakage.
        """
        to_drop = pd.Index([])
        for start, end in test_intervals:
            # Define overlap zone to purge
            purge_start = start - pd.Timedelta(days=purge_days)
            purge_end = end + pd.Timedelta(days=purge_days)
            
            overlap = train_index[(train_index >= purge_start) & (train_index <= purge_end)]
            to_drop = to_drop.union(overlap)
            
        return train_index.difference(to_drop)

    def cpcv_split(
        self, X: pd.DataFrame, n_groups: int = 6, n_test_groups: int = 2, purge_days: int = 7
    ):
        """
        CPCV splitter. Splits indices into n_groups.
        Yields (train_index, test_index) by selecting all combinations of n_test_groups as test sets,
        and using remaining groups (purged) as training sets.
        """
        indices = X.index
        group_size = len(indices) // n_groups
        groups = []
        for g in range(n_groups):
            start_idx = g * group_size
            end_idx = (g + 1) * group_size if g < n_groups - 1 else len(indices)
            groups.append(indices[start_idx:end_idx])
            
        import itertools
        group_indices = list(range(n_groups))
        for test_comb in itertools.combinations(group_indices, n_test_groups):
            test_index = pd.Index([])
            test_intervals = []
            for g in test_comb:
                test_index = test_index.union(groups[g])
                test_intervals.append((groups[g].min(), groups[g].max()))
                
            train_index = pd.Index([])
            for g in group_indices:
                if g not in test_comb:
                    train_index = train_index.union(groups[g])
                    
            train_index_purged = self.purge_train_set(train_index, test_intervals, purge_days)
            
            yield train_index_purged, test_index

    def generate_wfo_folds(
        self,
        index: pd.DatetimeIndex,
        train_window_days: int = 1095,   # 3 years
        val_window_days: int = 180,      # 6 months
        test_window_days: int = 180,     # 6 months
    ):
        """
        Yields chronological train, validation, and test fold splits.
        Guarantees strict precedence: train -> validate -> test.
        """
        min_date = index.min()
        max_date = index.max()
        
        current_test_start = min_date + pd.Timedelta(days=train_window_days + val_window_days)
        
        while current_test_start < max_date:
            current_test_end = current_test_start + pd.Timedelta(days=test_window_days)
            if current_test_end > max_date:
                current_test_end = max_date
                
            val_end = current_test_start - pd.Timedelta(days=1)
            val_start = val_end - pd.Timedelta(days=val_window_days)
            
            train_end = val_start - pd.Timedelta(days=1)
            train_start = train_end - pd.Timedelta(days=train_window_days)
            
            train_idx = index[(index >= train_start) & (index <= train_end)]
            val_idx = index[(index >= val_start) & (index <= val_end)]
            test_idx = index[(index >= current_test_start) & (index <= current_test_end)]
            
            if len(train_idx) > 0 and len(val_idx) > 0 and len(test_idx) > 0:
                yield train_idx, val_idx, test_idx
                
            # Slide forward by test_window_days
            current_test_start += pd.Timedelta(days=test_window_days)

    def run_wfo_pipeline(self, X: pd.DataFrame, y: pd.Series) -> pd.Series:
        """
        Runs the complete WFO pipeline:
        For each fold (3yr train -> 6mo val -> 6mo test):
        - Apply FeatureProcessor (VIF + PCA) on train data.
        - Transform validation and test data.
        - Train L1LassoEnsemble on processed train data.
        - Predict scores on processed test data.
        Returns a combined pd.Series of out-of-sample predicted scores.
        Also calculates and stores out-of-sample R^2 scores for audit.
        """
        from src.ensemble.model import L1LassoEnsemble
        from src.features.processor import FeatureProcessor
        from sklearn.metrics import r2_score
        
        y = pd.Series(y, index=X.index)
        out_of_sample_scores = pd.Series(dtype=float)
        self.r2_scores = {}
        
        folds = list(self.generate_wfo_folds(X.index))
        if not folds:
            # Fallback: if data is too short, fit once on everything
            processor = FeatureProcessor()
            processor.fit(X, y)
            X_proc = processor.transform(X)
            model = L1LassoEnsemble()
            model.fit(X_proc, y)
            scores = model.predict_score(X_proc)
            self.r2_scores[X.index[0]] = float(r2_score(y, (scores > 0).astype(int)))
            return scores
            
        for idx, (train_idx, val_idx, test_idx) in enumerate(folds):
            X_train = X.loc[train_idx]
            y_train = y.loc[train_idx]
            
            X_test = X.loc[test_idx]
            y_test = y.loc[test_idx]
            
            # Feature processing (VIF + PCA)
            processor = FeatureProcessor()
            processor.fit(X_train, y_train)
            
            X_train_proc = processor.transform(X_train)
            X_test_proc = processor.transform(X_test)
            
            # Model fitting
            model = L1LassoEnsemble()
            model.fit(X_train_proc, y_train)
            
            # Out-of-sample predictions
            test_scores = model.predict_score(X_test_proc)
            
            # Avoid duplicate index issues
            overlap_idx = out_of_sample_scores.index.intersection(test_scores.index)
            if not overlap_idx.empty:
                out_of_sample_scores = out_of_sample_scores.drop(overlap_idx)
            
            out_of_sample_scores = pd.concat([out_of_sample_scores, test_scores])
            
            # Calculate R2 score
            preds_binary = (test_scores > 0).astype(int)
            r2 = float(r2_score(y_test, preds_binary))
            self.r2_scores[test_idx[0]] = r2
            
        return out_of_sample_scores

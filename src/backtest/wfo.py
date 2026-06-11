import itertools
from typing import Generator, Tuple, List
import pandas as pd


class WFOIterator:
    """
    Orchestrates Walk-Forward Optimization (WFO) rolling windows and
    Combinatorial Purged Cross-Validation (CPCV) splits.
    """
    def __init__(
        self,
        train_window_days: int = 1095,   # 3 years
        val_window_days: int = 180,      # 6 months
        test_window_days: int = 180,     # 6 months
        purge_days: int = 350,           # CPCV purge days (up to 350 days for OU Half-Life)
    ):
        self.train_window_days = train_window_days
        self.val_window_days = val_window_days
        self.test_window_days = test_window_days
        self.purge_days = purge_days

    def generate_wfo_folds(
        self,
        index: pd.DatetimeIndex,
    ) -> Generator[Tuple[pd.DatetimeIndex, pd.DatetimeIndex, pd.DatetimeIndex], None, None]:
        """
        Yields chronological train, validation, and test fold splits.
        Guarantees strict precedence: train -> validate -> test.
        """
        if not isinstance(index, pd.DatetimeIndex):
            index = pd.to_datetime(index)

        min_date = index.min()
        max_date = index.max()
        
        current_test_start = min_date + pd.Timedelta(days=self.train_window_days + self.val_window_days)
        
        while current_test_start < max_date:
            current_test_end = current_test_start + pd.Timedelta(days=self.test_window_days)
            if current_test_end > max_date:
                current_test_end = max_date
                
            val_end = current_test_start - pd.Timedelta(days=1)
            val_start = val_end - pd.Timedelta(days=self.val_window_days)
            
            train_end = val_start - pd.Timedelta(days=1)
            train_start = train_end - pd.Timedelta(days=self.train_window_days)
            
            # Extract raw indices
            raw_train_idx = index[(index >= train_start) & (index <= train_end)]
            val_idx = index[(index >= val_start) & (index <= val_end)]
            test_idx = index[(index >= current_test_start) & (index <= current_test_end)]
            
            # Apply CPCV purging on train set: drop train bars adjacent to the validation/test window
            test_intervals = [(val_idx.min(), test_idx.max())]
            train_idx = self.purge_train_set(raw_train_idx, test_intervals, self.purge_days)
            
            if len(train_idx) > 0 and len(val_idx) > 0 and len(test_idx) > 0:
                yield train_idx, val_idx, test_idx
                
            # Slide forward by test_window_days
            current_test_start += pd.Timedelta(days=self.test_window_days)

    def purge_train_set(
        self,
        train_index: pd.DatetimeIndex,
        test_intervals: List[Tuple[pd.Timestamp, pd.Timestamp]],
        purge_days: int,
    ) -> pd.DatetimeIndex:
        """
        Purges training indices that fall within `purge_days` of any test interval
        to prevent overlap and serial correlation leakage.
        """
        if len(train_index) == 0 or purge_days <= 0:
            return train_index
            
        to_drop = pd.Index([])
        for start, end in test_intervals:
            # Define overlap zone to purge
            purge_start = start - pd.Timedelta(days=purge_days)
            purge_end = end + pd.Timedelta(days=purge_days)
            
            overlap = train_index[(train_index >= purge_start) & (train_index <= purge_end)]
            to_drop = to_drop.union(overlap)
            
        return train_index.difference(to_drop)

    def cpcv_split(
        self,
        X: pd.DataFrame,
        n_groups: int = 6,
        n_test_groups: int = 2,
        purge_days: int = 350,
    ) -> Generator[Tuple[pd.DatetimeIndex, pd.DatetimeIndex], None, None]:
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


def point_in_time_join(ohlcv_df: pd.DataFrame, onchain_df: pd.DataFrame) -> pd.DataFrame:
    """
    Causally join OHLCV data and BRK on-chain data using pandas.merge_asof with direction='backward',
    keyed on the BRK 'stamp' field (representing the point-in-time release date).
    """
    ohlcv = ohlcv_df.copy()
    onchain = onchain_df.copy()
    
    # Ensure ohlcv has a datetime index and is sorted
    if not isinstance(ohlcv.index, pd.DatetimeIndex):
        ohlcv.index = pd.to_datetime(ohlcv.index)
    ohlcv = ohlcv.sort_index()
    
    # Ensure onchain has 'stamp' column. If not, try to construct it from index
    if 'stamp' not in onchain.columns:
        if isinstance(onchain.index, pd.DatetimeIndex):
            onchain['stamp'] = onchain.index
        else:
            onchain['stamp'] = pd.to_datetime(onchain.index)
            
    # Ensure stamp column is datetime and sorted
    onchain['stamp'] = pd.to_datetime(onchain['stamp'])
    onchain = onchain.sort_values('stamp')
    
    # Reset ohlcv index to make it a mergeable column
    ohlcv = ohlcv.reset_index()
    ohlcv_date_col = ohlcv.columns[0]
    ohlcv[ohlcv_date_col] = pd.to_datetime(ohlcv[ohlcv_date_col])
    
    # merge_asof backward keyed on stamp / date
    merged = pd.merge_asof(
        ohlcv,
        onchain,
        left_on=ohlcv_date_col,
        right_on='stamp',
        direction='backward'
    )
    
    # Set the ohlcv date column back as the index
    merged = merged.set_index(ohlcv_date_col)
    if merged.index.name == 'index':
        merged.index.name = None
        
    return merged

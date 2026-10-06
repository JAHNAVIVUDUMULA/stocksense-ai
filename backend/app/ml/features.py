import pandas as pd
import numpy as np
from typing import Tuple, List

def build_time_series_features(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Constructs autoregressive lag features, rolling statistics, calendar indicators,
    and trend metrics for machine learning demand forecasting.
    """
    if daily_df.empty or len(daily_df) < 2:
        return pd.DataFrame()

    df = daily_df.copy()
    df["datetime"] = pd.to_datetime(df["date"])
    
    # Calendar features
    df["day_of_week"] = df["datetime"].dt.dayofweek
    df["day_of_month"] = df["datetime"].dt.day
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    
    # Lag features (previous day demand, 2 days ago, 7 days ago)
    df["lag_1"] = df["quantity"].shift(1)
    df["lag_2"] = df["quantity"].shift(2)
    df["lag_7"] = df["quantity"].shift(7)

    # Rolling window statistics (7-day and 14-day)
    df["rolling_mean_7"] = df["quantity"].shift(1).rolling(window=7, min_periods=1).mean()
    df["rolling_std_7"] = df["quantity"].shift(1).rolling(window=7, min_periods=1).std().fillna(0)
    df["rolling_mean_14"] = df["quantity"].shift(1).rolling(window=14, min_periods=1).mean()

    # Drop initial rows that don't have enough history for lag_1
    feature_df = df.dropna(subset=["lag_1"]).copy()
    # Fill remaining NaNs from lag_7 with backward/mean fill
    feature_df["lag_2"] = feature_df["lag_2"].fillna(feature_df["lag_1"])
    feature_df["lag_7"] = feature_df["lag_7"].fillna(feature_df["rolling_mean_7"])
    
    return feature_df

def get_feature_matrix(feature_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Extracts the feature matrix X and target y for training.
    """
    feature_cols = [
        "lag_1", "lag_2", "lag_7",
        "rolling_mean_7", "rolling_std_7", "rolling_mean_14",
        "day_of_week", "day_of_month", "is_weekend"
    ]
    X = feature_df[feature_cols].values
    y = feature_df["quantity"].values
    return X, y, feature_cols

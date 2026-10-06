import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import List, Dict, Any, Tuple

def prepare_daily_sales_series(sales_records: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Transforms raw sales transaction records into a continuous daily time-series DataFrame.
    Fills days with zero sales as 0, ensuring consistent time intervals for ML and statistics.
    """
    if not sales_records:
        return pd.DataFrame(columns=["date", "quantity", "revenue"])

    df = pd.DataFrame(sales_records)
    # Convert sale_date to datetime.date
    df["date"] = pd.to_datetime(df["sale_date"]).dt.date
    
    # Aggregate by date (sum quantity and revenue)
    daily = df.groupby("date").agg(
        quantity=("quantity", "sum"),
        revenue=("price", lambda p: (p * df.loc[p.index, "quantity"]).sum() if "price" in df else 0.0)
    ).reset_index()

    # Reindex to full date range from earliest sale to today (or latest sale)
    min_date = daily["date"].min()
    max_date = max(daily["date"].max(), date.today())
    
    all_dates = pd.date_range(start=min_date, end=max_date, freq="D").date
    full_df = pd.DataFrame({"date": all_dates})
    merged = pd.merge(full_df, daily, on="date", how="left")
    merged["quantity"] = merged["quantity"].fillna(0).astype(float)
    merged["revenue"] = merged["revenue"].fillna(0.0).astype(float)
    
    return merged.sort_values("date").reset_index(drop=True)

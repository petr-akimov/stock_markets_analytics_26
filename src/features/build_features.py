"""Feature engineering module for calculating technical indicators and target variables."""

from __future__ import annotations

import typer
import pandas as pd
import numpy as np
import ta

from src import config
from src.utils.io import load_parquet, save_parquet, save_to_db

app = typer.Typer(add_completion=False, help="Feature engineering CLI")


def generate_features(prices: pd.DataFrame) -> pd.DataFrame:
    """Generate technical indicators and momentum features for sector rotation safely across groups."""
    df = prices.copy()
    if "ticker" not in df.columns:
        raise ValueError(f"Prices DataFrame missing 'ticker' column. Available columns: {df.columns.tolist()}")

    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    processed_frames = []
    for ticker, sub in df.groupby("ticker"):
        sub = sub.copy()
        
        # Returns across multiple windows (momentum)
        sub["ret_1d"] = sub["adjclose"].pct_change(1)
        sub["ret_21d"] = sub["adjclose"].pct_change(21)   # ~1 month
        sub["ret_63d"] = sub["adjclose"].pct_change(63)   # ~3 months
        sub["ret_126d"] = sub["adjclose"].pct_change(126) # ~6 months

        # Volatility
        sub["vol_21d"] = sub["ret_1d"].rolling(21).std()

        # Calendar features
        sub["dow"] = sub["date"].dt.day_of_week
        sub["month"] = sub["date"].dt.month

        # Technical indicators
        sub["sma_20"] = ta.trend.sma_indicator(sub["adjclose"], window=20)
        sub["sma_50"] = ta.trend.sma_indicator(sub["adjclose"], window=50)
        sub["ema_20"] = ta.trend.ema_indicator(sub["adjclose"], window=20)
        sub["rsi_14"] = ta.momentum.rsi(sub["adjclose"], window=14)
        
        macd = ta.trend.MACD(sub["adjclose"])
        sub["macd"] = macd.macd()
        sub["macd_signal"] = macd.macd_signal()

        # Target definition: Forward 21-day return (next month return)
        sub["target_reg_21d"] = sub["adjclose"].pct_change(21).shift(-21)
        
        # Binary target: 1 if positive forward return, 0 otherwise
        sub["target_cls_21d"] = (sub["target_reg_21d"] > 0).astype(int)

        processed_frames.append(sub)

    df_out = pd.concat(processed_frames, ignore_index=True)
    df_out = df_out.sort_values(["ticker", "date"]).reset_index(drop=True)
    return df_out


@app.command("run")
def run(to_db: bool = typer.Option(False, "--to-db", help="Persist features into SQLite")):
    """Execute feature generation pipeline."""
    prices_path = config.PROCESSED_DIR / "prices.parquet"
    features_path = config.ANALYTICS_DIR / "features.parquet"

    prices = load_parquet(prices_path)
    if prices is None or prices.empty:
        typer.secho(f"Prices file not found at {prices_path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.secho("Generating features...", fg=typer.colors.CYAN)
    features = generate_features(prices)

    save_parquet(features, features_path, index=False)
    if to_db:
        save_to_db(features, table_name="features", if_exists="replace")

    typer.secho(f"Features successfully generated: {len(features)} rows | Saved to {features_path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
"""Signal generation module using Top-K sector selection based on ML predictions."""

from __future__ import annotations

import typer
import joblib
import pandas as pd
import numpy as np
from pathlib import Path

from src import config
from src.utils.io import load_parquet, save_parquet

app = typer.Typer(add_completion=False, help="Signal generation CLI")


@app.command("run")
def run(
    top_k: int = typer.Option(config.TOP_K_SECTORS, "--top-k", help="Number of top sectors to select"),
):
    """Generate portfolio allocation weights by selecting Top-K sectors per period."""
    features_path = config.ANALYTICS_DIR / "features.parquet"
    model_path = config.MODELS_DIR / "sector_rf_model.joblib"
    signals_path = config.SIGNALS_DIR / "signals.parquet"

    feats = load_parquet(features_path)
    if feats is None or feats.empty:
        typer.secho(f"Features file not found at {features_path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not model_path.exists():
        typer.secho(f"Model file not found at {model_path}. Train the model first.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    model = joblib.load(model_path)

    exclude = {"date", "ticker", "target_reg_21d", "target_cls_21d"}
    feature_cols = [c for c in feats.columns if c not in exclude and pd.api.types.is_numeric_dtype(feats[c])]

    # Predict probabilities for all rows
    X = feats[feature_cols].fillna(0)
    probs = model.predict_proba(X)[:, 1]

    df_preds = feats[["date", "ticker"]].copy()
    df_preds["proba_up"] = probs

    # Rank sectors per date to select Top-K
    df_preds["rank"] = df_preds.groupby("date")["proba_up"].rank(method="first", ascending=False)

    # Signal: 1 if selected in Top-K, 0 otherwise
    df_preds["signal"] = (df_preds["rank"] <= top_k).astype(int)

    # Equal weight allocation among Top-K sectors
    df_preds["weight"] = df_preds["signal"] / top_k
    df_preds["strategy"] = f"top_k_sector_rotation_k{top_k}"

    out_cols = ["date", "ticker", "signal", "weight", "proba_up", "strategy"]
    signals_df = df_preds[out_cols].sort_values(["date", "ticker"]).reset_index(drop=True)

    save_parquet(signals_df, signals_path, index=False)

    # Извлекаем рекомендацию для самой последней даты в датасете
    latest_date = signals_df["date"].max()
    latest_signals = signals_df[signals_df["date"] == latest_date]
    active_picks = latest_signals[latest_signals["signal"] == 1]

    # Формируем период прогноза (например, на следующие 21 день / месяц)
    start_period = pd.to_datetime(latest_date).strftime("%Y-%m-%d")
    end_period = (pd.to_datetime(latest_date) + pd.Timedelta(days=21)).strftime("%Y-%m-%d")

    recommendations_lines = [
        f"Signals generated successfully: {len(signals_df)} rows | Saved to {signals_path}",
        f"\n--- TRADING RECOMMENDATION ---",
        f"Target Period: {start_period} to {end_period}",
        f"Top-{top_k} Recommended Assets & Allocation Weights:"
    ]
    
    for _, row in active_picks.iterrows():
        ticker = row["ticker"]
        weight_pct = row["weight"] * 100
        prob = row["proba_up"] * 100
        recommendations_lines.append(f"  • Long {ticker}: Weight = {weight_pct:.1f}% (Model Confidence: {prob:.1f}%)")

    success_msg = "\n".join(recommendations_lines)
    typer.secho(success_msg, fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
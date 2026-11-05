"""Backtest simulator module for evaluating sector rotation strategy performance."""

from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
import typer

from src import config
from src.utils.io import load_parquet, save_parquet

app = typer.Typer(add_completion=False, help="Backtest simulator CLI")


def compute_metrics(equity: pd.Series, ret_daily: pd.Series, trading_days: int = 252) -> dict:
    """Calculate standard performance metrics."""
    eq = equity.dropna()
    r = ret_daily.dropna()

    if eq.empty or r.empty:
        return {
            "CAGR": None,
            "Sharpe": None,
            "Vol_Ann": None,
            "MaxDrawdown": None,
            "N_Days": int(len(r)),
        }

    n_days = len(r)
    start_val, end_val = float(eq.iloc[0]), float(eq.iloc[-1])
    years = max(n_days / trading_days, 1e-9)
    cagr = (end_val / start_val) ** (1 / years) - 1 if start_val > 0 else None

    mu = r.mean()
    sigma = r.std(ddof=0)
    vol_ann = sigma * np.sqrt(trading_days) if sigma is not None else None
    sharpe = (mu / sigma) * np.sqrt(trading_days) if sigma and sigma > 0 else None

    roll_max = eq.cummax()
    drawdown = eq / roll_max - 1.0
    maxdd = drawdown.min()

    return {
        "CAGR": None if cagr is None else float(cagr),
        "Sharpe": None if sharpe is None else float(sharpe),
        "Vol_Ann": None if vol_ann is None else float(vol_ann),
        "MaxDrawdown": None if maxdd is None else float(maxdd),
        "N_Days": int(n_days),
    }


@app.command("run")
def run(
    fee_bps: float = typer.Option(5.0, "--fee-bps", help="Transaction fee in basis points"),
    slippage_bps: float = typer.Option(2.0, "--slippage-bps", help="Slippage in basis points"),
):
    """Execute backtest simulation based on generated signals and prices."""
    prices_path = config.PROCESSED_DIR / "prices.parquet"
    signals_path = config.SIGNALS_DIR / "signals.parquet"
    results_dir = config.BACKTESTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)

    prices = load_parquet(prices_path)
    signals = load_parquet(signals_path)

    if prices is None or prices.empty:
        typer.secho(f"Prices file not found at {prices_path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if signals is None or signals.empty:
        typer.secho(f"Signals file not found at {signals_path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Merge prices and signals
    df = pd.merge(prices, signals[["date", "ticker", "weight"]], on=["date", "ticker"], how="inner")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    # Calculate daily market returns
    df["ret_mkt"] = df.groupby("ticker")["adjclose"].pct_change().fillna(0.0)

    # Shift weights to avoid look-ahead bias (execution on next day)
    df["weight_prev"] = df.groupby("ticker")["weight"].shift(1).fillna(0.0)

    # Turnover calculation for transaction costs
    df["weight_diff"] = df.groupby("ticker")["weight_prev"].diff().abs().fillna(0.0)
    cost_rate = (fee_bps + slippage_bps) / 10_000.0
    df["cost"] = df["weight_diff"] * cost_rate

    # Portfolio gross and net return
    df["ret_gross"] = df["weight_prev"] * df["ret_mkt"]
    df["ret_net"] = df["ret_gross"] - df["cost"]

    # Aggregate portfolio daily returns (equal-weighted across active selections)
    daily = df.groupby("date").agg(ret_port=("ret_net", "sum")).reset_index().sort_values("date")
    daily["equity"] = (1.0 + daily["ret_port"]).cumprod() * 100_000.0

    equity_series = daily.set_index("date")["equity"]
    ret_series = daily.set_index("date")["ret_port"]

    summary = compute_metrics(equity_series, ret_series)

    # Save outputs
    save_parquet(daily, results_dir / "equity.parquet", index=False)
    summary_path = results_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    typer.secho(f"Backtest completed successfully. Saved to {results_dir}", fg=typer.colors.GREEN)
    typer.secho(f"CAGR: {summary.get('CAGR'):.4%} | Sharpe: {summary.get('Sharpe'):.2f} | MaxDD: {summary.get('MaxDrawdown'):.4%}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
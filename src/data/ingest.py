"""Market data ingestion module using yfinance for sector ETFs and benchmarks."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd
import typer
import yfinance as yf

from src import config
from src.utils.io import save_parquet, load_parquet, save_to_db

app = typer.Typer(add_completion=False, help="Market data ingestion CLI")


def _download_yf(
    tickers: List[str],
    start: str,
    end: Optional[str] = None,
    interval: str = "1d",
) -> pd.DataFrame:
    """Download data from Yahoo Finance ticker by ticker for robust parsing."""
    if not tickers:
        return pd.DataFrame()

    frames = []
    for t in tickers:
        sub = yf.download(
            t,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if sub is None or sub.empty:
            continue

        sub = sub.copy()
        # Flatten columns if multiindex
        sub.columns = [
            str(c[0]).lower().replace(" ", "_") if isinstance(c, tuple) else str(c).lower().replace(" ", "_")
            for c in sub.columns
        ]
        sub = sub.reset_index()

        date_cols = [c for c in sub.columns if "date" in c.lower()]
        if not date_cols:
            continue
        date_col = date_cols[0]

        sub = sub.rename(columns={date_col: "date"})
        sub["ticker"] = t
        frames.append(sub)

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)

    if "adj_close" in df.columns and "adjclose" not in df.columns:
        df = df.rename(columns={"adj_close": "adjclose"})
    if "close" in df.columns and "adjclose" not in df.columns:
        df["adjclose"] = df["close"]

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

    needed = ["date", "ticker", "open", "high", "low", "close", "adjclose", "volume"]
    existing_cols = [c for c in needed if c in df.columns]
    df = df[existing_cols].sort_values(["ticker", "date"]).reset_index(drop=True)
    return df


@app.command("run")
def run(
    tickers: Optional[List[str]] = typer.Option(
        None, "--tickers", "-t", help="List of tickers to download"
    ),
    start: Optional[str] = typer.Option(
        None, "--start", "-s", help="Start date YYYY-MM-DD"
    ),
    end: Optional[str] = typer.Option(
        None, "--end", "-e", help="End date YYYY-MM-DD"
    ),
    to_db: bool = typer.Option(
        False, "--to-db", help="Persist data into SQLite database"
    ),
    overwrite: bool = typer.Option(
        True, "--overwrite", help="Overwrite existing historical data"
    ),
):
    """Execute data ingestion for sector rotation project."""
    prices_path = config.PROCESSED_DIR / "prices.parquet"

    if tickers is None or len(tickers) == 0:
        tickers = config.SECTOR_TICKERS + [config.BENCHMARK_TICKER]
    if start is None:
        start = config.DATA_START

    df_all = _download_yf(tickers, start=start, end=end)
    if df_all.empty:
        typer.secho("No new data downloaded.", fg=typer.colors.YELLOW)
        return

    save_parquet(df_all, prices_path, index=False)
    if to_db:
        save_to_db(df_all, table_name="prices", if_exists="replace")

    # Формируем расширенную сводку с периодом дат и превью столбцов
    min_date = df_all["date"].min().strftime("%Y-%m-%d") if "date" in df_all.columns else "N/A"
    max_date = df_all["date"].max().strftime("%Y-%m-%d") if "date" in df_all.columns else "N/A"
    columns_list = ", ".join(df_all.columns.tolist())
    head_preview = df_all.head(5).to_string(index=False)

    success_msg = (
        f"Ingestion completed successfully.\n"
        f"- Total rows: {len(df_all)}\n"
        f"- Date range: {min_date} to {max_date}\n"
        f"- Columns ({len(df_all.columns)}): {columns_list}\n"
        f"- First 5 rows preview:\n{head_preview}\n"
        f"Saved to {prices_path}"
    )

    typer.secho(success_msg, fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
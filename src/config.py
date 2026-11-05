"""Global project configurations for Sector Rotation ML strategy."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env", override=True)

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ANALYTICS_DIR = DATA_DIR / "analytics"
SIGNALS_DIR = DATA_DIR / "signals"
BACKTESTS_DIR = DATA_DIR / "backtests"
MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports"
IMG_DIR = REPORTS_DIR / "img"
STORAGE_DIR = BASE_DIR / "storage"

for d in [
    RAW_DIR,
    PROCESSED_DIR,
    ANALYTICS_DIR,
    SIGNALS_DIR,
    BACKTESTS_DIR,
    MODELS_DIR,
    REPORTS_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)

DATA_START = os.getenv("DATA_START", "2010-01-01")
SECTOR_TICKERS = [
    t.strip()
    for t in os.getenv(
        "SECTOR_TICKERS",
        "XLK,XLF,XLV,XLE,XLI,XLP,XLY,XLU,XLB,XLRE,XLC",
    ).split(",")
    if t.strip()
]
BENCHMARK_TICKER = os.getenv("BENCHMARK_TICKER", "SPY")
DB_PATH = os.getenv("DB_PATH", str(STORAGE_DIR / "app.db"))
TOP_K_SECTORS = int(os.getenv("TOP_K_SECTORS", "3"))
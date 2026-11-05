"""Data input and output utilities for Parquet, CSV, and SQLite."""

from pathlib import Path
from typing import Optional
import pandas as pd
from sqlalchemy import create_engine
from src import config


def save_parquet(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    """Save DataFrame to Parquet format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=index)


def load_parquet(path: Path) -> Optional[pd.DataFrame]:
    """Load DataFrame from Parquet format if it exists."""
    if not path.exists():
        return None
    return pd.read_parquet(path)


def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    """Save DataFrame to CSV format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)


def load_csv(path: Path) -> Optional[pd.DataFrame]:
    """Load DataFrame from CSV format if it exists."""
    if not path.exists():
        return None
    return pd.read_csv(path)


def get_db_engine():
    """Return SQLAlchemy SQLite engine."""
    return create_engine(f"sqlite:///{config.DB_PATH}")


def save_to_db(df: pd.DataFrame, table_name: str, if_exists: str = "replace") -> None:
    """Save DataFrame to SQLite table."""
    engine = get_db_engine()
    with engine.begin() as conn:
        df.to_sql(table_name, conn, if_exists=if_exists, index=False)


def load_from_db(table_name: str) -> Optional[pd.DataFrame]:
    """Load DataFrame from SQLite table if it exists."""
    engine = get_db_engine()
    with engine.begin() as conn:
        try:
            return pd.read_sql(f"SELECT * FROM {table_name}", conn)
        except Exception:
            return None
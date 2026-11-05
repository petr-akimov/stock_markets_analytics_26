"""End-to-end pipeline orchestrator for sector rotation strategy."""

from __future__ import annotations

import traceback
import typer

from src.data.ingest import run as ingest_run
from src.features.build_features import run as features_run
from src.models.train import run as train_run
from src.strategy.generate_signals import run as signals_run
from src.backtest.simulator import run as backtest_run

app = typer.Typer(add_completion=False, help="End-to-end pipeline CLI")


def _safe_step(step_name: str, func, **kwargs) -> None:
    """Execute a pipeline step with error handling and logging."""
    typer.secho(f"[pipeline] >>> Running: {step_name}", fg=typer.colors.CYAN, bold=True)
    try:
        func(**kwargs)
        typer.secho(f"[pipeline] OK: {step_name}", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"[pipeline] ERROR in {step_name}: {e}", fg=typer.colors.RED)
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command("run")
def run(
    retrain: bool = typer.Option(False, "--retrain", help="Retrain ML models before generating signals"),
):
    """Execute the entire end-to-end quantitative pipeline."""
    typer.secho("================ SECTOR ROTATION PIPELINE ================", fg=typer.colors.MAGENTA, bold=True)

    # Step 1: Data Ingestion
    _safe_step("Data Ingestion", ingest_run)

    # Step 2: Feature Engineering
    _safe_step("Feature Engineering", features_run, to_db=False)

    # Step 3: Model Training (conditional)
    if retrain:
        _safe_step("Model Training", train_run)
    else:
        typer.secho("[pipeline] Skipping model training (retrain=false)", fg=typer.colors.YELLOW)

    # Step 4: Signal Generation
    _safe_step("Signal Generation", signals_run)

    # Step 5: Backtest Simulation
    _safe_step("Backtest Simulation", backtest_run)

    typer.secho("================ PIPELINE COMPLETED SUCCESSFULLY ================", fg=typer.colors.GREEN, bold=True)


if __name__ == "__main__":
    app()
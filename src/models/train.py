"""Model training module using TimeSeriesSplit cross-validation."""

from __future__ import annotations

import typer
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score

from src import config
from src.utils.io import load_parquet, save_parquet

app = typer.Typer(add_completion=False, help="Model training CLI")


def _prepare_data(features: pd.DataFrame):
    """Prepare feature matrix X and target y for classification."""
    exclude = {"date", "ticker", "target_reg_21d", "target_cls_21d"}
    cols = [c for c in features.columns if c not in exclude and pd.api.types.is_numeric_dtype(features[c])]
    
    # Drop rows with NaN in features or target
    df_clean = features.dropna(subset=cols + ["target_cls_21d"]).copy()
    
    X = df_clean[cols].fillna(0)
    y = df_clean["target_cls_21d"].astype(int)
    return X, y, cols, df_clean


@app.command("run")
def run(
    n_estimators: int = typer.Option(300, "--n-estimators", help="Number of trees in Random Forest"),
    max_depth: int = typer.Option(5, "--max-depth", help="Maximum depth of trees"),
):
    """Train Random Forest model with TimeSeriesSplit cross-validation."""
    features_path = config.ANALYTICS_DIR / "features.parquet"
    models_dir = config.MODELS_DIR
    models_dir.mkdir(parents=True, exist_ok=True)

    feats = load_parquet(features_path)
    if feats is None or feats.empty:
        typer.secho(f"Features file not found at {features_path}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    X, y, feature_cols, df_clean = _prepare_data(feats)
    
    tscv = TimeSeriesSplit(n_splits=5)
    aucs, accs = [], []

    typer.secho("Starting TimeSeriesSplit cross-validation...", fg=typer.colors.CYAN)
    for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced"
        )
        model.fit(X_train, y_train)
        
        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]

        acc = accuracy_score(y_test, preds)
        try:
            auc = roc_auc_score(y_test, probs)
        except Exception:
            auc = float('nan')

        accs.append(acc)
        aucs.append(auc)
        typer.secho(f"Fold {fold+1} | Accuracy: {acc:.4f} | AUC: {auc:.4f}", fg=typer.colors.BLUE)

    # Final training on full dataset
    typer.secho("Training final model on full dataset...", fg=typer.colors.CYAN)
    final_model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced"
    )
    final_model.fit(X, y)

    model_path = models_dir / "sector_rf_model.joblib"
    joblib.dump(final_model, model_path)
    
    typer.secho(f"Model successfully saved to {model_path}", fg=typer.colors.GREEN)
    typer.secho(f"Mean CV Accuracy: {np.mean(accs):.4f} | Mean CV AUC: {np.nanmean(aucs):.4f}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
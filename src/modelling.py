"""Leakage-safe chronological modelling helpers. No row shuffling."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import (
    CHRONOLOGICAL_SPLIT_DATE,
    DEFAULT_LOW_STORAGE_THRESHOLD_PCT,
    FEATURE_COLUMNS,
    RISK_BANDS,
    SENSITIVITY_THRESHOLDS_PCT,
)


def load_modelling_table(path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["week_start"])
    if "future_storage_pct" in frame.columns:
        for threshold in SENSITIVITY_THRESHOLDS_PCT:
            column = f"future_low_storage_{int(threshold)}"
            if column not in frame.columns:
                future = frame["future_storage_pct"]
                frame[column] = np.where(future.isna(), np.nan, (future < threshold).astype(int))
    return frame


def available_features(frame: pd.DataFrame) -> list[str]:
    return [name for name in FEATURE_COLUMNS if name in frame.columns]


def labelled_rows(frame: pd.DataFrame, target: str = "future_low_storage") -> pd.DataFrame:
    needed = [target, "combined_storage_pct", "week_start"]
    return frame.dropna(subset=needed).sort_values("week_start").reset_index(drop=True)


def chronological_split(
    frame: pd.DataFrame,
    split_date: str = CHRONOLOGICAL_SPLIT_DATE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on weeks strictly before split_date; test on split_date onward."""
    cutoff = pd.Timestamp(split_date)
    train = frame.loc[frame["week_start"] < cutoff].copy()
    test = frame.loc[frame["week_start"] >= cutoff].copy()
    if train.empty or test.empty:
        raise ValueError(
            f"Chronological split at {split_date} produced an empty side "
            f"(train={len(train)}, test={len(test)})."
        )
    if train["week_start"].max() >= test["week_start"].min():
        raise ValueError("Train and test weeks overlap; refusing to shuffle or leak.")
    return train.reset_index(drop=True), test.reset_index(drop=True)


def matrix(frame: pd.DataFrame, feature_names: list[str]) -> pd.DataFrame:
    return frame.reindex(columns=feature_names)


def persistence_labels(storage_pct: pd.Series, threshold: float) -> np.ndarray:
    """Baseline: the system is low in four weeks if it is already below threshold."""
    return (storage_pct.to_numpy(dtype="float64") < threshold).astype(int)


def majority_labels(train_y: np.ndarray, n_test: int) -> np.ndarray:
    majority = int(pd.Series(train_y).mode().iloc[0])
    return np.full(n_test, majority, dtype=int)


def classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray | None = None,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "n": int(len(y_true)),
        "n_positive": int(np.sum(y_true == 1)),
        "n_negative": int(np.sum(y_true == 0)),
    }
    if y_score is not None and len(np.unique(y_true)) == 2:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_score)), 4)
        metrics["pr_auc"] = round(float(average_precision_score(y_true, y_score)), 4)
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
    return metrics


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
        "n": int(len(y_true)),
    }


def make_classifier(name: str) -> Pipeline:
    if name == "logistic_regression":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        )
    if name == "random_forest":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=3,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=1,
                    ),
                ),
            ]
        )
    raise ValueError(f"Unknown classifier {name}")


def make_regressor() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]
    )


def select_primary_model(metrics_by_name: dict[str, dict[str, Any]]) -> str:
    """Prefer higher recall for the low-storage class, then PR-AUC, then F1."""
    ranked = []
    for name, metrics in metrics_by_name.items():
        if name in {"majority", "persistence"}:
            continue
        ranked.append(
            (
                float(metrics.get("recall") or 0.0),
                float(metrics.get("pr_auc") or 0.0),
                float(metrics.get("f1") or 0.0),
                name,
            )
        )
    if not ranked:
        return "logistic_regression"
    ranked.sort(reverse=True)
    return ranked[0][3]


def risk_band(probability: float) -> str:
    value = min(max(float(probability), 0.0), 1.0)
    for low, high, label in RISK_BANDS:
        if low <= value < high:
            return label
    return "Critical"


def coverage_notes(frame: pd.DataFrame) -> dict[str, Any]:
    labelled = labelled_rows(frame) if "future_low_storage" in frame.columns else frame
    by_year = (
        labelled.groupby(labelled["week_start"].dt.year)
        .agg(
            n_labelled=("future_low_storage", "size"),
            n_positive=("future_low_storage", "sum"),
        )
        .reset_index()
        .rename(columns={"week_start": "year"})
    )
    return {
        "n_weeks_total": int(len(frame)),
        "n_weeks_with_combined_storage": int(frame["combined_storage_pct"].notna().sum()),
        "n_labelled": int(len(labelled)),
        "threshold_pct": DEFAULT_LOW_STORAGE_THRESHOLD_PCT,
        "limitation": (
            "DWS HyData Point listings are capped at 7 000 primary records. "
            "12-minute stations (Midmar, Albert Falls, Spring Grove) therefore "
            "cover only about the first eight weeks of most years. Combined "
            "five-dam labels are not a full 2014–2026 weekly series."
        ),
        "labelled_weeks_by_year": by_year.to_dict(orient="records"),
    }


def feature_importance(pipeline: Pipeline, feature_names: list[str]) -> pd.DataFrame:
    model = pipeline.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        values = model.feature_importances_
        kind = "gini_importance"
    elif hasattr(model, "coef_"):
        values = np.abs(np.ravel(model.coef_))
        kind = "abs_coefficient"
    else:
        return pd.DataFrame(columns=["feature", "importance", "kind"])
    return (
        pd.DataFrame({"feature": feature_names, "importance": values, "kind": kind})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

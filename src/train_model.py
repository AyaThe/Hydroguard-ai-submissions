"""Fit chronological baselines and models; save the Streamlit pipeline bundle."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.config import (
    CHRONOLOGICAL_SPLIT_DATE,
    DATA_PROCESSED,
    DEFAULT_LOW_STORAGE_THRESHOLD_PCT,
    MODELS_DIR,
    PREDICTION_HORIZON_WEEKS,
    SENSITIVITY_THRESHOLDS_PCT,
)
from src.modelling import (
    available_features,
    chronological_split,
    classification_metrics,
    coverage_notes,
    feature_importance,
    labelled_rows,
    load_modelling_table,
    majority_labels,
    make_classifier,
    make_regressor,
    matrix,
    persistence_labels,
    regression_metrics,
    select_primary_model,
)

LOGGER = logging.getLogger(__name__)


def _scores(pipeline, features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    pred = pipeline.predict(features)
    if hasattr(pipeline, "predict_proba"):
        proba = pipeline.predict_proba(features)[:, 1]
    else:
        proba = pred.astype("float64")
    return pred, proba


def train_and_evaluate(
    table: pd.DataFrame,
    *,
    split_date: str,
    threshold: float,
) -> dict:
    labelled = labelled_rows(table)
    features = available_features(labelled)
    train, test = chronological_split(labelled, split_date=split_date)
    x_train = matrix(train, features)
    x_test = matrix(test, features)
    y_train = train["future_low_storage"].to_numpy(dtype=int)
    y_test = test["future_low_storage"].to_numpy(dtype=int)
    y_train_reg = train["future_storage_pct"].to_numpy(dtype="float64")
    y_test_reg = test["future_storage_pct"].to_numpy(dtype="float64")

    report: dict = {
        "split_date": split_date,
        "threshold_pct": threshold,
        "horizon_weeks": PREDICTION_HORIZON_WEEKS,
        "features": features,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "train_positive_rate": round(float(y_train.mean()), 4),
        "test_positive_rate": round(float(y_test.mean()), 4),
        "coverage": coverage_notes(table),
        "sensitivity_class_balance": {},
        "models": {},
        "regression": {},
    }
    for level in SENSITIVITY_THRESHOLDS_PCT:
        column = f"future_low_storage_{int(level)}"
        if column in labelled.columns:
            series = labelled[column].dropna()
            report["sensitivity_class_balance"][str(int(level))] = {
                "n": int(len(series)),
                "n_positive": int(series.sum()),
                "positive_rate": round(float(series.mean()), 4),
            }

    majority = majority_labels(y_train, len(y_test))
    persist = persistence_labels(test["combined_storage_pct"], threshold)
    report["models"]["majority"] = classification_metrics(y_test, majority)
    report["models"]["persistence"] = classification_metrics(y_test, persist)

    fitted: dict[str, object] = {}
    learned_metrics: dict[str, dict] = {}
    for name in ("logistic_regression", "random_forest"):
        pipeline = make_classifier(name)
        pipeline.fit(x_train, y_train)
        pred, proba = _scores(pipeline, x_test)
        metrics = classification_metrics(y_test, pred, proba)
        report["models"][name] = metrics
        learned_metrics[name] = metrics
        fitted[name] = pipeline
        LOGGER.info("%s test metrics: %s", name, metrics)

    primary_name = select_primary_model(learned_metrics)
    primary = fitted[primary_name]
    importance = feature_importance(primary, features)

    ridge = make_regressor()
    ridge.fit(x_train, y_train_reg)
    reg_pred = ridge.predict(x_test)
    report["regression"]["ridge"] = regression_metrics(y_test_reg, reg_pred)

    return {
        "report": report,
        "primary_name": primary_name,
        "pipelines": fitted,
        "regressor": ridge,
        "importance": importance,
        "train": train,
        "test": test,
        "features": features,
    }


def save_bundle(result: dict, models_dir: Path) -> Path:
    models_dir.mkdir(parents=True, exist_ok=True)
    bundle = {
        "sklearn_pipeline": result["pipelines"][result["primary_name"]],
        "all_classifiers": result["pipelines"],
        "regressor": result["regressor"],
        "model_type": result["primary_name"],
        "features": result["features"],
        "threshold_pct": DEFAULT_LOW_STORAGE_THRESHOLD_PCT,
        "horizon_weeks": PREDICTION_HORIZON_WEEKS,
        "split_date": CHRONOLOGICAL_SPLIT_DATE,
        "trained_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "metrics": result["report"],
        "volume_conversion": "V=FSC*((H+level_above_fsl)/H)**2 academic approximation",
        "warning": (
            "Academic prototype only. Not an official eThekwini or UUW early-warning "
            "system. Combined storage uses a documented volume conversion, not the "
            "unpublished DWS rating table. HyData Point downloads were truncated by "
            "the 7 000-record cap."
        ),
    }
    bundle_path = models_dir / "pipeline.joblib"
    joblib.dump(bundle, bundle_path)
    (models_dir / "metrics.json").write_text(
        json.dumps(result["report"], indent=2) + "\n",
        encoding="utf-8",
    )
    result["importance"].to_csv(models_dir / "feature_importance.csv", index=False)

    test = result["test"].copy()
    primary = result["pipelines"][result["primary_name"]]
    features = matrix(test, result["features"])
    pred, proba = _scores(primary, features)
    test["predicted_low_storage"] = pred
    test["predicted_probability"] = proba
    test["predicted_storage_pct"] = result["regressor"].predict(features)
    test["split"] = "test"
    test.to_csv(models_dir / "test_predictions.csv", index=False)
    LOGGER.info("Saved %s (primary=%s)", bundle_path, result["primary_name"])
    return bundle_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--table",
        default=str(DATA_PROCESSED / "weekly_modelling_table.csv"),
    )
    parser.add_argument("--models-dir", default=str(MODELS_DIR))
    parser.add_argument("--split-date", default=CHRONOLOGICAL_SPLIT_DATE)
    parser.add_argument("--threshold", type=float, default=DEFAULT_LOW_STORAGE_THRESHOLD_PCT)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    table_path = Path(args.table)
    if not table_path.exists():
        raise FileNotFoundError(
            f"Missing {table_path}. Run python -m src.build_dataset first."
        )
    table = load_modelling_table(table_path)
    result = train_and_evaluate(table, split_date=args.split_date, threshold=args.threshold)
    save_bundle(result, Path(args.models_dir))
    LOGGER.info("Primary model: %s", result["primary_name"])
    LOGGER.info("Test metrics: %s", result["report"]["models"][result["primary_name"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())

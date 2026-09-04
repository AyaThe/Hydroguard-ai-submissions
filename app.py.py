"""HydroGuard AI — Streamlit demo for four-week Mgeni WSS low-storage forecasting."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import joblib
import pandas as pd
import plotly.express as px
import streamlit as st

from src.config import (
    DAMS,
    DATA_PROCESSED,
    DEFAULT_LOW_STORAGE_THRESHOLD_PCT,
    MGENI_WSS_FSC_MM3,
    MODELS_DIR,
    PREDICTION_HORIZON_WEEKS,
    PROJECT_ROOT,
)
from src.modelling import available_features, coverage_notes, load_modelling_table, matrix, risk_band

st.set_page_config(
    page_title="HydroGuard AI — four-week Mgeni storage forecast",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_table() -> pd.DataFrame:
    path = DATA_PROCESSED / "weekly_modelling_table.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return load_modelling_table(path)


@st.cache_resource(show_spinner=False)
def load_bundle() -> dict:
    path = MODELS_DIR / "pipeline.joblib"
    if not path.exists():
        raise FileNotFoundError(path)
    return joblib.load(path)


def page_overview(table: pd.DataFrame, bundle: dict | None) -> None:
    st.title("HydroGuard AI — Water Crisis Prediction for Durban / eThekwini")
    st.caption(
        "Same group project as HydroGuard AI, now with dated data and a four-week forecast "
        "of bulk Mgeni Water Supply System storage."
    )
    coverage = coverage_notes(table)
    labelled = table.dropna(subset=["future_low_storage"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dams in the target", "5")
    c2.metric("Horizon", f"{PREDICTION_HORIZON_WEEKS} weeks")
    c3.metric("Low-storage threshold", f"{DEFAULT_LOW_STORAGE_THRESHOLD_PCT:.0f}%")
    c4.metric("Labelled weeks", f"{coverage['n_labelled']}")

    st.subheader("From HydroGuard AI to forecasting")
    st.write(
        "HydroGuard AI was this group's water-crisis idea: predict risk from South African "
        "infrastructure and water-quality snapshots. Those tables had **no date column**, "
        "so they could not support forecasting. This build keeps the HydroGuard problem "
        "(will there be a water-crisis state?) and replaces that snapshot with **dated** "
        "public time series so the model can forecast **four weeks ahead**."
    )

    st.subheader("Problem")
    st.write(
        "Predict whether the **combined Mgeni Water Supply System** that bulk-supplies "
        "eThekwini will be below **70%** of current full-supply capacity four weeks later. "
        "The 70% cut is an academic / operational proxy from UUW 2017 public recovery "
        "statements. It is **not** a gazetted drought trigger."
    )
    st.write(
        "eThekwini buys more than 98% of treated water from uMngeni-uThukela Water. "
        "This prototype does **not** predict street-level outages."
    )

    st.subheader("Forecasting (this is a dated time-series model)")
    st.write(
        "Every row in the dataset has a **date**: `week_start` (Monday). "
        "The model is not a random snapshot classifier. It is a **four-week-ahead forecast**: "
        "features on date *t* predict storage on date *t* + 4 weeks (`future_storage_pct`, "
        "`future_low_storage`). Training never shuffles weeks; train is before 2020-01-01 "
        "and test is after. The **Four-week outlook** page forecasts a **future Monday**, "
        "not a past week."
    )
    dated = table.dropna(subset=["combined_storage_pct"])[
        ["week_start", "combined_storage_pct", "future_storage_pct", "future_low_storage", "horizon_weeks"]
    ].head(8)
    dated = dated.rename(
        columns={
            "week_start": "Date (Monday)",
            "combined_storage_pct": "Storage % on that date",
            "future_storage_pct": "Storage % four weeks later",
            "future_low_storage": "Low storage in 4 weeks? (1=yes)",
            "horizon_weeks": "Horizon (weeks)",
        }
    )
    st.dataframe(dated, hide_index=True, use_container_width=True)
    st.caption(
        "Source: data/processed/weekly_modelling_table.csv — one dated week per row."
    )

    st.subheader("System")
    dam_rows = [
        {
            "Dam": meta["name"],
            "DWS station": meta["station"],
            "FSC (Mm³)": meta["fsc_mm3"],
            "River": meta["river"],
        }
        for meta in DAMS.values()
    ]
    st.dataframe(pd.DataFrame(dam_rows), hide_index=True, use_container_width=True)
    st.caption(f"Combined current FSC used for % full: {MGENI_WSS_FSC_MM3} Mm³ (DWS UM total).")

    st.subheader("What the current labels actually cover")
    st.warning(coverage["limitation"])
    year_frame = pd.DataFrame(coverage["labelled_weeks_by_year"])
    if not year_frame.empty:
        year_frame["n_positive"] = year_frame["n_positive"].astype(int)
        fig = px.bar(
            year_frame,
            x="year",
            y=["n_labelled", "n_positive"],
            barmode="group",
            title="Labelled weeks and low-storage weeks by year (truncated HyData coverage)",
            labels={"value": "Weeks", "year": "Year", "variable": "Count"},
        )
        st.plotly_chart(fig, use_container_width=True)

    if bundle:
        st.subheader("Saved pipeline")
        st.write(
            f"Primary model: **{bundle['model_type']}**. "
            f"Trained {bundle.get('trained_at_utc', 'unknown')} with a chronological "
            f"split at **{bundle.get('split_date')}** (no shuffling)."
        )


def page_lineage() -> None:
    st.title("Project lineage — HydroGuard AI")
    st.write(
        "This repository is the **same group project** as HydroGuard AI (Lesson 16). "
        "The forecasting build replaced undated municipal snapshots with **dated** official "
        "time series. Legacy Lesson 16 files live in `legacy/` for reference only."
    )
    st.subheader("Before vs after")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Aspect": "Project name",
                    "Lesson 16 (legacy)": "HydroGuard AI — smart water crisis prediction",
                    "Current build (forecasting)": "HydroGuard AI — four-week Mgeni storage forecast",
                },
                {
                    "Aspect": "Data shape",
                    "Lesson 16 (legacy)": "353-row municipal snapshots",
                    "Current build (forecasting)": "652 Monday weeks (2014–2026 index)",
                },
                {
                    "Aspect": "Date column",
                    "Lesson 16 (legacy)": "None — cannot forecast",
                    "Current build (forecasting)": "`week_start` (Monday) + t+4 target",
                },
                {
                    "Aspect": "Geography",
                    "Lesson 16 (legacy)": "Mixed SA cities (JHB, CPT, Durban, …)",
                    "Current build (forecasting)": "Mgeni five-dam system bulk-supplying eThekwini",
                },
                {
                    "Aspect": "Features",
                    "Lesson 16 (legacy)": "Pressure, flow, pH, turbidity, coordinates",
                    "Current build (forecasting)": "Dam storage %, rainfall, lags, season",
                },
                {
                    "Aspect": "Target",
                    "Lesson 16 (legacy)": "`HydroGuard_Risk_Level` (same-week classify)",
                    "Current build (forecasting)": "`future_low_storage` four weeks ahead",
                },
                {
                    "Aspect": "Demo tool",
                    "Lesson 16 (legacy)": "Jupyter notebook EDA",
                    "Current build (forecasting)": "Streamlit app + saved `pipeline.joblib`",
                },
                {
                    "Aspect": "Data licence",
                    "Lesson 16 (legacy)": "Practice / Kaggle-style tables",
                    "Current build (forecasting)": "DWS HyData + NASA POWER (official public)",
                },
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.subheader("Legacy files in this repo")
    legacy_rows = []
    legacy_root = PROJECT_ROOT / "legacy"
    if legacy_root.exists():
        for path in sorted(legacy_root.rglob("*")):
            if path.is_file() and path.name != ".gitkeep":
                legacy_rows.append(
                    {
                        "File": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "Size (KB)": round(path.stat().st_size / 1024, 1),
                    }
                )
    if legacy_rows:
        st.dataframe(pd.DataFrame(legacy_rows), hide_index=True, use_container_width=True)
    else:
        st.info("No legacy files found under `legacy/`.")
    st.caption(
        "Lesson 16 notebooks are for EDA history only. Training and forecasting use "
        "`data/processed/weekly_modelling_table.csv` at the repo root."
    )


def page_sources() -> None:
    st.title("HydroGuard AI — Data sources")
    st.write(
        "Lecturer supplied no dataset. The model uses **two real public sources** "
        "(DWS HyData and NASA POWER). Details and licences: `DATA_SOURCES.md`."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Source": "DWS HyData Point listings",
                    "What": "Reservoir water level (m above spillway)",
                    "Use": "Storage features and 4-week target",
                    "Terms": "Academic/research; DWS copyright retained; do not sell",
                },
                {
                    "Source": "NASA POWER Daily",
                    "What": "Catchment rainfall, temperature, humidity, ET",
                    "Use": "Weather features at Midmar, Albert Falls, Inanda — not Durban CBD",
                    "Terms": "CC BY 4.0; cite POWER",
                },
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.subheader("Volume conversion")
    st.write(
        "DWS Point data is **metres above the spillway**. Official weekly % full uses "
        "an unpublished rating table. This project uses:"
    )
    st.code("V = FSC * ((H + level_above_spillway) / H) ** 2")
    st.write(
        "Midmar on 2016-01-01 (`level = -7.9 m`, `H = 25.84 m`) converts to about **48%**, "
        "matching the DWS KZN drought briefing figure of 48.06%. Label every % as academic."
    )
    st.subheader("Not used")
    st.write(
        "- The original HydroGuard snapshot CSVs (no dates; mixed cities; cannot forecast).\n"
        "- Cape Town Day Zero series (wrong city).\n"
        "- CHIRPS rainfall (researched; not used in the two-dataset model).\n"
        "- eThekwini FEWS scraping (terms forbid it).\n"
        "- SAWS gauges (not open).\n"
        "- Hazelmere (separate North Coast system).\n"
        "- Mearns weir as bulk storage."
    )


def page_eda(table: pd.DataFrame) -> None:
    st.title("HydroGuard AI — Exploratory analysis")
    storage = table.dropna(subset=["combined_storage_pct"])
    fig = px.line(
        storage,
        x="week_start",
        y="combined_storage_pct",
        markers=True,
        title="Combined Mgeni WSS storage (academic % of 920.90 Mm³)",
        labels={"week_start": "Week starting Monday", "combined_storage_pct": "Storage (%)"},
    )
    fig.add_hline(y=DEFAULT_LOW_STORAGE_THRESHOLD_PCT, line_dash="dash", annotation_text="70% academic threshold")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Gaps are missing five-dam weeks, mainly from the DWS 7 000-record Point cap — not empty dams.")

    dam_cols = [f"{key}_storage_pct" for key in DAMS]
    dam_long = storage.melt(
        id_vars=["week_start"],
        value_vars=dam_cols,
        var_name="dam",
        value_name="storage_pct",
    )
    dam_long["dam"] = dam_long["dam"].str.replace("_storage_pct", "", regex=False)
    fig = px.line(
        dam_long.dropna(subset=["storage_pct"]),
        x="week_start",
        y="storage_pct",
        color="dam",
        title="Per-dam academic storage %",
        labels={"week_start": "Week starting Monday", "storage_pct": "Storage (%)", "dam": "Dam"},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Combined % can hide Albert Falls stress: Inanda can stay high while Albert Falls is low."
    )

    rain = table.dropna(subset=["weekly_rainfall_mm"])
    fig = px.line(
        rain,
        x="week_start",
        y="weekly_rainfall_mm",
        title="Catchment-mean NASA POWER weekly rainfall (Midmar, Albert Falls, Inanda)",
        labels={"week_start": "Week starting Monday", "weekly_rainfall_mm": "Rainfall (mm)"},
    )
    st.plotly_chart(fig, use_container_width=True)

    if "season" in table.columns:
        fig = px.box(
            rain,
            x="season",
            y="weekly_rainfall_mm",
            title="Weekly rainfall by southern-hemisphere season",
            labels={"season": "Season", "weekly_rainfall_mm": "Rainfall (mm)"},
        )
        st.plotly_chart(fig, use_container_width=True)

    labelled = table.dropna(subset=["future_low_storage"])
    balance = (
        labelled["future_low_storage"]
        .map({0.0: "Not low in 4 weeks", 1.0: "Low storage in 4 weeks"})
        .value_counts()
        .rename_axis("class")
        .reset_index(name="weeks")
    )
    fig = px.bar(
        balance,
        x="class",
        y="weeks",
        title="Class balance on weeks that have a four-week label",
        labels={"class": "Class", "weeks": "Weeks"},
    )
    st.plotly_chart(fig, use_container_width=True)

    missing = pd.DataFrame(
        {
            "series": dam_cols + ["combined_storage_pct", "weekly_rainfall_mm"],
            "missing_weeks": [
                int(table[col].isna().sum()) if col in table.columns else len(table)
                for col in dam_cols + ["combined_storage_pct", "weekly_rainfall_mm"]
            ],
        }
    )
    fig = px.bar(
        missing,
        x="series",
        y="missing_weeks",
        title="Missing weeks (of 652 Monday weeks, 2014-03-10 to 2026-09-01)",
        labels={"series": "Series", "missing_weeks": "Missing weeks"},
    )
    st.plotly_chart(fig, use_container_width=True)

    if not labelled.empty:
        corr = labelled[
            [
                c
                for c in [
                    "combined_storage_pct",
                    "storage_lag_1w",
                    "weekly_rainfall_mm",
                    "rain_4w",
                    "rain_12w",
                    "future_storage_pct",
                    "future_low_storage",
                ]
                if c in labelled.columns
            ]
        ].corr(numeric_only=True)
        fig = px.imshow(
            corr,
            text_auto=".2f",
            title="Correlations on labelled weeks (no shuffling, past and future as stored)",
            aspect="auto",
        )
        st.plotly_chart(fig, use_container_width=True)


def page_models(bundle: dict) -> None:
    st.title("HydroGuard AI — Model comparison")
    st.write(
        "Chronological split only: train before 2020-01-01, test from 2020-01-01. "
        "Rows are never shuffled. Recall is prioritised because missing a coming "
        "low-storage period is worse than a false alarm in this academic setting."
    )
    metrics = bundle["metrics"]["models"]
    rows = []
    for name, values in metrics.items():
        rows.append(
            {
                "Model": name,
                "Precision": values.get("precision"),
                "Recall": values.get("recall"),
                "F1": values.get("f1"),
                "ROC-AUC": values.get("roc_auc"),
                "PR-AUC": values.get("pr_auc"),
                "Accuracy": values.get("accuracy"),
                "N test": values.get("n"),
            }
        )
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(
        f"Train weeks: {bundle['metrics']['n_train']} "
        f"(positive rate {bundle['metrics']['train_positive_rate']}). "
        f"Test weeks: {bundle['metrics']['n_test']} "
        f"(positive rate {bundle['metrics']['test_positive_rate']}). "
        "Only weeks that have **both** current five-dam storage and a four-week-ahead "
        "label are modelled. Persistence is stronger than logistic regression and "
        "random forest on F1 in this truncated sample. Test positives = 3, so "
        "ROC-AUC 1.0 is not evidence of a general early-warning system."
    )
    st.subheader("Primary model")
    st.write(f"**{bundle['model_type']}** is the pipeline loaded by this app.")
    primary = metrics[bundle["model_type"]]
    matrix_values = primary["confusion_matrix"]
    fig = px.imshow(
        matrix_values,
        text_auto=True,
        x=["Predicted not low", "Predicted low"],
        y=["Actual not low", "Actual low"],
        title=f"Test confusion matrix — {bundle['model_type']}",
        color_continuous_scale="Blues",
        aspect="equal",
    )
    st.plotly_chart(fig, use_container_width=True)

    importance_path = MODELS_DIR / "feature_importance.csv"
    if importance_path.exists():
        importance = pd.read_csv(importance_path)
        fig = px.bar(
            importance.sort_values("importance"),
            x="importance",
            y="feature",
            orientation="h",
            title="Primary-model feature importance (test-time model, training fit only)",
            labels={"importance": "Importance", "feature": "Feature"},
        )
        st.plotly_chart(fig, use_container_width=True)

    if "regression" in bundle["metrics"]:
        st.subheader("Four-week storage regression (backup task)")
        st.write(
            "Because low-storage weeks are clustered in the drought and the HyData "
            "series is truncated, classification can be brittle. Ridge regression "
            "predicts `future_storage_pct` on the same chronological split."
        )
        st.json(bundle["metrics"]["regression"])

    st.subheader("Sensitivity thresholds (labels only, not retrained)")
    st.json(bundle["metrics"].get("sensitivity_class_balance", {}))


def _predict_row(bundle: dict, row: pd.Series) -> tuple[float, int, str, float]:
    features = available_features(pd.DataFrame([row]))
    frame = matrix(pd.DataFrame([row]), bundle["features"] if bundle.get("features") else features)
    pipeline = bundle["sklearn_pipeline"]
    proba = float(pipeline.predict_proba(frame)[0, 1])
    label = int(pipeline.predict(frame)[0])
    storage = float(bundle["regressor"].predict(frame)[0])
    return proba, label, risk_band(proba), storage


def _monday_on_or_after(value: date) -> date:
    stamp = pd.Timestamp(value).normalize()
    return (stamp + pd.Timedelta(days=(7 - int(stamp.dayofweek)) % 7)).date()


def page_predict(table: pd.DataFrame, bundle: dict) -> None:
    st.title("HydroGuard AI — Four-week outlook")
    observed = table.dropna(subset=["combined_storage_pct"]).sort_values("week_start")
    latest = observed.iloc[-1]
    horizon = int(bundle.get("horizon_weeks", PREDICTION_HORIZON_WEEKS))
    today = date.today()
    default_as_of = _monday_on_or_after(today)
    picked = st.date_input(
        "As-of date (today or later)",
        value=default_as_of,
        min_value=today,
        max_value=today + timedelta(days=365),
    )
    as_of = _monday_on_or_after(picked if picked >= today else today)
    forecast_week = as_of + timedelta(weeks=horizon)

    d1, d2, d3 = st.columns(3)
    d1.metric("As-of Monday", as_of.isoformat())
    d2.metric("Forecast week starting", forecast_week.isoformat())
    d3.metric("Horizon", f"{horizon} weeks")

    st.caption(
        f"Last real DWS/NASA week in the table: "
        f"{pd.Timestamp(latest['week_start']).strftime('%Y-%m-%d')}. "
        "Sliders start from that observed week. Change them to describe conditions "
        f"on {as_of.isoformat()}."
    )

    combined = st.slider(
        "Combined academic storage % on the as-of date",
        40.0,
        110.0,
        float(latest["combined_storage_pct"]),
    )
    albert = st.slider(
        "Albert Falls academic storage %",
        20.0,
        110.0,
        float(latest.get("albert_falls_storage_pct", combined)),
    )
    rain = st.slider("This week's catchment rainfall (mm)", 0.0, 80.0, float(latest["weekly_rainfall_mm"]))
    rain4 = st.slider("Rain last 4 weeks (mm)", 0.0, 250.0, float(latest.get("rain_4w", rain)))

    row = latest.copy()
    row["week_start"] = pd.Timestamp(as_of)
    row["combined_storage_pct"] = combined
    row["albert_falls_storage_pct"] = albert
    row["weekly_rainfall_mm"] = rain
    row["rain_4w"] = rain4
    row["month"] = as_of.month
    row["storage_lag_1w"] = combined
    row["storage_change_1w"] = 0.0

    proba, label, band, pred_storage = _predict_row(bundle, row)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Low-storage probability", f"{proba:.1%}")
    c2.metric("Risk band", band)
    c3.metric("Class at 70%", "Low storage" if label == 1 else "Not low")
    c4.metric(f"Ridge storage on {forecast_week.isoformat()}", f"{pred_storage:.1f}%")

    st.write(
        f"This is a **forecast for a future date**. Using conditions on **{as_of.isoformat()}**, "
        f"the model predicts the week starting **{forecast_week.isoformat()}** "
        f"({horizon} weeks ahead). Threshold **{bundle['threshold_pct']}%**."
    )

    st.subheader("Feature values sent to the saved pipeline")
    show = {name: row.get(name) for name in bundle["features"]}
    st.dataframe(pd.DataFrame([show]), hide_index=True, use_container_width=True)


def main() -> None:
    try:
        table = load_table()
    except FileNotFoundError:
        st.error(
            "Missing `data/processed/weekly_modelling_table.csv`. "
            "Run `python -m src.build_dataset` from the project folder."
        )
        st.stop()
        return

    bundle = None
    try:
        bundle = load_bundle()
    except FileNotFoundError:
        st.warning("No saved pipeline yet. Run `python -m src.train_model` then refresh.")

    page = st.sidebar.radio(
        "Page",
        (
            "Overview",
            "Project lineage",
            "Data sources",
            "Exploratory analysis",
            "Model comparison",
            "Four-week outlook",
        ),
    )
    st.sidebar.write(f"Project folder: `{PROJECT_ROOT}`")
    st.sidebar.caption("HydroGuard AI · `streamlit run app.py`")

    if page == "Overview":
        page_overview(table, bundle)
    elif page == "Project lineage":
        page_lineage()
    elif page == "Data sources":
        page_sources()
    elif page == "Exploratory analysis":
        page_eda(table)
    elif page == "Model comparison":
        if bundle is None:
            st.error("Train the model first.")
        else:
            page_models(bundle)
    else:
        if bundle is None:
            st.error("Train the model first.")
        else:
            page_predict(table, bundle)


if __name__ == "__main__":
    main()

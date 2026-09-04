"""Build a leakage-safe weekly modelling table from cached raw downloads."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import (
    CATCHMENT_POINTS,
    DAMS,
    DATA_PROCESSED,
    DATA_RAW,
    DEFAULT_LOW_STORAGE_THRESHOLD_PCT,
    END_DATE,
    MGENI_WSS_FSC_MM3,
    PREDICTION_HORIZON_WEEKS,
    SOUTHERN_SEASONS,
    START_DATE,
)
from src.dws_hydata import parse_hydata_point_file, storage_percent, storage_volume_mm3

LOGGER = logging.getLogger(__name__)


def week_start_monday(values: pd.Series | pd.DatetimeIndex) -> pd.Series:
    """Map each timestamp to the Monday of its calendar week (Monday=0)."""
    stamps = pd.to_datetime(values)
    return stamps.dt.normalize() - pd.to_timedelta(stamps.dt.dayofweek, unit="D")


def _weekly_index(start: str, end: str) -> pd.DatetimeIndex:
    start_ts = week_start_monday(pd.Series([start])).iloc[0]
    end_ts = week_start_monday(pd.Series([end])).iloc[0]
    return pd.date_range(start_ts, end_ts, freq="W-MON", name="week_start")


def load_dam_daily(raw_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for dam_key, meta in DAMS.items():
        station = str(meta["station"])
        files = sorted(raw_dir.glob(f"{dam_key}_{station}_*_point.txt"))
        if not files:
            LOGGER.warning("No HyData files for %s", dam_key)
            continue
        pieces = []
        for path in files:
            try:
                piece = parse_hydata_point_file(path)
            except ValueError as exc:
                LOGGER.warning("Skipping %s: %s", path.name, exc)
                continue
            pieces.append(piece)
        if not pieces:
            continue
        daily = pd.concat(pieces, ignore_index=True).drop_duplicates("date")
        daily["date"] = pd.to_datetime(daily["date"])
        daily["dam"] = dam_key
        daily["volume_mm3"] = daily["level_m_above_fsl"].map(
            lambda level: storage_volume_mm3(
                float(level),
                float(meta["fsc_mm3"]),
                float(meta["fsl_depth_m"]),
            )
        )
        daily["storage_pct"] = daily["level_m_above_fsl"].map(
            lambda level: storage_percent(
                float(level),
                float(meta["fsc_mm3"]),
                float(meta["fsl_depth_m"]),
            )
        )
        frames.append(daily)
    if not frames:
        raise FileNotFoundError(f"No parseable DWS HyData files in {raw_dir}")
    return pd.concat(frames, ignore_index=True)


def weekly_storage(daily: pd.DataFrame, weeks: pd.DatetimeIndex) -> pd.DataFrame:
    daily = daily.copy()
    daily["week_start"] = week_start_monday(daily["date"])
    # Publication delay: use the last observation in the week, never a future week.
    last = (
        daily.sort_values("date")
        .groupby(["week_start", "dam"], as_index=False)
        .agg(
            level_m_above_fsl=("level_m_above_fsl", "last"),
            volume_mm3=("volume_mm3", "last"),
            storage_pct=("storage_pct", "last"),
            n_daily_obs=("date", "size"),
        )
    )
    volume = last.pivot(index="week_start", columns="dam", values="volume_mm3")
    percent = last.pivot(index="week_start", columns="dam", values="storage_pct")
    volume = volume.reindex(weeks)
    percent = percent.reindex(weeks)

    combined = pd.DataFrame({"week_start": weeks})
    combined = combined.set_index("week_start")
    for dam_key in DAMS:
        combined[f"{dam_key}_storage_pct"] = (
            percent[dam_key] if dam_key in percent.columns else pd.NA
        )
        combined[f"{dam_key}_volume_mm3"] = (
            volume[dam_key] if dam_key in volume.columns else pd.NA
        )
    combined["n_dams_observed"] = volume.notna().sum(axis=1)
    combined["combined_volume_mm3"] = volume.sum(axis=1, min_count=len(DAMS))
    combined["combined_storage_pct"] = 100.0 * combined["combined_volume_mm3"] / MGENI_WSS_FSC_MM3
    return combined.reset_index()


def _power_series(payload: dict[str, Any], parameter: str) -> pd.Series:
    values = payload["properties"]["parameter"][parameter]
    index = pd.to_datetime(list(values.keys()), format="%Y%m%d")
    series = pd.Series(list(values.values()), index=index, dtype="float64")
    fill = payload.get("header", {}).get("fill_value", -999)
    return series.replace(fill, np.nan).sort_index()


def load_nasa_power(raw_dir: Path) -> pd.DataFrame:
    files = sorted(
        path
        for path in raw_dir.glob("nasa_power_*.json")
        if not path.name.endswith(".manifest.json")
    )
    if not files:
        raise FileNotFoundError(f"No NASA POWER JSON files in {raw_dir}")
    daily_frames: list[pd.DataFrame] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        frame = pd.DataFrame(
            {
                "precip_mm": _power_series(payload, "PRECTOTCORR"),
                "t2m_c": _power_series(payload, "T2M"),
                "t2m_max_c": _power_series(payload, "T2M_MAX"),
                "t2m_min_c": _power_series(payload, "T2M_MIN"),
                "rh2m_pct": _power_series(payload, "RH2M"),
                "evptrns_mj": _power_series(payload, "EVPTRNS"),
            }
        )
        stem = path.stem.replace("nasa_power_", "")
        point_key = next(
            (key for key in sorted(CATCHMENT_POINTS, key=len, reverse=True) if stem.startswith(f"{key}_")),
            stem.split("_")[0],
        )
        frame["point"] = point_key
        daily_frames.append(frame.reset_index().rename(columns={"index": "date"}))
    daily = pd.concat(daily_frames, ignore_index=True)
    daily["date"] = pd.to_datetime(daily["date"])
    catchment = (
        daily.groupby("date", as_index=False)
        .agg(
            precip_mm=("precip_mm", "mean"),
            t2m_c=("t2m_c", "mean"),
            t2m_max_c=("t2m_max_c", "mean"),
            t2m_min_c=("t2m_min_c", "mean"),
            rh2m_pct=("rh2m_pct", "mean"),
            evptrns_mj=("evptrns_mj", "mean"),
        )
        .sort_values("date")
    )
    catchment["week_start"] = week_start_monday(catchment["date"])
    weekly = catchment.groupby("week_start", as_index=False).agg(
        weekly_rainfall_mm=("precip_mm", "sum"),
        t2m_c=("t2m_c", "mean"),
        t2m_max_c=("t2m_max_c", "mean"),
        t2m_min_c=("t2m_min_c", "mean"),
        rh2m_pct=("rh2m_pct", "mean"),
        evptrns_mj=("evptrns_mj", "sum"),
        n_weather_days=("date", "size"),
    )
    return weekly


def _parse_climateserv_records(payload: Any) -> pd.DataFrame:
    if isinstance(payload, dict) and "data" in payload:
        records = payload["data"]
    else:
        records = payload
    if isinstance(records, dict) and "values" in records:
        records = records["values"]
    rows: list[dict[str, Any]] = []
    if not isinstance(records, list):
        raise ValueError("Unrecognised ClimateSERV payload")
    for item in records:
        if not isinstance(item, dict):
            continue
        value = item.get("raw_value", item.get("value"))
        if isinstance(value, dict):
            value = value.get("avg", value.get("raw_value"))
        date_value = item.get("isodate") or item.get("date") or item.get("Date")
        if date_value is None and {"Year", "Month", "Day"} <= item.keys():
            date_value = f"{int(item['Year']):04d}-{int(item['Month']):02d}-{int(item['Day']):02d}"
        if value is None or date_value is None:
            continue
        if isinstance(date_value, (int, float)):
            timestamp = pd.to_datetime(date_value, unit="ms", origin="unix", errors="coerce")
            if pd.isna(timestamp):
                timestamp = pd.to_datetime(date_value, unit="s", origin="unix", errors="coerce")
        else:
            timestamp = pd.to_datetime(date_value, format="%m/%d/%Y", errors="coerce")
        if pd.isna(timestamp):
            continue
        number = float(value)
        if number <= -9000:
            number = float("nan")
        rows.append({"date": timestamp.normalize(), "chirps_mm": number})
    if not rows:
        raise ValueError("No ClimateSERV rainfall rows parsed")
    return pd.DataFrame(rows).drop_duplicates("date").sort_values("date")


def load_chirps(raw_dir: Path, weeks: pd.DatetimeIndex) -> pd.DataFrame:
    json_files = sorted(
        path
        for path in raw_dir.glob("chirps_climateserv_*.json")
        if not path.name.endswith(".manifest.json")
    )
    monthly_csv = raw_dir / "chirps_monthly_points.csv"
    if json_files:
        pieces = []
        for path in json_files:
            payload = json.loads(path.read_text(encoding="utf-8"))
            piece = _parse_climateserv_records(payload)
            pieces.append(piece)
        daily = pd.concat(pieces, ignore_index=True)
        daily = daily.groupby("date", as_index=False)["chirps_mm"].mean()
        daily["week_start"] = week_start_monday(daily["date"])
        weekly = daily.groupby("week_start", as_index=False)["chirps_mm"].sum()
        weekly = weekly.rename(columns={"chirps_mm": "chirps_weekly_mm"})
        return weekly.set_index("week_start").reindex(weeks).reset_index()

    if monthly_csv.exists():
        monthly = pd.read_csv(monthly_csv)
        monthly = monthly.groupby(["year", "month"], as_index=False)["precipitation_mm"].mean()
        monthly["month_start"] = pd.to_datetime(
            dict(year=monthly["year"], month=monthly["month"], day=1)
        )
        week_frame = pd.DataFrame({"week_start": weeks})
        week_frame["month_start"] = week_frame["week_start"].dt.to_period("M").dt.start_time
        merged = week_frame.merge(
            monthly[["month_start", "precipitation_mm"]],
            on="month_start",
            how="left",
        )
        # Monthly totals are not weekly totals; store as a monthly covariate only.
        return merged.rename(columns={"precipitation_mm": "chirps_month_mm"})[
            ["week_start", "chirps_month_mm"]
        ]

    LOGGER.warning("No CHIRPS files found in %s", raw_dir)
    return pd.DataFrame({"week_start": weeks})


def add_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.sort_values("week_start").copy()
    storage = out["combined_storage_pct"]
    rain = out["weekly_rainfall_mm"]
    out["storage_lag_1w"] = storage.shift(1)
    out["storage_lag_4w"] = storage.shift(4)
    out["storage_lag_8w"] = storage.shift(8)
    out["storage_lag_12w"] = storage.shift(12)
    out["storage_change_1w"] = storage - storage.shift(1)
    out["storage_change_4w"] = storage - storage.shift(4)
    out["storage_change_8w"] = storage - storage.shift(8)
    out["storage_change_12w"] = storage - storage.shift(12)
    out["rain_4w"] = rain.rolling(4, min_periods=4).sum()
    out["rain_8w"] = rain.rolling(8, min_periods=8).sum()
    out["rain_12w"] = rain.rolling(12, min_periods=12).sum()
    out["month"] = out["week_start"].dt.month
    out["season"] = out["month"].map(SOUTHERN_SEASONS)
    # Past-only monthly rainfall climatology (no future years).
    month_means: list[float] = []
    for idx, row in out.iterrows():
        history = out.loc[
            (out["week_start"] < row["week_start"]) & (out["month"] == row["month"]),
            "weekly_rainfall_mm",
        ]
        month_means.append(float(history.mean()) if len(history) else float("nan"))
    out["rain_month_climatology_pastonly_mm"] = month_means
    out["rain_anomaly_mm"] = out["weekly_rainfall_mm"] - out["rain_month_climatology_pastonly_mm"]
    dry = (out["weekly_rainfall_mm"] < 5.0).astype("float")
    consecutive = []
    run = 0.0
    for flag, missing in zip(dry, out["weekly_rainfall_mm"].isna()):
        if missing:
            consecutive.append(float("nan"))
            run = 0.0
            continue
        run = run + 1.0 if flag else 0.0
        consecutive.append(run)
    out["consecutive_dry_weeks"] = consecutive
    return out


def add_target(frame: pd.DataFrame, threshold: float, horizon: int) -> pd.DataFrame:
    out = frame.copy()
    future = out["combined_storage_pct"].shift(-horizon)
    out["future_storage_pct"] = future
    out["future_low_storage"] = np.where(
        future.isna(),
        np.nan,
        (future < threshold).astype(int),
    )
    out["low_storage_threshold_pct"] = threshold
    out["horizon_weeks"] = horizon
    out["threshold_definition"] = (
        "academic_proxy_uuw_2017_recovery_not_gazetted_trigger"
    )
    return out


def summarise_class_balance(frame: pd.DataFrame) -> dict[str, Any]:
    labelled = frame.dropna(subset=["future_low_storage"])
    positives = int((labelled["future_low_storage"] == 1).sum())
    negatives = int((labelled["future_low_storage"] == 0).sum())
    total = positives + negatives
    return {
        "n_weeks_total": int(len(frame)),
        "n_weeks_labelled": total,
        "n_positive_low_storage": positives,
        "n_negative": negatives,
        "positive_rate": None if total == 0 else round(positives / total, 4),
    }


def build_modelling_table(
    *,
    start: str,
    end: str,
    threshold: float,
    horizon: int,
    raw_root: Path,
    processed_dir: Path,
) -> pd.DataFrame:
    weeks = _weekly_index(start, end)
    daily = load_dam_daily(raw_root / "dws")
    storage = weekly_storage(daily, weeks)
    weather = load_nasa_power(raw_root / "nasa_power")
    # Modelling uses two real public datasets: DWS HyData levels and NASA POWER.
    # CHIRPS was researched (DATA_SOURCES.md) but is not joined into the table.
    table = storage.merge(weather, on="week_start", how="left")
    table = add_features(table)
    table = add_target(table, threshold=threshold, horizon=horizon)
    table["feature_as_of_week_start"] = table["week_start"]
    table["leakage_note"] = (
        "Features use only observations dated on or before week_start. "
        "Target is combined storage four weeks later. Rain climatology is past-only."
    )

    processed_dir.mkdir(parents=True, exist_ok=True)
    modelling_path = processed_dir / "weekly_modelling_table.csv"
    table.to_csv(modelling_path, index=False)
    balance = summarise_class_balance(table)
    summary_path = processed_dir / "dataset_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "start": start,
                "end": end,
                "threshold_pct": threshold,
                "horizon_weeks": horizon,
                "combined_fsc_mm3": MGENI_WSS_FSC_MM3,
                "volume_conversion": "V=FSC*((H+level_above_fsl)/H)**2 academic approximation",
                "class_balance": balance,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Wrote %s", modelling_path)
    LOGGER.info("Class balance: %s", balance)
    if balance["n_positive_low_storage"] is not None and balance["n_weeks_labelled"]:
        if balance["n_positive_low_storage"] < 30:
            LOGGER.warning(
                "Few positive low-storage weeks (%s). Classification may be unreliable; "
                "consider four-week storage regression.",
                balance["n_positive_low_storage"],
            )
    return table


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--threshold", type=float, default=DEFAULT_LOW_STORAGE_THRESHOLD_PCT)
    parser.add_argument("--horizon-weeks", type=int, default=PREDICTION_HORIZON_WEEKS)
    parser.add_argument("--raw-root", default=str(DATA_RAW))
    parser.add_argument("--processed-dir", default=str(DATA_PROCESSED))
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build_modelling_table(
        start=args.start,
        end=args.end,
        threshold=args.threshold,
        horizon=args.horizon_weeks,
        raw_root=Path(args.raw_root),
        processed_dir=Path(args.processed_dir),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

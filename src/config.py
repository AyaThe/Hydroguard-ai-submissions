"""Shared configuration for dates, dams, catchment points, and the academic target."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"

# Modelling window: Spring Grove (V2R003) verified record starts 2014-03-10.
START_DATE = "2014-03-10"
END_DATE = "2026-09-01"

HTTP_TIMEOUT_SECONDS = 90
HTTP_RETRIES = 4
HTTP_RETRY_BACKOFF_SECONDS = 3.0
USER_AGENT = (
    "DurbanWaterCrisisPrediction/0.1 "
    "(academic research; eThekwini Mgeni WSS; contact: local student project)"
)

# Combined Mgeni WSS full-supply capacity used in DWS Weekly State of Dams (UM).
MGENI_WSS_FSC_MM3 = 920.90

# Academic / operational proxy from UUW 2017 public recovery statements.
# Not a gazetted drought trigger. Configurable at dataset-build time.
DEFAULT_LOW_STORAGE_THRESHOLD_PCT = 70.0
SENSITIVITY_THRESHOLDS_PCT = (60.0, 70.0, 75.0)
PREDICTION_HORIZON_WEEKS = 4
VOLUME_DEPTH_EXPONENT = 2.0
CHRONOLOGICAL_SPLIT_DATE = "2020-01-01"

# Features available at week t only. Storage lags beyond 4 weeks are usually
# missing because DWS Point year-files are truncated by the 7 000-record cap.
FEATURE_COLUMNS = (
    "combined_storage_pct",
    "albert_falls_storage_pct",
    "storage_lag_1w",
    "storage_change_1w",
    "weekly_rainfall_mm",
    "rain_4w",
    "rain_8w",
    "rain_12w",
    "rain_anomaly_mm",
    "consecutive_dry_weeks",
    "t2m_c",
    "rh2m_pct",
    "month",
)

# Prototype probability bands for the Streamlit demo only. Not UUW/DWS alerts.
RISK_BANDS = (
    (0.00, 0.25, "Low"),
    (0.25, 0.50, "Moderate"),
    (0.50, 0.75, "High"),
    (0.75, 1.01, "Critical"),
)

DWS_HYDATA_URL = "https://www.dws.gov.za/hydrology/Verified/HyData.aspx"
# Official HyData primary/point cap: 7 000 records or 1 year, whichever first.
# 12-minute reservoir levels hit the record cap after ~2 months, so downloads
# are requested by calendar month (and split further if still truncated).
DWS_HYDATA_PRIMARY_RECORD_LIMIT = 7000
DWS_KZN_WEEKLY_URL = "https://www.dws.gov.za/Hydrology/Weekly/ProvinceWeek.aspx?region=KN"
NASA_POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
CHIRPS_MONTHLY_BASE_URL = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs"
)
CLIMATESERV_SUBMIT_URL = "https://climateserv.servirglobal.net/api/submitDataRequest/"
CLIMATESERV_PROGRESS_URL = "https://climateserv.servirglobal.net/api/getDataRequestProgress/"
CLIMATESERV_DATA_URL = "https://climateserv.servirglobal.net/api/getDataFromRequest/"

# DWS verified reservoir stations that form the Mgeni WSS combined series.
# Coordinates from DWS HyDataSets / WMA3 reservoir catalogue (accessed 2026-09-02).
# fsl_depth_m is gauge height at spillway zero, used only for the documented
# academic volume conversion V = FSC * ((H + level_above_fsl) / H) ** 2.
DAMS: dict[str, dict[str, object]] = {
    "midmar": {
        "name": "Midmar",
        "station": "U2R001",
        "river": "uMngeni",
        "fsc_mm3": 235.42,
        "fsl_depth_m": 25.84,
        "latitude": -29.49508,
        "longitude": 30.20145,
        "record_start": "1963-10-29",
    },
    "albert_falls": {
        "name": "Albert Falls",
        "station": "U2R003",
        "river": "uMngeni",
        "fsc_mm3": 285.64,
        "fsl_depth_m": 21.63,
        "latitude": -29.43111,
        "longitude": 30.42583,
        "record_start": "1975-06-09",
    },
    "nagle": {
        "name": "Nagle",
        "station": "U2R002",
        "river": "uMngeni",
        "fsc_mm3": 23.24,
        # Catalogue GP at FSL is 103.77 m (not a physical max depth). Use 2 * V/A.
        "fsl_depth_m": 29.8,
        "latitude": -29.59056,
        "longitude": 30.62750,
        "record_start": "1980-12-01",
        "fsl_depth_note": "Approximate max depth from 2*V/A; GP 103.77 is not used as H.",
    },
    "inanda": {
        "name": "Inanda",
        "station": "U2R004",
        "river": "uMngeni",
        "fsc_mm3": 237.40,
        "fsl_depth_m": 31.17,
        "latitude": -29.70890,
        "longitude": 30.86706,
        "record_start": "1989-04-25",
    },
    "spring_grove": {
        "name": "Spring Grove",
        "station": "V2R003",
        "river": "Mooi",
        "fsc_mm3": 139.20,
        "fsl_depth_m": 26.40,
        "latitude": -29.31913,
        "longitude": 29.96569,
        "record_start": "2014-03-10",
    },
}

# Catchment weather points. Do not use Durban CBD as if it were Midmar rainfall.
CATCHMENT_POINTS: dict[str, dict[str, float]] = {
    "midmar": {"latitude": -29.49508, "longitude": 30.20145},
    "albert_falls": {"latitude": -29.43111, "longitude": 30.42583},
    "inanda": {"latitude": -29.70890, "longitude": 30.86706},
}

NASA_POWER_PARAMETERS = (
    "PRECTOTCORR",
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
    "EVPTRNS",
)

SOUTHERN_SEASONS = {
    12: "summer",
    1: "summer",
    2: "summer",
    3: "autumn",
    4: "autumn",
    5: "autumn",
    6: "winter",
    7: "winter",
    8: "winter",
    9: "spring",
    10: "spring",
    11: "spring",
}


def combined_fsc_mm3() -> float:
    return float(sum(float(dam["fsc_mm3"]) for dam in DAMS.values()))

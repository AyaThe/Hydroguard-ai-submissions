# HydroGuard AI — Water Crisis Prediction for Durban / eThekwini

**GitHub:** https://github.com/MrNtuli/HydroGuard-AI (private; group collaborators invited)

This is the same group project as **HydroGuard AI** (Lesson 16), continued with the instruction to **forecast**, using a dataset that has **dates**.

The original HydroGuard tables (pressure, flow, pH, turbidity by municipality) had **no date column**, so they could not forecast. Those snapshots are kept in `legacy/` for reference only and are **not** used in training. This build keeps the HydroGuard idea — predict a water-crisis state — and uses dated DWS dam levels plus NASA POWER weather for the **Mgeni Water Supply System** that bulk-supplies eThekwini.

Academic prototype: predict whether that five-dam system will be in a low-storage state **four weeks later**.

This is **not** an official municipal early-warning system. City outages are often caused by pipe failures and demand, not empty dams.

## Project lineage (Lesson 16 → forecasting)

| | Lesson 16 (`legacy/`) | Current build (repo root) |
| --- | --- | --- |
| Tool | Jupyter notebook EDA | Streamlit app + Python pipeline |
| Data | Municipal snapshots, no dates | DWS + NASA weekly time series |
| Task | Same-week risk classification | **Four-week-ahead** forecast |
| Target | `HydroGuard_Risk_Level` | `future_low_storage` at t+4 weeks |

Open **Project lineage** in the Streamlit sidebar for the full before/after table.

## Open and present (due-day demo)

In PowerShell:

```powershell
cd C:\Users\Lenovo\Documents\PROJECTS\WATER-CRISIS-PREDICTION
python -m pip install -r requirements.txt
python -m src.train_model
streamlit run app.py
```

The browser opens at [http://localhost:8501](http://localhost:8501). Use the sidebar: **Overview**, **Project lineage**, **Data sources**, **Exploratory analysis**, **Model comparison**, **Four-week outlook**.

**What to say in the viva / slides**

1. We are still **HydroGuard AI** — Lesson 16 had no dates; this build adds dated data and forecasting.
2. The target is combined **Mgeni five-dam** storage (Midmar, Albert Falls, Nagle, Inanda, Spring Grove), not “Durban taps”.
3. Low storage = academic **70%** proxy from UUW 2017 recovery statements — **not** a gazetted crisis rule. 60% and 75% balances are reported as sensitivity.
4. Data are **two real public downloads**: DWS HyData and NASA POWER. Lecturer provided no dataset. Cape Town data were not used. CHIRPS was researched but is not in the model.
5. DWS Point levels are metres above the spillway. Official % uses a private rating table. The conversion `V = FSC * ((H + level) / H) ** 2` recovers Midmar January 2016 at about 48% vs DWS 48.06%.
6. **Limitation you must state:** DWS caps Point listings at **7 000 records**. 12-minute dams only cover about the first eight weeks of most years, so labelled weeks are **not** a full 2014–2026 weekly series.
7. Models use a **chronological** split (train before 2020-01-01, test after). Persistence beats sklearn on F1 (0.86 vs random forest 0.75). Random forest is kept because it outputs a probability. Test set has only **3** low-storage weeks — do not quote ROC-AUC 1.0 as a general result.
8. End on **Four-week outlook**: forecast a **future Monday**, academic prototype only.

Also show `DATA_SOURCES.md` and `legacy/` if they ask about the original HydroGuard work.

## Problem

- **Target:** `future_low_storage`
- **Horizon:** 4 weeks
- **Positive class:** combined Mgeni WSS storage below **70%** of current full-supply capacity (920.90 Mm³)
- **Threshold status:** academic / operational proxy, configurable

## Project layout

| Path | Role |
| --- | --- |
| `data/README.md` | **Submission:** where every dataset lives |
| `data/raw/dws/` | DWS HyData downloads (dataset 1) |
| `data/raw/nasa_power/` | NASA POWER downloads (dataset 2) |
| `data/processed/weekly_modelling_table.csv` | Dated modelling table built from raw |
| `legacy/` | Lesson 16 HydroGuard notebooks and snapshot CSVs (reference only) |
| `DATA_SOURCES.md` | Source register, licences, limits |
| `PRESENTATION.md` | Word-for-word viva script |
| `src/download_dam_data.py`, `src/download_weather_data.py` | Official DWS and NASA POWER downloads (never overwrite `data/raw/`) |
| `src/build_dataset.py` | Weekly join, leakage-safe features, target |
| `src/train_model.py` | Chronological baselines + logistic regression + random forest + ridge |
| `src/evaluate_model.py` | Prints `models/metrics.json` |
| `app.py` | Streamlit demo of the **saved** pipeline |
| `notebooks/HydroGuard_AI_Forecasting.ipynb` | Jupyter: cleaning summary, EDA, models, sample forecast |
| `data/processed/weekly_modelling_table.csv` | Dated modelling table |
| `models/pipeline.joblib` | Saved sklearn pipeline used by the app |

## Data sources

| Source | What is downloaded | Access |
| --- | --- | --- |
| DWS HyData verified reservoir point levels | Water level above spillway (m) | Official `HyData.aspx`; **7 000 primary records or 1 year** per request |
| NASA POWER Daily | Catchment rainfall, temperature, humidity, ET | Public REST API, CC BY 4.0 |

The submitted model uses **these two datasets only**. CHIRPS was checked in `DATA_SOURCES.md` as an optional rainfall QA source and is **not** used in training.

Durban CBD coordinates are **not** used as Midmar catchment rainfall.

## Rebuild the weekly table (optional)

```powershell
python -m src.download_dam_data
python -m src.download_weather_data
python -m src.build_dataset
python -m src.train_model
```

Raw files in `data/raw/` are **never overwritten**.

## Volume conversion

`V = FSC * ((H + level_above_fsl) / H) ** 2`

Academic only. Replace if an official rating table is obtained.

## Leakage controls

- Monday week starts. Dam storage for a week is the last observation **in that week**.
- Features use only data on or before `week_start`.
- Rainfall climatology is the mean of the same calendar month in **previous years only**.
- Target is storage four weeks later; the last four weeks are unlabelled.
- Train/test split is chronological. Time series are not shuffled.

## Tests

```powershell
pytest -q
```

## Ethics and limits

- DWS data: academic/research use, copyright retained by DWS, do not sell, acknowledge DWS.
- NASA POWER: CC BY 4.0; cite POWER and date accessed.
- Do not present this app as operational advice for eThekwini or UUW.
- Combined storage can hide Albert Falls collapse while Inanda stays high.
- HyData verified series can lag the weekly bulletin.

## Group

| Student number | Name |
| --- | --- |
| 22409287 | A.Z. Zwana |
| 22442801 | A. Tshabalala |
| 22327842 | T. Ngongoma |
| 22339617 | S.S. Mathonsi |

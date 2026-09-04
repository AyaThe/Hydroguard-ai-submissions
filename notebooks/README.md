# HydroGuard AI notebooks

## Main notebook (forecasting build)

**`HydroGuard_AI_Forecasting.ipynb`** — data load, cleaning summary, EDA charts, model metrics, example forecast.

Run from repository root:

```powershell
cd C:\Users\Lenovo\Documents\PROJECTS\WATER-CRISIS-PREDICTION
python -m pip install jupyter
jupyter notebook notebooks/HydroGuard_AI_Forecasting.ipynb
```

Prerequisites (if not already built):

```powershell
python -m pip install -r requirements.txt
python -m src.build_dataset
python -m src.train_model
```

Regenerate the notebook file after editing `build_forecasting_notebook.py`:

```powershell
python notebooks/build_forecasting_notebook.py
```

## Legacy (Lesson 16)

Lesson 16 EDA notebooks are in `legacy/notebooks/` — reference only, not used for the current model.

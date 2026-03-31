from __future__ import annotations

from pathlib import Path
from typing import Union
import pandas as pd

PathLike = Union[str, Path]



def read_hourly_par_csv(csv_path: PathLike) -> pd.DataFrame:
    csv_path = Path(csv_path)
    return pd.read_csv(csv_path)



def read_total_par_csv(csv_path: PathLike) -> pd.DataFrame:
    csv_path = Path(csv_path)
    return pd.read_csv(csv_path)



def summarize_total_par(csv_path: PathLike) -> dict:
    df = read_total_par_csv(csv_path)
    if df.empty:
        return {"n_rows": 0, "par_min": None, "par_max": None, "par_mean": None}
    return {
        "n_rows": int(len(df)),
        "par_min": float(df["PAR_total"].min()),
        "par_max": float(df["PAR_total"].max()),
        "par_mean": float(df["PAR_total"].mean()),
    }

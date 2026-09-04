"""Parse DWS HyData point files and convert level-above-FSL to storage volume."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.config import DWS_HYDATA_PRIMARY_RECORD_LIMIT, VOLUME_DEPTH_EXPONENT


@dataclass(frozen=True)
class HyDataPoint:
    date: datetime
    time_label: str
    level_m_above_fsl: float
    level_quality: int
    flow_m3s: float | None
    flow_quality: int | None


_HEADER_END = re.compile(r"^DATE\s+TIME", re.IGNORECASE)
_ROW = re.compile(
    r"^(?P<date>\d{8})\s+(?P<time>\d{6})\s+(?P<level>-?\d+\.\d+)\s+(?P<lqual>\d+)"
    r"(?:\s+(?P<flow>-?\d+\.\d+)\s+(?P<fqual>\d+))?"
)


def parse_hydata_point_text(text: str) -> list[HyDataPoint]:
    """Parse the official DWS Point (primary) text listing for a reservoir."""
    if "COR.LEVEL" not in text and "Corrected level" not in text:
        raise ValueError("Not a DWS reservoir point-level listing")

    lines = text.replace("\r", "").split("\n")
    started = False
    rows: list[HyDataPoint] = []
    for line in lines:
        stripped = line.strip()
        if not started:
            if _HEADER_END.match(stripped):
                started = True
            continue
        if not stripped or stripped.startswith("ZZZZ"):
            break
        if stripped.startswith("<"):
            break
        match = _ROW.match(stripped)
        if match is None:
            continue
        flow = match.group("flow")
        flow_quality = match.group("fqual")
        rows.append(
            HyDataPoint(
                date=datetime.strptime(match.group("date"), "%Y%m%d"),
                time_label=match.group("time"),
                level_m_above_fsl=float(match.group("level")),
                level_quality=int(match.group("lqual")),
                flow_m3s=None if flow is None else float(flow),
                flow_quality=None if flow_quality is None else int(flow_quality),
            )
        )
    if not rows:
        raise ValueError("No HyData point rows parsed")
    return rows


def last_observation_date(records: list[HyDataPoint]) -> date | None:
    if not records:
        return None
    return records[-1].date.date()


def listing_is_truncated(
    text: str,
    requested_end: date,
    *,
    record_limit: int = DWS_HYDATA_PRIMARY_RECORD_LIMIT,
    slack: int = 50,
) -> bool:
    """True when a Point listing stopped because of the DWS 7 000-record cap.

    Sparse complete listings (daily or weekly) can end before requested_end
    because of genuine gaps or publication lag. Those have far fewer than
    7 000 primary rows and must not be treated as truncated.
    """
    records = parse_hydata_point_text(text)
    last = last_observation_date(records)
    if last is None:
        return True
    return len(records) >= (record_limit - slack) and last < requested_end


def parse_hydata_point_file(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8", errors="replace")
    records = parse_hydata_point_text(text)
    frame = pd.DataFrame(
        [
            {
                "date": record.date.date(),
                "time_label": record.time_label,
                "level_m_above_fsl": record.level_m_above_fsl,
                "level_quality": record.level_quality,
                "flow_m3s": record.flow_m3s,
                "flow_quality": record.flow_quality,
            }
            for record in records
        ]
    )
    return (
        frame.groupby("date", as_index=False)
        .agg(
            level_m_above_fsl=("level_m_above_fsl", "mean"),
            level_quality=("level_quality", "max"),
            n_observations=("level_m_above_fsl", "size"),
        )
        .sort_values("date")
        .reset_index(drop=True)
    )


def storage_volume_mm3(
    level_m_above_fsl: float,
    fsc_mm3: float,
    fsl_depth_m: float,
    exponent: float = VOLUME_DEPTH_EXPONENT,
) -> float:
    """Academic conversion from metres above spillway/FSL to stored volume.

    DWS Point listings report corrected level above the spillway. Official
    weekly % full uses an unpublished rating table. This project therefore
    uses a documented quadratic depth-volume curve:

        V = FSC * max(h / H, 0) ** exponent

    where h = H + level_above_fsl. For Midmar in January 2016 this recovers
    about 48%, matching the DWS drought briefing (48.06%). It is not an
    official DWS percentage and must be labelled as an academic conversion.
    """
    if fsl_depth_m <= 0 or fsc_mm3 <= 0 or math.isnan(level_m_above_fsl):
        return float("nan")
    depth = fsl_depth_m + level_m_above_fsl
    if depth <= 0:
        return 0.0
    fraction = (depth / fsl_depth_m) ** exponent
    return float(fsc_mm3 * fraction)


def storage_percent(
    level_m_above_fsl: float,
    fsc_mm3: float,
    fsl_depth_m: float,
    exponent: float = VOLUME_DEPTH_EXPONENT,
) -> float:
    volume = storage_volume_mm3(level_m_above_fsl, fsc_mm3, fsl_depth_m, exponent)
    if math.isnan(volume) or fsc_mm3 <= 0:
        return float("nan")
    return 100.0 * volume / fsc_mm3

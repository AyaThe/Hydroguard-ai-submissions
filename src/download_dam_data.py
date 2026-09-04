"""Download DWS verified reservoir water-level listings for Mgeni WSS dams.

Uses the official HyData.aspx query interface (not HTML scraping of the weekly
bulletin). Primary/point data is limited to 7 000 records or one year per
request, whichever is first. Sub-daily stations are requested by calendar
month so a year of 12-minute levels is not truncated after ~two months.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path

from src.config import (
    DAMS,
    DATA_RAW,
    DWS_HYDATA_URL,
    DWS_KZN_WEEKLY_URL,
    END_DATE,
    START_DATE,
)
from src.dws_hydata import last_observation_date, listing_is_truncated, parse_hydata_point_text
from src.http_client import download_file, utc_now_iso

LOGGER = logging.getLogger(__name__)

_TRANSIENT_HYDATA_ERRORS = (
    "HY000",
    "ScriptServer",
    "ERROR [28000]",
    "ERROR [HY000]",
    "Client unable to establish connection",
)


def _is_valid_hydata_listing(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    if any(marker in text for marker in _TRANSIENT_HYDATA_ERRORS):
        return False
    return "COR.LEVEL" in text or "Corrected level" in text


def _quarantine_invalid(path: Path) -> Path:
    stamp = utc_now_iso().replace(":", "")
    quarantined = path.with_name(f"{path.stem}.invalid_{stamp}{path.suffix}")
    path.replace(quarantined)
    manifest = path.with_name(path.name + ".manifest.json")
    if manifest.exists():
        manifest.replace(quarantined.with_name(quarantined.name + ".manifest.json"))
    LOGGER.warning("Quarantined invalid HyData file as %s", quarantined.name)
    return quarantined


def _month_chunks(start: date, end: date) -> list[tuple[date, date]]:
    chunks: list[tuple[date, date]] = []
    cursor = date(start.year, start.month, 1)
    while cursor <= end:
        last_day = monthrange(cursor.year, cursor.month)[1]
        month_end = date(cursor.year, cursor.month, last_day)
        chunk_start = max(cursor, start)
        chunk_end = min(month_end, end)
        if chunk_start <= chunk_end:
            chunks.append((chunk_start, chunk_end))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return chunks


def download_station_range(
    dam_key: str,
    station: str,
    chunk_start: date,
    chunk_end: date,
    output_dir: Path,
) -> list[Path]:
    """Download one HyData Point window and split further if DWS truncates it."""
    params = {
        "Station": f"{station}100.00",
        "DataType": "Point",
        "StartDT": chunk_start.isoformat(),
        "EndDT": chunk_end.isoformat(),
        "SiteType": "RES",
    }
    filename = f"{dam_key}_{station}_{chunk_start.isoformat()}_{chunk_end.isoformat()}_point.txt"
    destination = output_dir / filename
    if destination.exists() and not _is_valid_hydata_listing(destination):
        _quarantine_invalid(destination)
    path = download_file(
        DWS_HYDATA_URL,
        destination,
        params=params,
        source_name="DWS Hydrological Services HyData (verified reservoir point levels)",
        expected_content_substrings=("cor.level", "corrected level"),
    )
    if not _is_valid_hydata_listing(path):
        _quarantine_invalid(path)
        raise RuntimeError(f"DWS returned an error page instead of levels for {filename}")

    saved = [path]
    text = path.read_text(encoding="utf-8", errors="replace")
    if not listing_is_truncated(text, chunk_end):
        return saved

    records = parse_hydata_point_text(text)
    last = last_observation_date(records)
    if last is None or last < chunk_start:
        LOGGER.warning(
            "Truncated listing %s does not cover %s–%s; not splitting further",
            path.name,
            chunk_start,
            chunk_end,
        )
        return saved

    nxt = last + timedelta(days=1)
    if nxt > chunk_end:
        return saved

    LOGGER.warning(
        "DWS 7 000-record cap truncated %s at %s; requesting remainder %s to %s",
        path.name,
        last.isoformat(),
        nxt.isoformat(),
        chunk_end.isoformat(),
    )
    time.sleep(1.0)
    saved.extend(download_station_range(dam_key, station, nxt, chunk_end, output_dir))
    return saved


def download_weekly_bulletin(output_dir: Path) -> Path:
    destination = output_dir / "dws_kzn_weekly_latest.html"
    return download_file(
        DWS_KZN_WEEKLY_URL,
        destination,
        source_name="DWS Weekly State of Dams — KwaZulu-Natal (latest bulletin only)",
        expected_content_substrings=("html", "state of dams", "provincial"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--output-dir", default=str(DATA_RAW / "dws"))
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date()
    output_dir = Path(args.output_dir)

    download_weekly_bulletin(output_dir)
    for dam_key, meta in DAMS.items():
        station = str(meta["station"])
        LOGGER.info("Downloading %s (%s) in monthly HyData windows", meta["name"], station)
        for chunk_start, chunk_end in _month_chunks(start, end):
            try:
                paths = download_station_range(
                    dam_key, station, chunk_start, chunk_end, output_dir
                )
            except Exception as exc:
                LOGGER.error(
                    "Skipping %s %s–%s after retries: %s",
                    station,
                    chunk_start,
                    chunk_end,
                    exc,
                )
                time.sleep(1.0)
                continue
            for path in paths:
                LOGGER.info("  %s", path.name)
            time.sleep(1.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())

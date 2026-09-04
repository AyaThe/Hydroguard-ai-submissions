"""Download CHIRPS rainfall for Mgeni catchment points.

Primary path: ClimateSERV point/polygon extraction (official SERVIR API) so the
project does not store hundreds of megabytes of Africa-wide GeoTIFFs.

Fallback: CHIRPS v2 Africa monthly GeoTIFF.gz from the CHC data repository,
with point extraction via a documented 0.05° Africa grid.
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd

from src.config import (
    CATCHMENT_POINTS,
    CHIRPS_MONTHLY_BASE_URL,
    CLIMATESERV_DATA_URL,
    CLIMATESERV_PROGRESS_URL,
    CLIMATESERV_SUBMIT_URL,
    DATA_RAW,
    END_DATE,
    HTTP_TIMEOUT_SECONDS,
    START_DATE,
)
from src.http_client import HttpError, cache_is_fresh, download_file, request_bytes, utc_now_iso, write_manifest

LOGGER = logging.getLogger(__name__)

# CHIRPS v2 Africa monthly grid (CHC product documentation).
CHIRPS_AFRICA_WEST = -20.0
CHIRPS_AFRICA_NORTH = 40.0
CHIRPS_AFRICA_PIXEL = 0.05
CHIRPS_AFRICA_NCOLS = 1500
CHIRPS_AFRICA_NROWS = 1600
CHIRPS_MISSING = -9999.0


def _polygon_around(longitude: float, latitude: float, half_deg: float = 0.05) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [longitude - half_deg, latitude - half_deg],
                [longitude - half_deg, latitude + half_deg],
                [longitude + half_deg, latitude + half_deg],
                [longitude + half_deg, latitude - half_deg],
                [longitude - half_deg, latitude - half_deg],
            ]
        ],
    }


def _climateserv_callback_payload(body: bytes) -> Any:
    text = body.decode("utf-8", errors="replace").strip()
    if text.startswith("successCallback(") and text.endswith(")"):
        text = text[len("successCallback(") : -1]
    return json.loads(text)


def submit_climateserv_job(longitude: float, latitude: float, start: str, end: str) -> str:
    begin = datetime.strptime(start, "%Y-%m-%d").strftime("%m/%d/%Y")
    finish = datetime.strptime(end, "%Y-%m-%d").strftime("%m/%d/%Y")
    params = {
        "datatype": "0",
        "begintime": begin,
        "endtime": finish,
        "intervaltype": "0",
        "operationtype": "5",
        "dateType_Category": "default",
        "geometry": json.dumps(_polygon_around(longitude, latitude), separators=(",", ":")),
    }
    url = f"{CLIMATESERV_SUBMIT_URL}?{urlencode(params)}"
    body, _, _ = request_bytes(url, min_bytes=10)
    payload = _climateserv_callback_payload(body)
    if isinstance(payload, list) and payload:
        job_id = str(payload[0])
        if job_id and job_id != "-1":
            return job_id
    raise HttpError(f"ClimateSERV did not return a job id: {payload!r}")


def poll_climateserv_job(job_id: str, timeout_seconds: int = 180) -> None:
    deadline = time.time() + timeout_seconds
    url = f"{CLIMATESERV_PROGRESS_URL}?id={job_id}"
    while time.time() < deadline:
        body, _, _ = request_bytes(url, min_bytes=3)
        payload = _climateserv_callback_payload(body)
        progress = payload[0] if isinstance(payload, list) and payload else payload
        LOGGER.info("ClimateSERV job %s progress=%s", job_id, progress)
        if str(progress) == "-1":
            raise HttpError(f"ClimateSERV job failed: {job_id}")
        try:
            numeric = float(progress)
        except (TypeError, ValueError) as exc:
            raise HttpError(f"ClimateSERV progress unreadable: {payload!r}") from exc
        if numeric >= 100:
            return
        time.sleep(3)
    raise HttpError(f"ClimateSERV job timed out: {job_id}")


def fetch_climateserv_data(job_id: str) -> dict[str, Any]:
    url = f"{CLIMATESERV_DATA_URL}?id={job_id}"
    body, content_type, _ = request_bytes(url, min_bytes=20, timeout=HTTP_TIMEOUT_SECONDS)
    text = body.decode("utf-8", errors="replace")
    if text.startswith("successCallback(") and text.endswith(")"):
        text = text[len("successCallback(") : -1]
    payload = json.loads(text)
    if not payload:
        raise HttpError(f"ClimateSERV returned empty data ({content_type})")
    return payload if isinstance(payload, dict) else {"data": payload}


def download_climateserv_point(
    point_key: str,
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    output_dir: Path,
) -> Path:
    destination = output_dir / f"chirps_climateserv_{point_key}_{start}_{end}.json"
    if cache_is_fresh(destination) or destination.exists():
        LOGGER.info("Cache hit: %s", destination)
        return destination

    job_id = submit_climateserv_job(longitude, latitude, start, end)
    poll_climateserv_job(job_id)
    payload = fetch_climateserv_data(job_id)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload), encoding="utf-8")
    write_manifest(
        destination,
        {
            "source_name": "SERVIR ClimateSERV CHIRPS extraction",
            "source_url": CLIMATESERV_SUBMIT_URL,
            "job_id": job_id,
            "retrieved_at_utc": utc_now_iso(),
            "point": point_key,
            "latitude": latitude,
            "longitude": longitude,
            "start": start,
            "end": end,
            "bytes": destination.stat().st_size,
        },
    )
    return destination


def _read_tiff_float32_strip(payload: bytes, row: int, col: int) -> float:
    """Minimal GeoTIFF sample for uncompressed or Pillow-readable CHIRPS files."""
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - optional fallback
        raise HttpError("Pillow is required to sample CHIRPS GeoTIFFs") from exc

    image = Image.open(io.BytesIO(payload))
    if col < 0 or row < 0 or col >= image.size[0] or row >= image.size[1]:
        return float("nan")
    value = image.getpixel((col, row))
    if isinstance(value, tuple):
        value = value[0]
    number = float(value)
    if number <= CHIRPS_MISSING + 1:
        return float("nan")
    return number


def chirps_row_col(longitude: float, latitude: float) -> tuple[int, int]:
    col = int((longitude - CHIRPS_AFRICA_WEST) / CHIRPS_AFRICA_PIXEL)
    row = int((CHIRPS_AFRICA_NORTH - latitude) / CHIRPS_AFRICA_PIXEL)
    return row, col


def download_monthly_geotiffs(
    start: str,
    end: str,
    output_dir: Path,
    points: dict[str, dict[str, float]],
) -> Path:
    """Fallback if ClimateSERV is unavailable: monthly Africa TIFFs, then point CSV."""
    tif_dir = output_dir / "geotiff"
    extracted_path = output_dir / "chirps_monthly_points.csv"
    if cache_is_fresh(extracted_path) or extracted_path.exists():
        LOGGER.info("Cache hit: %s", extracted_path)
        return extracted_path

    start_dt = datetime.strptime(start[:7], "%Y-%m")
    end_dt = datetime.strptime(end[:7], "%Y-%m")
    rows: list[dict[str, Any]] = []
    year, month = start_dt.year, start_dt.month
    while (year, month) <= (end_dt.year, end_dt.month):
        name = f"chirps-v2.0.{year}.{month:02d}.tif.gz"
        url = f"{CHIRPS_MONTHLY_BASE_URL}/{name}"
        gz_path = download_file(
            url,
            tif_dir / name,
            source_name="CHC CHIRPS v2.0 Africa monthly GeoTIFF",
            expected_content_substrings=("octet-stream", "gzip", "application"),
            binary=True,
        )
        raw = gzip.decompress(gz_path.read_bytes())
        for point_key, coords in points.items():
            row, col = chirps_row_col(float(coords["longitude"]), float(coords["latitude"]))
            try:
                value = _read_tiff_float32_strip(raw, row, col)
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Could not sample %s at %s: %s", name, point_key, exc)
                value = float("nan")
            rows.append(
                {
                    "year": year,
                    "month": month,
                    "point": point_key,
                    "latitude": coords["latitude"],
                    "longitude": coords["longitude"],
                    "precipitation_mm": value,
                }
            )
        month += 1
        if month == 13:
            month = 1
            year += 1

    frame = pd.DataFrame(rows)
    extracted_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(extracted_path, index=False)
    write_manifest(
        extracted_path,
        {
            "source_name": "CHC CHIRPS v2.0 Africa monthly GeoTIFF point sample",
            "source_url": CHIRPS_MONTHLY_BASE_URL,
            "retrieved_at_utc": utc_now_iso(),
            "bytes": extracted_path.stat().st_size,
            "n_rows": int(len(frame)),
        },
    )
    return extracted_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--output-dir", default=str(DATA_RAW / "chirps"))
    parser.add_argument(
        "--backend",
        choices=("climateserv", "geotiff", "auto"),
        default="auto",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    output_dir = Path(args.output_dir)
    backend = args.backend

    if backend in {"auto", "climateserv"}:
        try:
            for point_key, coords in CATCHMENT_POINTS.items():
                LOGGER.info("ClimateSERV CHIRPS %s", point_key)
                path = download_climateserv_point(
                    point_key,
                    float(coords["latitude"]),
                    float(coords["longitude"]),
                    args.start,
                    args.end,
                    output_dir,
                )
                LOGGER.info("  %s", path.name)
            return 0
        except (HttpError, json.JSONDecodeError, TimeoutError) as exc:
            LOGGER.warning("ClimateSERV failed (%s); falling back to monthly GeoTIFFs", exc)
            if backend == "climateserv":
                raise

    download_monthly_geotiffs(args.start, args.end, output_dir, CATCHMENT_POINTS)
    return 0


if __name__ == "__main__":
    sys.exit(main())

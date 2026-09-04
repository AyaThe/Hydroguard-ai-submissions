"""Download NASA POWER daily meteorology for Mgeni catchment points."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.config import (
    CATCHMENT_POINTS,
    DATA_RAW,
    END_DATE,
    NASA_POWER_DAILY_URL,
    NASA_POWER_PARAMETERS,
    START_DATE,
)
from src.http_client import download_file

LOGGER = logging.getLogger(__name__)


def download_point(
    point_key: str,
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    output_dir: Path,
) -> Path:
    params = {
        "parameters": ",".join(NASA_POWER_PARAMETERS),
        "community": "ag",
        "longitude": f"{longitude:.5f}",
        "latitude": f"{latitude:.5f}",
        "start": start.replace("-", ""),
        "end": end.replace("-", ""),
        "format": "JSON",
        "time-standard": "LST",
    }
    filename = f"nasa_power_{point_key}_{params['start']}_{params['end']}.json"
    destination = output_dir / filename
    return download_file(
        NASA_POWER_DAILY_URL,
        destination,
        params=params,
        source_name="NASA POWER Daily API (MERRA-2 meteorology)",
        expected_content_substrings=("json", "prectotcorr", "parameter"),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=START_DATE)
    parser.add_argument("--end", default=END_DATE)
    parser.add_argument("--output-dir", default=str(DATA_RAW / "nasa_power"))
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    datetime.strptime(args.start, "%Y-%m-%d")
    datetime.strptime(args.end, "%Y-%m-%d")
    output_dir = Path(args.output_dir)

    for point_key, coords in CATCHMENT_POINTS.items():
        LOGGER.info("NASA POWER %s (%.4f, %.4f)", point_key, coords["latitude"], coords["longitude"])
        path = download_point(
            point_key,
            float(coords["latitude"]),
            float(coords["longitude"]),
            args.start,
            args.end,
            output_dir,
        )
        LOGGER.info("  %s", path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

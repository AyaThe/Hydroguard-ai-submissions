"""Print saved test metrics. Training already evaluated the chronological split."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.config import MODELS_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", default=str(MODELS_DIR / "metrics.json"))
    args = parser.parse_args(argv)
    path = Path(args.metrics)
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run python -m src.train_model first.")
    print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

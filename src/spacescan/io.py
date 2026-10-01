from __future__ import annotations

import csv
import json
from pathlib import Path


def read_csv_clean(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.reader(handle)
        header = [cell.strip() for cell in next(rows)]
        return [dict(zip(header, [cell.strip() for cell in row])) for row in rows]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


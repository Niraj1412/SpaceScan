from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from .io import write_json


def _error(predicted: float, actual: float) -> dict:
    absolute = abs(predicted - actual)
    return {
        "predicted_m": round(predicted, 4),
        "actual_m": round(actual, 4),
        "absolute_error_m": round(absolute, 4),
        "relative_error_pct": round(100 * absolute / actual, 2) if actual else None,
    }


def evaluate(prediction: dict, truth: dict) -> dict:
    predicted_rooms = {room["id"]: room for room in prediction["property"]["rooms"]}
    measurements: list[dict] = []
    for expected_room in truth.get("rooms", []):
        room = predicted_rooms.get(expected_room["id"])
        if room is None:
            measurements.append({"room_id": expected_room["id"], "kind": "room", "status": "missed"})
            continue
        if "ceiling_height_m" in expected_room:
            item = _error(room["ceiling_height"]["value"], float(expected_room["ceiling_height_m"]))
            item.update({"room_id": room["id"], "kind": "ceiling_height", "gate_m": 0.015})
            item["pass"] = item["absolute_error_m"] <= item["gate_m"]
            item["interval_covers_truth"] = room["ceiling_height"]["low"] <= expected_room["ceiling_height_m"] <= room["ceiling_height"]["high"]
            measurements.append(item)
        walls = {wall["id"]: wall for wall in room["walls"]}
        for expected_wall in expected_room.get("walls", []):
            wall = walls.get(expected_wall["id"])
            if wall is None:
                measurements.append({"room_id": room["id"], "kind": "wall", "id": expected_wall["id"], "status": "missed"})
                continue
            item = _error(wall["length"]["value"], float(expected_wall["length_m"]))
            item.update({"room_id": room["id"], "kind": "wall_length", "id": wall["id"]})
            tier = prediction["capture"]["tier"]
            item["gate_m"] = max(0.01, expected_wall["length_m"] * ({"photos": 0.08, "video": 0.03, "lidar": 0.005}[tier]))
            item["pass"] = item["absolute_error_m"] <= item["gate_m"]
            item["interval_covers_truth"] = wall["length"]["low"] <= expected_wall["length_m"] <= wall["length"]["high"]
            measurements.append(item)
        expected_openings = {opening["id"]: opening for opening in expected_room.get("openings", [])}
        predicted_openings = {opening["id"]: opening for opening in room.get("openings", [])}
        for opening_id, expected_opening in expected_openings.items():
            opening = predicted_openings.get(opening_id)
            if opening is None:
                measurements.append({
                    "room_id": room["id"],
                    "kind": "opening_detection",
                    "id": opening_id,
                    "status": "missed",
                    "pass": False,
                })
                continue
            measurements.append({
                "room_id": room["id"],
                "kind": "opening_detection",
                "id": opening_id,
                "status": "detected",
                "pass": True,
            })
            if "width_m" in expected_opening:
                item = _error(opening["width"]["value"], float(expected_opening["width_m"]))
                item.update({"room_id": room["id"], "kind": "opening_width", "id": opening_id, "gate_m": 0.02})
                item["pass"] = item["absolute_error_m"] <= item["gate_m"]
                item["interval_covers_truth"] = opening["width"]["low"] <= expected_opening["width_m"] <= opening["width"]["high"]
                measurements.append(item)
        for opening_id in sorted(set(predicted_openings) - set(expected_openings)):
            measurements.append({
                "room_id": room["id"],
                "kind": "opening_detection",
                "id": opening_id,
                "status": "phantom",
                "pass": False,
            })
    scored = [item for item in measurements if "pass" in item]
    calibrated = [item for item in scored if "interval_covers_truth" in item]
    numeric = [item for item in scored if "absolute_error_m" in item]
    opening_detection = [item for item in scored if item["kind"] == "opening_detection"]
    return {
        "capture_id": prediction["capture"]["id"],
        "tier": prediction["capture"]["tier"],
        "summary": {
            "measurements": len(scored),
            "pass_rate": round(sum(bool(item["pass"]) for item in scored) / len(scored), 4) if scored else None,
            "mean_absolute_error_m": round(mean(item["absolute_error_m"] for item in numeric), 4) if numeric else None,
            "interval_coverage": round(sum(bool(item["interval_covers_truth"]) for item in calibrated) / len(calibrated), 4) if calibrated else None,
            "opening_detection_rate": round(sum(bool(item["pass"]) for item in opening_detection) / len(opening_detection), 4) if opening_detection else None,
        },
        "measurements": measurements,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a SpaceScan result against laser/tape ground truth")
    parser.add_argument("prediction")
    parser.add_argument("ground_truth")
    parser.add_argument("--output", "-o", default="evaluation.json")
    args = parser.parse_args()
    prediction = json.loads(Path(args.prediction).read_text(encoding="utf-8"))
    truth = json.loads(Path(args.ground_truth).read_text(encoding="utf-8"))
    report = evaluate(prediction, truth)
    write_json(Path(args.output), report)
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()

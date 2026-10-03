import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image

from spacescan.geometry import deterministic_kmeans, oriented_envelope, polygon_area, quaternion_matrix, robust_mode, voronoi_partition
from spacescan.validate import validate_result
from spacescan.cli import detect_tier
from spacescan.inspection import derive_claims, detect_damage_regions, detect_lidar_openings
from spacescan.models import Room, Wall, interval
from spacescan.metric_depth import estimate_room_dimensions
from spacescan.evaluate import evaluate


class GeometryTests(unittest.TestCase):
    def test_identity_quaternion(self):
        np.testing.assert_allclose(quaternion_matrix(np.array([0, 0, 0, 1.0])), np.eye(3))

    def test_mode_rejects_outlier(self):
        values = np.r_[np.full(100, 2.4), 99.0]
        self.assertAlmostEqual(robust_mode(values)[0], 2.4, places=2)

    def test_envelope_area(self):
        points = np.array([[0, 0], [4, 0], [4, 3], [0, 3]] * 100, dtype=float)
        polygon = oriented_envelope(points, 0.0)
        self.assertAlmostEqual(polygon_area(polygon), 12.0, places=4)

    def test_voronoi_rooms_partition_without_area_overlap(self):
        boundary = np.array([[0, 0], [10, 0], [10, 6], [0, 6]], dtype=float)
        centers = np.array([[2, 3], [5, 3], [8, 3]], dtype=float)
        cells = voronoi_partition(boundary, centers)
        self.assertEqual(len(cells), 3)
        self.assertAlmostEqual(sum(polygon_area(cell) for cell in cells), polygon_area(boundary), places=6)

    def test_kmeans_is_deterministic(self):
        points = np.array([[0, 0], [0.1, 0], [5, 5], [5.1, 5]], dtype=float)
        first = deterministic_kmeans(points, 2)
        second = deterministic_kmeans(points, 2)
        np.testing.assert_allclose(first[0], second[0])
        np.testing.assert_array_equal(first[1], second[1])

    def test_validator_rejects_empty_payload(self):
        self.assertTrue(validate_result({}))

    def test_nested_photo_capture_is_detected(self):
        fixture = Path(__file__).parent / "fixtures" / "photo_capture"
        self.assertEqual(detect_tier(fixture), "photos")

    def test_damage_requires_repeated_centered_evidence(self):
        wall = Wall("wall-1", [0, 0], [4, 0], interval(4, 0.1, "test"), interval(9.8, 0.5, "test", "m2"))
        room = Room("room-1", "Room", [[0, 0], [4, 0], [4, 3], [0, 3]], [wall], interval(12, 1, "test", "m2"), interval(2.45, 0.1, "test"))
        pixels = np.full((120, 160, 3), 180, dtype=np.uint8)
        pixels[40:80, 60:100] = [140, 100, 60]
        damaged = Image.fromarray(pixels)
        self.assertEqual(detect_damage_regions([damaged], room, "photos"), [])
        room.damages = detect_damage_regions([damaged, damaged], room, "photos")
        self.assertTrue(room.damages)
        flags, scope = derive_claims([room])
        self.assertTrue(flags)
        self.assertTrue(scope)

    def test_lidar_door_gap_detector(self):
        xx, yy = np.meshgrid(np.linspace(0, 4, 161), np.linspace(0.1, 2.4, 93))
        keep = ~((xx > 1.5) & (xx < 2.4) & (yy < 2.05))
        points = np.column_stack([xx[keep], yy[keep], np.zeros(int(keep.sum()))])
        wall = Wall("wall-1", [0, 0], [4, 0], interval(4, 0.03, "test"), interval(9.6, 0.2, "test", "m2"))
        polygon = np.array([[0, 0], [4, 0], [4, 3], [0, 3]], dtype=float)
        openings = detect_lidar_openings(polygon, [wall], points, 0.0, 2.4, 0.03)
        self.assertEqual(len(openings), 1)
        self.assertEqual(openings[0].kind, "door")

    @patch("spacescan.metric_depth.calibration")
    @patch("spacescan.metric_depth.predict_metric_depth")
    def test_metric_depth_room_aggregation(self, predict, get_calibration):
        predict.return_value = np.full((96, 128), 2.0, dtype=np.float32)
        get_calibration.return_value = {
            "scale": 1.1,
            "relative_error_95": 0.22,
            "source": "test reference",
        }
        images = [Image.new("RGB", (128, 96), "white") for _ in range(3)]
        estimate = estimate_room_dimensions(images)
        self.assertEqual(estimate.frames_used, 3)
        self.assertAlmostEqual(estimate.length_m, 4.0)
        self.assertGreaterEqual(estimate.width_m, 2.2)
        self.assertLessEqual(estimate.width_m, estimate.length_m)
        self.assertAlmostEqual(estimate.uncertainty_fraction, 0.22)

    def test_evaluator_counts_missed_and_phantom_openings(self):
        prediction = {
            "capture": {"id": "test", "tier": "lidar"},
            "property": {"rooms": [{
                "id": "room-1",
                "ceiling_height": {"value": 2.4, "low": 2.38, "high": 2.42},
                "walls": [],
                "openings": [{"id": "phantom", "width": {"value": 0.8, "low": 0.78, "high": 0.82}}],
            }]},
        }
        truth = {"rooms": [{"id": "room-1", "openings": [{"id": "real-door", "width_m": 0.8}]}]}
        report = evaluate(prediction, truth)
        detections = [item for item in report["measurements"] if item["kind"] == "opening_detection"]
        self.assertEqual({item["status"] for item in detections}, {"missed", "phantom"})
        self.assertEqual(report["summary"]["opening_detection_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()

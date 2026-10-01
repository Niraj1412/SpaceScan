import unittest
import numpy as np

from spacescan.geometry import oriented_envelope, polygon_area, quaternion_matrix, robust_mode
from spacescan.validate import validate_result


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

    def test_validator_rejects_empty_payload(self):
        self.assertTrue(validate_result({}))


if __name__ == "__main__":
    unittest.main()

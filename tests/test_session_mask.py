import unittest
import numpy as np

from src.research.market_study import session_mask


class SessionMaskTests(unittest.TestCase):
    def test_wraparound_spelling_with_clock_hour_end(self):
        h = np.array([22.0, 23.0, 1.0, 10.5, 12.0])
        mask = session_mask(h, (21.5, 11.5))
        np.testing.assert_array_equal(mask, np.array([True, True, True, True, False]))

    def test_full_day_when_same_hour(self):
        h = np.array([0.0, 6.0, 12.0, 18.0, 23.9])
        mask = session_mask(h, (5.0, 5.0))
        self.assertTrue(mask.all())


if __name__ == "__main__":
    unittest.main()

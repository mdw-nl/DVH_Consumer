import unittest
from test_data import generate_df_sample
from DICOM_solver.callback import verify_full


class TestCallback(unittest.TestCase):

    def test_verify_full(self):
        dt = generate_df_sample()
        result = verify_full(dt)
        self.assertTrue(result)
        dt_2 = dt.drop([0, 1, 2])
        result = verify_full(dt_2)
        self.assertTrue(result)
        dt_3 = dt.drop([0, 1, 2, 3, 4 ])
        result = verify_full(dt_3)
        self.assertFalse(result)
        dt_4 = dt.drop([0, 1, 3, 5,6])
        result = verify_full(dt_4)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()

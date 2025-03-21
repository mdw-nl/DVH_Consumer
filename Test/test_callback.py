import unittest
from test_data import generate_df_sample
from DICOM_solver.callback import verify_full


class TestCallback(unittest.TestCase):

    def test_verify_full(self):
        dt = generate_df_sample()

        # Ensure the sample data has at least 7 rows
        self.assertGreaterEqual(dt.shape[0], 7, "Sample data must have at least 7 rows.")

        cases = [
            ("Full dataset", dt, True),
            ("Remove first 3 rows", dt.iloc[3:], True),
            ("Remove first 5 rows", dt.iloc[5:], False),
            ("Remove specific indices", dt.drop([0, 1, 3, 5, 6]), False),
        ]

        for name, df, expected in cases:
            with self.subTest(name=name):
                result = verify_full(df)
                self.assertEqual(result, expected)




if __name__ == "__main__":
    unittest.main()

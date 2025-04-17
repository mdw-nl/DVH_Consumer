import unittest
from test_data import generate_df_sample
from DICOM_solver.callback import verify_full, collect_patients_dicom
from DICOM_solver.dicom_process import dicom_object


class TestCallback(unittest.TestCase):

    def test_verify_full(self):
        dt, dp1, dp2 = generate_df_sample()

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

    def test_collect_patients_dicom(self):
        dt, dp1, dp2 = generate_df_sample()

        # Ensure the sample data has at least 7 rows
        self.assertGreaterEqual(dt.shape[0], 7, "Sample data must have at least 7 rows.")
        cases = [
            ("Full dataset", dt, [dp1, dp2]),
        ]

        for name, df, expected in cases:
            with self.subTest(name=name):
                res = collect_patients_dicom(dt)
                sorted(res, key=lambda x: x.p_id)
                sorted(expected, key=lambda x: x.p_id)
                for i in range(len(res)):
                    print(res[i].__dict__)
                    print(f"Comparing res[{i}]: {res[i].__dict__} with expected[{i}]: {expected[i].__dict__}")
                    self.assertEqual(res[i], expected[i])


if __name__ == "__main__":
    unittest.main()

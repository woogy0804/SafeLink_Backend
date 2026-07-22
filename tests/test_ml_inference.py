import unittest
from unittest.mock import patch

from features.feature_extractor import FEATURE_NAMES
from ml.inference import predict_feature_dict


class FakeEstimator:
    classes_ = [0, 1]

    def __init__(self, probability):
        self.probability = probability
        self.call_count = 0

    def predict_proba(self, rows):
        self.call_count += 1
        return [[1 - self.probability, self.probability] for _ in rows]


class TestMlInference(unittest.TestCase):
    def setUp(self):
        self.features = {name: 1 for name in FEATURE_NAMES}

    def test_skips_forest_outside_gray_zone(self):
        logistic = FakeEstimator(0.1)
        forest = FakeEstimator(0.9)
        with patch(
            "ml.inference._load_models",
            return_value=({"estimator": logistic}, {"estimator": forest}),
        ):
            prediction = predict_feature_dict(self.features)

        self.assertEqual(prediction.risk, "safe")
        self.assertFalse(prediction.gray_zone)
        self.assertEqual(forest.call_count, 0)

    def test_runs_forest_inside_gray_zone(self):
        logistic = FakeEstimator(0.5)
        forest = FakeEstimator(0.8)
        with patch(
            "ml.inference._load_models",
            return_value=({"estimator": logistic}, {"estimator": forest}),
        ):
            prediction = predict_feature_dict(self.features)

        self.assertEqual(prediction.risk, "phishing")
        self.assertTrue(prediction.gray_zone)
        self.assertEqual(prediction.phishing_probability, 0.8)
        self.assertEqual(forest.call_count, 1)

    def test_rejects_incomplete_features(self):
        features = dict(self.features)
        features.pop(FEATURE_NAMES[0])
        with self.assertRaisesRegex(ValueError, "Feature keys mismatch"):
            predict_feature_dict(features)


if __name__ == "__main__":
    unittest.main()

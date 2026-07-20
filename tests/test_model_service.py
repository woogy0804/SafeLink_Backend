import os
import unittest
from unittest.mock import patch

from features.feature_extractor import FEATURE_NAMES
from services.model_service import predict_phishing


class FakeEstimator:
    classes_ = [0, 1]

    def __init__(self, phishing_probability):
        self.phishing_probability = phishing_probability

    def predict_proba(self, rows):
        probability = self.phishing_probability
        return [[1 - probability, probability] for _ in rows]


class TestModelService(unittest.TestCase):
    def setUp(self):
        self.features = {name: 1 for name in FEATURE_NAMES}

    def _predict(self, probability):
        artifact = {
            "feature_names": list(FEATURE_NAMES),
            "estimator": FakeEstimator(probability),
            "model_name": "test_model",
            "model_version": "v1",
            "gray_zone": [0.4, 0.6],
        }
        with patch("services.model_service.get_file_snapshot", return_value=object()):
            with patch("services.model_service._load_model_snapshot", return_value=artifact):
                return predict_phishing(self.features)

    def test_predicts_phishing_above_gray_zone(self):
        prediction = self._predict(0.8)

        self.assertIsNotNone(prediction)
        self.assertEqual(prediction.risk, "phishing")
        self.assertEqual(prediction.model_used, "test_model_v1")
        self.assertFalse(prediction.gray_zone)

    def test_marks_probability_inside_gray_zone_as_suspicious(self):
        prediction = self._predict(0.5)

        self.assertEqual(prediction.risk, "suspicious")
        self.assertTrue(prediction.gray_zone)

    def test_rule_mode_disables_model(self):
        with patch.dict(os.environ, {"SAFELINK_MODEL_MODE": "rule"}):
            self.assertIsNone(predict_phishing(self.features))

    def test_rejects_missing_feature(self):
        incomplete = dict(self.features)
        incomplete.pop(FEATURE_NAMES[0])
        self.assertIsNone(predict_phishing(incomplete))


if __name__ == "__main__":
    unittest.main()

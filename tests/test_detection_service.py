import unittest
from unittest.mock import patch

from services.detection_service import detect_url
from services.model_service import ModelPrediction


class TestDetectionService(unittest.TestCase):
    def test_uses_model_probability_and_preserves_rule_score(self):
        features = {"a": 1, "b": -1}
        prediction = ModelPrediction(
            phishing_probability=0.82,
            risk="phishing",
            model_used="random_forest_v1",
            gray_zone=False,
        )
        with patch("services.detection_service.extract_features", return_value=features):
            with patch(
                "services.detection_service.predict_phishing",
                return_value=prediction,
            ):
                response = detect_url("https://example.com")

        self.assertEqual(response["score"], 0.82)
        self.assertEqual(response["rule_score"], 0.5)
        self.assertEqual(response["model_used"], "random_forest_v1")

    def test_falls_back_to_rule_when_model_is_unavailable(self):
        features = {"a": 1, "b": -1}
        with patch("services.detection_service.extract_features", return_value=features):
            with patch("services.detection_service.predict_phishing", return_value=None):
                response = detect_url("https://example.com")

        self.assertEqual(response["score"], 0.5)
        self.assertEqual(response["risk"], "suspicious")
        self.assertEqual(response["model_used"], "temporary_rule")


if __name__ == "__main__":
    unittest.main()

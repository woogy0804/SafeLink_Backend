import json
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from routes.detect_routes import DetectRequest, detect


class TestDetectApi(unittest.TestCase):
    @patch("routes.detect_routes.validate_public_url", return_value="https://example.com")
    @patch("routes.detect_routes.detect_url")
    def test_returns_detection_result(self, mock_detect_url, mock_validate_url):
        mock_detect_url.return_value = {
            "url": "https://example.com",
            "risk": "safe",
            "score": 0.0,
            "model_used": "temporary_rule",
            "gray_zone": False,
            "message": "안전한 URL로 판단됩니다.",
            "features": {},
        }

        response = detect(DetectRequest(url="https://example.com"))

        self.assertEqual(response["model_used"], "temporary_rule")

    def test_rejects_missing_url(self):
        with self.assertRaises(ValidationError):
            DetectRequest()

    def test_rejects_invalid_scheme(self):
        response = detect(DetectRequest(url="ftp://example.com"))
        body = json.loads(response.body)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "INVALID_URL")

    def test_rejects_localhost(self):
        response = detect(DetectRequest(url="http://localhost/admin"))
        body = json.loads(response.body)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["error"]["code"], "INVALID_URL")

    @patch("routes.detect_routes.validate_public_url", return_value="https://example.com")
    @patch("routes.detect_routes.detect_url", side_effect=RuntimeError("failed"))
    def test_formats_detection_failure(self, mock_detect_url, mock_validate_url):
        response = detect(DetectRequest(url="https://example.com"))
        body = json.loads(response.body)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(body["error"]["code"], "DETECTION_FAILED")


if __name__ == "__main__":
    unittest.main()

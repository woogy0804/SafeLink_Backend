import socket
import unittest
from unittest.mock import patch

from features.safe_http import (
    MAX_REDIRECTS,
    MAX_RESPONSE_BYTES,
    REQUEST_HEADERS,
    RedirectLimitError,
    ResponseTooLargeError,
    UnsafeDestinationError,
    UnsupportedContentTypeError,
    fetch_html_document,
    resolve_public_destination,
    validate_public_destination,
)


PUBLIC_ADDRESS_INFO = [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
]


class FakeResponse:
    def __init__(
        self,
        *,
        status_code=200,
        headers=None,
        text="",
        chunks=None,
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.encoding = "utf-8"
        self._chunks = chunks if chunks is not None else [text.encode("utf-8")]
        self.closed = False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield from self._chunks

    def close(self):
        self.closed = True


class TestSafeHttp(unittest.TestCase):
    def test_rejects_private_ip_destination(self):
        with self.assertRaises(UnsafeDestinationError):
            validate_public_destination("http://127.0.0.1/admin")

    def test_rejects_fullwidth_unicode_private_ip(self):
        with self.assertRaises(UnsafeDestinationError):
            validate_public_destination("http://１２７.０.０.１/admin")

    def test_rejects_zero_port_instead_of_using_default(self):
        with self.assertRaises(UnsafeDestinationError):
            validate_public_destination("https://example.com:0")

    def test_resolution_returns_normalized_hostname_and_public_ip(self):
        with patch(
            "features.safe_http.socket.getaddrinfo",
            return_value=PUBLIC_ADDRESS_INFO,
        ):
            destination = resolve_public_destination("https://EXAMPLE.com")

        self.assertEqual(destination.hostname, "example.com")
        self.assertEqual(destination.port, 443)
        self.assertEqual(str(destination.addresses[0]), "93.184.216.34")

    def test_rejects_domain_when_any_dns_result_is_private(self):
        address_info = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.8", 443)),
        ]
        with patch("features.safe_http.socket.getaddrinfo", return_value=address_info):
            with self.assertRaises(UnsafeDestinationError):
                validate_public_destination("https://example.com")

    def test_rejects_redirect_to_private_ip_before_second_request(self):
        redirect_response = FakeResponse(
            status_code=302,
            headers={"Location": "http://127.0.0.1/internal"},
        )
        with patch(
            "features.safe_http.socket.getaddrinfo",
            return_value=PUBLIC_ADDRESS_INFO,
        ):
            with patch(
                "features.safe_http.requests.get",
                return_value=redirect_response,
            ) as mock_get:
                with self.assertRaises(UnsafeDestinationError):
                    fetch_html_document("https://example.com")

        self.assertEqual(mock_get.call_count, 1)
        self.assertTrue(redirect_response.closed)

    def test_rejects_more_than_five_redirects(self):
        responses = [
            FakeResponse(status_code=302, headers={"Location": "/next"})
            for _ in range(MAX_REDIRECTS + 1)
        ]
        with patch(
            "features.safe_http.validate_public_destination",
            side_effect=lambda url: url,
        ):
            with patch("features.safe_http.requests.get", side_effect=responses) as mock_get:
                with self.assertRaises(RedirectLimitError):
                    fetch_html_document("https://example.com")

        self.assertEqual(mock_get.call_count, MAX_REDIRECTS + 1)
        self.assertTrue(all(response.closed for response in responses))

    def test_rejects_large_content_length_before_reading_body(self):
        response = FakeResponse(
            headers={
                "Content-Type": "text/html",
                "Content-Length": str(MAX_RESPONSE_BYTES + 1),
            },
            text="small fake body",
        )
        with patch(
            "features.safe_http.validate_public_destination",
            side_effect=lambda url: url,
        ):
            with patch("features.safe_http.requests.get", return_value=response):
                with self.assertRaises(ResponseTooLargeError):
                    fetch_html_document("https://example.com")

        self.assertTrue(response.closed)

    def test_rejects_stream_that_exceeds_size_limit(self):
        response = FakeResponse(
            headers={"Content-Type": "text/html"},
            chunks=[b"a" * MAX_RESPONSE_BYTES, b"b"],
        )
        with patch(
            "features.safe_http.validate_public_destination",
            side_effect=lambda url: url,
        ):
            with patch("features.safe_http.requests.get", return_value=response):
                with self.assertRaises(ResponseTooLargeError):
                    fetch_html_document("https://example.com")

    def test_rejects_non_html_content_type(self):
        response = FakeResponse(
            headers={"Content-Type": "application/octet-stream"},
            text="binary",
        )
        with patch(
            "features.safe_http.validate_public_destination",
            side_effect=lambda url: url,
        ):
            with patch("features.safe_http.requests.get", return_value=response):
                with self.assertRaises(UnsupportedContentTypeError):
                    fetch_html_document("https://example.com/file")

    def test_fetches_valid_html_with_security_options(self):
        response = FakeResponse(
            headers={"Content-Type": "text/html; charset=utf-8"},
            text="<html><body>ok</body></html>",
        )
        with patch(
            "features.safe_http.validate_public_destination",
            side_effect=lambda url: url,
        ):
            with patch(
                "features.safe_http.requests.get",
                return_value=response,
            ) as mock_get:
                document = fetch_html_document("https://example.com")

        self.assertEqual(document.final_url, "https://example.com")
        self.assertEqual(document.text, "<html><body>ok</body></html>")
        self.assertTrue(response.closed)
        mock_get.assert_called_once_with(
            "https://example.com",
            timeout=(3, 5),
            allow_redirects=False,
            stream=True,
            headers=REQUEST_HEADERS,
        )


if __name__ == "__main__":
    unittest.main()

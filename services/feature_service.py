from urllib.parse import urlparse


def extract_features(url: str) -> dict:
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname or ""

    return {
        "url_length": 1 if len(url) > 75 else 0,
        "has_at_symbol": 1 if "@" in url else 0,
        "has_dash": 1 if "-" in hostname else 0,
        "uses_https": 1 if parsed_url.scheme == "https" else 0,
        "has_ip_address": 1 if _looks_like_ip_address(hostname) else 0,
    }


def _looks_like_ip_address(hostname: str) -> bool:
    parts = hostname.split(".")

    if len(parts) != 4:
        return False

    return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)

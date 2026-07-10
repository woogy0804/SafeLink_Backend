from typing import Dict, List

from features.having_ip_feature import having_ip_feature
from features.url_length_feature import url_length_feature
from features.shortener_feature import shortener_feature
from features.prefix_suffix_feature import prefix_suffix_feature
from features.ssl_feature import ssl_feature
from features.domain_age_feature import domain_age_feature
from features.dns_feature import dns_feature
from features.request_url_feature import request_url_feature
from features.anchor_feature import anchor_feature
from features.sfh_feature import sfh_feature
from features.forwarding_feature import forwarding_feature
from features.iframe_feature import iframe_feature


VALID_FEATURE_VALUES = {-1, 0, 1}

FEATURE_FUNCTIONS = (
    ("having_ip", having_ip_feature),
    ("url_length", url_length_feature),
    ("shortener", shortener_feature),
    ("prefix_suffix", prefix_suffix_feature),
    ("ssl", ssl_feature),
    ("domain_age", domain_age_feature),
    ("dns", dns_feature),
    ("request_url", request_url_feature),
    ("anchor", anchor_feature),
    ("sfh", sfh_feature),
    ("forwarding", forwarding_feature),
    ("iframe", iframe_feature),
)

FEATURE_NAMES = [feature_name for feature_name, _ in FEATURE_FUNCTIONS]


def _normalize_feature_value(value: int) -> int:
    return value if value in VALID_FEATURE_VALUES else -1


def extract_features(url: str) -> List[int]:
    """
    URL 하나를 받아 고정 순서의 feature 값 list를 반환한다.
    각 값은 1, 0, -1 중 하나로 보정된다.
    """
    feature_values = []

    for _, feature_function in FEATURE_FUNCTIONS:
        try:
            feature_values.append(_normalize_feature_value(feature_function(url)))
        except Exception:
            feature_values.append(-1)

    return feature_values


def extract_feature_dict(url: str) -> Dict[str, int]:
    """
    API 응답이나 디버깅용으로 feature 이름과 값을 함께 반환한다.
    모델 입력에는 extract_features(url)의 list를 사용한다.
    """
    return dict(zip(FEATURE_NAMES, extract_features(url)))

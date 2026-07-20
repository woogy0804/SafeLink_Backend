import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Dict, List

from features.ssl_feature import ssl_feature
from features.anchor_feature import anchor_feature
from features.web_traffic_feature import web_traffic_feature
from features.prefix_suffix_feature import prefix_suffix_feature
from features.subdomain_feature import subdomain_feature
from features.links_in_tags_feature import links_in_tags_feature
from features.links_pointing_to_page_feature import links_pointing_to_page_feature
from features.request_url_feature import request_url_feature
from features.sfh_feature import sfh_feature
from features.domain_age_feature import domain_age_feature
from features.domain_registration_length_feature import (
    domain_registration_length_feature,
)
from features.having_ip_feature import having_ip_feature
from features.html_context import fetch_html_context
from features.domain_context import fetch_domain_context


VALID_FEATURE_VALUES = {-1, 0, 1}

FEATURE_FUNCTIONS = (
    ("SSLfinal_State", ssl_feature),
    ("URL_of_Anchor", anchor_feature),
    ("web_traffic", web_traffic_feature),
    ("Prefix_Suffix", prefix_suffix_feature),
    ("having_Sub_Domain", subdomain_feature),
    ("Links_in_tags", links_in_tags_feature),
    ("Links_pointing_to_page", links_pointing_to_page_feature),
    ("Request_URL", request_url_feature),
    ("SFH", sfh_feature),
    ("age_of_domain", domain_age_feature),
    ("Domain_registeration_length", domain_registration_length_feature),
    ("having_IP_Address", having_ip_feature),
)

FEATURE_NAMES = [feature_name for feature_name, _ in FEATURE_FUNCTIONS]
HTML_FEATURE_FUNCTIONS = frozenset(
    {
        anchor_feature,
        links_in_tags_feature,
        request_url_feature,
        sfh_feature,
    }
)
DOMAIN_FEATURE_FUNCTIONS = frozenset(
    {
        domain_age_feature,
        domain_registration_length_feature,
    }
)

# requests/socket 기반 수집을 서로 겹쳐 실행한다. FastAPI의 현재 sync route는
# 자체 worker thread에서 이 함수를 호출하며, async route에서는 아래
# extract_features_async를 사용하면 event loop를 막지 않는다.
_NETWORK_EXECUTOR = ThreadPoolExecutor(
    max_workers=12,
    thread_name_prefix="safelink-feature",
)


def _normalize_feature_value(value: int) -> int:
    return value if value in VALID_FEATURE_VALUES else -1


def extract_features(url: str) -> List[int]:
    """
    URL 하나를 받아 고정 순서의 feature 값 list를 반환한다.
    각 값은 1, 0, -1 중 하나로 보정된다.
    """
    feature_values = []
    html_context = None
    domain_context = None
    feature_functions = {function for _, function in FEATURE_FUNCTIONS}
    ssl_future: Future | None = None
    html_future: Future | None = None
    domain_future: Future | None = None

    if ssl_feature in feature_functions:
        ssl_future = _NETWORK_EXECUTOR.submit(ssl_feature, url)
    if feature_functions.intersection(HTML_FEATURE_FUNCTIONS):
        html_future = _NETWORK_EXECUTOR.submit(fetch_html_context, url)
    if feature_functions.intersection(DOMAIN_FEATURE_FUNCTIONS):
        domain_future = _NETWORK_EXECUTOR.submit(fetch_domain_context, url)

    for _, feature_function in FEATURE_FUNCTIONS:
        try:
            if feature_function is ssl_feature and ssl_future is not None:
                value = ssl_future.result()
            elif feature_function in HTML_FEATURE_FUNCTIONS:
                if html_context is None:
                    if html_future is not None:
                        html_context = html_future.result()
                    else:
                        html_context = fetch_html_context(url)
                value = feature_function(url, html_context=html_context)
            elif feature_function in DOMAIN_FEATURE_FUNCTIONS:
                if domain_context is None:
                    if domain_future is not None:
                        domain_context = domain_future.result()
                    else:
                        domain_context = fetch_domain_context(url)
                value = feature_function(url, domain_context=domain_context)
            else:
                value = feature_function(url)
            feature_values.append(_normalize_feature_value(value))
        except Exception:
            feature_values.append(-1)

    return feature_values


def extract_feature_dict(url: str) -> Dict[str, int]:
    """
    API 응답이나 디버깅용으로 feature 이름과 값을 함께 반환한다.
    모델 입력에는 extract_features(url)의 list를 사용한다.
    """
    return dict(zip(FEATURE_NAMES, extract_features(url)))


async def extract_features_async(url: str) -> List[int]:
    """Run the synchronous extractor without blocking an asyncio event loop."""

    return await asyncio.to_thread(extract_features, url)


async def extract_feature_dict_async(url: str) -> Dict[str, int]:
    values = await extract_features_async(url)
    return dict(zip(FEATURE_NAMES, values))

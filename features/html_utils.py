"""HTML 기반 feature가 공통으로 사용하는 정적 문서 판별 도구."""

from bs4 import BeautifulSoup


ANALYZABLE_BODY_TAGS = (
    "a",
    "form",
    "img",
    "video",
    "audio",
    "picture",
    "source",
    "input",
    "button",
)


def is_static_html_unavailable(soup: BeautifulSoup) -> bool:
    """본문이 비었거나 JavaScript 실행 전 SPA shell뿐이면 True를 반환한다.

    일반 텍스트나 분석 가능한 정적 태그가 있으면 정적 HTML로 판단한다.
    테스트와 재사용을 위한 HTML fragment는 실제 태그가 하나라도 있으면
    분석 가능한 문서로 취급한다.
    """

    body = soup.body
    if body is None:
        return soup.find() is None and not soup.get_text(" ", strip=True)

    if body.get_text(" ", strip=True):
        return False

    return body.find(ANALYZABLE_BODY_TAGS) is None

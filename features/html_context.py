"""HTML 기반 feature가 공유하는 단일 수집·파싱 컨텍스트."""

from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup

from features.html_utils import is_static_html_unavailable
from features.safe_http import fetch_html_document


@dataclass(frozen=True)
class HtmlAnalysisContext:
    document_url: str
    soup: Optional[BeautifulSoup]
    fetch_failed: bool
    static_unavailable: bool


def fetch_html_context(url: str) -> HtmlAnalysisContext:
    """URL을 한 번 요청하고 HTML 파싱 결과와 상태를 반환한다."""

    try:
        document = fetch_html_document(url)
        soup = BeautifulSoup(document.text, "html.parser")
        return HtmlAnalysisContext(
            document_url=document.final_url,
            soup=soup,
            fetch_failed=False,
            static_unavailable=is_static_html_unavailable(soup),
        )
    except Exception:
        return HtmlAnalysisContext(
            document_url=url,
            soup=None,
            fetch_failed=True,
            static_unavailable=True,
        )

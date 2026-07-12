from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.detection_service import detect_url
from utils.response_formatter import format_error_response
from utils.url_validator import validate_public_url

router = APIRouter(prefix="/detect", tags=["Detection"])


class DetectRequest(BaseModel):
    url: str


@router.post("")
def detect(request: DetectRequest):
    try:
        url = validate_public_url(request.url)
        return detect_url(url)
    except ValueError as error:
        return JSONResponse(
            status_code=400,
            content=format_error_response("INVALID_URL", str(error)),
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content=format_error_response(
                "DETECTION_FAILED",
                "URL 분석 중 오류가 발생했습니다.",
            ),
        )

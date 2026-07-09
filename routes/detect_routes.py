from fastapi import APIRouter
from pydantic import BaseModel

from services.detection_service import detect_url

router = APIRouter(prefix="/detect", tags=["Detection"])


class DetectRequest(BaseModel):
    url: str


@router.post("")
def detect(request: DetectRequest):
    return detect_url(request.url)
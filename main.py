from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from routes.detect_routes import router as detect_router
from utils.response_formatter import format_error_response

app = FastAPI(
    title="SafeLink Backend",
    description="악성 URL 탐지 API",
    version="0.1.0",
)

app.include_router(detect_router)
app.mount(
    "/app",
    StaticFiles(directory=Path(__file__).parent / "frontend", html=True),
    name="frontend",
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content=format_error_response(
            "INVALID_REQUEST",
            "요청 본문에 url 문자열을 입력해주세요.",
        ),
    )


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "SafeLink backend is running",
    }

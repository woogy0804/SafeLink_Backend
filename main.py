from fastapi import FastAPI
from routes.detect_routes import router as detect_router

app = FastAPI(
    title="SafeLink Backend",
    description="악성 URL 탐지 API",
    version="0.1.0",
)

app.include_router(detect_router)


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "SafeLink backend is running",
    }
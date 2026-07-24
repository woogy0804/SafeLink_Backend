from pathlib import Path

from main import app


FRONTEND_DIR = Path(__file__).parents[1] / "frontend"


def test_frontend_is_mounted():
    mount_paths = {getattr(route, "path", None) for route in app.routes}

    assert "/app" in mount_paths


def test_frontend_files_are_connected_to_detect_api():
    index = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    css = (FRONTEND_DIR / "styles.css").read_text(encoding="utf-8")
    javascript = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")

    assert "SafeLink" in index
    assert "URL 검사" in index
    assert "--accent" in css
    assert 'fetch("/detect"' in javascript

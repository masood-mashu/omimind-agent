import os
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from backend.main import app
except Exception as e:
    import traceback
    tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    app = FastAPI()
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def error_catcher(path: str = ""):
        return PlainTextResponse(f"Initialization Error:\n{tb}", status_code=500)

__all__ = ["app"]

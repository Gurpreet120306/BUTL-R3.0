"""Start with the configured localhost host and port: python -m scripts.run_backend."""
import os

from dotenv import load_dotenv
import uvicorn

from backend.shared.config import local_url


if __name__ == "__main__":
    load_dotenv()
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    local_url(f"http://{host}", {"http"})
    uvicorn.run("backend.main:app", host=host, port=int(os.getenv("BACKEND_PORT", "8765")), reload=True)

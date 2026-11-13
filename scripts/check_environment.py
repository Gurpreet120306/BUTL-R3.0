"""Non-capturing environment checks: python -m scripts.check_environment."""
import asyncio
import importlib.util
import shutil
import sys
from pathlib import Path


def check(label, ok, message):
    print(f"[{'OK' if ok else 'MISSING'}] {label}: {message}")
    return ok


async def main():
    success = check("Python", sys.version_info >= (3, 11), sys.version.split()[0])
    dependencies = ["fastapi", "uvicorn", "pydantic", "dotenv", "pymongo", "httpx", "mss", "PIL", "pytesseract", "psutil"]
    if sys.platform == "win32":
        dependencies += ["pywinauto", "win32gui"]
    installed = True
    for dependency in dependencies:
        installed &= check(dependency, importlib.util.find_spec(dependency) is not None, "Python dependency")
    success &= installed
    if installed:
        from backend.shared.config import Config
        from backend.assistant_engine import OllamaClient
        from backend.memory_engine import MongoConnection
        config = Config()
        tesseract = config.tesseract_cmd or shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        success &= check("Tesseract", Path(tesseract).is_file(), tesseract)
        mongo = MongoConnection(config.mongodb_uri, config.mongodb_db)
        ai = OllamaClient(config.ollama_url, config.ollama_timeout)
        try:
            database, model = await asyncio.gather(mongo.health(), ai.health(config.vision_model))
            success &= check("MongoDB", database.available, database.message)
            success &= check("Ollama vision model", model.available, model.message)
            chat = await ai.health(config.chat_model)
            success &= check("Ollama chat model", chat.available, chat.message)
            print(f"Installed local models: {', '.join(model.models) or 'none'}")
        finally:
            await mongo.close()
            await ai.close()
    success &= check("Node.js", bool(shutil.which("node")), shutil.which("node") or "Install Node.js LTS")
    success &= check("Frontend dependencies", Path("frontend/node_modules/vite/package.json").is_file(), "Run npm install in frontend/")
    print("No screen was captured. No model inference was requested.")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

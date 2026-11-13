from PIL import Image, ImageFilter, ImageOps
from pathlib import Path
import shutil


def preprocess(image: Image.Image) -> Image.Image:
    gray = ImageOps.autocontrast(image.convert("L"))
    if gray.width < 1600:
        gray = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS)
    return gray.filter(ImageFilter.SHARPEN)


def extract_text(image: Image.Image, command: str | None = None) -> tuple[str, list[str]]:
    import pytesseract
    if not command and not shutil.which("tesseract"):
        installed = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        command = str(installed) if installed.is_file() else None
    if command:
        pytesseract.pytesseract.tesseract_cmd = command
    try:
        return pytesseract.image_to_string(preprocess(image), config="--psm 11", timeout=20), []
    except pytesseract.TesseractNotFoundError:
        return "", ["Tesseract is missing. Install it and set TESSERACT_CMD in .env"]
    except (pytesseract.TesseractError, RuntimeError, OSError):
        return "", ["OCR could not read this capture; accessibility and vision remain available"]

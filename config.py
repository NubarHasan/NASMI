from pathlib import Path
import platform

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "db" / "nasmi.db"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"

for _dir in [DATA_DIR, UPLOAD_DIR, OUTPUT_DIR, DB_PATH.parent]:
    _dir.mkdir(parents=True, exist_ok=True)

OLLAMA_BASE_URL = "http://192.168.0.101:11434"

MODELS = {
    "text": "mistral:latest",
    "vision": "llava:latest",
    "general": "llama3.2:latest",
    "embed": "nomic-embed-text:latest",
    "fallback": "llama3.2:latest",
}

EXTRACTION = {
    "max_file_size_mb": 50,
    "supported_formats": [
        ".pdf",
        ".png",
        ".jpg",
        ".heic",
        ".jpeg",
        ".tiff",
        ".docx",
    ],
    "ocr_dpi": 300,
    "confidence_threshold": 0.85,
}

TESSERACT = {
    "cmd": (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if platform.system() == "Windows"
        else "/usr/bin/tesseract"
    ),
    "langs": ["eng", "ara", "deu"],
}

DB = {
    "path": str(DB_PATH),
    "timeout": 30,
}

APP = {
    "name": "NASMI",
    "version": "2.0.0",
    "debug": False,
}

SECRET_KEY = "nasmi-secret-key-change-in-production"
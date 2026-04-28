from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "db" / "nasmi.db"
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"


for _dir in [DATA_DIR, UPLOAD_DIR, OUTPUT_DIR, DB_PATH.parent]:
    _dir.mkdir(parents=True, exist_ok=True)


OLLAMA_BASE_URL = "http://localhost:11434"

MODELS = {
    "text": "qwen2.5:7b",
    "vision": "moondream:latest",
    "general": "llama3.2:latest",
    "heavy": "gpt-oss:120b",
    "fallback": "gemma3:4b",
}

EXTRACTION = {
    "max_file_size_mb": 50,
    "supported_formats": [".pdf", ".png", ".jpg", ".heic", ".jpeg", ".tiff", ".docx"],
    "ocr_dpi": 300,
    "confidence_threshold": 0.85,
}

TESSERACT = {
    "cmd": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    "langs": ["eng", "ara", "deu"],
}

DB = {
    "path": str(DB_PATH),
    "timeout": 30,
}

APP = {
    "name": "NASMI",
    "version": "1.0.0",
    "debug": False,
}

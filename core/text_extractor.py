import pdfplumber
import docx
from pathlib import Path
from config import EXTRACTION


class TextExtractor:

    def __init__(self):
        self.confidence_threshold = EXTRACTION["confidence_threshold"]

    def extract_pdf(self, file_path: str) -> dict:
        pages = []
        full_text = ""

        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    pages.append({"page": i + 1, "text": text.strip()})
                    full_text += text.strip() + "\n"

        return {
            "success": len(pages) > 0,
            "method": "pdfplumber",
            "pages": pages,
            "full_text": full_text.strip(),
            "page_count": len(pages),
        }

    def extract_docx(self, file_path: str) -> dict:
        doc = docx.Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(paragraphs)

        return {
            "success": len(paragraphs) > 0,
            "method": "python-docx",
            "full_text": full_text,
            "paragraphs": paragraphs,
        }

    def extract(self, file_path: str) -> dict:
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            return self.extract_pdf(file_path)

        if ext == ".docx":
            return self.extract_docx(file_path)

        if ext in [".png", ".jpg", ".jpeg", ".tiff", ".heic"]:
            return {
                "success": False,
                "method": "ocr_required",
                "full_text": "",
                "note": "Use OCREngine for image files",
            }

        return {
            "success": False,
            "method": "unknown",
            "full_text": "",
            "note": f"Unsupported type: {ext}",
        }

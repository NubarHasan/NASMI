import pytesseract
import pdfplumber
from PIL import Image
from pillow_heif import register_heif_opener
from pathlib import Path
from config import TESSERACT, EXTRACTION

register_heif_opener()

pytesseract.pytesseract.tesseract_cmd = TESSERACT["cmd"]

SUPPORTED_LANGS = TESSERACT["langs"]
IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".tiff", ".heic"}
PDF_FORMAT = ".pdf"


class OCREngine:

    def __init__(self):
        self._lang = "+".join(SUPPORTED_LANGS)
        self._dpi = EXTRACTION["ocr_dpi"]

    def extract(self, file_path: str) -> dict:
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == PDF_FORMAT:
            return self._extract_pdf(path)
        elif suffix in IMAGE_FORMATS:
            return self._extract_image(path)
        else:
            return self._error(f"Unsupported format: {suffix}")

    def _extract_pdf(self, path: Path) -> dict:
        pages = []
        try:
            with pdfplumber.open(path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        pages.append(
                            {"page": i + 1, "text": text.strip(), "method": "direct"}
                        )
                    else:
                        image = page.to_image(resolution=self._dpi).original
                        ocr_text = self._run_ocr(image)
                        pages.append({"page": i + 1, "text": ocr_text, "method": "ocr"})
            return {"status": "success", "source": str(path), "pages": pages}
        except Exception as e:
            return self._error(str(e))

    def _extract_image(self, path: Path) -> dict:
        try:
            image = Image.open(path)
            text = self._run_ocr(image)
            return {
                "status": "success",
                "source": str(path),
                "pages": [{"page": 1, "text": text, "method": "ocr"}],
            }
        except Exception as e:
            return self._error(str(e))

    def _run_ocr(self, image: Image.Image) -> str:
        config = f"--dpi {self._dpi}"
        return pytesseract.image_to_string(
            image, lang=self._lang, config=config
        ).strip()

    def _error(self, message: str) -> dict:
        return {"status": "error", "message": message, "pages": []}

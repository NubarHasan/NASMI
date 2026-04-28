import pdfplumber
from pathlib import Path
from dataclasses import dataclass, field
from core.document_loader import LoadedDocument


@dataclass
class ExtractedText:
    source: str
    method: str
    pages: list[dict] = field(default_factory=list)
    full_text: str = ""
    metadata: dict = field(default_factory=dict)


class TextExtractor:

    def extract(self, doc: LoadedDocument) -> ExtractedText:
        if doc.file_type == "pdf":
            return self._extract_pdf(doc)
        raise ValueError(f"TextExtractor only handles PDF — got: {doc.file_type}")

    def _extract_pdf(self, doc: LoadedDocument) -> ExtractedText:
        pages = []

        with pdfplumber.open(doc.file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                pages.append(
                    {
                        "page": i + 1,
                        "text": text,
                        "width": page.width,
                        "height": page.height,
                    }
                )

        full_text = "\n".join(str(p["text"]) for p in pages)

        return ExtractedText(
            source=doc.filename,
            method="pdfplumber",
            pages=pages,
            full_text=full_text,
            metadata={"page_count": len(pages)},
        )

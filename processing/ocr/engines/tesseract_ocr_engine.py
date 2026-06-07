from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytesseract
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image

from core.exceptions import OcrProcessingError
from core.types import ConfidenceScore
from processing.ocr.bounding_box import BoundingBox
from processing.ocr.ocr_block import OcrBlock, OcrBlockType
from processing.ocr.ocr_line import OcrLine
from processing.ocr.ocr_page import OcrPage
from processing.ocr.ocr_request import OcrRequest
from processing.ocr.ocr_result import OcrResult
from processing.ocr.ocr_word import OcrWord

_ENGINE_NAME = "tesseract"
_ENGINE_VERSION: str | None = str(pytesseract.get_tesseract_version())
_DPI = 300
_CONF_SCALE = 100.0
_DEFAULT_LANG = "eng"

_LANG_MAP: dict[str, str] = {
    "en": "eng",
    "de": "deu",
    "fr": "fra",
    "es": "spa",
    "ar": "ara",
    "zh": "chi_sim",
    "ja": "jpn",
    "ko": "kor",
    "pt": "por",
    "it": "ita",
    "ru": "rus",
    "nl": "nld",
    "tr": "tur",
}


def _normalize_lang(lang: str) -> str:
    return _LANG_MAP.get(lang.lower().strip(), lang.strip())


def _lang_string(request: OcrRequest) -> str:
    if request.languages:
        return _normalize_lang(request.languages[0])
    return _DEFAULT_LANG


def _to_images(request: OcrRequest) -> list[Image.Image]:
    if request.file_path is not None:
        suffix = Path(request.file_path).suffix.lower()
        if suffix == ".pdf":
            return convert_from_path(request.file_path, dpi=_DPI)
        return [Image.open(request.file_path)]
    assert request.content is not None
    suffix = (request.mime_type or "").lower()
    if "pdf" in suffix:
        return convert_from_bytes(request.content, dpi=_DPI)
    return [Image.open(io.BytesIO(request.content))]


def _parse_conf(raw: Any) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _confidence(raw: float) -> ConfidenceScore:
    return round(max(0.0, min(1.0, raw / _CONF_SCALE)), 4)


def _build_page(
    image: Image.Image,
    page_number: int,
    lang: str,
) -> OcrPage | None:
    data = pytesseract.image_to_data(
        image,
        lang=lang,
        output_type=pytesseract.Output.DICT,
    )

    width, height = image.size

    blocks: dict[int, dict[int, dict[int, list[OcrWord]]]] = {}

    n = len(data["level"])
    for i in range(n):
        if data["level"][i] != 5:
            continue
        text = (data["text"][i] or "").strip()
        if not text:
            continue

        conf = _confidence(max(0.0, _parse_conf(data["conf"][i])))
        bb = BoundingBox.create(
            x=float(data["left"][i]),
            y=float(data["top"][i]),
            width=float(data["width"][i]),
            height=float(data["height"][i]),
        )
        block_num = data["block_num"][i]
        par_num = data["par_num"][i]
        line_num = data["line_num"][i]

        word = OcrWord.create(
            text=text,
            confidence=conf,
            bounding_box=bb,
            metadata={
                "block_num": block_num,
                "par_num": par_num,
                "line_num": line_num,
            },
        )

        blocks.setdefault(block_num, {}).setdefault(par_num, {}).setdefault(
            line_num, []
        ).append(word)

    ocr_blocks: list[OcrBlock] = []

    for block_num, paragraphs in sorted(blocks.items()):
        ocr_lines: list[OcrLine] = []

        for par_num, lines in sorted(paragraphs.items()):
            for line_num, words in sorted(lines.items()):
                if not words:
                    continue
                xs = [w.bounding_box.x for w in words]
                ys = [w.bounding_box.y for w in words]
                x2s = [w.bounding_box.x2 for w in words]
                y2s = [w.bounding_box.y2 for w in words]
                line_bb = BoundingBox.create(
                    x=min(xs),
                    y=min(ys),
                    width=max(x2s) - min(xs),
                    height=max(y2s) - min(ys),
                )
                line_text = " ".join(w.text for w in words)
                line_conf = round(sum(w.confidence for w in words) / len(words), 4)
                ocr_lines.append(
                    OcrLine.create(
                        text=line_text,
                        confidence=line_conf,
                        bounding_box=line_bb,
                        words=words,
                        metadata={
                            "block_num": block_num,
                            "par_num": par_num,
                            "line_num": line_num,
                        },
                    )
                )

        if not ocr_lines:
            continue

        all_words = [w for line in ocr_lines for w in line.words]
        xs = [w.bounding_box.x for w in all_words]
        ys = [w.bounding_box.y for w in all_words]
        x2s = [w.bounding_box.x2 for w in all_words]
        y2s = [w.bounding_box.y2 for w in all_words]
        block_bb = BoundingBox.create(
            x=min(xs),
            y=min(ys),
            width=max(x2s) - min(xs),
            height=max(y2s) - min(ys),
        )
        block_conf = round(sum(w.confidence for w in all_words) / len(all_words), 4)
        block_text = "\n".join(line.reconstructed_text for line in ocr_lines)

        ocr_blocks.append(
            OcrBlock.create(
                text=block_text,
                confidence=block_conf,
                bounding_box=block_bb,
                block_type=OcrBlockType.PARAGRAPH,
                lines=ocr_lines,
                metadata={"block_num": block_num},
            )
        )

    if not ocr_blocks:
        return None

    return OcrPage.create(
        page_number=page_number,
        width=float(width),
        height=float(height),
        blocks=ocr_blocks,
    )


class TesseractOcrEngine:

    @property
    def engine_name(self) -> str:
        return _ENGINE_NAME

    @property
    def engine_version(self) -> str | None:
        return _ENGINE_VERSION

    def process(self, request: OcrRequest) -> OcrResult:
        lang = _lang_string(request)
        images = _to_images(request)
        total = len(images)

        pages: list[OcrPage] = []
        for i, image in enumerate(images):
            try:
                page = _build_page(image, page_number=i + 1, lang=lang)
                if page is not None:
                    pages.append(page)
            finally:
                image.close()

        if not pages:
            raise OcrProcessingError(
                "All pages are empty — no OCR content extracted.",
                details={
                    "source_id": request.source_id,
                    "total_pages": total,
                },
            )

        return OcrResult.create(
            source_id=request.source_id,
            pages=pages,
            metadata={
                "engine": _ENGINE_NAME,
                "engine_version": _ENGINE_VERSION,
                "language": lang,
                "total_pages": total,
                "processed_pages": len(pages),
                "empty_pages": total - len(pages),
            },
        )

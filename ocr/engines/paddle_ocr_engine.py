from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from paddleocr import PaddleOCR
from pdf2image import convert_from_bytes, convert_from_path
from PIL import Image

from core.exceptions import OcrProcessingError
from core.types import ConfidenceScore
from ocr.bounding_box import BoundingBox
from ocr.ocr_block import OcrBlock, OcrBlockType
from ocr.ocr_line import OcrLine
from ocr.ocr_page import OcrPage
from ocr.ocr_request import OcrRequest
from ocr.ocr_result import OcrResult
from ocr.ocr_word import OcrWord

try:
    import paddleocr as _paddleocr_module

    _ENGINE_VERSION: str | None = getattr(_paddleocr_module, "__version__", None)
except Exception:
    _ENGINE_VERSION = None

_ENGINE_NAME = "paddle"
_DPI = 300
_DEFAULT_LANG = "en"


def _lang_string(request: OcrRequest) -> str:
    if request.languages:
        return str(request.languages[0])
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
    return round(max(0.0, min(1.0, raw)), 4)


def _normalize_raw(raw: Any) -> list[Any]:
    if not raw:
        return []
    first = raw[0]
    if (
        isinstance(first, (list, tuple))
        and first
        and isinstance(first[0], (list, tuple))
    ):
        return list(first)
    return list(raw)


def _quad_to_bbox(quad: Sequence[Sequence[float]]) -> BoundingBox:
    if len(quad) < 4:
        raise OcrProcessingError(
            "Invalid PaddleOCR quadrilateral.",
            details={"quad": quad},
        )
    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    x = min(xs)
    y = min(ys)
    return BoundingBox.create(
        x=x,
        y=y,
        width=max(xs) - x,
        height=max(ys) - y,
    )


def _split_box_horizontally(
    line_bb: BoundingBox,
    n: int,
    idx: int,
) -> BoundingBox:
    word_width = line_bb.width / n
    return BoundingBox.create(
        x=line_bb.x + idx * word_width,
        y=line_bb.y,
        width=word_width,
        height=line_bb.height,
    )


def _build_words(
    text: str,
    conf: ConfidenceScore,
    line_bb: BoundingBox,
) -> list[OcrWord]:
    tokens = text.split()
    if not tokens:
        return []
    return [
        OcrWord.create(
            text=token,
            confidence=conf,
            bounding_box=_split_box_horizontally(line_bb, len(tokens), i),
            metadata={"derived_from_line": True},
        )
        for i, token in enumerate(tokens)
    ]


def _build_page(
    image: Image.Image,
    page_number: int,
    engine: PaddleOCR,
) -> OcrPage | None:
    raw: Any = engine.ocr(np.array(image), cls=True)
    entries = _normalize_raw(raw)

    if not entries:
        return None

    width, height = image.size
    ocr_lines: list[OcrLine] = []

    for entry in entries:
        if not entry or len(entry) < 2:
            continue
        quad = entry[0]
        text_conf: Any = entry[1]
        if not isinstance(text_conf, (list, tuple)) or len(text_conf) < 2:
            continue

        text = (text_conf[0] or "").strip()
        raw_conf = text_conf[1]

        if not text:
            continue

        conf = _confidence(_parse_conf(raw_conf))
        line_bb = _quad_to_bbox(quad)
        words = _build_words(text, conf, line_bb)

        if not words:
            continue

        ocr_lines.append(
            OcrLine.create(
                text=text,
                confidence=conf,
                bounding_box=line_bb,
                words=words,
            )
        )

    if not ocr_lines:
        return None

    xs = [line.bounding_box.x for line in ocr_lines]
    ys = [line.bounding_box.y for line in ocr_lines]
    x2s = [line.bounding_box.x2 for line in ocr_lines]
    y2s = [line.bounding_box.y2 for line in ocr_lines]
    block_bb = BoundingBox.create(
        x=min(xs),
        y=min(ys),
        width=max(x2s) - min(xs),
        height=max(y2s) - min(ys),
    )
    block_conf = round(sum(line.confidence for line in ocr_lines) / len(ocr_lines), 4)
    block_text = "\n".join(line.reconstructed_text for line in ocr_lines)

    block = OcrBlock.create(
        text=block_text,
        confidence=block_conf,
        bounding_box=block_bb,
        block_type=OcrBlockType.PARAGRAPH,
        lines=ocr_lines,
    )

    return OcrPage.create(
        page_number=page_number,
        width=float(width),
        height=float(height),
        blocks=[block],
    )


class PaddleOcrEngine:

    def __init__(self, lang: str = _DEFAULT_LANG) -> None:
        self._lang = lang
        self._engine = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

    @property
    def engine_name(self) -> str:
        return _ENGINE_NAME

    @property
    def engine_version(self) -> str | None:
        return _ENGINE_VERSION

    def process(self, request: OcrRequest) -> OcrResult:
        lang = _lang_string(request)
        if lang != self._lang:
            self._engine = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
            self._lang = lang

        images = _to_images(request)
        total = len(images)
        pages: list[OcrPage] = []

        for i, image in enumerate(images):
            try:
                page = _build_page(image, page_number=i + 1, engine=self._engine)
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

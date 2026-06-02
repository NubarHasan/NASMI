from __future__ import annotations

import re
from typing import Literal

from core.exceptions import OcrProcessingError
from core.guards import require
from core.types import ConfidenceScore
from processing.ocr.bounding_box import BoundingBox
from processing.ocr.ocr_block import OcrBlock, OcrBlockType
from processing.ocr.ocr_engine import OcrEngine
from processing.ocr.ocr_line import OcrLine
from processing.ocr.ocr_page import OcrPage
from processing.ocr.ocr_request import OcrRequest
from processing.ocr.ocr_result import OcrResult

MatchStatus = Literal["matched", "primary_only", "secondary_only"]

_ENGINE_NAME = "fusion"


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _fuse_confidence(
    status: MatchStatus,
    conf_a: ConfidenceScore | None,
    conf_b: ConfidenceScore | None,
) -> ConfidenceScore:
    if status == "matched":
        require(conf_a is not None, "conf_a required for matched")
        require(conf_b is not None, "conf_b required for matched")
        return round((conf_a + conf_b) / 2.0, 4)  # type: ignore[operator]
    if status == "primary_only":
        require(conf_a is not None, "conf_a required for primary_only")
        return conf_a  # type: ignore[return-value]
    require(conf_b is not None, "conf_b required for secondary_only")
    return conf_b  # type: ignore[return-value]


def _fuse_lines(
    primary_lines: list[OcrLine],
    secondary_lines: list[OcrLine],
    primary_name: str,
    secondary_name: str,
) -> list[OcrLine]:
    secondary_index: dict[str, int] = {}
    for s_idx, s_line in enumerate(secondary_lines):
        key = _normalise(s_line.text)
        if key not in secondary_index:
            secondary_index[key] = s_idx

    used: set[int] = set()
    fused: list[OcrLine] = []

    for p_line in primary_lines:
        key = _normalise(p_line.text)
        s_idx = secondary_index.get(key, -1)
        matched = s_idx >= 0 and s_idx not in used

        if matched:
            s_line = secondary_lines[s_idx]
            used.add(s_idx)
            status: MatchStatus = "matched"
            conf = _fuse_confidence(status, p_line.confidence, s_line.confidence)
            fused.append(
                OcrLine.create(
                    text=p_line.text,
                    confidence=conf,
                    bounding_box=p_line.bounding_box,
                    words=list(p_line.words),
                    metadata={
                        "match_status": status,
                        "confidence_primary": p_line.confidence,
                        "confidence_secondary": s_line.confidence,
                        "fusion_confidence": conf,
                        "primary_engine": primary_name,
                        "secondary_engine": secondary_name,
                    },
                )
            )
        else:
            status = "primary_only"
            conf = _fuse_confidence(status, p_line.confidence, None)
            fused.append(
                OcrLine.create(
                    text=p_line.text,
                    confidence=conf,
                    bounding_box=p_line.bounding_box,
                    words=list(p_line.words),
                    metadata={
                        "match_status": status,
                        "confidence_primary": p_line.confidence,
                        "fusion_confidence": conf,
                        "primary_engine": primary_name,
                    },
                )
            )

    for s_idx, s_line in enumerate(secondary_lines):
        if s_idx in used:
            continue
        status = "secondary_only"
        conf = _fuse_confidence(status, None, s_line.confidence)
        fused.append(
            OcrLine.create(
                text=s_line.text,
                confidence=conf,
                bounding_box=s_line.bounding_box,
                words=list(s_line.words),
                metadata={
                    "match_status": status,
                    "confidence_secondary": s_line.confidence,
                    "fusion_confidence": conf,
                    "secondary_engine": secondary_name,
                },
            )
        )

    return sorted(fused, key=lambda ln: (ln.bounding_box.y, ln.bounding_box.x))


def _rebuild_block(lines: list[OcrLine]) -> OcrBlock:
    xs = [ln.bounding_box.x for ln in lines]
    ys = [ln.bounding_box.y for ln in lines]
    x2s = [ln.bounding_box.x2 for ln in lines]
    y2s = [ln.bounding_box.y2 for ln in lines]
    bb = BoundingBox.create(
        x=min(xs),
        y=min(ys),
        width=max(x2s) - min(xs),
        height=max(y2s) - min(ys),
    )
    conf = round(sum(ln.confidence for ln in lines) / len(lines), 4)
    text = "\n".join(ln.reconstructed_text for ln in lines)
    return OcrBlock.create(
        text=text,
        confidence=conf,
        bounding_box=bb,
        block_type=OcrBlockType.PARAGRAPH,
        lines=lines,
        metadata={"source": "fusion"},
    )


def _collect_lines(page: OcrPage) -> list[OcrLine]:
    return [line for block in page.blocks for line in block.lines]


def _fuse_pages(
    primary_pages: list[OcrPage],
    secondary_pages: list[OcrPage],
    primary_name: str,
    secondary_name: str,
) -> list[OcrPage]:
    secondary_map: dict[int, OcrPage] = {p.page_number: p for p in secondary_pages}
    primary_map: dict[int, OcrPage] = {p.page_number: p for p in primary_pages}

    all_page_numbers = sorted(set(primary_map.keys()) | set(secondary_map.keys()))

    fused_pages: list[OcrPage] = []

    for page_num in all_page_numbers:
        p_page = primary_map.get(page_num)
        s_page = secondary_map.get(page_num)

        if p_page is not None and s_page is not None:
            fused_lines = _fuse_lines(
                _collect_lines(p_page),
                _collect_lines(s_page),
                primary_name,
                secondary_name,
            )
            if not fused_lines:
                continue
            fused_pages.append(
                OcrPage.create(
                    page_number=page_num,
                    width=max(p_page.width, s_page.width),
                    height=max(p_page.height, s_page.height),
                    blocks=[_rebuild_block(fused_lines)],
                    metadata={
                        "fusion_page_status": "both_engines",
                        "primary_engine": primary_name,
                        "secondary_engine": secondary_name,
                        "tables_fused": False,
                    },
                )
            )

        elif p_page is not None:
            lines = _collect_lines(p_page)
            if not lines:
                continue
            engine_only_lines = [
                OcrLine.create(
                    text=ln.text,
                    confidence=ln.confidence,
                    bounding_box=ln.bounding_box,
                    words=list(ln.words),
                    metadata={
                        "match_status": "primary_only",
                        "confidence_primary": ln.confidence,
                        "fusion_confidence": ln.confidence,
                        "primary_engine": primary_name,
                    },
                )
                for ln in lines
            ]
            fused_pages.append(
                OcrPage.create(
                    page_number=page_num,
                    width=p_page.width,
                    height=p_page.height,
                    blocks=[_rebuild_block(engine_only_lines)],
                    metadata={
                        "fusion_page_status": "engine_only",
                        "engine_only": primary_name,
                        "tables_fused": False,
                    },
                )
            )

        else:
            assert s_page is not None
            lines = _collect_lines(s_page)
            if not lines:
                continue
            engine_only_lines = [
                OcrLine.create(
                    text=ln.text,
                    confidence=ln.confidence,
                    bounding_box=ln.bounding_box,
                    words=list(ln.words),
                    metadata={
                        "match_status": "secondary_only",
                        "confidence_secondary": ln.confidence,
                        "fusion_confidence": ln.confidence,
                        "secondary_engine": secondary_name,
                    },
                )
                for ln in lines
            ]
            fused_pages.append(
                OcrPage.create(
                    page_number=page_num,
                    width=s_page.width,
                    height=s_page.height,
                    blocks=[_rebuild_block(engine_only_lines)],
                    metadata={
                        "fusion_page_status": "engine_only",
                        "engine_only": secondary_name,
                        "tables_fused": False,
                    },
                )
            )

    return fused_pages


class FusionOcrEngine(OcrEngine):

    def __init__(
        self,
        primary: OcrEngine,
        secondary: OcrEngine,
    ) -> None:
        require(isinstance(primary, OcrEngine), "primary must implement OcrEngine")
        require(isinstance(secondary, OcrEngine), "secondary must implement OcrEngine")
        self._primary = primary
        self._secondary = secondary

    @property
    def engine_name(self) -> str:
        return _ENGINE_NAME

    @property
    def engine_version(self) -> str | None:
        return None

    def process(self, request: OcrRequest) -> OcrResult:
        primary_result = self._primary.process(request)
        secondary_result = self._secondary.process(request)

        fused_pages = _fuse_pages(
            primary_pages=list(primary_result.pages),
            secondary_pages=list(secondary_result.pages),
            primary_name=self._primary.engine_name,
            secondary_name=self._secondary.engine_name,
        )

        if not fused_pages:
            raise OcrProcessingError(
                "Fusion produced no pages.",
                details={"source_id": request.source_id},
            )

        return OcrResult.create(
            source_id=request.source_id,
            pages=fused_pages,
            metadata={
                "engine": _ENGINE_NAME,
                "primary_engine": self._primary.engine_name,
                "secondary_engine": self._secondary.engine_name,
                "primary_pages": len(primary_result.pages),
                "secondary_pages": len(secondary_result.pages),
                "fused_pages": len(fused_pages),
                "tables_supported": False,
            },
        )

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def create_pdf_overlay(
    source_pdf_path: str,
    output_pdf_path: str,
    fields: list[dict[str, Any]],
) -> str:
    source_path = Path(source_pdf_path)
    output_path = Path(output_pdf_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(source_path))
    writer = PdfWriter()

    pages_overlays: dict[int, list[dict[str, Any]]] = {}

    for field in fields:
        value = str(field.get("value") or "").strip()
        if not value:
            continue

        try:
            page_index = int(field.get("page", 1)) - 1
        except Exception:
            page_index = 0

        if page_index < 0:
            page_index = 0

        pages_overlays.setdefault(page_index, []).append(field)

    for index, page in enumerate(reader.pages):
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        packet = BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))

        for field in pages_overlays.get(index, []):
            value = str(field.get("value") or "").strip()

            try:
                x = float(field.get("x", 0))
                y = float(field.get("y", 0))
                font_size = int(field.get("font_size", 9))
            except Exception:
                x = 0
                y = 0
                font_size = 9

            c.setFont("Helvetica", font_size)
            c.drawString(x, page_height - y, value)

        c.save()
        packet.seek(0)

        overlay_reader = PdfReader(packet)
        overlay_page = overlay_reader.pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    with output_path.open("wb") as f:
        writer.write(f)

    return str(output_path)

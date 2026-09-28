from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from docx import Document
from openpyxl import load_workbook


# ---------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------

def _clean_text(text: str) -> str:
    """Normalize extracted text without destroying useful structure."""
    if not text:
        return ""

    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive spaces while preserving line structure.
    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        lines.append(line)

    # Remove excessive blank lines.
    output = []
    previous_blank = False

    for line in lines:
        blank = not line

        if blank and previous_blank:
            continue

        output.append(line)
        previous_blank = blank

    return "\n".join(output).strip()


def _read_text_file(path: Path) -> str:
    """Read text-like files with safe fallback encodings."""
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding, errors="ignore")
        except Exception:
            continue

    return ""


# ---------------------------------------------------------
# PDF
# ---------------------------------------------------------

def _extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))

    pages = []

    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""

            if text.strip():
                pages.append(
                    f"[PDF Page {index}]\n{text}"
                )
            else:
                pages.append(
                    f"[PDF Page {index}]\n[No text extracted from this page]"
                )

        except Exception as exc:
            pages.append(
                f"[PDF Page {index}]\n"
                f"[Extraction failed: {exc}]"
            )

    return _clean_text("\n\n".join(pages))


# ---------------------------------------------------------
# DOCX
# ---------------------------------------------------------

def _extract_docx(path: Path) -> str:
    document = Document(str(path))

    sections = []

    # Paragraphs
    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    if paragraphs:
        sections.append(
            "[DOCUMENT TEXT]\n" +
            "\n".join(paragraphs)
        )

    # Tables
    for table_index, table in enumerate(document.tables, start=1):
        rows = []

        for row in table.rows:
            values = []

            for cell in row.cells:
                values.append(cell.text.strip())

            rows.append(" | ".join(values))

        if rows:
            sections.append(
                f"[TABLE {table_index}]\n" +
                "\n".join(rows)
            )

    return _clean_text("\n\n".join(sections))


# ---------------------------------------------------------
# XLSX / XLSM
# ---------------------------------------------------------

def _extract_xlsx(path: Path) -> str:
    workbook = load_workbook(
        str(path),
        read_only=True,
        data_only=True
    )

    sections = []

    for worksheet in workbook.worksheets:
        rows = [
            f"[EXCEL SHEET: {worksheet.title}]"
        ]

        for row in worksheet.iter_rows(values_only=True):
            values = []

            for value in row:
                if value is None:
                    values.append("")
                else:
                    values.append(str(value))

            # Skip completely empty rows.
            if any(value.strip() for value in values):
                rows.append(" | ".join(values))

        sections.append("\n".join(rows))

    return _clean_text("\n\n".join(sections))


# ---------------------------------------------------------
# CSV
# ---------------------------------------------------------

def _extract_csv(path: Path) -> str:
    sections = []

    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(
                path,
                "r",
                encoding=encoding,
                errors="ignore",
                newline=""
            ) as file:
                reader = csv.reader(file)

                for row in reader:
                    sections.append(
                        " | ".join(
                            str(value).strip()
                            for value in row
                        )
                    )

            break

        except Exception:
            sections = []

    return _clean_text("\n".join(sections))


# ---------------------------------------------------------
# JSON
# ---------------------------------------------------------

def _extract_json(path: Path) -> str:
    raw = _read_text_file(path)

    if not raw:
        return ""

    try:
        data: Any = json.loads(raw)

        return _clean_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False
            )
        )

    except Exception:
        # Still return the original content if JSON is malformed.
        return _clean_text(raw)


# ---------------------------------------------------------
# XML
# ---------------------------------------------------------

def _extract_xml(path: Path) -> str:
    raw = _read_text_file(path)

    if not raw:
        return ""

    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(raw)

        values = []

        for element in root.iter():
            if element.text and element.text.strip():
                values.append(element.text.strip())

        return _clean_text("\n".join(values))

    except Exception:
        # If XML parsing fails, preserve the raw content.
        return _clean_text(raw)


# ---------------------------------------------------------
# HTML
# ---------------------------------------------------------

def _extract_html(path: Path) -> str:
    raw = _read_text_file(path)

    if not raw:
        return ""

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw, "html.parser")

        # Remove non-content elements.
        for element in soup(
            ["script", "style", "noscript"]
        ):
            element.decompose()

        return _clean_text(
            soup.get_text("\n")
        )

    except Exception:
        # Basic fallback if BeautifulSoup is unavailable.
        text = re.sub(
            r"<[^>]+>",
            " ",
            raw
        )

        return _clean_text(text)


# ---------------------------------------------------------
# RTF
# ---------------------------------------------------------

def _extract_rtf(path: Path) -> str:
    raw = _read_text_file(path)

    if not raw:
        return ""

    try:
        from striprtf.striprtf import rtf_to_text

        return _clean_text(
            rtf_to_text(raw)
        )

    except Exception:
        # Basic fallback.
        text = re.sub(
            r"\\[a-zA-Z]+-?\d* ?",
            " ",
            raw
        )

        text = text.replace("{", "")
        text = text.replace("}", "")

        return _clean_text(text)


# ---------------------------------------------------------
# POWERPOINT
# ---------------------------------------------------------

def _extract_pptx(path: Path) -> str:
    try:
        from pptx import Presentation

        presentation = Presentation(str(path))

        slides = []

        for slide_number, slide in enumerate(
            presentation.slides,
            start=1
        ):
            slide_text = []

            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text = shape.text.strip()

                    if text:
                        slide_text.append(text)

            if slide_text:
                slides.append(
                    f"[SLIDE {slide_number}]\n" +
                    "\n".join(slide_text)
                )

        return _clean_text(
            "\n\n".join(slides)
        )

    except Exception as exc:
        return _clean_text(
            f"[PPTX extraction failed: {exc}]"
        )


# ---------------------------------------------------------
# OLD .XLS
# ---------------------------------------------------------

def _extract_xls(path: Path) -> str:
    """
    Legacy Excel .xls support.

    xlrd is optional. If it is installed, extract all sheets.
    Otherwise return a clear unsupported message.
    """

    try:
        import xlrd
    except ImportError:
        return (
            "[XLS FILE]\n"
            "[Legacy .xls extraction requires the xlrd package]"
        )

    try:
        workbook = xlrd.open_workbook(
            str(path),
            on_demand=True
        )

        sections = []

        for sheet in workbook.sheets():
            rows = [
                f"[EXCEL SHEET: {sheet.name}]"
            ]

            for row_index in range(sheet.nrows):
                values = []

                for col_index in range(sheet.ncols):
                    value = sheet.cell_value(
                        row_index,
                        col_index
                    )

                    values.append(str(value))

                if any(
                    value.strip()
                    for value in values
                ):
                    rows.append(
                        " | ".join(values)
                    )

            sections.append(
                "\n".join(rows)
            )

        return _clean_text(
            "\n\n".join(sections)
        )

    except Exception as exc:
        return (
            "[XLS FILE]\n"
            f"[Extraction failed: {exc}]"
        )


# ---------------------------------------------------------
# IMAGE OCR
# ---------------------------------------------------------

def _extract_image(path: Path) -> str:
    """
    OCR for procurement images such as:
    - scanned quotations
    - screenshots
    - invoices
    - photographs of documents
    """

    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return (
            "[IMAGE FILE]\n"
            "[OCR dependencies are not installed]"
        )

    try:
        image = Image.open(path)

        text = pytesseract.image_to_string(
            image
        )

        if not text.strip():
            return (
                "[IMAGE FILE]\n"
                "[OCR completed but no readable text was detected]"
            )

        return _clean_text(
            "[IMAGE OCR]\n" + text
        )

    except Exception as exc:
        return (
            "[IMAGE FILE]\n"
            f"[OCR extraction failed: {exc}]"
        )


# ---------------------------------------------------------
# MAIN EXTRACTION FUNCTION
# ---------------------------------------------------------

def extract_file(path: str) -> str:
    """
    Extract readable content from a procurement attachment.

    Supported:
        PDF
        DOCX
        XLSX
        XLSM
        XLS
        CSV
        TXT
        MD
        JSON
        XML
        HTML
        RTF
        PPTX
        PNG/JPG/JPEG/TIFF/BMP/WEBP

    Unsupported binary formats are reported instead of
    causing the application to crash.
    """

    file_path = Path(path)

    if not file_path.exists():
        return (
            "[ATTACHMENT ERROR]\n"
            f"File does not exist: {file_path}"
        )

    if not file_path.is_file():
        return (
            "[ATTACHMENT ERROR]\n"
            f"Path is not a file: {file_path}"
        )

    extension = file_path.suffix.lower()

    try:

        if extension == ".pdf":
            return _extract_pdf(file_path)

        if extension == ".docx":
            return _extract_docx(file_path)

        if extension in {".xlsx", ".xlsm"}:
            return _extract_xlsx(file_path)

        if extension == ".xls":
            return _extract_xls(file_path)

        if extension == ".csv":
            return _extract_csv(file_path)

        if extension in {".txt", ".md"}:
            return _clean_text(
                _read_text_file(file_path)
            )

        if extension == ".json":
            return _extract_json(file_path)

        if extension == ".xml":
            return _extract_xml(file_path)

        if extension in {".html", ".htm"}:
            return _extract_html(file_path)

        if extension == ".rtf":
            return _extract_rtf(file_path)

        if extension == ".pptx":
            return _extract_pptx(file_path)

        if extension in {
            ".png",
            ".jpg",
            ".jpeg",
            ".tif",
            ".tiff",
            ".bmp",
            ".webp"
        }:
            return _extract_image(file_path)

        return (
            "[UNSUPPORTED ATTACHMENT FORMAT]\n"
            f"Filename: {file_path.name}\n"
            f"Extension: {extension or '[none]'}\n"
            "The attachment was received but its contents "
            "could not be automatically extracted."
        )

    except Exception as exc:
        return (
            "[ATTACHMENT EXTRACTION ERROR]\n"
            f"Filename: {file_path.name}\n"
            f"Extension: {extension or '[none]'}\n"
            f"Error: {exc}"
        )
"""Raw text extraction from uploaded documents (PDF, DOCX, plain text) —
no interpretation happens here, just getting readable text out of the
file. Structured field extraction (section 6) happens in extract.py,
downstream of this."""

from __future__ import annotations

import io


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    if lower.endswith(".docx"):
        return _extract_docx(file_bytes)
    if lower.endswith((".txt", ".md")):
        return file_bytes.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported file type for extraction: {filename}")


def _extract_pdf(file_bytes: bytes) -> str:
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _extract_docx(file_bytes: bytes) -> str:
    import docx

    document = docx.Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in document.paragraphs)
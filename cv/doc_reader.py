# cv/doc_reader.py
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
import pdfplumber
from ai import constants

W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _clamp(text: str) -> str:
    text = (text or "").strip()
    if len(text) > constants.MAX_DOC_CHARS:
        return text[: constants.MAX_DOC_CHARS]
    return text


def _read_docx_all_text(docx_path: Path) -> str:
    parts = []

    with zipfile.ZipFile(docx_path, "r") as z:
        # read main doc + all headers/footers if present
        xml_files = ["word/document.xml"]
        xml_files += [n for n in z.namelist() if n.startswith("word/header") and n.endswith(".xml")]
        xml_files += [n for n in z.namelist() if n.startswith("word/footer") and n.endswith(".xml")]

        for name in xml_files:
            try:
                xml_bytes = z.read(name)
            except KeyError:
                continue

            root = ET.fromstring(xml_bytes)

            # grab all text nodes; this includes tables + textboxes because they still use w:t
            texts = [t.text for t in root.findall(".//w:t", W_NS) if t.text]
            if texts:
                parts.append(" ".join(texts))

    return _clamp("\n\n".join(parts))


def read_document_text(document_path: str) -> str:
    p = Path(document_path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")

    ext = p.suffix.lower()
    if ext not in constants.ALLOWED_EXTS:
        raise ValueError(f"Unsupported file type: {ext}. Allowed: {sorted(constants.ALLOWED_EXTS)}")

    if ext == ".txt":
        return _clamp(p.read_text(encoding="utf-8", errors="ignore"))

    if ext == ".docx":
        return _read_docx_all_text(p)

    # pdf
    text_parts = []
    with pdfplumber.open(str(p)) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            if t.strip():
                text_parts.append(t)
    return _clamp("\n\n".join(text_parts))

"""OCR preprocessing for scanned PDFs via ocrmypdf."""

import logging
import os
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class OCRError(RuntimeError):
    """Raised when OCR preprocessing fails."""


# Preferred OCR languages — auto-detect picks whatever is installed.
# Order matters: earlier languages are listed first in the resulting string,
# which Tesseract treats as a tie-breaker when multiple match.
_PREFERRED_OCR_LANGS = ("eng", "pol", "deu", "fra", "spa", "ita", "por", "nld")


def list_installed_languages() -> set[str]:
    """Return Tesseract language packs available on this system.

    Empty set if tesseract isn't on PATH.
    """
    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True, text=True, check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set()
    # Output: "List of available languages (3):\neng\nosd\n..."
    return {line.strip() for line in result.stdout.splitlines() if line.strip() and " " not in line}


def detect_default_language() -> str:
    """Build a multi-language OCR string from installed Tesseract packs.

    Returns 'eng' alone when only English is installed (or detection fails).
    Users who need Chinese/Japanese/etc. should pass --ocr-language explicitly.
    """
    available = list_installed_languages()
    if not available:
        return "eng"
    matched = [lang for lang in _PREFERRED_OCR_LANGS if lang in available]
    return "+".join(matched) if matched else "eng"


def ocr_preprocess(pdf_path: str, language: str = "auto") -> str:
    """Add an OCR text layer to a PDF and return the path to the new file.

    Uses ocrmypdf, which wraps Tesseract. The output file is written to a
    system tempdir; the caller is responsible for cleaning it up.

    Args:
        pdf_path: Input PDF (typically scanned, no embedded text layer).
        language: Tesseract language code(s), e.g. "eng", "pol", "eng+pol".

    Raises:
        OCRError: ocrmypdf binary missing or the OCR run failed.
        FileNotFoundError: input PDF does not exist.
    """
    src = Path(pdf_path)
    if not src.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if language == "auto":
        language = detect_default_language()
        logger.info("OCR language auto-detected: %s", language)

    fd, out_path = tempfile.mkstemp(suffix=".pdf", prefix="twinktalks_ocr_")
    os.close(fd)

    cmd = [
        "ocrmypdf",
        "--language", language,
        "--skip-text",  # leave already-text pages alone (mixed PDFs)
        "--quiet",
        str(src),
        out_path,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError as e:
        Path(out_path).unlink(missing_ok=True)
        raise OCRError(
            "ocrmypdf is not installed. Install with:\n"
            "  brew install tesseract ghostscript qpdf\n"
            "  pip install ocrmypdf"
        ) from e
    except subprocess.CalledProcessError as e:
        Path(out_path).unlink(missing_ok=True)
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        raise OCRError(f"OCR failed: {stderr.strip() or e}") from e

    logger.info("OCR'd %s -> %s (language=%s)", src.name, out_path, language)
    return out_path

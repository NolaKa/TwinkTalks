"""Tests for OCR preprocessing — subprocess is mocked, real ocrmypdf not required."""

import subprocess
from unittest.mock import patch

import pytest

from twinktalks.ocr import OCRError, ocr_preprocess


class TestOCRPreprocess:
    def test_missing_input_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ocr_preprocess(str(tmp_path / "missing.pdf"))

    def test_invokes_ocrmypdf_with_expected_args(self, tmp_path):
        pdf = tmp_path / "scan.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%fake\n")

        with patch("twinktalks.ocr.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, b"", b"")
            out_path = ocr_preprocess(str(pdf), language="eng+pol")

        assert run.call_count == 1
        cmd = run.call_args[0][0]
        assert cmd[0] == "ocrmypdf"
        assert "--language" in cmd
        assert cmd[cmd.index("--language") + 1] == "eng+pol"
        assert "--skip-text" in cmd
        # Input is the original PDF; output path follows it
        assert cmd[-2] == str(pdf)
        assert cmd[-1] == out_path
        assert out_path.endswith(".pdf")

    def test_missing_ocrmypdf_binary_raises_with_install_hint(self, tmp_path):
        pdf = tmp_path / "scan.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        with patch("twinktalks.ocr.subprocess.run", side_effect=FileNotFoundError("no binary")):
            with pytest.raises(OCRError, match="ocrmypdf is not installed"):
                ocr_preprocess(str(pdf))

    def test_subprocess_failure_propagates_as_ocrerror(self, tmp_path):
        pdf = tmp_path / "scan.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        err = subprocess.CalledProcessError(returncode=2, cmd=["ocrmypdf"], stderr=b"bad scan")
        with patch("twinktalks.ocr.subprocess.run", side_effect=err):
            with pytest.raises(OCRError, match="bad scan"):
                ocr_preprocess(str(pdf))


class TestPdfExtractorOCRFlag:
    def test_ocr_kwarg_calls_preprocess(self, tmp_path):
        """When extract_text receives ocr=True, ocr_preprocess is invoked."""
        from twinktalks import pdf_extractor
        pdf = tmp_path / "scan.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        called = {}

        def fake_preprocess(path, language="eng"):
            called["path"] = path
            called["language"] = language
            return str(pdf)  # reuse path so cleanup is safe

        with patch("twinktalks.ocr.ocr_preprocess", side_effect=fake_preprocess):
            with patch.object(
                pdf_extractor, "_extract_with_pdfplumber",
                return_value="Recovered text content from OCR. " * 5,
            ):
                text = pdf_extractor.extract_text(
                    str(pdf), ocr=True, ocr_language="eng+pol",
                )

        assert called["path"] == str(pdf)
        assert called["language"] == "eng+pol"
        assert "Recovered text content" in text

    def test_no_ocr_does_not_invoke_preprocess(self, tmp_path):
        from twinktalks import pdf_extractor
        pdf = tmp_path / "real.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        with patch("twinktalks.ocr.ocr_preprocess") as mock:
            with patch.object(
                pdf_extractor, "_extract_with_pdfplumber",
                return_value="Real text content already in this PDF. " * 5,
            ):
                pdf_extractor.extract_text(str(pdf))
        mock.assert_not_called()

    def test_ocr_hint_in_error_when_extraction_yields_nothing(self, tmp_path):
        """When the PDF is empty AND ocr=False, the error should suggest --ocr."""
        from twinktalks.pdf_extractor import extract_text, ExtractionError
        pdf = tmp_path / "empty.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        from twinktalks import pdf_extractor
        with patch.object(pdf_extractor, "_extract_with_pdfplumber", return_value=""):
            with patch.object(pdf_extractor, "_extract_with_pymupdf", return_value=""):
                with pytest.raises(ExtractionError, match="--ocr"):
                    extract_text(str(pdf))

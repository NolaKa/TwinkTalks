"""Tests for language detection."""

from twinktalks.language_detect import detect_language, resolve_language, DEFAULT_LANGUAGE


class TestDetectLanguage:
    def test_english(self):
        assert detect_language(
            "The quick brown fox jumps over the lazy dog. "
            "This is a sample of clearly English text long enough for detection."
        ) == "English"

    def test_german(self):
        # Long enough sample for detector reliability
        text = (
            "Der schnelle braune Fuchs springt über den faulen Hund. "
            "Dies ist ein Beispiel für deutschen Text mit ausreichender Länge."
        )
        assert detect_language(text) == "German"

    def test_french(self):
        text = (
            "Le rapide renard brun saute par-dessus le chien paresseux. "
            "Ceci est un exemple de texte français suffisamment long."
        )
        assert detect_language(text) == "French"

    def test_empty_returns_default(self):
        assert detect_language("") == DEFAULT_LANGUAGE
        assert detect_language("   \n\n  ") == DEFAULT_LANGUAGE

    def test_unmapped_language_falls_back_to_default(self):
        # Welsh isn't in our Qwen3-TTS language list
        text = "Mae'r cadno cyflym brown yn neidio dros y ci diog hwn yn Gymraeg."
        assert detect_language(text) == DEFAULT_LANGUAGE


class TestResolveLanguage:
    def test_auto_triggers_detection(self):
        text = "Le rapide renard brun saute par-dessus le chien paresseux."
        assert resolve_language("Auto", text) == "French"

    def test_auto_case_insensitive(self):
        text = "Der schnelle braune Fuchs."
        # Even with mixed casing
        for variant in ("auto", "AUTO", "Auto"):
            assert resolve_language(variant, text) in {"German", "English"}

    def test_explicit_language_passes_through(self):
        # Even if the text is German, we honor the user's pick.
        text = "Der schnelle braune Fuchs."
        assert resolve_language("Japanese", text) == "Japanese"

    def test_empty_request_passes_through(self):
        assert resolve_language("English", "") == "English"

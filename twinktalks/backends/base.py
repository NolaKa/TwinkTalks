"""TTSBackend abstract base — every concrete model lives behind this interface."""

from abc import ABC, abstractmethod

import numpy as np


class SynthesisError(RuntimeError):
    """Raised when a backend fails to render audio for a single chunk."""


class ModelDownloadError(RuntimeError):
    """Raised when model weights can't be obtained from any source."""


class TTSBackend(ABC):
    """Pluggable TTS engine.

    Concrete subclasses encapsulate model loading and a single-chunk
    synthesis call. Higher-level orchestration (chunking, retries,
    streaming concatenation, session resume) lives in TTSEngine and
    is backend-agnostic.
    """

    name: str = ""
    voices: list[str] = []
    default_voice: str = ""
    supported_languages: list[str] = []
    default_language: str = ""
    supports_instruct: bool = False
    sample_rate: int = 24000

    # Concrete subclasses set this once load_model() succeeds.
    model = None

    @abstractmethod
    def load_model(self) -> None:
        """Materialize model weights — may download from network on first run."""

    @abstractmethod
    def synthesize_one(
        self,
        text: str,
        *,
        voice: str,
        speed: float = 1.0,
        instruct: str = "",
        language: str = "",
    ) -> tuple[np.ndarray, int]:
        """Generate audio for one text chunk.

        Returns (waveform float32, sample_rate Hz).
        """

    @classmethod
    @abstractmethod
    def is_cached(cls) -> bool:
        """Return True if the next load_model() call would NOT have to fetch
        weights from the network. Used by the API to tell the UI whether the
        first generate will hang on a multi-GB download."""

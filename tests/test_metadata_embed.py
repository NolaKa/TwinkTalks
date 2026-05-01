"""Tests for embedding BookMetadata into MP3 and M4B files."""

import numpy as np
import pytest

from twinktalks.audio_utils import save_audio, embed_metadata
from twinktalks.book_metadata import BookMetadata


@pytest.fixture
def waveform():
    return (np.random.randn(24000).astype(np.float32) * 0.3)


@pytest.fixture
def png_cover():
    """A minimal valid PNG (1x1 transparent pixel)."""
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\rIDATx\x9cc\xfa\xcf\x00\x00\x00\x02\x00\x01\xe5'\xde\xfc"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


class TestEmbedMP3:
    def test_title_and_author(self, tmp_path, waveform):
        path = tmp_path / "track.mp3"
        save_audio(waveform, str(path), 24000)
        embed_metadata(str(path), BookMetadata(title="My Book", author="Jane Doe"))

        from mutagen.id3 import ID3
        tags = ID3(str(path))
        assert tags["TIT2"].text == ["My Book"]
        assert tags["TPE1"].text == ["Jane Doe"]
        assert tags["TALB"].text == ["My Book"]

    def test_cover_art(self, tmp_path, waveform, png_cover):
        path = tmp_path / "track.mp3"
        save_audio(waveform, str(path), 24000)
        embed_metadata(str(path), BookMetadata(
            title="With Cover",
            cover_image=png_cover,
            cover_mime="image/png",
        ))

        from mutagen.id3 import ID3
        tags = ID3(str(path))
        apic_keys = [k for k in tags.keys() if k.startswith("APIC")]
        assert len(apic_keys) == 1
        apic = tags[apic_keys[0]]
        assert apic.mime == "image/png"
        assert apic.type == 3  # front cover

    def test_partial_metadata_only_writes_what_exists(self, tmp_path, waveform):
        path = tmp_path / "track.mp3"
        save_audio(waveform, str(path), 24000)
        embed_metadata(str(path), BookMetadata(title="Just Title"))

        from mutagen.id3 import ID3
        tags = ID3(str(path))
        assert tags["TIT2"].text == ["Just Title"]
        assert "TPE1" not in tags  # no author


class TestEmbedM4B:
    def test_title_author_cover(self, tmp_path, waveform, png_cover):
        path = tmp_path / "book.m4b"
        save_audio(waveform, str(path), 24000)
        embed_metadata(str(path), BookMetadata(
            title="Audiobook Title",
            author="A. Author",
            cover_image=png_cover,
            cover_mime="image/png",
        ))

        from mutagen.mp4 import MP4
        audio = MP4(str(path))
        assert audio.tags["\xa9nam"] == ["Audiobook Title"]
        assert audio.tags["\xa9ART"] == ["A. Author"]
        assert audio.tags["\xa9alb"] == ["Audiobook Title"]
        assert len(audio.tags["covr"]) == 1


class TestEmbedRouting:
    def test_wav_is_noop(self, tmp_path, waveform):
        path = tmp_path / "track.wav"
        save_audio(waveform, str(path), 24000)
        # Should not raise
        embed_metadata(str(path), BookMetadata(title="WAV Title"))

    def test_unsupported_extension_raises(self, tmp_path):
        path = tmp_path / "fake.ogg"
        path.write_bytes(b"not really audio")
        with pytest.raises(ValueError, match="Cannot embed metadata"):
            embed_metadata(str(path), BookMetadata(title="x"))

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match="does not exist"):
            embed_metadata(str(tmp_path / "ghost.mp3"), BookMetadata())

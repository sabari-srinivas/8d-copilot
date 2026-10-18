"""What a judge's laptop and a browser's MediaRecorder actually hand us."""
import pytest

from agent.tools.media_types import (
    base_type,
    image_needs_reencoding,
    normalize_audio_mime,
)


class TestBaseType:
    def test_strips_the_codecs_parameter_a_mediarecorder_always_adds(self):
        # The single most common real value, and the one Gemini rejects verbatim.
        assert base_type("audio/webm;codecs=opus") == "audio/webm"

    def test_is_case_and_whitespace_insensitive(self):
        assert base_type("  IMAGE/JPEG ") == "image/jpeg"

    def test_none_and_empty_degrade_to_empty_rather_than_raising(self):
        assert base_type(None) == ""
        assert base_type("") == ""


class TestNormalizeAudioMime:
    def test_chrome_and_firefox_recordings_pass_through(self):
        assert normalize_audio_mime("audio/webm;codecs=opus") == "audio/webm"

    def test_safari_records_audio_mp4_which_gemini_only_knows_as_m4a(self):
        """Safari's MediaRecorder emits AAC-in-MP4 labelled `audio/mp4`, which is not in
        Gemini's list; `audio/m4a` is the same container under the name it does know. If
        this mapping is lost, live recording silently fails on every iPhone and Mac."""
        assert normalize_audio_mime("audio/mp4") == "audio/m4a"

    def test_a_chromium_audio_only_stream_mislabelled_as_video_webm(self):
        assert normalize_audio_mime("video/webm;codecs=opus") == "audio/webm"

    @pytest.mark.parametrize("supplied,expected", [
        ("audio/x-wav", "audio/wav"),
        ("audio/wave", "audio/wav"),
        ("audio/x-m4a", "audio/m4a"),
        ("audio/mpeg3", "audio/mp3"),
        ("audio/x-flac", "audio/flac"),
    ])
    def test_common_file_picker_spellings_resolve(self, supplied, expected):
        assert normalize_audio_mime(supplied) == expected

    def test_an_already_correct_type_is_returned_unchanged(self):
        assert normalize_audio_mime("audio/ogg") == "audio/ogg"

    def test_an_unreadable_container_raises_naming_the_format(self):
        """Audio cannot be transcoded without a library we do not ship, so this has to
        fail -- but it fails here with the format named, not as an opaque model 400."""
        with pytest.raises(ValueError, match="audio/amr"):
            normalize_audio_mime("audio/amr")

    def test_the_error_lists_what_would_have_worked(self):
        with pytest.raises(ValueError, match="audio/webm"):
            normalize_audio_mime("audio/amr")

    def test_a_missing_content_type_falls_back_instead_of_raising(self):
        """FastAPI's UploadFile.content_type is Optional; a missing value is not the
        caller doing something wrong, so it must not 400."""
        assert normalize_audio_mime(None) == "audio/wav"


class TestImageNeedsReencoding:
    @pytest.mark.parametrize("mime", [
        "image/png", "image/jpeg", "image/webp", "image/heic", "image/heif",
    ])
    def test_the_five_types_gemini_accepts_are_left_alone(self, mime):
        assert image_needs_reencoding(mime) is False

    @pytest.mark.parametrize("mime", [
        "image/gif", "image/bmp", "image/tiff", "image/x-icon", "image/svg+xml",
    ])
    def test_anything_else_a_judge_might_upload_is_converted(self, mime):
        assert image_needs_reencoding(mime) is True

    def test_a_missing_type_is_treated_as_needing_conversion(self):
        assert image_needs_reencoding(None) is True

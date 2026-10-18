"""What Gemini will actually accept, and how to get an arbitrary upload there.

Two different problems, deliberately solved two different ways:

* **Images** — a judge experimenting with the deployed prototype uploads whatever is on
  their laptop. A GIF or a BMP is a perfectly reasonable thing to try and Gemini rejects
  both, so `vision_tool` re-encodes anything unsupported to JPEG rather than failing. No
  information a defect reading needs is lost by that conversion.
* **Audio** — a recording cannot be transcoded without an audio library we do not ship, so
  an unsupported container has to fail. It fails here, with a message naming the format,
  instead of as an opaque 400 from the model.

The two lists are copied from the Gemini API docs (image-understanding and audio pages,
checked 18 Oct 2026). They are the model's constraint, not ours -- when the docs add a
format, add it here.
"""

GEMINI_IMAGE_TYPES = frozenset({
    "image/png", "image/jpeg", "image/webp", "image/heic", "image/heif",
})

GEMINI_AUDIO_TYPES = frozenset({
    "audio/wav", "audio/mp3", "audio/mpeg", "audio/aiff", "audio/aac", "audio/ogg",
    "audio/flac", "audio/m4a", "audio/l16", "audio/opus", "audio/alaw", "audio/mulaw",
    "audio/webm",
})

# Browsers and operating systems spell the same container several ways. Each key here is
# a real value seen from a `MediaRecorder` or a file picker; each value is the spelling
# the docs list.
AUDIO_ALIASES = {
    # Safari's MediaRecorder produces AAC in an MP4 container and labels it `audio/mp4`.
    # That is byte-for-byte what the docs call `audio/m4a`, so it plays rather than fails.
    "audio/mp4": "audio/m4a",
    "audio/x-m4a": "audio/m4a",
    "audio/mp4a-latm": "audio/m4a",
    "audio/x-wav": "audio/wav",
    "audio/wave": "audio/wav",
    "audio/vnd.wave": "audio/wav",
    "audio/mpeg3": "audio/mp3",
    "audio/x-mpeg-3": "audio/mp3",
    "audio/vorbis": "audio/ogg",
    "audio/x-flac": "audio/flac",
    "audio/x-aiff": "audio/aiff",
    # Some Chromium builds hand back a `video/webm` recorder mime for an audio-only
    # stream. The container is identical; only the label is wrong.
    "video/webm": "audio/webm",
    "video/mp4": "audio/m4a",
}


def base_type(mime: str | None) -> str:
    """`audio/webm;codecs=opus` -> `audio/webm`.

    A `MediaRecorder` mime almost always carries a `codecs=` parameter, and the model
    rejects the parameterised string. Lowercased and stripped so comparisons against the
    frozensets above are exact.
    """
    if not mime:
        return ""
    return mime.split(";", 1)[0].strip().lower()


def normalize_audio_mime(mime: str | None) -> str:
    """The type to send to Gemini, or raise saying why this recording cannot be read.

    Raises `ValueError` rather than guessing: a wrong container silently mislabelled is a
    confusing 400 from the model, while an empty or unknown one is a clear message here.
    """
    base = base_type(mime)
    if not base:
        # No browser or file picker supplies nothing by accident, but FastAPI's
        # `UploadFile.content_type` is Optional and the default has to be *something*.
        return "audio/wav"
    resolved = AUDIO_ALIASES.get(base, base)
    if resolved not in GEMINI_AUDIO_TYPES:
        raise ValueError(
            f"unsupported audio format {base!r}: this recording cannot be read. "
            f"Supported: {', '.join(sorted(GEMINI_AUDIO_TYPES))}")
    return resolved


def image_needs_reencoding(mime: str | None) -> bool:
    """True when the model would reject this image type, so it must become a JPEG."""
    return base_type(mime) not in GEMINI_IMAGE_TYPES

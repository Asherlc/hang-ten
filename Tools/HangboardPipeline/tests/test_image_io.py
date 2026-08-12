from __future__ import annotations

from io import BytesIO
import time

import pytest
import requests
from PIL import Image

import hangboard_vectorizer.image_io as image_io
from hangboard_vectorizer.image_io import load_image
from hangboard_vectorizer.models import ConversionError


def test_load_image_applies_exif_orientation(tmp_path):
    source = tmp_path / "rotated.jpg"
    image = Image.new("RGB", (40, 20), "white")
    exif = image.getexif()
    exif[274] = 6
    image.save(source, exif=exif)

    loaded = load_image(str(source))

    assert loaded.rgb.shape == (40, 20, 3)


def test_load_image_rejects_missing_local_path(tmp_path):
    source = tmp_path / "missing.jpg"

    with pytest.raises(ConversionError):
        load_image(str(source))


def test_load_image_rejects_non_image_local_file(tmp_path):
    source = tmp_path / "not-an-image.bin"
    source.write_bytes(b"nope")

    with pytest.raises(ConversionError):
        load_image(str(source))


class FakeResponse:
    def __init__(
        self,
        *,
        content_type: str = "image/png",
        chunks: list[bytes] | None = None,
        error: Exception | None = None,
        iterator_error: Exception | None = None,
        chunk_delay: float = 0.0,
    ) -> None:
        self.headers = {"Content-Type": content_type}
        self.chunks = chunks or []
        self.error = error
        self.iterator_error = iterator_error
        self.chunk_delay = chunk_delay
        self.closed = False

    def raise_for_status(self) -> None:
        if self.error:
            raise self.error

    def iter_content(self, chunk_size: int):
        if self.iterator_error:
            raise self.iterator_error
        for chunk in self.chunks:
            if self.chunk_delay:
                time.sleep(self.chunk_delay)
            yield chunk

    def close(self) -> None:
        self.closed = True


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 3), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def compressed_png_bytes(width: int = 80, height: int = 80) -> bytes:
    buffer = BytesIO()
    Image.new("1", (width, height), 0).save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def test_load_image_downloads_and_decodes_png(monkeypatch):
    monkeypatch.setattr(
        "hangboard_vectorizer.image_io.requests.get",
        lambda *args, **kwargs: FakeResponse(chunks=[png_bytes()]),
    )

    loaded = load_image("https://example.test/hangboard.png")

    assert loaded.source == "https://example.test/hangboard.png"
    assert loaded.rgb.shape == (3, 2, 3)


def test_load_image_rejects_remote_non_image_content_type(monkeypatch):
    monkeypatch.setattr(
        "hangboard_vectorizer.image_io.requests.get",
        lambda *args, **kwargs: FakeResponse(content_type="text/html"),
    )

    with pytest.raises(ConversionError, match="unsupported content type"):
        load_image("https://example.test/not-image")


def test_load_image_rejects_download_larger_than_limit(monkeypatch):
    monkeypatch.setattr(
        "hangboard_vectorizer.image_io.requests.get",
        lambda *args, **kwargs: FakeResponse(chunks=[b"123", b"456"]),
    )

    with pytest.raises(ConversionError, match="download exceeds"):
        load_image("https://example.test/large.png", max_bytes=5)


def test_load_image_checks_chunk_limit_before_extending(monkeypatch):
    response = FakeResponse(chunks=[b"123456"])
    extensions: list[bytes] = []

    class TrackingBytearray(bytearray):
        def extend(self, chunk: bytes) -> None:
            extensions.append(chunk)
            super().extend(chunk)

    monkeypatch.setattr(
        "hangboard_vectorizer.image_io.requests.get", lambda *args, **kwargs: response
    )
    monkeypatch.setattr(image_io, "bytearray", TrackingBytearray, raising=False)

    with pytest.raises(ConversionError, match="download exceeds"):
        load_image("https://example.test/large.png", max_bytes=5)

    assert extensions == []


def test_load_image_closes_remote_response_on_success(monkeypatch):
    response = FakeResponse(chunks=[png_bytes()])
    monkeypatch.setattr(
        "hangboard_vectorizer.image_io.requests.get", lambda *args, **kwargs: response
    )

    load_image("https://example.test/hangboard.png")

    assert response.closed is True


@pytest.mark.parametrize(
    "response, kwargs",
    [
        (FakeResponse(content_type="text/plain"), {}),
        (FakeResponse(chunks=[b"123456"]), {"max_bytes": 5}),
        (FakeResponse(iterator_error=requests.ConnectionError("dropped")), {}),
        (FakeResponse(chunks=[b"not image"]), {}),
        (FakeResponse(error=requests.HTTPError("not found")), {}),
    ],
)
def test_load_image_closes_remote_response_on_failure(monkeypatch, response, kwargs):
    monkeypatch.setattr(
        "hangboard_vectorizer.image_io.requests.get", lambda *args, **kwargs: response
    )

    with pytest.raises(ConversionError):
        load_image("https://example.test/image", **kwargs)

    assert response.closed is True


def test_load_image_wraps_http_errors(monkeypatch):
    monkeypatch.setattr(
        "hangboard_vectorizer.image_io.requests.get",
        lambda *args, **kwargs: FakeResponse(error=requests.HTTPError("not found")),
    )

    with pytest.raises(ConversionError, match="could not download"):
        load_image("https://example.test/missing.png")


def test_load_image_rejects_local_image_over_decoded_pixel_limit(tmp_path):
    source = tmp_path / "compressed.png"
    source.write_bytes(compressed_png_bytes())

    with pytest.raises(ConversionError, match="pixel limit"):
        load_image(str(source), max_pixels=6_399)


def test_load_image_rejects_remote_image_over_decoded_pixel_limit(monkeypatch):
    response = FakeResponse(chunks=[compressed_png_bytes()])
    monkeypatch.setattr(image_io.requests, "get", lambda *args, **kwargs: response)

    with pytest.raises(ConversionError, match="pixel limit"):
        load_image("https://example.test/compressed.png", max_pixels=6_399)

    assert response.closed is True


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("local.png", "could not load image"),
        ("https://example.test/bomb.png", "could not decode image"),
    ],
)
def test_load_image_wraps_pillow_decompression_bomb_errors(
    monkeypatch, source, message
):
    response = FakeResponse(chunks=[png_bytes()])
    monkeypatch.setattr(image_io.requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(
        image_io.Image,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            Image.DecompressionBombError("bomb")
        ),
    )

    with pytest.raises(ConversionError, match=message):
        load_image(source)

    if source.startswith("https"):
        assert response.closed is True


def test_load_image_enforces_total_remote_deadline_while_stream_is_blocked(
    monkeypatch,
):
    response = FakeResponse(chunks=[png_bytes()], chunk_delay=0.30)
    monkeypatch.setattr(image_io.requests, "get", lambda *args, **kwargs: response)

    started = time.monotonic()
    with pytest.raises(ConversionError, match="timed out"):
        load_image("https://example.test/slow.png", timeout=0.05)
    elapsed = time.monotonic() - started

    # The 0.30-second fake chunk must not complete before the deadline returns.
    # Allow CI scheduling/cleanup overhead beyond the 0.05-second deadline.
    assert elapsed < 0.25
    assert response.closed is True


@pytest.mark.parametrize("max_pixels", [0, -1, True, float("inf")])
def test_load_image_rejects_non_positive_or_non_integer_pixel_limits(
    tmp_path, max_pixels
):
    source = tmp_path / "tiny.png"
    source.write_bytes(png_bytes())

    with pytest.raises(ValueError, match="max_pixels"):
        load_image(str(source), max_pixels=max_pixels)

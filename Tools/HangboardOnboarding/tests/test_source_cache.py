from __future__ import annotations

from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

import pytest
from PIL import Image

from hangboard_vectorizer.source_cache import SourceLimits, cache_source


def _png_bytes(size: tuple[int, int] = (700, 512)) -> bytes:
    from io import BytesIO

    stream = BytesIO()
    Image.new("RGB", size, (40, 100, 160)).save(stream, "PNG")
    return stream.getvalue()


@pytest.fixture
def image_server():
    payload = _png_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path.startswith("/redirect"):
                self.send_response(302)
                self.send_header("Location", "/image.png")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join()


def test_local_and_http_sources_cache_exact_bytes_and_pixel_hashes(
    tmp_path: Path, image_server: str
):
    local = tmp_path / "input.png"
    local.write_bytes(_png_bytes())
    local_cached = cache_source(str(local), tmp_path / "local-cache")
    http_cached = cache_source(
        f"{image_server}/image.png",
        tmp_path / "http-cache",
        limits=SourceLimits(allow_private_networks=True),
    )

    assert local_cached.cached_path.read_bytes() == local.read_bytes()
    assert http_cached.cached_path.read_bytes() == local.read_bytes()
    assert (
        local_cached.raw_sha256
        == http_cached.raw_sha256
        == sha256(local.read_bytes()).hexdigest()
    )
    assert local_cached.decoded_rgb_sha256 == http_cached.decoded_rgb_sha256
    assert http_cached.kind == "http"
    assert json.loads(http_cached.evidence_path.read_text())["kind"] == "http"


def test_source_json_strips_url_credentials_query_and_fragment(
    tmp_path: Path, image_server: str
):
    source = cache_source(
        f"{image_server}/redirect?token=secret#fragment",
        tmp_path / "cache",
        limits=SourceLimits(allow_private_networks=True),
    )
    evidence = json.loads(source.evidence_path.read_text())

    assert evidence["sanitizedLocator"] == f"{image_server}/image.png"
    assert "token" not in source.evidence_path.read_text()
    assert "fragment" not in source.evidence_path.read_text()


def test_private_network_sources_are_rejected_before_fetch(tmp_path: Path):
    with pytest.raises(ValueError, match="public addresses"):
        cache_source("http://127.0.0.1/image.png", tmp_path / "cache")
    assert not (tmp_path / "cache").exists()


def test_decoded_pixel_limit_rejects_compressed_image(tmp_path: Path):
    source = tmp_path / "large.png"
    source.write_bytes(_png_bytes((700, 512)))

    with pytest.raises(ValueError, match="maximum decoded pixels"):
        cache_source(
            str(source),
            tmp_path / "cache",
            limits=SourceLimits(maximum_pixels=100),
        )


def test_oversized_empty_animated_and_malformed_sources_publish_nothing(tmp_path: Path):
    oversized = tmp_path / "oversized.bin"
    oversized.write_bytes(b"x" * 100)
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    animated = tmp_path / "animated.gif"
    Image.new("RGB", (700, 512)).save(
        animated, save_all=True, append_images=[Image.new("RGB", (700, 512), "red")]
    )
    malformed = tmp_path / "malformed.bin"
    malformed.write_bytes(b"not an image")

    cases = (
        (oversized, SourceLimits(maximum_bytes=50)),
        (empty, SourceLimits()),
        (animated, SourceLimits()),
        (malformed, SourceLimits()),
    )
    for index, (locator, limits) in enumerate(cases):
        root = tmp_path / f"cache-{index}"
        with pytest.raises(ValueError):
            cache_source(str(locator), root, limits=limits)
        assert not root.exists()


def test_cached_source_never_contains_an_absolute_local_path(tmp_path: Path):
    source_path = tmp_path / "private-photo.png"
    source_path.write_bytes(_png_bytes())
    cached = cache_source(str(source_path), tmp_path / "cache")

    evidence = cached.evidence_path.read_text()
    assert str(source_path) not in evidence
    assert cached.sanitized_locator == source_path.name

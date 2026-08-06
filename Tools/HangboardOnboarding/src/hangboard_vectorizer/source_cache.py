"""Immutable, locally-published source images for product onboarding."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import ipaddress
import json
from pathlib import Path
import shutil
import socket
import tempfile
from typing import Literal
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

import numpy as np
from PIL import Image, ImageOps


@dataclass(frozen=True, slots=True)
class SourceLimits:
    maximum_bytes: int = 50_000_000
    maximum_pixels: int = 80_000_000
    timeout_seconds: float = 20.0
    minimum_long_edge: int = 512
    allow_private_networks: bool = False


@dataclass(frozen=True, slots=True)
class CachedSource:
    cached_path: Path
    evidence_path: Path
    kind: Literal["local", "http", "https"]
    image_format: str
    width: int
    height: int
    raw_sha256: str
    decoded_rgb_sha256: str
    sanitized_locator: str
    locator_sha256: str


_FORMAT_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
_USER_AGENT = "hangboard-vectorizer-source-cache/1.0"


def cache_source(
    locator: str,
    input_root: Path,
    *,
    limits: SourceLimits = SourceLimits(),
) -> CachedSource:
    """Validate and atomically publish an immutable copy of a source image."""
    if input_root.exists():
        raise FileExistsError(f"source cache already exists: {input_root}")
    if (
        limits.maximum_bytes <= 0
        or limits.maximum_pixels <= 0
        or limits.timeout_seconds <= 0
        or limits.minimum_long_edge <= 0
    ):
        raise ValueError("source limits must be positive")

    parsed = urlparse(locator)
    temporary_root: Path | None = None
    try:
        if not parsed.scheme:
            source_path = Path(locator)
            if not source_path.is_file():
                raise ValueError("local source locator must name a regular file")
            raw = _read_local(source_path, limits.maximum_bytes)
            kind: Literal["local", "http", "https"] = "local"
            sanitized_locator = source_path.name
        else:
            raw, final_url = _read_network(locator, limits)
            final = urlparse(final_url)
            if (
                final.scheme.lower() not in {"http", "https"}
                or not final.hostname
                or final.username is not None
                or final.password is not None
            ):
                raise ValueError("redirected source locator must remain HTTP(S)")
            kind = "http" if final.scheme.lower() == "http" else "https"
            sanitized_locator = _sanitize_url(final)

        image_format, rgb = _decode_rgb(raw, limits.maximum_pixels)
        height, width = rgb.shape[:2]
        if max(width, height) < limits.minimum_long_edge:
            raise ValueError("source image is smaller than the minimum long edge")

        extension = _FORMAT_EXTENSIONS.get(image_format)
        if extension is None:
            raise ValueError("source image format must be JPEG, PNG, or WEBP")
        input_root.parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(
            tempfile.mkdtemp(prefix=f".{input_root.name}.tmp-", dir=input_root.parent)
        )
        cached_path = temporary_root / f"source.{extension}"
        evidence_path = temporary_root / "source.json"
        cached_path.write_bytes(raw)
        raw_sha256 = sha256(raw).hexdigest()
        decoded_rgb_sha256 = sha256(rgb.tobytes()).hexdigest()
        evidence = {
            "cachedPath": cached_path.name,
            "decodedRgbSha256": decoded_rgb_sha256,
            "height": height,
            "imageFormat": image_format.lower(),
            "kind": kind,
            "locatorSha256": sha256(locator.encode("utf-8")).hexdigest(),
            "rawSha256": raw_sha256,
            "sanitizedLocator": sanitized_locator,
            "width": width,
        }
        evidence_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary_root.replace(input_root)
        return CachedSource(
            cached_path=input_root / cached_path.name,
            evidence_path=input_root / evidence_path.name,
            kind=kind,
            image_format=image_format.lower(),
            width=width,
            height=height,
            raw_sha256=raw_sha256,
            decoded_rgb_sha256=decoded_rgb_sha256,
            sanitized_locator=sanitized_locator,
            locator_sha256=sha256(locator.encode("utf-8")).hexdigest(),
        )
    except Exception:
        if temporary_root is not None:
            shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def _read_local(source_path: Path, maximum_bytes: int) -> bytes:
    with source_path.open("rb") as stream:
        raw = stream.read(maximum_bytes + 1)
    return _validate_raw(raw, maximum_bytes)


def _read_network(locator: str, limits: SourceLimits) -> tuple[bytes, str]:
    _validate_network_url(locator, allow_private=limits.allow_private_networks)
    request = Request(locator, headers={"User-Agent": _USER_AGENT})
    opener = build_opener(_ValidatedRedirectHandler(limits.allow_private_networks))
    with opener.open(request, timeout=limits.timeout_seconds) as response:  # noqa: S310
        raw = response.read(limits.maximum_bytes + 1)
        final_url = response.geturl()
    return _validate_raw(raw, limits.maximum_bytes), final_url


class _ValidatedRedirectHandler(HTTPRedirectHandler):
    def __init__(self, allow_private: bool) -> None:
        super().__init__()
        self._allow_private = allow_private

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urljoin(req.full_url, newurl)
        _validate_network_url(target, allow_private=self._allow_private)
        return super().redirect_request(req, fp, code, msg, headers, target)


def _validate_network_url(locator: str, *, allow_private: bool) -> None:
    parsed = urlparse(locator)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("network source locator must use HTTP(S)")
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("network source locator must not contain credentials")
    try:
        addresses = {
            ipaddress.ip_address(result[4][0])
            for result in socket.getaddrinfo(
                parsed.hostname,
                parsed.port or (443 if parsed.scheme.lower() == "https" else 80),
            )
        }
    except (OSError, ValueError) as error:
        raise ValueError("network source hostname could not be resolved") from error
    if not addresses or (
        not allow_private and any(not address.is_global for address in addresses)
    ):
        raise ValueError("network source locator must resolve only to public addresses")


def _validate_raw(raw: bytes, maximum_bytes: int) -> bytes:
    if not raw:
        raise ValueError("source content is empty")
    if len(raw) > maximum_bytes:
        raise ValueError("source content exceeds maximum bytes")
    return raw


def _decode_rgb(raw: bytes, maximum_pixels: int) -> tuple[str, np.ndarray]:
    try:
        with Image.open(BytesIO(raw)) as image:
            image_format = image.format
            if (
                getattr(image, "is_animated", False)
                or getattr(image, "n_frames", 1) != 1
            ):
                raise ValueError("animated source images are not supported")
            if image_format is None:
                raise ValueError("source image format is unknown")
            if image.width * image.height > maximum_pixels:
                raise ValueError("source image exceeds maximum decoded pixels")
            rgb = ImageOps.exif_transpose(image).convert("RGB")
            return image_format, np.asarray(rgb, dtype=np.uint8)
    except ValueError:
        raise
    except (OSError, Image.DecompressionBombError) as error:
        raise ValueError("source content is not a decodable image") from error


def _sanitize_url(parsed) -> str:
    host = parsed.hostname
    if host is None:
        raise ValueError("network source locator must include a host")
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunparse((parsed.scheme.lower(), host, parsed.path or "/", "", "", ""))

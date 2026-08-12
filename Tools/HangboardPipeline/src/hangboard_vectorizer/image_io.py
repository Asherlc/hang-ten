from __future__ import annotations

from io import BytesIO
import math
from queue import Empty, Queue
from threading import Event, Lock, Thread
from urllib.parse import urlparse

import numpy as np
import requests
from PIL import Image, ImageOps

from .models import ConversionError, LoadedImage


def load_image(
    source: str,
    *,
    max_bytes: int = 20_000_000,
    max_pixels: int = 40_000_000,
    timeout: float = 10.0,
) -> LoadedImage:
    """Load a local image or a size-bounded HTTP(S) image as RGB pixels."""
    if type(max_pixels) is not int or max_pixels <= 0:
        raise ValueError("max_pixels must be a positive integer")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(timeout)
        or timeout <= 0
    ):
        raise ValueError("timeout must be a finite positive number")
    scheme = urlparse(source).scheme.lower()
    if scheme in {"http", "https"}:
        return _load_remote_image(
            source,
            max_bytes=max_bytes,
            max_pixels=max_pixels,
            timeout=float(timeout),
        )
    if scheme:
        raise ConversionError(f"unsupported source scheme: {scheme}")
    return _load_local_image(source, max_pixels=max_pixels)


def _load_local_image(source: str, *, max_pixels: int) -> LoadedImage:
    try:
        with Image.open(source) as image:
            _enforce_pixel_limit(image, max_pixels)
            return LoadedImage(source=source, rgb=_to_rgb_array(image))
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ConversionError(f"could not load image: {source}") from exc


def _load_remote_image(
    source: str, *, max_bytes: int, max_pixels: int, timeout: float
) -> LoadedImage:
    """Bound the complete blocking HTTP/decode operation by one wall deadline."""
    result_queue: Queue[LoadedImage | Exception] = Queue(maxsize=1)
    response_lock = Lock()
    response_holder: list[requests.Response] = []
    cancelled = Event()

    def run() -> None:
        try:
            result = _download_remote_image(
                source,
                max_bytes=max_bytes,
                max_pixels=max_pixels,
                timeout=timeout,
                response_lock=response_lock,
                response_holder=response_holder,
                cancelled=cancelled,
            )
        except Exception as exc:
            result_queue.put(exc)
        else:
            result_queue.put(result)

    Thread(target=run, name="hangboard-image-download", daemon=True).start()
    try:
        result = result_queue.get(timeout=timeout)
    except Empty as exc:
        cancelled.set()
        with response_lock:
            if response_holder:
                response_holder[0].close()
        raise ConversionError(f"image download timed out: {source}") from exc
    if isinstance(result, Exception):
        raise result
    return result


def _download_remote_image(
    source: str,
    *,
    max_bytes: int,
    max_pixels: int,
    timeout: float,
    response_lock: Lock,
    response_holder: list[requests.Response],
    cancelled: Event,
) -> LoadedImage:
    try:
        response = requests.get(source, stream=True, timeout=timeout)
    except requests.RequestException as exc:
        raise ConversionError(f"could not download image: {source}") from exc

    with response_lock:
        response_holder.append(response)
        already_cancelled = cancelled.is_set()
    if already_cancelled:
        response.close()
        raise ConversionError(f"image download timed out: {source}")

    try:
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ConversionError(f"could not download image: {source}") from exc

        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.split(";", 1)[0].startswith("image/"):
            raise ConversionError(f"unsupported content type: {content_type or 'missing'}")

        data = bytearray()
        try:
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                if len(data) + len(chunk) > max_bytes:
                    raise ConversionError(f"download exceeds {max_bytes} bytes")
                data.extend(chunk)
        except requests.RequestException as exc:
            raise ConversionError(f"could not download image: {source}") from exc

        try:
            with Image.open(BytesIO(data)) as image:
                _enforce_pixel_limit(image, max_pixels)
                return LoadedImage(source=source, rgb=_to_rgb_array(image))
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            raise ConversionError(f"could not decode image: {source}") from exc
    finally:
        response.close()


def _to_rgb_array(image: Image.Image) -> np.ndarray:
    return np.asarray(ImageOps.exif_transpose(image).convert("RGB"))


def _enforce_pixel_limit(image: Image.Image, max_pixels: int) -> None:
    if image.width * image.height > max_pixels:
        raise ConversionError(f"decoded image exceeds {max_pixels} pixel limit")

from __future__ import annotations

import cv2
import numpy as np


def make_hangboard() -> np.ndarray:
    """Return a simple RGB hangboard on a white background."""
    image = np.full((300, 400, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (60, 50), (340, 250), (196, 148, 94), thickness=-1)
    cv2.circle(image, (130, 115), 16, (48, 38, 30), thickness=-1)
    cv2.circle(image, (270, 115), 16, (48, 38, 30), thickness=-1)
    cv2.rectangle(image, (115, 180), (285, 190), (48, 38, 30), thickness=-1)
    return image


def perspective_distort(rgb: np.ndarray) -> np.ndarray:
    """Map image corners to a known trapezoid while preserving canvas size."""
    height, width = rgb.shape[:2]
    source = np.float32(
        [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]]
    )
    destination = np.float32(
        [
            [width * 0.075, height * 0.067],
            [width * 0.925, height * 0.033],
            [width * 0.963, height * 0.933],
            [width * 0.038, height * 0.967],
        ]
    )
    transform = cv2.getPerspectiveTransform(source, destination)
    return cv2.warpPerspective(rgb, transform, (width, height))

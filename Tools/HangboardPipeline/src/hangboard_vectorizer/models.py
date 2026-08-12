from dataclasses import dataclass

import numpy as np


class ConversionError(RuntimeError):
    """Raised when a source cannot be converted into a hangboard image."""


@dataclass(frozen=True, slots=True)
class LoadedImage:
    source: str
    rgb: np.ndarray

import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_cord_routes


def test_near_boundary_interval_fails_closed_with_bounded_work(monkeypatch):
    # Exact signed-distance field of a parallel plane just 1 nm above the
    # accepted boundary. Subdivision must not expand without a resource limit.
    count = 0
    def signed_distance(mesh, points):
        nonlocal count
        count += len(points)
        return np.full(len(points), -(.002-1e-5+1e-9))
    monkeypatch.setattr(native_cord_routes.trimesh.proximity, "signed_distance", signed_distance)
    with pytest.raises(ValueError, match="could not be certified within"):
        native_cord_routes.checked_clearance(None, np.array([[0.,0.,0.], [.1,0.,0.]]), .002)
    assert count <= 131072

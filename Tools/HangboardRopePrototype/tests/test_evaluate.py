"""Geometry acceptance is independent of the solver's self-reported status."""

import numpy as np
import pytest

from Tools.HangboardRopePrototype.evaluate import (
    contact_grade, routes_separate, segment_triangle_distance,
    point_inside_mesh, repeatable, signed_surface_clearance,
)


TRIANGLE = np.array([[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]])


def test_tangent_tube_and_gap():
    assert segment_triangle_distance(np.array([.2, .2, .002]),
                                     np.array([.4, .2, .002]), TRIANGLE) == pytest.approx(.002)
    assert contact_grade(0, penetration_limit=.0005, gap_limit=.001)
    assert not contact_grade(.0011, penetration_limit=.0005, gap_limit=.001)


def test_penetration_limits():
    assert contact_grade(-.0005, penetration_limit=.0005, gap_limit=.001)
    assert not contact_grade(-.0006, penetration_limit=.0005, gap_limit=.001)
    # An open oriented surface still supplies a local inward/outward sign.
    assert signed_surface_clearance(np.array([.2, .2, -.0025]),
                                    np.array([TRIANGLE]), .002) == pytest.approx(-.0045)


def test_segment_crossing_triangle_and_inside_classification():
    assert segment_triangle_distance(np.array([.2, .2, -.01]),
                                     np.array([.2, .2, .01]), TRIANGLE) == pytest.approx(0)
    vertices = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                         [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], dtype=float)
    faces = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7],
                      [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
                      [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    assert point_inside_mesh(np.array([.5, .5, .5]), vertices[faces])
    assert not point_inside_mesh(np.array([1.1, .5, .5]), vertices[faces])


def test_loop_overlap_and_repeatability():
    left = np.array([[-.1, 0, 0], [-.1, -.1, 0]])
    right = np.array([[.1, 0, 0], [.1, -.1, 0]])
    assert routes_separate(left, right, radius=.002, minimum_clearance=.001)
    assert not routes_separate(left, left, radius=.002, minimum_clearance=.001)
    assert repeatable(left, left + .000001, tolerance=.00001)
    assert not repeatable(left, left + .0001, tolerance=.00001)

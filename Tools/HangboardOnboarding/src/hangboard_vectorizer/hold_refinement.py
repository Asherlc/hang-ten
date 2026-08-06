"""Deterministic pixel refinement for coarse Stage 2 hold anchors."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .semantic_holds import CoarseHoldHint


@dataclass(frozen=True, slots=True)
class HoldDiscoveryProfile:
    """Material-neutral thresholds used by the deterministic tracer."""

    profile_id: str = "generic-local-contrast-seams-v1"
    grid_width: int = 20
    grid_height: int = 8
    contrast_sigmas: tuple[float, ...] = (6.0, 12.0, 24.0)
    contrast_thresholds: tuple[float, ...] = (10.0, 14.0, 18.0, 22.0, 26.0, 30.0)
    minimum_component_area_ratio: float = 0.00035
    aperture_rounding_ratio: float = 0.34
    aperture_support_expansion_px: int = 20
    aperture_ambiguity_margin: float = 1e-6
    surface_boundary_search_cells: float = 0.8
    surface_scan_height_ratio: float = 0.34
    seam_step_radius: int = 2
    seam_smoothness_weight: float = 2.00
    seam_curvature_weight: float = 3.00
    seam_alpha_proximity_weight: float = 0.03

    def __post_init__(self) -> None:
        if not self.profile_id or (self.grid_width, self.grid_height) != (20, 8):
            raise ValueError("hold discovery profile requires the 20x8 generic grid")
        if not self.contrast_sigmas or not self.contrast_thresholds:
            raise ValueError("hold discovery profile requires multiscale thresholds")
        if any(
            value <= 0 for value in (*self.contrast_sigmas, *self.contrast_thresholds)
        ):
            raise ValueError("hold discovery scales and thresholds must be positive")
        if not (0 < self.minimum_component_area_ratio < 0.1):
            raise ValueError("invalid hold discovery component area ratio")
        if not (0 < self.aperture_rounding_ratio < 0.5):
            raise ValueError("invalid aperture rounding ratio")
        if self.aperture_ambiguity_margin < 0:
            raise ValueError("invalid aperture ambiguity margin")
        if self.seam_step_radius < 1 or any(
            value < 0
            for value in (
                self.seam_smoothness_weight,
                self.seam_curvature_weight,
                self.seam_alpha_proximity_weight,
            )
        ):
            raise ValueError("invalid minimum-cost seam weights")


@dataclass(frozen=True, slots=True)
class RefinedMask:
    mask: np.ndarray
    evidence: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        frozen = np.frombuffer(
            self.mask.astype(np.uint8).tobytes(), dtype=np.uint8
        ).reshape(self.mask.shape)
        object.__setattr__(self, "mask", frozen)


@dataclass(frozen=True, slots=True)
class ApertureCandidate:
    """One image-derived recess tracked across the threshold sweep."""

    mask: np.ndarray
    boxes: tuple[tuple[int, int, int, int], ...]
    threshold_scores: tuple[float, ...]
    center: tuple[float, float]
    area: int
    stability: float
    compactness: float
    boundary_gradient: float
    alpha_containment: float
    dark_core_coverage: float
    threshold_masks: tuple[np.ndarray, ...] = ()

    def __post_init__(self) -> None:
        frozen = np.frombuffer(
            self.mask.astype(np.uint8).tobytes(), dtype=np.uint8
        ).reshape(self.mask.shape)
        object.__setattr__(self, "mask", frozen)
        object.__setattr__(
            self,
            "threshold_masks",
            tuple(
                np.frombuffer(value.astype(np.uint8).tobytes(), dtype=np.uint8).reshape(
                    value.shape
                )
                for value in self.threshold_masks
            ),
        )


def multiscale_local_contrast(
    rgb: np.ndarray, profile: HoldDiscoveryProfile
) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    maps = [
        cv2.GaussianBlur(gray, (0, 0), sigma) - gray
        for sigma in profile.contrast_sigmas
    ]
    return np.maximum.reduce(maps)


def generate_aperture_candidates(
    *,
    piece_mask: np.ndarray,
    contrast: np.ndarray,
    gray: np.ndarray,
    profile: HoldDiscoveryProfile,
) -> tuple[ApertureCandidate, ...]:
    """Track independent dark components from the darkest stable cores outward."""
    allowed = piece_mask.astype(bool)
    area_floor = max(
        12,
        int(np.count_nonzero(piece_mask) * profile.minimum_component_area_ratio),
    )
    states: list[tuple[np.ndarray, tuple[np.ndarray, ...]]] = []
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 5))
    for threshold in profile.contrast_thresholds:
        binary = ((contrast >= threshold) & allowed).astype(np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
        components = tuple(
            labels == index
            for index in range(1, count)
            if stats[index, cv2.CC_STAT_AREA] >= area_floor
        )
        states.append((binary, components))
    if not states or not states[-1][1]:
        raise ValueError("no stable aperture candidates were generated")

    smooth = cv2.GaussianBlur(gray, (0, 0), 1.2)
    gradient = cv2.magnitude(
        cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3),
        cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3),
    )
    gradient_scale = max(1.0, float(np.percentile(gradient[allowed], 95)))
    candidates: list[ApertureCandidate] = []
    stable_cores = states[-1][1]
    for core in stable_cores:
        boxes: list[tuple[int, int, int, int]] = []
        threshold_scores: list[float] = []
        threshold_masks: list[np.ndarray] = []
        for _, components in states:
            overlapping = [
                component for component in components if np.any(component & core)
            ]
            if not overlapping:
                continue
            component = max(
                overlapping,
                key=lambda value: (
                    int(np.count_nonzero(value & core)),
                    -int(np.count_nonzero(value)),
                ),
            )
            if sum(np.any(component & other_core) for other_core in stable_cores) != 1:
                continue
            ys, xs = np.nonzero(component)
            boxes.append((int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())))
            threshold_scores.append(float(np.mean(contrast[component])))
            threshold_masks.append(component.astype(np.uint8))
        if not boxes:
            continue
        area = int(np.count_nonzero(core))
        moments = cv2.moments(core.astype(np.uint8), binaryImage=True)
        center = (
            float(moments["m10"] / moments["m00"]),
            float(moments["m01"] / moments["m00"]),
        )
        contours, _ = cv2.findContours(
            core.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contour = max(contours, key=cv2.contourArea)
        hull_area = max(1.0, float(cv2.contourArea(cv2.convexHull(contour))))
        boundary = core & ~(
            cv2.erode(core.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        )
        candidates.append(
            ApertureCandidate(
                mask=core,
                boxes=tuple(boxes),
                threshold_scores=tuple(threshold_scores),
                center=center,
                area=area,
                stability=len(boxes) / len(profile.contrast_thresholds),
                compactness=min(1.0, area / hull_area),
                boundary_gradient=min(
                    1.0, float(np.mean(gradient[boundary])) / gradient_scale
                ),
                alpha_containment=float(np.count_nonzero(core & allowed) / area),
                dark_core_coverage=min(
                    1.0,
                    float(np.mean(contrast[core])) / max(profile.contrast_thresholds),
                ),
                threshold_masks=tuple(threshold_masks),
            )
        )
    return tuple(
        sorted(
            candidates, key=lambda value: (value.center[1], value.center[0], value.area)
        )
    )


def assign_aperture_candidates(
    hints: tuple[CoarseHoldHint, ...],
    *,
    candidates: tuple[ApertureCandidate, ...],
    anchor_points: dict[str, tuple[float, float]],
    support_masks: dict[str, np.ndarray],
    piece_mask: np.ndarray,
    profile: HoldDiscoveryProfile,
) -> dict[str, ApertureCandidate]:
    """Globally assign unique recess tracks and reject ambiguous optima."""
    if not hints:
        return {}
    if len(candidates) < len(hints):
        raise ValueError("aperture hints have unmatched dark components")
    height, width = piece_mask.shape
    cell_x, cell_y = width / profile.grid_width, height / profile.grid_height
    ordered_hints = tuple(sorted(hints, key=lambda value: value.hint_key))
    costs = np.empty((len(ordered_hints), len(candidates)), dtype=np.float64)
    invalid = 1e6
    for row, hint in enumerate(ordered_hints):
        ax, ay = anchor_points[hint.hint_key]
        support = support_masks[hint.hint_key].astype(bool)
        for column, candidate in enumerate(candidates):
            support_coverage = float(
                np.count_nonzero(candidate.mask & support) / candidate.area
            )
            if support_coverage < 0.25:
                costs[row, column] = invalid
                continue
            dx = (candidate.center[0] - ax) / cell_x
            dy = (candidate.center[1] - ay) / cell_y
            anchor_distance = float(np.hypot(dx, dy))
            costs[row, column] = (
                2.5 * anchor_distance
                + 3.0 * (1.0 - support_coverage)
                + 0.8 * (1.0 - candidate.stability)
                + 0.5 * (1.0 - candidate.compactness)
                + 0.4 * (1.0 - candidate.boundary_gradient)
                + 1.0 * (1.0 - candidate.alpha_containment)
                + 0.4 * (1.0 - candidate.dark_core_coverage)
            )
    assignment = _minimum_unique_assignment(
        costs, ambiguity_margin=profile.aperture_ambiguity_margin
    )
    if any(costs[row, column] >= invalid for row, column in enumerate(assignment)):
        raise ValueError("aperture hint could not be matched inside its support cell")
    return {
        hint.hint_key: candidates[column]
        for hint, column in zip(ordered_hints, assignment, strict=True)
    }


def refine_aperture(
    hint: CoarseHoldHint,
    *,
    candidate: ApertureCandidate,
    piece_mask: np.ndarray,
    support_mask: np.ndarray | None = None,
    exclusion_masks: tuple[np.ndarray, ...] = (),
    gray: np.ndarray,
    profile: HoldDiscoveryProfile,
) -> RefinedMask:
    """Select the observed multithreshold mouth contour with strongest edge support."""
    boxes = candidate.boxes
    scores = candidate.threshold_scores
    support = piece_mask.astype(bool)
    if support_mask is not None:
        support &= support_mask.astype(bool)
    smooth = cv2.GaussianBlur(gray, (0, 0), max(0.6, min(gray.shape) / 350.0))
    signed_grad_x = cv2.Scharr(smooth, cv2.CV_32F, 1, 0)
    signed_grad_y = cv2.Scharr(smooth, cv2.CV_32F, 0, 1)
    grad_x = np.abs(signed_grad_x)
    grad_y = np.abs(signed_grad_y)
    gradient = cv2.magnitude(grad_x, grad_y)
    observed_masks = candidate.threshold_masks or (candidate.mask,)
    core = candidate.mask.astype(bool)
    exclusion_data = tuple(
        (
            value.astype(bool),
            cv2.erode(value.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool),
        )
        for value in exclusion_masks
    )
    tracked = []
    ranked_observations: list[tuple[float, int, np.ndarray]] = []
    gradient_scale = max(1.0, float(np.percentile(gradient[support], 95)))
    for ordinal, raw in enumerate(observed_masks):
        observed = _component_overlapping_core(
            raw.astype(bool) & support, core, candidate.center
        )
        if not np.any(observed):
            continue
        tracked.append(observed)
        contour_candidates, _ = cv2.findContours(
            observed.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        contour = max(contour_candidates, key=cv2.contourArea)
        hull_area = max(1.0, float(cv2.contourArea(cv2.convexHull(contour))))
        compactness = float(np.count_nonzero(observed) / hull_area)
        boundary = observed & ~(
            cv2.erode(observed.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        )
        edge_support = float(np.mean(gradient[boundary]) / gradient_scale)
        ranked_observations.append(
            (compactness + 0.15 * edge_support, -ordinal, observed)
        )
    if not tracked:
        raise ValueError("aperture refinement found no tracked mouth contour")
    selected: np.ndarray | None = None
    selected_ordinal = -1
    for _, negative_ordinal, observed in sorted(
        ranked_observations, key=lambda item: (item[0], item[1]), reverse=True
    ):
        pre_ys, pre_xs = np.nonzero(observed)
        local_scale = min(
            int(pre_xs.max() - pre_xs.min() + 1),
            int(pre_ys.max() - pre_ys.min() + 1),
        )
        closing_radius = max(1, int(round(local_scale * 0.10)))
        observed = (
            cv2.morphologyEx(
                observed.astype(np.uint8),
                cv2.MORPH_CLOSE,
                cv2.getStructuringElement(
                    cv2.MORPH_ELLIPSE,
                    (closing_radius * 2 + 1, closing_radius * 2 + 1),
                ),
            ).astype(bool)
            & support
        )
        contour_candidates, _ = cv2.findContours(
            observed.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        exterior = np.zeros_like(observed, dtype=np.uint8)
        cv2.drawContours(
            exterior,
            [max(contour_candidates, key=cv2.contourArea)],
            -1,
            1,
            thickness=-1,
        )
        observed = _trace_aperture_mouth(
            exterior.astype(bool),
            support=support,
            signed_grad_x=signed_grad_x,
            signed_grad_y=signed_grad_y,
            character_source=exterior.astype(bool),
            profile=profile,
        )
        maximum_inward = max(1, int(round(local_scale * 0.06)))
        for inward in range(0, maximum_inward + 1):
            traced = (
                observed
                if inward == 0
                else cv2.erode(
                    observed.astype(np.uint8),
                    cv2.getStructuringElement(
                        cv2.MORPH_ELLIPSE, (inward * 2 + 1, inward * 2 + 1)
                    ),
                    borderType=cv2.BORDER_CONSTANT,
                    borderValue=0,
                ).astype(bool)
            )
            traced_interior = cv2.erode(
                traced.astype(np.uint8), np.ones((3, 3), np.uint8)
            ).astype(bool)
            if all(
                not np.any((traced & other) & (traced_interior | other_interior))
                for other, other_interior in exclusion_data
            ):
                selected = traced
                selected_ordinal = -negative_ordinal
                break
        if selected is not None:
            break
    if selected is None or not np.any(selected):
        raise ValueError(
            f"aperture refinement found no nonoverlapping observed mouth contour: {hint.hint_key}"
        )
    mask = _largest_connected_component(selected.astype(np.uint8), candidate.center)
    ys, xs = np.nonzero(mask)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
    if x1 - x0 < 5 or y1 - y0 < 5:
        raise ValueError("aperture refinement produced degenerate geometry")
    boundary = mask.astype(bool) & ~(cv2.erode(mask, np.ones((3, 3), np.uint8)) > 0)
    return RefinedMask(
        mask,
        (
            ("thresholdCount", float(len(boxes))),
            ("meanDarkCore", float(np.mean(scores))),
            ("compactness", candidate.compactness),
            ("boundaryGradient", candidate.boundary_gradient),
            ("alphaContainment", candidate.alpha_containment),
            ("thresholdStability", candidate.stability),
            ("selectedThresholdOrdinal", float(selected_ordinal)),
            ("thresholdConsensusCount", float(len(tracked))),
            ("mouthBoundaryGradient", float(np.mean(gradient[boundary]))),
            ("bboxWidth", float(x1 - x0 + 1)),
            ("bboxHeight", float(y1 - y0 + 1)),
        ),
    )


def _trace_aperture_mouth(
    observed: np.ndarray,
    *,
    support: np.ndarray,
    signed_grad_x: np.ndarray,
    signed_grad_y: np.ndarray,
    character_source: np.ndarray,
    profile: HoldDiscoveryProfile,
) -> np.ndarray:
    """Trace four local directional seams around an observed aperture mouth."""
    ys, xs = np.nonzero(observed)
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    local_scale = min(x1 - x0 + 1, y1 - y0 + 1)
    band = max(2, int(round(local_scale * 0.18)))

    columns = np.arange(x0, x1 + 1)
    column_values = observed[:, x0 : x1 + 1]
    top_observed = np.argmax(column_values, axis=0)
    bottom_observed = observed.shape[0] - 1 - np.argmax(column_values[::-1], axis=0)
    top = _trace_directional_edge(
        np.maximum(-signed_grad_y[:, x0 : x1 + 1], 0).T,
        support[:, x0 : x1 + 1].T,
        top_observed,
        band=band,
        center_weight=0.03,
        profile=profile,
    )
    bottom = _trace_directional_edge(
        np.maximum(signed_grad_y[:, x0 : x1 + 1], 0).T,
        support[:, x0 : x1 + 1].T,
        bottom_observed,
        band=band,
        center_weight=0.03,
        profile=profile,
    )

    rows = np.arange(y0, y1 + 1)
    row_values = observed[y0 : y1 + 1]
    left_observed = np.argmax(row_values, axis=1)
    right_observed = observed.shape[1] - 1 - np.argmax(row_values[:, ::-1], axis=1)
    left = _trace_directional_edge(
        np.maximum(-signed_grad_x[y0 : y1 + 1], 0),
        support[y0 : y1 + 1],
        left_observed,
        band=band,
        center_weight=0.03,
        profile=profile,
    )
    right = _trace_directional_edge(
        np.maximum(signed_grad_x[y0 : y1 + 1], 0),
        support[y0 : y1 + 1],
        right_observed,
        band=band,
        center_weight=0.03,
        profile=profile,
    )

    top_field = np.full(observed.shape[1], observed.shape[0], dtype=int)
    bottom_field = np.full(observed.shape[1], -1, dtype=int)
    top_field[columns] = top
    bottom_field[columns] = bottom
    left_field = np.full(observed.shape[0], observed.shape[1], dtype=int)
    right_field = np.full(observed.shape[0], -1, dtype=int)
    left_field[rows] = left
    right_field[rows] = right
    # Extend side traces to any rows reached by the top/bottom image seams.
    left_field[:y0] = left[0]
    left_field[y1 + 1 :] = left[-1]
    right_field[:y0] = right[0]
    right_field[y1 + 1 :] = right[-1]
    yy, xx = np.indices(observed.shape)
    traced = (
        support
        & (yy >= top_field[xx])
        & (yy <= bottom_field[xx])
        & (xx >= left_field[yy])
        & (xx <= right_field[yy])
    )
    character_radius = max(1, int(round(local_scale * 0.12)))
    character_envelope = cv2.dilate(
        character_source.astype(np.uint8),
        cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (character_radius * 2 + 1, character_radius * 2 + 1),
        ),
    ).astype(bool)
    traced &= character_envelope
    smoothing_sigma = max(0.5, local_scale * 0.08)
    smoothed = (
        cv2.GaussianBlur(traced.astype(np.float32), (0, 0), smoothing_sigma) >= 0.50
    )
    return smoothed & character_envelope


def _trace_directional_edge(
    directional: np.ndarray,
    allowed: np.ndarray,
    observed_positions: np.ndarray,
    *,
    band: int,
    center_weight: float,
    profile: HoldDiscoveryProfile,
) -> np.ndarray:
    lo = max(0, int(observed_positions.min()) - band)
    hi = min(directional.shape[1] - 1, int(observed_positions.max()) + band)
    evidence = directional[:, lo : hi + 1]
    scale = max(1.0, float(np.percentile(evidence, 95)))
    cost = 1.0 - np.clip(evidence / scale, 0.0, 1.0)
    positions = np.arange(lo, hi + 1)
    cost += (center_weight / max(1, band)) * np.abs(
        positions[np.newaxis, :] - observed_positions[:, np.newaxis]
    )
    cost += (~allowed[:, lo : hi + 1]) * 4.0
    path, _ = _minimum_cost_seam(cost, profile)
    return path + lo


def trace_surface_masks(
    hints: tuple[CoarseHoldHint, ...],
    *,
    anchor_points: dict[str, tuple[float, float]],
    piece_mask: np.ndarray,
    rgb: np.ndarray,
    profile: HoldDiscoveryProfile,
) -> dict[str, RefinedMask]:
    """Trace each surface inside a 2D anchor cell using Lab/Scharr evidence."""
    ordered = sorted(hints, key=lambda item: item.hint_key)
    if not ordered:
        return {}
    if rgb.ndim != 3 or rgb.shape[:2] != piece_mask.shape or rgb.shape[2] != 3:
        raise ValueError(
            "surface tracing requires an RGB raster matching the silhouette"
        )
    height, width = piece_mask.shape
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    sigma = max(0.6, min(height, width) / 350.0)
    lab = cv2.GaussianBlur(lab, (0, 0), sigma)
    grad_x = np.sqrt(
        sum(
            cv2.Scharr(lab[..., channel], cv2.CV_32F, 1, 0) ** 2 for channel in range(3)
        )
    )
    grad_y = np.sqrt(
        sum(
            cv2.Scharr(lab[..., channel], cv2.CV_32F, 0, 1) ** 2 for channel in range(3)
        )
    )
    allowed = piece_mask.astype(bool)
    grad_x[~allowed] = 0
    grad_y[~allowed] = 0
    alpha_distance = cv2.distanceTransform(piece_mask.astype(np.uint8), cv2.DIST_L2, 5)
    alpha_distance /= max(1.0, float(alpha_distance.max()))
    cell_width = width / profile.grid_width
    cell_height = height / profile.grid_height
    yy, xx = np.indices(piece_mask.shape)
    distances = np.stack(
        [
            ((xx - anchor_points[hint.hint_key][0]) / cell_width) ** 2
            + ((yy - anchor_points[hint.hint_key][1]) / cell_height) ** 2
            for hint in ordered
        ]
    )
    owner = np.argmin(distances, axis=0)
    horizontal_order = sorted(
        range(len(ordered)),
        key=lambda value: (
            anchor_points[ordered[value].hint_key][0],
            ordered[value].hint_key,
        ),
    )
    for left_index, right_index in zip(horizontal_order, horizontal_order[1:]):
        left_anchor = anchor_points[ordered[left_index].hint_key]
        right_anchor = anchor_points[ordered[right_index].hint_key]
        if abs(left_anchor[1] - right_anchor[1]) / cell_height > 0.5:
            continue
        seam, _ = _trace_vertical_support_seam(
            left_anchor,
            right_anchor,
            grad_x=grad_x,
            alpha_distance=alpha_distance,
            allowed=allowed,
            cell_width=cell_width,
            cell_height=cell_height,
            profile=profile,
        )
        pair_domain = allowed & ((owner == left_index) | (owner == right_index))
        owner[pair_domain & (xx < seam[:, np.newaxis])] = left_index
        owner[pair_domain & (xx >= seam[:, np.newaxis])] = right_index

    result: dict[str, RefinedMask] = {}
    for index, hint in enumerate(ordered):
        support = allowed & (owner == index)
        anchor_x, anchor_y = anchor_points[hint.hint_key]
        anchor_row = min(height - 1, max(0, int(round(anchor_y))))
        local_rows = slice(
            max(0, int(round(anchor_y - cell_height * 0.35))),
            min(height, int(round(anchor_y + cell_height * 0.35)) + 1),
        )
        active_columns = np.flatnonzero(np.any(support[local_rows], axis=0))
        if active_columns.size < 6:
            raise ValueError("surface anchor has insufficient 2D pixel support")
        sample0, sample1 = int(active_columns.min()), int(active_columns.max())
        coarse0 = max(1, int(round(anchor_y)))
        coarse1 = min(height - 2, int(round(anchor_y + cell_height * 1.75)))
        column_support = support[coarse0 : coarse1 + 1, sample0 : sample1 + 1]
        directional_field = grad_y[coarse0 : coarse1 + 1, sample0 : sample1 + 1]
        row_counts = np.maximum(1, column_support.sum(axis=1))
        row_evidence = (directional_field * column_support).sum(axis=1) / row_counts
        evidence_scale = max(1.0, float(np.percentile(row_evidence, 95)))
        downstream_distance = np.arange(row_evidence.size) / max(1.0, cell_height)
        baseline_score = (
            np.clip(row_evidence / evidence_scale, 0.0, 1.0)
            - 0.35 * downstream_distance
        )
        baseline = coarse0 + int(np.argmax(baseline_score))
        corridor = max(1, int(round(cell_height * 0.14)))
        search0, search1 = (
            max(coarse0, baseline - corridor),
            min(coarse1, baseline + corridor),
        )
        directional = grad_y[search0 : search1 + 1, sample0 : sample1 + 1].T
        scale = max(1.0, float(np.percentile(directional, 95)))
        cost = 1.0 - np.clip(directional / scale, 0.0, 1.0)
        cost += (0.15 / max(1, corridor)) * np.abs(
            np.arange(search0, search1 + 1) - baseline
        )[np.newaxis, :]
        cost += (
            profile.seam_alpha_proximity_weight
            * alpha_distance[search0 : search1 + 1, sample0 : sample1 + 1].T
        )
        cost += (~support[search0 : search1 + 1, sample0 : sample1 + 1].T) * 4.0
        bottom_local, bottom_cost = _minimum_cost_seam(cost, profile)
        bottom_path = bottom_local + search0
        bottom_field = np.full(piece_mask.shape, int(np.median(bottom_path)), dtype=int)
        bottom_field[:, sample0 : sample1 + 1] = bottom_path[np.newaxis, :]
        mask = (support & (yy <= bottom_field)).astype(np.uint8)
        mask = _largest_connected_component(mask, anchor_points[hint.hint_key])
        if not np.any(mask):
            raise ValueError("surface refinement produced an empty region")
        support_boundary = support & ~(
            cv2.erode(support.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        )
        vertical_cost = (
            float(np.mean(grad_x[support_boundary]))
            if np.any(support_boundary)
            else 0.0
        )
        ys, xs = np.nonzero(mask)
        x0, x1 = int(xs.min()), int(xs.max())
        result[hint.hint_key] = RefinedMask(
            mask,
            (
                ("leftSeam", float(x0)),
                ("rightSeam", float(x1)),
                ("bottomSeam", float(np.median(bottom_path))),
                ("verticalSeamCost", vertical_cost),
                ("bottomSeamCost", bottom_cost),
                ("seamSmoothness", float(np.abs(np.diff(bottom_path)).sum())),
                ("seamCurvature", float(np.abs(np.diff(bottom_path, n=2)).sum())),
            ),
        )
    return result


def _trace_vertical_support_seam(
    left_anchor: tuple[float, float],
    right_anchor: tuple[float, float],
    *,
    grad_x: np.ndarray,
    alpha_distance: np.ndarray,
    allowed: np.ndarray,
    cell_width: float,
    cell_height: float,
    profile: HoldDiscoveryProfile,
) -> tuple[np.ndarray, float]:
    """Trace a local Lab/Scharr boundary near a horizontal anchor bisector."""
    height, width = allowed.shape
    midpoint = (left_anchor[0] + right_anchor[0]) / 2.0
    radius = cell_width * profile.surface_boundary_search_cells
    lo = max(1, int(round(midpoint - radius)))
    hi = min(width - 2, int(round(midpoint + radius)))
    scan_height = min(
        height,
        max(6, int(round(max(left_anchor[1], right_anchor[1]) + cell_height * 0.8))),
    )
    coarse = grad_x[:scan_height, lo : hi + 1]
    coarse_allowed = allowed[:scan_height, lo : hi + 1]
    counts = np.maximum(1, coarse_allowed.sum(axis=0))
    baseline = lo + int(np.argmax((coarse * coarse_allowed).sum(axis=0) / counts))
    corridor = max(1, int(round(cell_width * 0.06)))
    seam_lo, seam_hi = max(lo, baseline - corridor), min(hi, baseline + corridor)
    directional = grad_x[:scan_height, seam_lo : seam_hi + 1]
    scale = max(1.0, float(np.percentile(directional, 95)))
    cost = 1.0 - np.clip(directional / scale, 0.0, 1.0)
    cost += (0.15 / max(1, corridor)) * np.abs(
        np.arange(seam_lo, seam_hi + 1) - baseline
    )[np.newaxis, :]
    cost += (
        profile.seam_alpha_proximity_weight
        * alpha_distance[:scan_height, seam_lo : seam_hi + 1]
    )
    cost += (~allowed[:scan_height, seam_lo : seam_hi + 1]) * 4.0
    local, total = _minimum_cost_seam(cost, profile)
    seam = np.full(height, int(np.median(local + seam_lo)), dtype=int)
    seam[:scan_height] = local + seam_lo
    return seam, total


def _component_overlapping_core(
    mask: np.ndarray,
    core: np.ndarray,
    anchor: tuple[float, float],
) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    if count <= 2:
        return mask.astype(bool)
    overlapping = [
        index for index in range(1, count) if np.any((labels == index) & core)
    ]
    if overlapping:
        selected = max(
            overlapping,
            key=lambda value: (
                int(np.count_nonzero((labels == value) & core)),
                stats[value, cv2.CC_STAT_AREA],
            ),
        )
        return labels == selected
    return _largest_connected_component(mask.astype(np.uint8), anchor).astype(bool)


def _largest_connected_component(
    mask: np.ndarray,
    anchor: tuple[float, float],
) -> np.ndarray:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    if count <= 2:
        return mask.astype(np.uint8)
    ax = min(mask.shape[1] - 1, max(0, int(round(anchor[0]))))
    ay = min(mask.shape[0] - 1, max(0, int(round(anchor[1]))))
    selected = int(labels[ay, ax])
    if selected == 0:
        selected = max(
            range(1, count), key=lambda index: (stats[index, cv2.CC_STAT_AREA], -index)
        )
    return (labels == selected).astype(np.uint8)


def _minimum_cost_seam(
    cost: np.ndarray,
    profile: HoldDiscoveryProfile,
) -> tuple[np.ndarray, float]:
    """Trace a deterministic seam with first-difference and curvature costs."""
    if cost.ndim != 2 or min(cost.shape) == 0 or not np.isfinite(cost).all():
        raise ValueError("minimum-cost seam requires one finite cost rectangle")
    length, positions = cost.shape
    deltas = (
        0,
        *(
            value
            for radius in range(1, profile.seam_step_radius + 1)
            for value in (-radius, radius)
        ),
    )
    delta_count = len(deltas)
    infinity = np.inf
    previous = np.full((positions, delta_count), infinity)
    previous[:, 0] = cost[0]
    back = np.full((length, positions, delta_count), -1, dtype=np.int16)
    for step in range(1, length):
        current = np.full((positions, delta_count), infinity)
        for position in range(positions):
            for delta_index, delta in enumerate(deltas):
                prior_position = position - delta
                if not 0 <= prior_position < positions:
                    continue
                transition = (
                    previous[prior_position]
                    + (profile.seam_smoothness_weight * abs(delta))
                    + np.asarray(
                        [
                            profile.seam_curvature_weight * abs(delta - prior_delta)
                            for prior_delta in deltas
                        ]
                    )
                )
                prior_delta_index = int(np.argmin(transition))
                current[position, delta_index] = (
                    cost[step, position] + transition[prior_delta_index]
                )
                back[step, position, delta_index] = prior_delta_index
        previous = current
    flat_index = int(np.argmin(previous))
    position, delta_index = np.unravel_index(flat_index, previous.shape)
    total_cost = float(previous[position, delta_index] / length)
    path = np.empty(length, dtype=int)
    path[-1] = position
    for step in range(length - 1, 0, -1):
        delta = deltas[delta_index]
        prior_position = position - delta
        prior_delta_index = int(back[step, position, delta_index])
        position, delta_index = prior_position, prior_delta_index
        path[step - 1] = position
    return path, total_cost


def _minimum_unique_assignment(
    cost: np.ndarray,
    *,
    ambiguity_margin: float,
) -> tuple[int, ...]:
    """Return a rectangular Hungarian assignment with a second-best gap gate."""
    assignment = minimum_assignment(cost)
    best = float(sum(cost[row, column] for row, column in enumerate(assignment)))
    alternate = float("inf")
    forbidden = max(1e9, float(np.max(cost)) + 1e6)
    for row, column in enumerate(assignment):
        changed = cost.copy()
        changed[row, column] = forbidden
        other = minimum_assignment(changed)
        total = float(sum(changed[index, value] for index, value in enumerate(other)))
        alternate = min(alternate, total)
    if alternate - best <= ambiguity_margin:
        raise ValueError("ambiguous aperture assignment")
    return assignment


from .assignment import minimum_assignment

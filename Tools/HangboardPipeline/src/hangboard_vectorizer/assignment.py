"""Deterministic minimum-cost assignment shared by evaluation stages."""

from __future__ import annotations

import numpy as np


def minimum_assignment(cost: np.ndarray) -> tuple[int, ...]:
    """Return a rectangular Hungarian assignment with stable column tie-breaking."""
    if (
        cost.ndim != 2
        or cost.shape[0] == 0
        or cost.shape[0] > cost.shape[1]
        or not np.isfinite(cost).all()
    ):
        raise ValueError(
            "assignment matrix must be finite and have at least as many columns as rows"
        )
    rows, columns = cost.shape
    row_potential = np.zeros(rows + 1)
    column_potential = np.zeros(columns + 1)
    matched_row = np.zeros(columns + 1, dtype=int)
    previous_column = np.zeros(columns + 1, dtype=int)
    for row in range(1, rows + 1):
        matched_row[0] = row
        column0 = 0
        minimum = np.full(columns + 1, np.inf)
        used = np.zeros(columns + 1, dtype=bool)
        while True:
            used[column0] = True
            row0 = matched_row[column0]
            delta = float("inf")
            column1 = 0
            for column in range(1, columns + 1):
                if used[column]:
                    continue
                current = (
                    cost[row0 - 1, column - 1]
                    - row_potential[row0]
                    - column_potential[column]
                )
                if current < minimum[column]:
                    minimum[column] = current
                    previous_column[column] = column0
                if minimum[column] < delta:
                    delta = minimum[column]
                    column1 = column
            for column in range(columns + 1):
                if used[column]:
                    row_potential[matched_row[column]] += delta
                    column_potential[column] -= delta
                else:
                    minimum[column] -= delta
            column0 = column1
            if matched_row[column0] == 0:
                break
        while True:
            column1 = previous_column[column0]
            matched_row[column0] = matched_row[column1]
            column0 = column1
            if column0 == 0:
                break
    assignment = np.full(rows, -1, dtype=int)
    for column in range(1, columns + 1):
        if matched_row[column]:
            assignment[matched_row[column] - 1] = column - 1
    if np.any(assignment < 0):
        raise ValueError("assignment is incomplete")
    return tuple(int(value) for value in assignment)

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PiecewiseState:
    times: np.ndarray
    values: np.ndarray
    cumulative_area: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        times = np.asarray(self.times, dtype=float)
        values = np.asarray(self.values, dtype=float)

        if times.ndim != 1 or values.ndim != 1:
            raise ValueError("times and values must be one-dimensional")
        if len(times) != len(values):
            raise ValueError("times and values must have equal length")
        if len(times) > 1 and np.any(np.diff(times) < 0):
            raise ValueError("times must be sorted in non-decreasing order")

        cumulative = np.zeros(len(times), dtype=float)
        if len(times) > 1:
            cumulative[1:] = np.cumsum(values[:-1] * np.diff(times))

        object.__setattr__(self, "times", times)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "cumulative_area", cumulative)


def canonical_state(state_df: pd.DataFrame, field: str) -> PiecewiseState:
    """Return the last post-event state at each timestamp as a piecewise-constant series."""
    if state_df.empty:
        return PiecewiseState(np.asarray([0.0]), np.asarray([0.0]))
    df = state_df.sort_values(["time"]).copy()
    df = df.groupby("time", as_index=False).tail(1).sort_values("time")
    return PiecewiseState(df["time"].to_numpy(float), df[field].to_numpy(float))


def value_at(series: PiecewiseState, t: float) -> float:
    idx = int(series.times.searchsorted(t, side="right") - 1)
    if idx < 0:
        return 0.0
    return float(series.values[idx])


def _area_to(series: PiecewiseState, t: float) -> float:
    """Exact integral of the piecewise-constant series up to time t."""
    idx = int(series.times.searchsorted(t, side="right") - 1)
    if idx < 0:
        return 0.0
    return float(
        series.cumulative_area[idx]
        + series.values[idx] * (t - series.times[idx])
    )


def integral(series: PiecewiseState, start: float, end: float) -> float:
    if end <= start:
        return 0.0
    return float(_area_to(series, end) - _area_to(series, start))


def time_weighted_mean(state_df: pd.DataFrame, field: str, start: float, end: float) -> float:
    if end <= start:
        raise ValueError("end must be > start")
    return integral(canonical_state(state_df, field), start, end) / (end - start)


def moving_average(series: PiecewiseState, t: float, window_s: float) -> float:
    if window_s <= 0:
        raise ValueError("window_s must be > 0")
    start = max(0.0, t - window_s)
    denom = t - start
    if denom <= 0:
        return 0.0
    return integral(series, start, t) / denom


def continuous_time_linear_slope(
    state_df: pd.DataFrame,
    field: str,
    start: float,
    end: float,
) -> float:
    """Least-squares slope for a piecewise-constant state over continuous time.

    It minimizes the integrated squared error over [start,end], avoiding arbitrary
    fixed-interval sampling. Units are field-units per second.
    """
    if end <= start:
        raise ValueError("end must be > start")
    series = canonical_state(state_df, field)
    mean_t = (start + end) / 2.0
    denominator = (end - start) ** 3 / 12.0
    if denominator == 0:
        return 0.0

    breakpoints = [start]
    mask = (series.times > start) & (series.times < end)
    breakpoints.extend(float(x) for x in series.times[mask])
    breakpoints.append(end)
    numerator = 0.0
    for a, b in zip(breakpoints[:-1], breakpoints[1:]):
        q = value_at(series, a)
        numerator += q * 0.5 * ((b - mean_t) ** 2 - (a - mean_t) ** 2)
    return float(numerator / denominator)


def _candidate_breakpoints(
    series: PiecewiseState,
    start: float,
    end: float,
    window_s: float,
) -> list[float]:
    points = {float(start), float(end)}
    for t in series.times:
        t = float(t)
        if start < t < end:
            points.add(t)
        shifted = t + window_s
        if start < shifted < end:
            points.add(shifted)
    return sorted(points)


def first_sustained_moving_average_below(
    state_df: pd.DataFrame,
    *,
    field: str,
    search_start: float,
    search_end: float,
    window_s: float,
    threshold: float,
    sustain_s: float,
) -> float | None:
    """Find the first time a sliding mean is <= threshold for sustain_s continuously.

    For a piecewise-constant queue, the moving average is piecewise linear. The
    implementation builds all slope-change points (state changes and state changes
    shifted by the moving window), adds any threshold crossings, then searches the
    exact linear segments for a continuous below-threshold interval.
    """
    if search_end <= search_start:
        return None
    series = canonical_state(state_df, field)
    base = _candidate_breakpoints(series, search_start, search_end, window_s)
    refined: list[float] = [base[0]]
    for a, b in zip(base[:-1], base[1:]):
        ya = moving_average(series, a, window_s) - threshold
        yb = moving_average(series, b, window_s) - threshold
        if ya == 0:
            refined.append(a)
        if ya * yb < 0:
            # Linear on this interval; solve y(t)=0 by interpolation.
            x = a + (b - a) * (-ya) / (yb - ya)
            refined.append(float(x))
        refined.append(b)
    points = sorted(set(refined))

    below_segments: list[tuple[float, float]] = []
    for a, b in zip(points[:-1], points[1:]):
        mid = (a + b) / 2.0
        if moving_average(series, mid, window_s) <= threshold + 1e-12:
            below_segments.append((a, b))

    if not below_segments:
        return None

    merged: list[list[float]] = []
    for a, b in below_segments:
        if not merged or a > merged[-1][1] + 1e-10:
            merged.append([a, b])
        else:
            merged[-1][1] = max(merged[-1][1], b)
    for a, b in merged:
        if b - a >= sustain_s - 1e-10:
            return float(a)
    return None

"""T-012 smoke tests for grid_roof.openings (pure geometry; fields/T-012_openings_smoke_spec.md).

``s`` is fixed at the summer-solstice 09:00 instant, linearly interpolated
between the 08:45 and 09:15 rows of ``fields/T-009_sun_sample_times.csv``
(no 09:00 row exists in that fixture) and renormalized. This is numeric
interpolation of an already-reviewed fixture, not a recomputation of solar
position, per ``ops/notes_T-012_for_claude.txt`` ("不重算太陽"). The result
is checked against the approximate value the spec table already locked
(``~(0.6428, 0.1237, 0.7560)``) as a sanity check, not derived independently
of it.
"""
import math

import numpy as np
import pytest

from grid_roof.brief import Brief
from grid_roof.openings import axes_parallel, forward_spot, invert_opening, pierces_keep, spot_error
from grid_roof.sun_field import load_sun_sample_times


def _solstice_0900_s():
    rows = [r for r in load_sun_sample_times() if r["date"] == "2025-06-21" and r["half"] == "am"]
    before = next(r for r in rows if r["local_time"] == "08:45")
    after = next(r for r in rows if r["local_time"] == "09:15")
    t = 0.5  # 09:00 is the midpoint of 08:45 and 09:15
    s = tuple(b + t * (a - b) for b, a in zip(before["s_k"], after["s_k"]))
    n = math.sqrt(sum(c * c for c in s))
    return tuple(c / n for c in s)


S_SOLSTICE_0900 = _solstice_0900_s()


def test_s_matches_spec_fixture_approx():
    expected = (0.6428, 0.1237, 0.7560)
    assert all(abs(a - b) < 5e-3 for a, b in zip(S_SOLSTICE_0900, expected))


def test_invert_opening_direction_and_formula():
    brief = Brief()
    y = (3000.0, 2000.0, 0.0)
    shell_z = brief.thickness
    x, lam, axis = invert_opening(y, S_SOLSTICE_0900, shell_z)
    assert lam > 0
    unit_s = np.array(S_SOLSTICE_0900) / np.linalg.norm(S_SOLSTICE_0900)
    assert np.allclose(axis, unit_s)
    assert np.allclose(np.asarray(x), np.asarray(y) + lam * axis)
    assert x[2] == pytest.approx(shell_z)


def test_invert_then_forward_round_trips_within_e_max():
    brief = Brief()
    y = (3000.0, 2000.0, 0.0)
    shell_z = brief.thickness
    x, _, _ = invert_opening(y, S_SOLSTICE_0900, shell_z)
    y_actual = forward_spot(x, S_SOLSTICE_0900, floor_z=y[2])
    e = spot_error(y_actual, y)
    assert e <= brief.e_max


def test_invert_opening_rejects_sun_below_horizon():
    with pytest.raises(ValueError):
        invert_opening((0.0, 0.0, 0.0), (0.5, 0.0, -0.1), 600.0)


def test_invert_opening_rejects_shell_below_target():
    with pytest.raises(ValueError):
        invert_opening((0.0, 0.0, 1000.0), S_SOLSTICE_0900, 600.0)


def test_axes_parallel_for_two_holes_same_instant():
    brief = Brief()
    shell_z = brief.thickness
    _, _, axis1 = invert_opening((3000.0, 2000.0, 0.0), S_SOLSTICE_0900, shell_z)
    _, _, axis2 = invert_opening((9000.0, 5000.0, 0.0), S_SOLSTICE_0900, shell_z)
    assert axes_parallel(axis1, axis2)


def test_axes_parallel_rejects_different_directions():
    assert not axes_parallel((1.0, 0.0, 1.0), (0.0, 1.0, 1.0))


def test_pierces_keep_rejects_hole_in_band_but_not_clear_hole():
    brief = Brief()
    shell_z = brief.thickness
    x_blocked, _, _ = invert_opening((1000.0, 2000.0, 0.0), S_SOLSTICE_0900, shell_z)
    band_half_width = 100.0
    keep_bands = {"xbands": [(x_blocked[0] - band_half_width, x_blocked[0] + band_half_width)]}
    assert pierces_keep(x_blocked, keep_bands)

    x_clear, _, _ = invert_opening((6000.0, 2000.0, 0.0), S_SOLSTICE_0900, shell_z)
    assert not pierces_keep(x_clear, keep_bands)

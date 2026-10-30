"""T-010: S (slope suitability) smoke tests against the locked probe table.

Probe geometry, points and expected values are
``fields/T-010_slope_spec.md`` (風場 spec, GOLD, not modified here), SS2/SS2.1,
preset A (alpha_min=0 deg, alpha_max=90 deg). S is checked via the
arccos formula, not ``max(n.z, 0)`` (SS1 explicitly forbids that shortcut).
"""
import math

import numpy as np
import pytest

from compas.datastructures import Mesh
from compas.geometry import Box

from grid_roof.slope_field import ALPHA_MAX_RAD, ALPHA_MIN_RAD, slope_field, slope_suitability


def _box(center, size):
    mesh = Mesh.from_shape(Box(*size))  # compas Box is centred at the origin
    mesh.translate(list(center))
    return mesh


def box0():
    """BOX0: 1000^3 box centred at the origin (same as T-008/T-009)."""
    return _box((0.0, 0.0, 0.0), (1000.0, 1000.0, 1000.0))


def row_at(result, point, atol=1e-6):
    i = int(np.argmin(np.linalg.norm(result["points"] - np.array(point), axis=1)))
    assert np.allclose(result["points"][i], point, atol=atol), (result["points"][i], point)
    return i


def test_preset_a_constants_locked():
    assert ALPHA_MIN_RAD == pytest.approx(0.0)
    assert ALPHA_MAX_RAD == pytest.approx(math.pi / 2)


# SS2.1 direct normal -> S checks (no mesh needed).
@pytest.mark.parametrize("normal,alpha_expected,s_expected", [
    ((0.0, 0.0, 1.0), 0.0, 1.0),                                     # n=(0,0,1)
    ((1.0, 0.0, 0.0), math.pi / 2, 0.0),                             # n=(1,0,0)
    ((0.0, 0.0, -1.0), math.pi, 0.0),                                # n=(0,0,-1)
    ((math.sqrt(2) / 2, 0.0, math.sqrt(2) / 2), math.pi / 4, 0.5),   # 45 deg
])
def test_section_2_1_single_normal_checks(normal, alpha_expected, s_expected):
    alpha, S = slope_suitability(np.array([normal]))
    assert alpha[0] == pytest.approx(alpha_expected, abs=1e-6)
    assert S[0] == pytest.approx(s_expected, abs=1e-6)


@pytest.mark.parametrize("n,alpha_expected,s_expected", [
    ((1.0, 0.0, math.sqrt(3.0)), math.pi / 6, 2.0 / 3.0),   # P6_30: alpha=30deg, S=(90-30)/90
    ((math.sqrt(3.0), 0.0, 1.0), math.pi / 3, 1.0 / 3.0),   # P7_60: alpha=60deg, S=(90-60)/90
])
def test_p6_p7_oblique_normals(n, alpha_expected, s_expected):
    n = np.array(n) / np.linalg.norm(n)
    alpha, S = slope_suitability(np.array([n]))
    assert alpha[0] == pytest.approx(alpha_expected, abs=1e-6)
    assert S[0] == pytest.approx(s_expected, abs=1e-6)


# SS2 box-face probes P1-P4 (horizontal top/bottom, vertical east/north).
@pytest.mark.parametrize("point,normal,alpha_expected,s_expected", [
    ((0.0, 0.0, 500.0), (0.0, 0.0, 1.0), 0.0, 1.0),               # P1_top
    ((0.0, 0.0, -500.0), (0.0, 0.0, -1.0), math.pi, 0.0),         # P2_bottom
    ((500.0, 0.0, 0.0), (1.0, 0.0, 0.0), math.pi / 2, 0.0),       # P3_east
    ((0.0, 500.0, 0.0), (0.0, 1.0, 0.0), math.pi / 2, 0.0),       # P4_north
])
def test_box0_probes_p1_p4(point, normal, alpha_expected, s_expected):
    result = slope_field(box0())
    i = row_at(result, point)
    assert result["normals"][i] == pytest.approx(normal, abs=1e-9)
    assert result["alpha"][i] == pytest.approx(alpha_expected, abs=1e-6)
    assert result["S"][i] == pytest.approx(s_expected, abs=1e-6)


def test_horizontal_up_is_near_one_and_vertical_is_near_zero():
    # Task-card acceptance wording: horizontal ~= 1, vertical ~= 0.
    result = slope_field(box0())
    top = row_at(result, (0.0, 0.0, 500.0))
    east = row_at(result, (500.0, 0.0, 0.0))
    assert result["S"][top] == pytest.approx(1.0, abs=1e-6)
    assert result["S"][east] == pytest.approx(0.0, abs=1e-6)


def test_45_degree_normal_gives_half():
    # Task-card acceptance wording: 45 deg ~= 0.5. Synthetic normal, not a box face.
    alpha, S = slope_suitability(np.array([(1.0, 0.0, 1.0)]) / math.sqrt(2.0))
    assert alpha[0] == pytest.approx(math.pi / 4, abs=1e-6)
    assert S[0] == pytest.approx(0.5, abs=1e-6)


def test_arccos_formula_not_equal_to_max_nz_0_shortcut():
    # SS1 warns the two are not the same function; pin a point where they diverge.
    n = np.array([(math.sqrt(2) / 2, 0.0, math.sqrt(2) / 2)])
    _, S = slope_suitability(n)
    shortcut = np.clip(n[:, 2], 0.0, None)
    assert S[0] == pytest.approx(0.5, abs=1e-6)
    assert shortcut[0] == pytest.approx(math.sqrt(2) / 2, abs=1e-6)
    assert S[0] != pytest.approx(shortcut[0], abs=1e-3)


def test_global_invariants_hold_on_box0():
    result = slope_field(box0())
    assert (result["S"] >= 0.0).all() and (result["S"] <= 1.0).all()
    assert (result["alpha"] >= 0.0).all() and (result["alpha"] <= math.pi + 1e-9).all()


def test_s_independent_of_sampling_order_same_mesh_twice():
    # "與風向/時刻無關(同 mesh 算兩次 S 應一致)" -- SS2 global check.
    a = slope_field(box0())
    b = slope_field(box0())
    assert np.allclose(a["S"], b["S"], atol=1e-9)

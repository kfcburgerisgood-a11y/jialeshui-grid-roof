"""T-011: salt smoke tests against the locked probe table + hard-gate checks.

Probe geometry, points and expected values are
``fields/T-011_salt_spec.md`` (風場 spec, GOLD, not modified here), §1/§2,
preset A (lambda=3000mm, Q=(2000,2000,0), C0: C=1). Hard gate (spec §5.4/§5.5
and the task card): salt must not read W/W_eff/V_wind/u_wind/WIND_DEFAULT,
and must be numerically independent of them (SE sea peak != ENE wind peak).
"""
import ast
import math
from pathlib import Path

import numpy as np
import pytest

from compas.datastructures import Mesh
from compas.geometry import Box

import grid_roof.fields_io as fields_io
from grid_roof.salt_field import (
    C_WETDRY,
    LAMBDA_MM,
    SHORE_POINT_Q,
    U_SEA,
    offshore_decay,
    salt_field,
    salt_suitability,
    sea_exposure,
)
from grid_roof.wind_field import wind_field

SALT_FIELD_SRC = Path(__file__).resolve().parent.parent / "grid_roof" / "salt_field.py"


def _box(center, size):
    mesh = Mesh.from_shape(Box(*size))  # compas Box is centred at the origin
    mesh.translate(list(center))
    return mesh


def box0():
    """BOX0: 1000^3 box centred at the origin (same as T-008/T-009/T-010)."""
    return _box((0.0, 0.0, 0.0), (1000.0, 1000.0, 1000.0))


def row_at(result, point, atol=1e-6):
    i = int(np.argmin(np.linalg.norm(result["points"] - np.array(point), axis=1)))
    assert np.allclose(result["points"][i], point, atol=atol), (result["points"][i], point)
    return i


def test_preset_a_constants_locked():
    assert U_SEA == pytest.approx((math.sqrt(2) / 2, -math.sqrt(2) / 2, 0.0), abs=1e-6)
    assert LAMBDA_MM == pytest.approx(3000.0)
    assert SHORE_POINT_Q == pytest.approx((2000.0, 2000.0, 0.0))
    assert C_WETDRY == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Hard gate H1: salt_field.py must not import/reference W, W_eff, V_wind,
# u_wind, or WIND_DEFAULT -- static AST scan (not a text grep, so prose in
# the module docstring explaining the hard gate itself cannot false-positive).
# ---------------------------------------------------------------------------
_FORBIDDEN_NAMES = {"W", "W_eff", "V_wind", "u_wind", "WIND_DEFAULT"}


def test_h1_salt_module_source_has_no_wind_identifiers():
    tree = ast.parse(SALT_FIELD_SRC.read_text(encoding="utf-8"))
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            used_names.add(node.attr)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                used_names.add(alias.asname or alias.name)
    hit = used_names & _FORBIDDEN_NAMES
    assert not hit, "salt_field.py references forbidden wind identifiers: {}".format(hit)


def test_h1_salt_module_only_imports_geometry_sampler_from_wind_field():
    tree = ast.parse(SALT_FIELD_SRC.read_text(encoding="utf-8"))
    imported_from_wind_field = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "wind_field":
            imported_from_wind_field.extend(alias.name for alias in node.names)
    assert imported_from_wind_field == ["sample_outer_surface"]


# ---------------------------------------------------------------------------
# Hard gate H2: same geometry, change u_wind/WIND_DEFAULT arbitrarily ->
# salt numbers do not change (dynamic, since salt_field takes no wind input).
# ---------------------------------------------------------------------------
def test_h2_salt_unchanged_when_wind_default_changes(monkeypatch):
    before = salt_field(box0())
    monkeypatch.setitem(fields_io.WIND_DEFAULT, "theta_deg", 310.0)
    after = salt_field(box0())
    assert np.allclose(before["salt"], after["salt"])
    assert np.allclose(before["E"], after["E"])


# ---------------------------------------------------------------------------
# Hard gate H3: ENE wind peak (east face) and SE salt peak are separable --
# a point with zero wind (W=0, leeward/calm) still carries high salt
# exposure, and vice versa the strongest-wind face is not the strongest-salt
# face.
# ---------------------------------------------------------------------------
def test_h3_wind_peak_and_salt_peak_are_separable_on_box0():
    salt = salt_field(box0())
    wind = wind_field(box0(), theta_deg=fields_io.WIND_DEFAULT["theta_deg"])

    i_east = row_at(salt, (500.0, 0.0, 0.0))
    i_south = row_at(salt, (0.0, -500.0, 0.0))

    # East face: the ENE wind's clear windward peak (W ~ 0.9239).
    assert wind["W"][i_east] == pytest.approx(0.9238795, abs=1e-6)
    # South face: wind-calm (leeward of ENE, W=0) yet carries the same high
    # sea exposure as the east face (both at E ~ 0.707) -- salt's SE peak
    # does not collapse onto the wind's ENE peak.
    assert wind["W"][i_south] == pytest.approx(0.0, abs=1e-6)
    assert salt["E"][i_south] == pytest.approx(salt["E"][i_east], abs=1e-6)
    assert salt["salt"][i_south] > 0.0


# ---------------------------------------------------------------------------
# SS2.1 direct normal -> E checks (no mesh needed).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("normal,e_expected", [
    (U_SEA, 1.0),                                    # n parallel to u_sea
    ((-U_SEA[0], -U_SEA[1], -U_SEA[2]), 0.0),        # n anti-parallel to u_sea
    ((1.0, 0.0, 0.0), math.sqrt(2) / 2),             # n_e
    ((0.0, 1.0, 0.0), 0.0),                          # n_n
])
def test_section_2_1_single_normal_sea_exposure(normal, e_expected):
    E = sea_exposure(np.array([normal]))
    assert E[0] == pytest.approx(e_expected, abs=1e-6)


def test_p1_se_direct_normal_full_salt():
    # P1_SE_edge (spec §2): n parallel to u_sea, on the sea side of the
    # fake shoreline -> E=1, A=1, C=1 -> salt=1.
    E, A, C, salt = salt_suitability(
        points=np.array([(3000.0, -3000.0, 0.0)]),  # SE of the Q=(2000,2000) shoreline
        normals=np.array([U_SEA]),
    )
    assert E[0] == pytest.approx(1.0, abs=1e-6)
    assert A[0] == pytest.approx(1.0, abs=1e-6)
    assert salt[0] == pytest.approx(1.0, abs=1e-6)


def test_p2_nw_direct_normal_zero_salt():
    # P2_NW (spec §2): n anti-parallel to u_sea -> E=0 -> salt=0 regardless of A.
    E, A, C, salt = salt_suitability(
        points=np.array([(-500.0, 500.0, 0.0)]),
        normals=np.array([(-U_SEA[0], -U_SEA[1], -U_SEA[2])]),
    )
    assert E[0] == pytest.approx(0.0, abs=1e-6)
    assert salt[0] == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# BOX0 face probes P3-P6 (spec §2 table).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("point,normal,e_expected,salt_is_zero", [
    ((500.0, 0.0, 0.0), (1.0, 0.0, 0.0), math.sqrt(2) / 2, False),    # P3_east
    ((0.0, -500.0, 0.0), (0.0, -1.0, 0.0), math.sqrt(2) / 2, False),  # P4_south
    ((0.0, 500.0, 0.0), (0.0, 1.0, 0.0), 0.0, True),                  # P5_north
    ((0.0, 0.0, 500.0), (0.0, 0.0, 1.0), 0.0, True),                  # P6_top
])
def test_box0_probes_p3_p6(point, normal, e_expected, salt_is_zero):
    result = salt_field(box0())
    i = row_at(result, point)
    assert result["normals"][i] == pytest.approx(normal, abs=1e-9)
    assert result["E"][i] == pytest.approx(e_expected, abs=1e-6)
    if salt_is_zero:
        assert result["salt"][i] == pytest.approx(0.0, abs=1e-6)
    else:
        assert result["salt"][i] > 0.0


def test_p3_and_p4_are_se_symmetric_same_salt():
    # Spec §2: P3_east and P4_south are "同級(SE對稱)" -- same E, same A (both
    # on BOX0's own sea-side of the fake shoreline through Q), same salt.
    result = salt_field(box0())
    i3 = row_at(result, (500.0, 0.0, 0.0))
    i4 = row_at(result, (0.0, -500.0, 0.0))
    assert result["E"][i3] == pytest.approx(result["E"][i4], abs=1e-6)
    assert result["A"][i3] == pytest.approx(result["A"][i4], abs=1e-6)
    assert result["salt"][i3] == pytest.approx(result["salt"][i4], abs=1e-6)


def test_offshore_decay_matches_shore_point_formula():
    # SS1.1 preset A worked example: Q=(2000,2000,0), lambda=3000mm.
    # P5_north (0,500,0): signed = (p-Q).u_sea = sqrt(2)/2 * (-500) < 0 -> decays.
    A = offshore_decay(np.array([(0.0, 500.0, 0.0)]))
    signed = (math.sqrt(2) / 2) * (0.0 - 500.0)
    assert A[0] == pytest.approx(math.exp(-abs(signed) / 3000.0), abs=1e-9)


# ---------------------------------------------------------------------------
# Global invariants.
# ---------------------------------------------------------------------------
def test_global_invariants_hold_on_box0():
    result = salt_field(box0())
    assert (result["salt"] >= 0.0).all() and (result["salt"] <= 1.0).all()
    assert (result["E"] >= 0.0).all() and (result["E"] <= 1.0).all()
    assert (result["A"] >= 0.0).all() and (result["A"] <= 1.0).all()
    assert (result["C"] == 1.0).all()


def test_salt_independent_of_sampling_order_same_mesh_twice():
    a = salt_field(box0())
    b = salt_field(box0())
    assert np.allclose(a["salt"], b["salt"], atol=1e-9)

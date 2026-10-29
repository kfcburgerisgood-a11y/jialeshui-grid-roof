"""T-008: W / V_wind / W_eff smoke tests against the locked probe table.

Probe geometry, points and expected values are
``fields/T-008_probe_expectations.md`` (風場 review, 2026-10-29), section A
-- not derived here. The real body_a_subd.stl run lives in
scripts/m3_wind_field.py and ops/reports/T-008.md. Not a validation of
W_eff -- see grid_roof/wind_field.py and
fields/T-006_epw_wind_sun_spec.md for what remains unverified.
"""
import numpy as np
import pytest

from compas.datastructures import Mesh
from compas.geometry import Box

from grid_roof import fields_io as F
from grid_roof.wind_field import sample_outer_surface, wind_field

U_WIND = np.array(F.u_wind_from_theta_deg(F.WIND_DEFAULT["theta_deg"]))  # ENE, ~(0.9238795, 0.3826834, 0)


def _box(center, size):
    mesh = Mesh.from_shape(Box(*size))  # compas Box is centred at the origin
    mesh.translate(list(center))
    return mesh


def box0():
    """BOX0 / TGT: 1000^3 box centred at the origin (table §A)."""
    return _box((0.0, 0.0, 0.0), (1000.0, 1000.0, 1000.0))


def blk():
    """BLK: 1000^3 windward blocker box, centre (3000,1000,0) (table §A)."""
    return _box((3000.0, 1000.0, 0.0), (1000.0, 1000.0, 1000.0))


def tgt_blk_scene():
    mesh = box0()
    mesh.join(blk())
    return mesh


def row_at(result, point, atol=1e-6):
    i = int(np.argmin(np.linalg.norm(result["points"] - np.array(point), axis=1)))
    assert np.allclose(result["points"][i], point, atol=atol), (result["points"][i], point)
    return i


def test_u_wind_matches_locked_ene_default():
    assert np.allclose(U_WIND, (0.9238795, 0.3826834, 0.0), atol=1e-6)


@pytest.mark.parametrize("point,normal,w_expected", [
    ((500.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.9238795),     # P1_E_windward
    ((-500.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0),          # P2_W_leeward
    ((0.0, 500.0, 0.0), (0.0, 1.0, 0.0), 0.3826834),      # P3_N_partial
    ((0.0, -500.0, 0.0), (0.0, -1.0, 0.0), 0.0),          # P4_S
    ((0.0, 0.0, 500.0), (0.0, 0.0, 1.0), 0.0),            # P5_top
    ((0.0, 0.0, -500.0), (0.0, 0.0, -1.0), 0.0),          # P5b_bottom
])
def test_box0_probes_w_and_unoccluded_w_eff(point, normal, w_expected):
    # BOX0 alone: no blocker, so every face is unoccluded (P1/P3/P5/P5b: V=1;
    # P2/P4: W=0 already forces W_eff=0, V not checked per the table's "不檢").
    result = wind_field(box0(), theta_deg=F.WIND_DEFAULT["theta_deg"])
    i = row_at(result, point)
    assert result["normals"][i] == pytest.approx(normal, abs=1e-9)
    assert result["W"][i] == pytest.approx(w_expected, abs=1e-6)
    assert result["W_eff"][i] == pytest.approx(w_expected, abs=1e-6)


def test_p6_occluded_vs_p7_control_shows_occlusion_effect():
    # P6: TGT's east face, same point as P1, with BLK present -> ray hits BLK's west face -> V=0.
    occluded = wind_field(tgt_blk_scene(), theta_deg=F.WIND_DEFAULT["theta_deg"])
    i6 = row_at(occluded, (500.0, 0.0, 0.0))
    assert occluded["W"][i6] == pytest.approx(0.9238795, abs=1e-6)
    assert occluded["V_wind"][i6] == pytest.approx(0.0)
    assert occluded["W_eff"][i6] == pytest.approx(0.0)

    # P7: identical point, BLK removed (= P1) -> unoccluded control.
    control = wind_field(box0(), theta_deg=F.WIND_DEFAULT["theta_deg"])
    i7 = row_at(control, (500.0, 0.0, 0.0))
    assert control["V_wind"][i7] == pytest.approx(1.0)
    assert control["W_eff"][i7] == pytest.approx(0.9238795, abs=1e-6)

    # The occlusion effect itself: same geometry, same point, blocker on vs off.
    assert occluded["W_eff"][i6] < control["W_eff"][i7]


def test_p8_near_miss_not_occluded_soft():
    # P8: TGT's north face; ray grazes past BLK (y~1535 > BLK's y<=1500) and misses.
    # fields/T-008_probe_expectations.md SS E.2 marks this "soft/informational", not a hard gate.
    result = wind_field(tgt_blk_scene(), theta_deg=F.WIND_DEFAULT["theta_deg"])
    i8 = row_at(result, (0.0, 500.0, 0.0))
    assert result["W"][i8] == pytest.approx(0.3826834, abs=1e-6)
    if result["V_wind"][i8] != pytest.approx(1.0):
        pytest.skip("P8 is a documented near-miss (soft check); implementation reads it as occluded")
    assert result["W_eff"][i8] == pytest.approx(0.3826834, abs=1e-6)


def test_p9_blocker_own_windward_face_is_not_self_occluded():
    # P9: BLK's own east face is windward and must not be shadowed by TGT (which sits upstream/west of it).
    result = wind_field(tgt_blk_scene(), theta_deg=F.WIND_DEFAULT["theta_deg"])
    i9 = row_at(result, (3500.0, 1000.0, 0.0))
    assert result["normals"][i9] == pytest.approx([1.0, 0.0, 0.0], abs=1e-9)
    assert result["W"][i9] == pytest.approx(0.9238795, abs=1e-6)
    assert result["V_wind"][i9] == pytest.approx(1.0)
    assert result["W_eff"][i9] == pytest.approx(0.9238795, abs=1e-6)


def test_global_invariants_hold_on_tgt_blk_scene():
    # Table's global assertions: W and W_eff in [0,1], W_eff <= W everywhere.
    result = wind_field(tgt_blk_scene(), theta_deg=F.WIND_DEFAULT["theta_deg"])
    assert (result["W"] >= 0.0).all() and (result["W"] <= 1.0).all()
    assert (result["W_eff"] >= 0.0).all() and (result["W_eff"] <= 1.0).all()
    assert (result["W_eff"] <= result["W"] + 1e-9).all()


def test_sample_outer_surface_gives_one_unit_normal_per_face():
    mesh = box0()
    points, normals = sample_outer_surface(mesh)
    assert points.shape == (mesh.number_of_faces(), 3)
    assert normals.shape == (mesh.number_of_faces(), 3)
    assert np.allclose(np.linalg.norm(normals, axis=1), 1.0)


def test_wind_field_defaults_to_locked_wind_default_theta():
    result = wind_field(box0())
    assert result["theta_deg"] == F.WIND_DEFAULT["theta_deg"]


def test_wind_default_conflict_is_flagged_as_assumed():
    # Light-touch per T-008: the ENE default's documented conflict with the
    # EPW's own summer statistics must stay labelled an assumption, not a
    # verified result.
    assert "推定" in F.WIND_DEFAULT["conflict"]

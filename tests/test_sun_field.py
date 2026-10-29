"""T-009: H_am / H_pm smoke tests against fields/T-009_sun_probe_spec.md.

That spec is Claude's own stand-in (no 風場-delivered sun probe spec existed
for T-009 at write time -- see the spec file's header) -- not a validation
of H_am/H_pm as an environmental field. See grid_roof/sun_field.py and
fields/T-006_epw_wind_sun_spec.md for what remains unverified.
"""
import numpy as np
import pytest

from compas.datastructures import Mesh
from compas.geometry import Box

from grid_roof.fields_io import sun_vector_ground_to_sun
from grid_roof.sun_field import (
    day_of_year,
    solar_position,
    sun_field,
    sun_slot_contribution,
)
from grid_roof.wind_field import sample_outer_surface, triangulate_faces

SUMMER_SOLSTICE = day_of_year(6, 21)
WINTER_SOLSTICE = day_of_year(12, 21)


def _box(center, size):
    mesh = Mesh.from_shape(Box(*size))  # compas Box is centred at the origin
    mesh.translate(list(center))
    return mesh


def box0():
    """TGT/BOX0: 1000^3 box centred at the origin (probe spec SS3/SS4)."""
    return _box((0.0, 0.0, 0.0), (1000.0, 1000.0, 1000.0))


def blk():
    """BLK: 1000^3 blocker box, centre (3000,0,1000) (probe spec SS4)."""
    return _box((3000.0, 0.0, 1000.0), (1000.0, 1000.0, 1000.0))


def tgt_blk_scene():
    mesh = box0()
    mesh.join(blk())
    return mesh


def row_at(points, point, atol=1e-6):
    i = int(np.argmin(np.linalg.norm(points - np.array(point), axis=1)))
    assert np.allclose(points[i], point, atol=atol), (points[i], point)
    return i


# -- SS2: solar_position sanity (spec SP1-SP4) --------------------------------

def test_summer_solstice_noon_altitude_near_zenith():
    # SP1: lat 22.006N is close to the Tropic of Cancer (~23.44N); at local
    # noon on the summer solstice the sun is almost directly overhead.
    altitude_deg, _ = solar_position(SUMMER_SOLSTICE, 12.0)
    assert altitude_deg > 85.0


def test_winter_solstice_noon_altitude_and_azimuth_are_lower_and_southerly():
    # SP2: declination ~-23.4 deg -> much lower noon sun, due south.
    altitude_deg, azimuth_deg = solar_position(WINTER_SOLSTICE, 12.0)
    assert 40.0 < altitude_deg < 50.0
    assert 170.0 < azimuth_deg < 190.0


@pytest.mark.parametrize("day", [SUMMER_SOLSTICE, WINTER_SOLSTICE])
@pytest.mark.parametrize("hour", [6.0, 7.0, 8.0, 9.0, 10.0, 11.0])
def test_morning_azimuth_is_in_the_eastern_half(day, hour):
    # SP3: before local noon, the sun's azimuth sits in the eastern half.
    _, azimuth_deg = solar_position(day, hour)
    assert 0.0 <= azimuth_deg <= 180.0


@pytest.mark.parametrize("day", [SUMMER_SOLSTICE, WINTER_SOLSTICE])
@pytest.mark.parametrize("hour", [13.0, 14.0, 15.0, 16.0, 17.0, 18.0])
def test_afternoon_azimuth_is_in_the_western_half(day, hour):
    # SP4: after local noon, the sun's azimuth sits in the western half.
    _, azimuth_deg = solar_position(day, hour)
    assert 180.0 <= azimuth_deg <= 360.0


# -- SS3: am/pm distribution differs on a synthetic box -----------------------

@pytest.mark.parametrize("day,point,normal", [
    (SUMMER_SOLSTICE, (500.0, 0.0, 0.0), (1.0, 0.0, 0.0)),    # D1_east_summer
    (WINTER_SOLSTICE, (500.0, 0.0, 0.0), (1.0, 0.0, 0.0)),
])
def test_east_face_gets_only_morning_sun(day, point, normal):
    result = sun_field(box0(), day, dt_hours=0.5)
    i = row_at(result["points"], point)
    assert result["normals"][i] == pytest.approx(normal, abs=1e-9)
    assert result["H_am"][i] > 0.0
    assert result["H_pm"][i] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("day,point,normal", [
    (SUMMER_SOLSTICE, (-500.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),  # D2_west_summer
    (WINTER_SOLSTICE, (-500.0, 0.0, 0.0), (-1.0, 0.0, 0.0)),
])
def test_west_face_gets_only_afternoon_sun(day, point, normal):
    result = sun_field(box0(), day, dt_hours=0.5)
    i = row_at(result["points"], point)
    assert result["normals"][i] == pytest.approx(normal, abs=1e-9)
    assert result["H_am"][i] == pytest.approx(0.0, abs=1e-9)
    assert result["H_pm"][i] > 0.0


def test_am_and_pm_distributions_differ_on_the_same_box():
    # The headline T-009 pass condition: am and pm distributions are not the
    # same. East vs west faces flip which half of the day they catch sun.
    result = sun_field(box0(), SUMMER_SOLSTICE, dt_hours=0.5)
    i_east = row_at(result["points"], (500.0, 0.0, 0.0))
    i_west = row_at(result["points"], (-500.0, 0.0, 0.0))
    assert result["H_am"][i_east] != pytest.approx(result["H_pm"][i_east])
    assert result["H_am"][i_west] != pytest.approx(result["H_pm"][i_west])
    assert result["H_am"][i_east] != pytest.approx(result["H_am"][i_west])


def test_north_face_summer_vs_winter_flips_from_lit_to_dark():
    # D3_north_summer / D6_north_winter: at this latitude, close to the
    # Tropic of Cancer, the summer-solstice sun passes just north of
    # zenith (declination > latitude), lighting the north face all day;
    # the winter-solstice sun stays well south, leaving it dark all day.
    summer = sun_field(box0(), SUMMER_SOLSTICE, dt_hours=0.5)
    winter = sun_field(box0(), WINTER_SOLSTICE, dt_hours=0.5)
    i = row_at(summer["points"], (0.0, 500.0, 0.0))
    assert summer["H_am"][i] > 0.0 and summer["H_pm"][i] > 0.0
    assert winter["H_am"][i] == pytest.approx(0.0, abs=1e-9)
    assert winter["H_pm"][i] == pytest.approx(0.0, abs=1e-9)


def test_global_invariants_hold_on_box0():
    result = sun_field(box0(), SUMMER_SOLSTICE, dt_hours=0.5)
    window_h = result["am_hours"][1] - result["am_hours"][0]
    assert (result["H_am"] >= 0.0).all() and (result["H_am"] <= window_h + 1e-9).all()
    assert (result["H_pm"] >= 0.0).all() and (result["H_pm"] <= window_h + 1e-9).all()


# -- SS4: occlusion smoke test (fixed altitude/azimuth, bypasses solar_position) ---

ALTITUDE_DEG = 30.0
AZIMUTH_DEG = 90.0


def test_occlusion_blocks_the_ray_and_drops_h_to_zero():
    # E1_occluded vs E2_control: same point/normal, same fixed sun
    # position; only the presence of BLK differs.
    points, normals = sample_outer_surface(tgt_blk_scene())
    vertices, triangles = triangulate_faces(tgt_blk_scene())
    i = row_at(points, (500.0, 0.0, 0.0))
    occluded_H = sun_slot_contribution(
        points, normals, vertices, triangles, ALTITUDE_DEG, AZIMUTH_DEG, dt_hours=1.0,
    )[i]

    points_c, normals_c = sample_outer_surface(box0())
    vertices_c, triangles_c = triangulate_faces(box0())
    i_c = row_at(points_c, (500.0, 0.0, 0.0))
    control_H = sun_slot_contribution(
        points_c, normals_c, vertices_c, triangles_c, ALTITUDE_DEG, AZIMUTH_DEG, dt_hours=1.0,
    )[i_c]

    assert occluded_H == pytest.approx(0.0)
    assert control_H == pytest.approx(1.0)
    assert occluded_H < control_H  # occlusion effect itself


def test_sun_slot_contribution_zero_below_horizon():
    points, normals = sample_outer_surface(box0())
    vertices, triangles = triangulate_faces(box0())
    H = sun_slot_contribution(points, normals, vertices, triangles,
                               altitude_deg=-5.0, azimuth_deg=90.0, dt_hours=1.0)
    assert (H == 0.0).all()


def test_sun_vector_matches_fixed_occlusion_geometry():
    # Sanity-check the locked (altitude, azimuth) -> s_k used by the
    # occlusion probes against the probe spec's worked-out s_k.
    s_k = sun_vector_ground_to_sun(ALTITUDE_DEG, AZIMUTH_DEG)
    assert np.allclose(s_k, (0.8660254, 0.0, 0.5), atol=1e-6)

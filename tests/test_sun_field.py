"""T-009: H_am / H_pm smoke tests against fields/T-009_sun_probe_spec.md.

That spec is the 風場-delivered, 挑洞-passed gold spec (see its header,
2026-10-30 note in its §5) -- not a validation of H_am/H_pm as an
environmental field. s_k and sample times come from
fields/T-009_sun_sample_times.csv (the same fixture, "方案 A"); this file
does not recompute solar position independently. See grid_roof/sun_field.py
and fields/T-006_epw_wind_sun_spec.md for what remains unverified.

Hard gates (fields/T-009_sun_probe_spec.md §3): P1/P2 am != pm, P7
occlusion drops H, §2.1 sign check.
"""
import numpy as np
import pytest

from compas.datastructures import Mesh
from compas.geometry import Box

from grid_roof.sun_field import (
    load_sun_sample_times,
    sun_field,
    sun_slot_contribution,
)
from grid_roof.wind_field import sample_outer_surface, triangulate_faces

SUMMER = "2025-06-21"
WINTER = "2025-12-21"


def _box(center, size):
    mesh = Mesh.from_shape(Box(*size))  # compas Box is centred at the origin
    mesh.translate(list(center))
    return mesh


def box0():
    """1000^3 box centred at the origin (probe spec §2, same convention as T-008 BOX0)."""
    return _box((0.0, 0.0, 0.0), (1000.0, 1000.0, 1000.0))


def row_at(points, point, atol=1e-6):
    i = int(np.argmin(np.linalg.norm(points - np.array(point), axis=1)))
    assert np.allclose(points[i], point, atol=atol), (points[i], point)
    return i


# -- CSV fixture sanity --------------------------------------------------------

def test_csv_fixture_rows_have_positive_altitude_and_both_halves():
    rows = load_sun_sample_times()
    assert len(rows) == 47
    assert all(r["alt_deg"] > 0.0 for r in rows)
    assert {r["half"] for r in rows} == {"am", "pm"}
    assert {r["date"] for r in rows} == {SUMMER, WINTER}


# -- §2.1: single-slot sign check (hard gate) ---------------------------------

def test_section_2_1_sign_check_summer_morning_and_winter_afternoon():
    # Closest CSV rows to the spec's worked examples (夏至 ~09:00, 冬至 ~15:00).
    rows = load_sun_sample_times()
    summer_0845 = next(r for r in rows if r["date"] == SUMMER and r["local_time"] == "08:45")
    winter_1445 = next(r for r in rows if r["date"] == WINTER and r["local_time"] == "14:45")

    mesh = box0()
    points, normals = sample_outer_surface(mesh)
    vertices, triangles = triangulate_faces(mesh)
    i_east = row_at(points, (500.0, 0.0, 0.0))
    i_west = row_at(points, (-500.0, 0.0, 0.0))
    i_north = row_at(points, (0.0, 500.0, 0.0))
    i_south = row_at(points, (0.0, -500.0, 0.0))

    h_summer = sun_slot_contribution(
        points, normals, vertices, triangles, summer_0845["s_k"], dt_hours=0.5,
    )
    assert h_summer[i_east] > 0.0 and h_summer[i_north] > 0.0
    assert h_summer[i_west] == pytest.approx(0.0) and h_summer[i_south] == pytest.approx(0.0)

    h_winter = sun_slot_contribution(
        points, normals, vertices, triangles, winter_1445["s_k"], dt_hours=0.5,
    )
    assert h_winter[i_west] > 0.0 and h_winter[i_south] > 0.0
    assert h_winter[i_east] == pytest.approx(0.0) and h_winter[i_north] == pytest.approx(0.0)


# -- P1/P2: east/west faces, summer (hard gate: am != pm) ---------------------

def test_east_face_summer_gets_only_morning_sun():
    result = sun_field(box0(), SUMMER, dt_hours=0.5)
    i = row_at(result["points"], (500.0, 0.0, 0.0))
    assert result["H_am"][i] > 0.0
    assert result["H_pm"][i] == pytest.approx(0.0, abs=1e-9)


def test_west_face_summer_gets_only_afternoon_sun():
    result = sun_field(box0(), SUMMER, dt_hours=0.5)
    i = row_at(result["points"], (-500.0, 0.0, 0.0))
    assert result["H_am"][i] == pytest.approx(0.0, abs=1e-9)
    assert result["H_pm"][i] > 0.0


def test_am_and_pm_distributions_differ_on_the_same_box():
    # The headline T-009 pass condition.
    result = sun_field(box0(), SUMMER, dt_hours=0.5)
    i_east = row_at(result["points"], (500.0, 0.0, 0.0))
    i_west = row_at(result["points"], (-500.0, 0.0, 0.0))
    assert result["H_am"][i_east] != pytest.approx(result["H_pm"][i_east])
    assert result["H_am"][i_west] != pytest.approx(result["H_pm"][i_west])
    assert result["H_am"][i_east] != pytest.approx(result["H_am"][i_west])


# -- P3/P4/P5: north/south faces, summer vs winter -----------------------------

def test_north_face_summer_lit_winter_dark():
    summer = sun_field(box0(), SUMMER, dt_hours=0.5)
    winter = sun_field(box0(), WINTER, dt_hours=0.5)
    i = row_at(summer["points"], (0.0, 500.0, 0.0))
    assert summer["H_am"][i] > 0.0 and summer["H_pm"][i] > 0.0
    assert winter["H_am"][i] == pytest.approx(0.0, abs=1e-9)
    assert winter["H_pm"][i] == pytest.approx(0.0, abs=1e-9)


def test_south_face_winter_lit_summer_dark():
    summer = sun_field(box0(), SUMMER, dt_hours=0.5)
    winter = sun_field(box0(), WINTER, dt_hours=0.5)
    i = row_at(summer["points"], (0.0, -500.0, 0.0))
    assert summer["H_am"][i] == pytest.approx(0.0, abs=1e-9)
    assert summer["H_pm"][i] == pytest.approx(0.0, abs=1e-9)
    assert winter["H_am"][i] > 0.0 and winter["H_pm"][i] > 0.0


# -- P6: top face, exact hour count (no self-occlusion on a convex box) -------

def test_top_face_hours_match_csv_sample_counts():
    for date in (SUMMER, WINTER):
        result = sun_field(box0(), date, dt_hours=0.5)
        i = row_at(result["points"], (0.0, 0.0, 500.0))
        assert result["H_am"][i] == pytest.approx(result["n_samples_am"] * 0.5)
        assert result["H_pm"][i] == pytest.approx(result["n_samples_pm"] * 0.5)


# -- P7: occlusion drops H (hard gate) -----------------------------------------

def test_occlusion_drops_summer_morning_h_on_east_face():
    # probe spec P7 geometry: main box [0,1000]^3, blocker box
    # X in [1500,2500], Y in [0,1000], Z in [0,3000]; east face centre
    # (1000, 500, 500). Low summer-morning sun angles clip the blocker;
    # high angles clear it, so only a drop (not a wipeout) is asserted.
    main = _box((500.0, 500.0, 500.0), (1000.0, 1000.0, 1000.0))
    blocker = _box((2000.0, 500.0, 1500.0), (1000.0, 1000.0, 3000.0))
    scene = main.copy()
    scene.join(blocker)

    unoccluded = sun_field(main, SUMMER, dt_hours=0.5)
    occluded = sun_field(scene, SUMMER, dt_hours=0.5)

    i_u = row_at(unoccluded["points"], (1000.0, 500.0, 500.0))
    i_o = row_at(occluded["points"], (1000.0, 500.0, 500.0))

    assert occluded["H_am"][i_o] < unoccluded["H_am"][i_u]
    assert occluded["H_am"][i_o] >= 0.0


# -- global invariants ---------------------------------------------------------

def test_global_invariants_hold_on_box0():
    for date in (SUMMER, WINTER):
        result = sun_field(box0(), date, dt_hours=0.5)
        am_cap = result["n_samples_am"] * 0.5
        pm_cap = result["n_samples_pm"] * 0.5
        assert (result["H_am"] >= 0.0).all() and (result["H_am"] <= am_cap + 1e-9).all()
        assert (result["H_pm"] >= 0.0).all() and (result["H_pm"] <= pm_cap + 1e-9).all()


# -- error handling -------------------------------------------------------------

def test_sun_field_raises_for_unknown_date():
    with pytest.raises(ValueError):
        sun_field(box0(), "2025-01-01", dt_hours=0.5)

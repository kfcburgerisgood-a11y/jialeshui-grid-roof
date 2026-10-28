"""M2 body: closed A test mesh -> shell field signs and thickness."""
import numpy as np
import pytest
from grid_roof import body as B
from grid_roof import Brief, design_roof
from grid_roof.checks import body_keep as check_body_keep
from grid_roof.design import box
from compas_vol.combinations import Subtraction


@pytest.fixture(scope="module")
def shell():
    return B.body_shell(B.body_field(B.test_box_a(), voxel=100.0))


def test_test_body_is_closed_and_in_mm():
    m = B.test_box_a()
    assert m.is_closed()
    p = np.array([m.vertex_coordinates(v) for v in m.vertices()])
    assert np.allclose(p.min(0), 0) and np.allclose(p.max(0), [10000, 6000, 4000])


def test_shell_signs(shell):
    d = lambda *p: float(shell.get_distance(p))  # noqa: E731
    assert d(5000, 3000, 150) == pytest.approx(-150, abs=40)    # mid-wall of floor: about -T/2
    assert d(5000, 3000, 2000) > 0                              # hollow inside
    assert d(5000, 3000, 4300) > 0                              # outside


def test_design_body_runs(shell):
    d = B.design_body(shell)
    assert float(d.roof.get_distance([5000, 3000, 150])) < 0


@pytest.fixture(scope="module")
def selected_body():
    mesh = B.test_box_a(2000, 1600, 1200)
    mesh.translate([-2300, 700, -800])
    return design_roof(Brief(voxel=100), body_mesh=mesh)


def test_body_entry_uses_mesh_bbox_and_hollow_shell(selected_body):
    body = selected_body
    assert body.bounds == (-2300, 700, -800, -300, 2300, 400)
    assert body.design.roof.get_distance([-1300, 1500, -200]) > 0  # cavity crosses negative Z
    assert body.design.roof.get_distance([-1300, 1500, -650]) < 0
    assert body.design.roof.get_distance([-1300, 1500, -1100]) > 0


def test_backplate_is_the_inner_band_not_the_whole_shell():
    field = box(-1000, -1000, -1000, 1000, 1000, 1000)
    kept = B.body_keep(field, thickness=300, b_min=100)
    # Outer skin, plate midpoint, cavity; translate/rotate no world-Z assumption.
    for axis in range(3):
        for sign in (-1, 1):
            p = [0, 0, 0]
            for coordinate, expected in ((950, 150), (750, -50), (600, 100)):
                p[axis] = sign * coordinate
                assert kept.get_distance(p) == pytest.approx(expected)
                assert float(kept.get_distance_numpy(*map(np.asarray, p))) == pytest.approx(expected)


@pytest.mark.parametrize("thickness,b_min", [(300, 0), (300, -1), (300, 301), (0, 1),
                                                   (float("inf"), 100), (300, float("nan"))])
def test_backplate_rejects_invalid_thickness(thickness, b_min):
    with pytest.raises(ValueError, match="0 < b_min <= body_thickness"):
        B.body_keep(box(0, 0, 0, 1000, 1000, 1000), thickness, b_min)


def test_keep_check_detects_loss_and_design_restores_it(selected_body):
    from dataclasses import replace
    from grid_roof.design import Design

    body = selected_body
    initial = check_body_keep(body)
    assert initial["kept_samples"] > 0
    assert initial["missing_samples"] == initial["keep_outside_shell_samples"] == 0
    # A deliberately destructive diagnostic cutter, not a change to opening/water/pores rules.
    removed = Subtraction(body.shell, box(*body.bounds))
    lost = check_body_keep(replace(body, design=Design(removed, removed)))
    assert lost["missing_samples"] > 0
    assert lost["max_missing_depth_mm"] > 0
    restored = replace(body, design=B.design_body(removed, body.keep))
    assert check_body_keep(restored)["missing_volume_mm3"] == 0
    outer_skin = [-1300, 1500, -750]
    assert body.shell.get_distance(outer_skin) < 0
    assert restored.design.roof.get_distance(outer_skin) > 0  # keep does not refill the whole shell


def test_body_parameters_round_trip(tmp_path):
    brief = Brief(body_thickness=400, b_min=150, voxel=100)
    assert Brief.load(brief.save(tmp_path / "body_brief.json")) == brief

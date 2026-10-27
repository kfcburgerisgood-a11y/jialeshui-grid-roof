"""M2 body: closed A test mesh -> shell field signs and thickness."""
import numpy as np
import pytest
from grid_roof import body as B


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

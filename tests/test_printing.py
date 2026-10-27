"""A sample to print: the right size, on the plate, closed, checked, and refused when it cannot be made."""

import pytest

import grid_roof as roof
from compas_vol.meshing import is_watertight
from grid_roof import nodes
from grid_roof.printing import PRINTERS, sample

pytest.importorskip("skfmm", reason="needs the processes extra")


@pytest.fixture(scope="module")
def brief():
    return roof.Brief(voxel=60.0)


@pytest.fixture(scope="module")
def built(brief):
    return roof.design_roof(brief, roof.Drawing.sample())


@pytest.fixture(scope="module")
def node(brief, built):
    return sample(brief, built.design, built.weathering, "node_1_1", scale=20, voxel=40)


def test_a_sample_is_its_piece_at_scale_on_the_plate(built, node):
    piece = built.assembly.find("node_1_1")
    assert node.vertices[:, 2].min() == pytest.approx(0.0)
    for printed, full in zip(node.size, piece.size):
        assert printed == pytest.approx(full / 20, abs=3.0)


def test_a_sample_is_closed_and_checked(node):
    assert is_watertight(node.vertices, node.faces)
    assert node.report.pieces == 1
    assert node.fits
    assert "fits the core-one-l: yes" in node.summary()


def test_a_sample_too_big_for_the_printer_says_so(brief, built):
    beam = sample(brief, built.design, built.weathering, "beam_x1_0_0", scale=10, voxel=60)
    assert max(beam.size) > PRINTERS["core-one-l"][0]
    assert not beam.fits and "choose a larger scale number" in beam.summary()


def test_unknown_printers_and_pieces_are_refused(brief, built):
    with pytest.raises(ValueError, match="core-one-l"):
        sample(brief, built.design, built.weathering, "node_1_1", printer="ender")
    with pytest.raises(ValueError, match="node_1_1"):
        sample(brief, built.design, built.weathering, "panel_9")


def test_the_component_function_writes_an_stl(tmp_path, brief, built):
    path = str(tmp_path / "node.stl")
    vertices, faces, text = nodes.sample(built, brief, "node_0_0", scale=20, file=path)
    assert (tmp_path / "node.stl").stat().st_size > 1000
    assert text.startswith("node_0_0 at 1:20")

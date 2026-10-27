"""M2 body: a closed mesh -> distance field -> shell (inside negative, outside positive, mm).

Parameters marked 推定 (provisional; framework §8 item 6 is undecided):
``SHELL_T`` = 300 mm, ``VOXEL`` = 40 mm preview voxel.

:func:`design_body` is the minimal path from a body to :func:`grid_roof.design.design`:
the shell stands in for the slab's solid, its pores, its keep. Water, openings,
pores and planters are NOT applied here -- they still assume the flat slab
(``brief.thickness``, a height field over ``brief.length x brief.width``).
"""

import math

from compas.datastructures import Mesh
from compas.geometry import Box

from compas_vol.modifications import Shell
from compas_vol.primitives import VolGrid

from .design import Slab, Soffit, Voids, design

__all__ = ["SHELL_T", "VOXEL", "PADDING", "test_box_a", "load_body", "resolution_for", "body_field", "body_shell",
           "design_body"]

SHELL_T = 300.0     # 推定 shell thickness, mm
VOXEL = 40.0        # 推定 preview voxel, mm
PADDING = 400.0     # space around the mesh, mm (> T, covers the shell)


def test_box_a(x=10000.0, y=6000.0, z=4000.0):
    """The A test body: a closed box, corner at the origin, mm. A test mesh, not an authored SubD."""
    mesh = Mesh.from_shape(Box(x, y, z))
    mesh.translate([x / 2, y / 2, z / 2])
    return mesh


def load_body(path):
    """Read a closed mesh (OBJ / STL / PLY) in mm."""
    path = str(path)
    if path.lower().endswith(".stl"):
        return Mesh.from_stl(path)
    if path.lower().endswith(".ply"):
        return Mesh.from_ply(path)
    return Mesh.from_obj(path)


def resolution_for(mesh, voxel=VOXEL, padding=PADDING):
    """Samples along the longest padded side so one sample is about ``voxel`` mm."""
    pts = [mesh.vertex_coordinates(v) for v in mesh.vertices()]
    longest = max(max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3))
    return int(math.ceil((longest + 2 * padding) / voxel))


def body_field(mesh, voxel=VOXEL, padding=PADDING):
    """The body's distance field (:class:`VolGrid`)."""
    return VolGrid.from_mesh(mesh, resolution=resolution_for(mesh, voxel, padding), padding=padding)


def body_shell(field, thickness=SHELL_T):
    """The shell, thickened inwards (``side=1.0``)."""
    return Shell(field, thickness, 1.0)


def design_body(shell):
    """The minimal body path to ``design``: no water, voids or pores yet (they assume the flat slab)."""
    s = Slab(deck=None, solid=shell, flat=shell)
    return design(s, Soffit(porous=shell, deep=None), Voids([], [], []), shell)




"""M2 body: a closed mesh -> distance field -> shell (inside negative, outside positive, mm).

Parameters marked 推定 (provisional; framework §8 item 6 is undecided):
``SHELL_T`` = 300 mm, ``VOXEL`` = 40 mm preview voxel.

:func:`build_body` builds a shell with a separate inner backplate keep.
:func:`design_body` composes it through :func:`grid_roof.design.design`. Water, openings,
pores and planters are NOT applied here -- they still assume the flat slab
(``brief.thickness``, a height field over ``brief.length x brief.width``).
"""

import math
from dataclasses import dataclass

from compas.datastructures import Mesh
from compas.geometry import Box

from compas_vol.modifications import Offset, Shell
from compas_vol.primitives import VolGrid

from .design import Slab, Soffit, Voids, design

__all__ = ["SHELL_T", "VOXEL", "PADDING", "test_box_a", "load_body", "resolution_for", "body_field", "body_shell",
           "design_body", "body_keep", "mesh_bounds", "BodyRoof", "build_body"]

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


def mesh_bounds(mesh):
    """World-space mesh bbox, including negative coordinates, in mm."""
    pts = [mesh.vertex_coordinates(v) for v in mesh.vertices()]
    return tuple(min(p[i] for p in pts) for i in range(3)) + tuple(max(p[i] for p in pts) for i in range(3))


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


def body_keep(field, thickness, b_min):
    """Inner backplate: ``-T <= field <= -(T-b_min)``; independent of world Z.

    Both thicknesses are provisional. This distance band constructs keep;
    it does not verify physical thickness or clearance on a thin curved body.
    """
    if not (math.isfinite(thickness) and math.isfinite(b_min) and 0 < b_min <= thickness):
        raise ValueError("body keep requires finite 0 < b_min <= body_thickness (mm)")
    return Shell(Offset(field, -(thickness - b_min)), b_min, 1.0)


def design_body(shell, keep=None):
    """Compose through ``design``; no water, voids or pores yet (flat-slab rules).

    Omitting keep preserves the T-003/T-004 smoke scripts' whole-shell keep.
    The selectable entry uses :func:`body_keep` instead.
    """
    s = Slab(deck=None, solid=shell, flat=shell)
    return design(s, Soffit(porous=shell, deep=None), Voids([], [], []), shell if keep is None else keep)


@dataclass
class BodyRoof:
    """Body route through design only; slab water, pores, kit and weathering are not connected."""

    field: object
    shell: object
    keep: object
    design: object
    bounds: tuple      # mesh bbox in world coordinates, not brief.bounds


def build_body(brief, mesh):
    """Closed mesh in mm -> field -> shell + inner backplate -> design."""
    if not mesh.is_closed():
        raise ValueError("body_shell requires a closed mesh in mm")
    field = body_field(mesh, voxel=brief.voxel)
    keep = body_keep(field, brief.body_thickness, brief.b_min)
    shell = body_shell(field, brief.body_thickness)
    return BodyRoof(field, shell, keep, design_body(shell, keep), mesh_bounds(mesh))


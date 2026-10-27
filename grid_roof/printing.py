"""A piece of the roof as a printed sample, for a Prusa CORE One L or XL.

The piece is built as for the kit, then made printable at the scale chosen:
nothing thinner than the printer can hold, pins loose enough to fit their
sockets, and placed as it was built, soffit on the plate. Measured on these
pieces, that orientation leaves the least unsupported area, and the pores open
downwards, so supports grown from the plate can be pulled out from below.
"""

from dataclasses import dataclass, replace

import numpy as np

from .design import kit

__all__ = ["PRINTERS", "Sample", "sample"]

#: Build volume, x, y, z in mm, of the printers a sample is checked against.
PRINTERS = {
    "core-one-l": (300.0, 300.0, 330.0),
    "xl": (360.0, 360.0, 360.0),
}

#: Printed sizes, in mm, for a 0.4 mm nozzle.
MIN_WALL = 1.2      # three extrusion lines
PIN_FIT = 0.2       # radial clearance of a printed pin in its socket
FACET = 0.6         # the finest step worth sampling: a voxel no coarser than this at print size


@dataclass
class Sample:
    """A printable sample: the mesh at print size, in mm, sitting on z = 0, and what the checks found."""

    name: str
    scale: float
    voxel: float
    vertices: np.ndarray
    faces: np.ndarray
    report: object
    printer: str

    @property
    def size(self):
        """tuple: The printed bounding box, x, y, z, in mm."""
        return tuple(float(v) for v in self.vertices.max(axis=0) - self.vertices.min(axis=0))

    @property
    def fits(self):
        """bool: Whether it fits the printer, turned on the plate if need be."""
        x, y, z = self.size
        bx, by, bz = PRINTERS[self.printer]
        return z <= bz and ((x <= bx and y <= by) or (x <= by and y <= bx))

    def summary(self):
        """str: Size, fit and the printability checks, to read before slicing."""
        x, y, z = self.size
        lines = [
            "{} at 1:{:g}: {:.0f} x {:.0f} x {:.0f} mm, sampled at {:.0f} mm ({:.2f} mm printed)".format(
                self.name, self.scale, x, y, z, self.voxel, self.voxel / self.scale),
            "fits the {}: {}".format(self.printer, "yes" if self.fits else "no; choose a larger scale number"),
            str(self.report),
        ]
        lines.append("slice: docs/print.md; supports on the build plate only, added where PrusaSlicer needs them")
        return "\n".join(lines)


def sample(brief, design, weathering, name, scale=20.0, voxel=None, printer="core-one-l"):
    """Step 15, a sample to print: piece ``name`` at 1:``scale``. *Canvas: Roof Print.*

    Parameters
    ----------
    brief : :class:`grid_roof.Brief`
        The brief the roof was designed with.
    design : :class:`grid_roof.Design`
        From :func:`grid_roof.design` (Step 8).
    weathering : callable
        From :func:`grid_roof.weathering` (Step 11).
    name : str
        A piece of the kit, such as ``"panel_0_1_00"``.
    scale : float
        1:``scale``. At 20, a 3 m panel prints 150 mm square.
    voxel : float, optional
        Sample spacing in mm at full size. Defaults to 0.6 mm at print size, and
        never finer than 12 mm, which a panel needs about 2.6 GB for.
    printer : str
        A key of :data:`PRINTERS`.

    Returns
    -------
    :class:`Sample`
    """
    from compas_vol import nodes
    from compas_vol.fabrication import inspect, keep_largest
    from compas_vol.processes import opened

    if printer not in PRINTERS:
        raise ValueError("No printer {!r}; choose from {}".format(printer, ", ".join(PRINTERS)))
    scale = float(scale)
    voxel = float(voxel or max(12.0, FACET * scale))

    # The same cuts, with pins loose enough for a printer at this scale.
    assembly = kit(replace(brief, dowel_fit=PIN_FIT * scale), design)
    names = [p.name for p in assembly]
    if name not in names:
        raise ValueError("No piece {!r}; the kit has {}".format(name, ", ".join(names)))
    piece = assembly.find(name)
    _, finished, _ = next(assembly.build(weathering, voxel, brief.halo, pieces=[piece]))

    # Nothing thinner than the printer can hold: slivers where the cut meets a pore.
    field, _ = keep_largest(opened(finished, MIN_WALL * scale / 2))

    report = inspect(field.values / scale, spacing=tuple(np.asarray(field.spacing) / scale), min_wall=MIN_WALL)
    vertices, faces = nodes.mesh(field.to_volume(), None, None, 0)
    vertices = np.asarray(vertices, dtype=float) / scale
    vertices -= vertices.min(axis=0)
    return Sample(name, scale, voxel, vertices, np.asarray(faces), report, printer)

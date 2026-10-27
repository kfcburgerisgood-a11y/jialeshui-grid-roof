"""
One piece as a sample to print at 1:scale: nothing thinner than a 0.4 mm
nozzle can hold, pins with 0.2 mm play, soffit on the plate. About three
minutes for a panel at 1:20, so keep run False until the design is settled.

    Args:
        roof: From Roof Design.
        brief: The same brief Roof Design used.
        name: A piece's name, from Roof Design's names. Defaults to the first.
        scale: Print at 1:scale. Default 20: a 3 m panel prints 150 mm square.
        printer: core-one-l (default, 300 x 300 x 330 mm) or xl (360 mm cube).
        file: An STL path to write, ready for PrusaSlicer. Optional.
        run: False holds the last result. Leave it False until the design is settled: a sample takes minutes.
    Returns:
        mesh: The sample at print size, in mm, on the plate.
        report: Size, fit, and the printability checks.
"""
# Rhino 8 evaluates the type annotations it adds to RunScript, so both names
# must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
from ghpythonlib.componentbase import executingcomponent as component


class GridRoofPrint(component):
    def RunScript(self, roof, brief, name: str, scale: float, printer: str, file: str, run: bool):
        from compas_vol.ghpython import mesh_to_rhino
        from grid_roof import nodes

        # The script instance survives between solutions, so it can hold a result.
        if run is not False and roof is not None and brief is not None:
            name = name or nodes.pieces(roof)[0][0]
            vertices, faces, report = nodes.sample(roof, brief, name, scale, printer, file or None)
            self.held = (mesh_to_rhino(vertices, faces), report)
        return getattr(self, "held", (None, None))

"""T-010: minimal S (slope suitability) smoke test on a body's outer surface.

Scope (``ops/tasks/T-010.md``; 總綱 §5.3; ``fields/T-010_slope_spec.md`` --
GOLD, not modified here): ``alpha = arccos(n.z)``; ``S = clamp((alpha_max -
alpha) / (alpha_max - alpha_min), 0, 1)``. Reuses ``wind_field``'s
``sample_outer_surface`` unchanged -- no new surface sampler, no
recomputation of W/H. S is independent of wind direction/time -- this
module does not read ``u_wind``, EPW, or the sun CSV.

Constants below (``ALPHA_MIN_RAD=0``, ``ALPHA_MAX_RAD=pi/2``) are the
spec's "預設 A", an assumption for the smoke test, not an author-settled
threshold (``fields/T-010_slope_spec.md`` SS1, SS1.1).
"""
from __future__ import annotations

import math

import numpy as np

from .wind_field import sample_outer_surface

__all__ = [
    "ALPHA_MIN_RAD",
    "ALPHA_MAX_RAD",
    "slope_suitability",
    "slope_field",
]

#: 預設 A (``fields/T-010_slope_spec.md`` SS1) -- 推定, not an author-settled 門檻.
ALPHA_MIN_RAD = 0.0
ALPHA_MAX_RAD = math.pi / 2


def slope_suitability(normals, alpha_min=ALPHA_MIN_RAD, alpha_max=ALPHA_MAX_RAD):
    """alpha (rad) and S (0-1) from unit outward normals, per the arccos formula.

    ``alpha = arccos(clamp(n.z, -1, 1))``; ``S = clamp((alpha_max - alpha) /
    (alpha_max - alpha_min), 0, 1)``. Must go through ``arccos`` -- not
    ``max(n.z, 0)`` -- per ``fields/T-010_slope_spec.md`` SS1 (the two are
    not the same function except at the probe points).
    """
    normals = np.asarray(normals, dtype=float)
    cos_alpha = np.clip(normals[:, 2], -1.0, 1.0)
    alpha = np.arccos(cos_alpha)
    S = np.clip((alpha_max - alpha) / (alpha_max - alpha_min), 0.0, 1.0)
    return alpha, S


def slope_field(mesh, alpha_min=ALPHA_MIN_RAD, alpha_max=ALPHA_MAX_RAD):
    """alpha, S (dimensionless, 0-1) on ``mesh``'s outer face samples.

    Returns
    -------
    dict
        ``points``, ``normals`` (mm, unit), ``alpha`` (rad), ``S`` (0-1),
        one row per face sample, plus the ``alpha_min``/``alpha_max``
        actually used, for the report.
    """
    points, normals = sample_outer_surface(mesh)
    alpha, S = slope_suitability(normals, alpha_min=alpha_min, alpha_max=alpha_max)
    return dict(
        points=points, normals=normals, alpha=alpha, S=S,
        alpha_min=alpha_min, alpha_max=alpha_max,
    )

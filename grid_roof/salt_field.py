"""T-011: minimal salt (鹽分) smoke test on a body's outer surface.

Scope (``ops/tasks/T-011.md``; 總綱 §5.3; ``fields/T-011_salt_spec.md`` --
GOLD, not modified here): ``salt = max(0, n.u_sea) * A_offshore * C_wetdry``.
Reuses ``wind_field``'s ``sample_outer_surface`` for geometry only (points +
outward unit normals) -- same pattern as ``slope_field`` (T-010) -- no new
surface sampler, no recomputation of W/H.

HARD GATE (spec §5.4/§5.5; 挑洞): salt is driven by ``u_sea`` (面海, assumed
SE 135 deg), not by wind. This module must never import or reference ``W``,
``W_eff``, ``V_wind``, ``u_wind``, or ``WIND_DEFAULT`` from ``wind_field`` /
``fields_io`` -- the SE salt peak and the ENE wind peak are deliberately
separable (spec §5), not the same mechanism. ``tests/test_salt_field.py``
checks this both statically (AST scan for those names) and dynamically
(salt unchanged if ``WIND_DEFAULT`` is changed).

Constants below (``U_SEA``, ``LAMBDA_MM``, ``SHORE_POINT_Q``, ``C_WETDRY``)
are the spec's 推定 defaults for a synthetic smoke test, not validated site
data -- see ``fields/T-011_salt_spec.md`` §4 for the open items (u_sea
bearing, real shoreline/lambda, wet-dry mechanism, terrain provenance).
"""
from __future__ import annotations

import math

import numpy as np

from .wind_field import sample_outer_surface

__all__ = [
    "U_SEA",
    "LAMBDA_MM",
    "SHORE_POINT_Q",
    "C_WETDRY",
    "sea_exposure",
    "offshore_decay",
    "salt_suitability",
    "salt_field",
]

#: u_sea, 陸->海單位向量, SE 135 deg 推定 (fields/T-011_salt_spec.md SS1).
U_SEA = (math.sin(math.radians(135.0)), math.cos(math.radians(135.0)), 0.0)

#: 離岸衰減特徵長度 (mm), 預設 A 推定 (spec SS1.1).
LAMBDA_MM = 3000.0

#: 假海岸線上一點, 法線 = U_SEA (指向海), 預設 A 推定 (spec SS1.1).
SHORE_POINT_Q = (2000.0, 2000.0, 0.0)

#: 乾濕循環, C0 預設: 未建模, 恆為 1 (spec SS1.2).
C_WETDRY = 1.0


def sea_exposure(normals, u_sea=U_SEA):
    """``E = max(0, n . u_sea)`` -- per-sample face-sea exposure, 0-1 range for unit n."""
    normals = np.asarray(normals, dtype=float)
    u_sea = np.asarray(u_sea, dtype=float)
    return np.clip(normals @ u_sea, 0.0, None)


def offshore_decay(points, u_sea=U_SEA, q=SHORE_POINT_Q, lam=LAMBDA_MM):
    """``A_offshore`` per spec SS1.1 預設 A: a signed distance to a fake shoreline plane.

    ``signed = (p - q) . u_sea``; ``A = 1`` on the sea side (``signed >= 0``),
    else ``A = exp(-|signed| / lam)`` decaying inland.
    """
    points = np.asarray(points, dtype=float)
    u_sea = np.asarray(u_sea, dtype=float)
    q = np.asarray(q, dtype=float)
    signed = (points - q) @ u_sea
    return np.where(signed >= 0.0, 1.0, np.exp(-np.abs(signed) / lam))


def salt_suitability(points, normals, u_sea=U_SEA, q=SHORE_POINT_Q, lam=LAMBDA_MM, c=C_WETDRY):
    """``E``, ``A``, ``C``, ``salt = E * A * C`` for each (point, normal) pair.

    Formula per ``fields/T-011_salt_spec.md`` §0/§1 -- no ``W``/``u_wind``
    term anywhere in this computation.
    """
    E = sea_exposure(normals, u_sea=u_sea)
    A = offshore_decay(points, u_sea=u_sea, q=q, lam=lam)
    C = np.full(E.shape, float(c))
    salt = E * A * C
    return E, A, C, salt


def salt_field(mesh, u_sea=U_SEA, q=SHORE_POINT_Q, lam=LAMBDA_MM, c=C_WETDRY):
    """E, A, C, salt (dimensionless, 0-1) on ``mesh``'s outer face samples.

    Returns
    -------
    dict
        ``points``, ``normals`` (mm, unit), ``E``, ``A``, ``C``, ``salt``
        (0-1), one row per face sample, plus the ``u_sea``/``q``/``lam``/``c``
        actually used, for the report.
    """
    points, normals = sample_outer_surface(mesh)
    E, A, C, salt = salt_suitability(points, normals, u_sea=u_sea, q=q, lam=lam, c=c)
    return dict(
        points=points, normals=normals, E=E, A=A, C=C, salt=salt,
        u_sea=list(u_sea), q=list(q), lam=lam, c=c,
    )

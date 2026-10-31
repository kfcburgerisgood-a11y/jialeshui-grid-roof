"""T-012: minimal light-opening inversion smoke test (pure geometry, no SDF).

Scope (``ops/tasks/T-012.md``; 總綱 §5.4 / §6.2 step 5 / M4): given a target
spot ``y`` on a floor plane and the sun direction ``s`` at one instant,
find the opening ``x`` on the shell's outer surface such that ``x = y +
lambda*s`` with ``lambda > 0`` (the hole sits *above* the spot, along the
sun). ``forward_spot`` runs the same ray back from ``x`` along ``-s`` to
check the spot it actually lands on, so ``spot_error`` can be compared
against the smoke-test bound ``Brief.e_max``
(``fields/T-012_openings_smoke_spec.md``).

This module only does the algebra for a flat horizontal shell/floor (a
synthetic box top, not a real roof shell), and a minimal axis-aligned
"keep band" stand-in for ``pierces_keep`` -- it does not touch
``voids``/``drawing``/``water``/``pores`` or the real ``body_keep`` SDF,
and does not recompute solar position (``s`` is taken as given, e.g. from
``sun_field.load_sun_sample_times``).
"""
from __future__ import annotations

import math

import numpy as np

__all__ = ["invert_opening", "forward_spot", "spot_error", "axes_parallel", "pierces_keep"]


def _unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    if n <= 0:
        raise ValueError("zero-length direction vector")
    return v / n


def invert_opening(y, s, shell_z, eps=1e-9):
    """Hole position ``x`` on the flat outer shell ``z=shell_z``, from target spot ``y`` and sun ``s``.

    Solves ``x = y + lambda*s`` for the ``lambda`` that lands ``x`` on
    ``z=shell_z`` (mm), requiring ``lambda > 0`` (總綱 §5.4: the hole is
    above the spot, along the sun). ``axis`` is ``s`` unitized -- the
    opening's bore axis.

    Raises
    ------
    ValueError
        If ``s`` does not point upward (``s_z <= eps``), or the shell is
        not strictly above ``y`` along ``s`` (``lambda <= 0``).

    Returns
    -------
    tuple
        ``(x, lam, axis)`` -- ``x`` mm (3,), ``lam`` mm, ``axis`` unit (3,).
    """
    y = np.asarray(y, dtype=float)
    axis = _unit(s)
    if axis[2] <= eps:
        raise ValueError("sun direction s_z={!r} is not above the horizon".format(axis[2]))
    lam = (shell_z - y[2]) / axis[2]
    if lam <= 0:
        raise ValueError("non-positive lambda={!r}; shell_z must be above y along s".format(lam))
    x = y + lam * axis
    return x, float(lam), axis


def forward_spot(x, s, floor_z=0.0, eps=1e-9):
    """Spot ``y_actual`` hit by firing from opening ``x`` back along ``-s`` to ``z=floor_z`` (mm).

    The check half of the inversion: this is the same ray as
    :func:`invert_opening`, run in the opposite direction, so composing
    the two should round-trip ``y`` up to floating-point error for a flat
    shell and floor.
    """
    x = np.asarray(x, dtype=float)
    axis = _unit(s)
    if axis[2] <= eps:
        raise ValueError("sun direction s_z={!r} is not above the horizon".format(axis[2]))
    lam = (x[2] - floor_z) / axis[2]
    return x - lam * axis


def spot_error(y_actual, y_target):
    """Euclidean distance between actual and target spot, in mm (``e`` of §5.4)."""
    return float(np.linalg.norm(np.asarray(y_actual, dtype=float) - np.asarray(y_target, dtype=float)))


def axes_parallel(a, b, tol_deg=1e-6):
    """Whether two opening axes are parallel within ``tol_deg`` (same-instant multi-hole check)."""
    a, b = _unit(a), _unit(b)
    cos_angle = np.clip(np.dot(a, b), -1.0, 1.0)
    return math.degrees(math.acos(cos_angle)) <= tol_deg


def pierces_keep(x, keep_bands):
    """Minimal keep stub: True if ``x``'s (x, y) falls inside an axis-aligned keep band.

    ``keep_bands`` is ``{"xbands": [(lo, hi), ...], "ybands": [(lo, hi), ...]}``,
    mirroring ``checks.beam_depth``'s ``beams.xbands``/``ybands`` -- a
    simple stand-in for a real keep SDF (e.g. a beam strip), not
    ``body_keep`` itself. A hole landing in a band is rejected; it may not
    be counted as a passing opening.
    """
    x = np.asarray(x, dtype=float)
    px, py = x[0], x[1]
    for lo, hi in keep_bands.get("xbands", []):
        if lo < px < hi:
            return True
    for lo, hi in keep_bands.get("ybands", []):
        if lo < py < hi:
            return True
    return False

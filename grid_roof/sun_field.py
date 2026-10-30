"""T-009: minimal H_am / H_pm smoke test (direct-sun hours, with self-occlusion).

Scope (``ops/tasks/T-009.md``; 總綱 §5.3): ``H_am, H_pm = Sum_k V_k(x) *
I[n.s_k > 0] * dt`` -- morning/afternoon direct-sun hours on a mesh's outer
surface. Reuses ``wind_field``'s sampling/ray machinery
(``sample_outer_surface``, ``triangulate_faces``, ``ray_mesh_occluded``)
unchanged. Does not touch ``body_shell``, ``body_keep``, ``design``,
S/salt, or any opening/void/water rule.

Time/``s_k`` source: ``fields/T-009_sun_sample_times.csv``, the 挑洞-passed
fixture delivered by the parallel 風場 review alongside
``fields/T-009_sun_probe_spec.md`` (2026-10-29). Per ``ops/notes_T-009_for_claude.txt``
("方案 A"), this module reads that CSV rather than recomputing solar
position (day/time -> altitude/azimuth) independently, since an
independently-recomputed solar position would drift from the reviewed
fixture by the formula's own stated accuracy (~0.5 deg) and make the two
not comparable. ``load_sun_sample_times`` only parses the CSV; it does not
derive altitude/azimuth from a date and clock time itself.

Earlier draft of this module (and of ``fields/T-009_sun_probe_spec.md``)
mistakenly reimplemented solar position from scratch and clobbered the
real spec file in the process, before the real CSV fixture and its
"方案 A" note had been noticed in ``fields/``/``ops/``. That draft is
discarded; see ``ops/reports/T-009.md`` for the correction.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .wind_field import ray_mesh_occluded, sample_outer_surface, triangulate_faces

__all__ = [
    "SUN_SAMPLE_TIMES_CSV",
    "load_sun_sample_times",
    "sun_slot_contribution",
    "sun_field",
]

#: 風場-reviewed time/s_k fixture (fields/T-009_sun_probe_spec.md "方案 A"); read-only.
SUN_SAMPLE_TIMES_CSV = Path(__file__).resolve().parents[1] / "fields" / "T-009_sun_sample_times.csv"


def load_sun_sample_times(path=SUN_SAMPLE_TIMES_CSV):
    """Read the CSV time/s_k fixture.

    Columns: ``date, local_time, half (am/pm), alt_deg, az_deg, sx_E, sy_N,
    sz_U``. ``s_k`` (ground -> sun unit vector, Rhino X=east/Y=north/Z=up)
    is already computed in the file; rows with altitude <= 0 were already
    excluded when the fixture was generated (``fields/T-009_sun_probe_spec.md``
    §1), so every row returned here has a usable ``s_k``.

    Returns
    -------
    list[dict]
        One dict per row: ``date``, ``local_time``, ``half`` (``"am"`` or
        ``"pm"``), ``alt_deg``, ``az_deg``, ``s_k`` (3-tuple, unit).
    """
    rows = []
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append({
                "date": row["date"],
                "local_time": row["local_time"],
                "half": row["half"],
                "alt_deg": float(row["alt_deg"]),
                "az_deg": float(row["az_deg"]),
                "s_k": (float(row["sx_E"]), float(row["sy_N"]), float(row["sz_U"])),
            })
    return rows


def sun_slot_contribution(points, normals, vertices, triangles, s_k, dt_hours, eps=1e-3):
    """H contribution (h) for one fixed ``s_k``: ``dt_hours`` where facing and unoccluded, else 0.

    Implements ``V_k(x) * I[n.s_k > 0] * Delta t`` for a single time slot.
    ``s_k`` is taken as given (from the CSV fixture); this function does
    not validate altitude > 0 itself.
    """
    s_k = np.asarray(s_k, dtype=float)
    facing = (normals @ s_k) > 0.0
    origins = points + eps * normals
    occluded = ray_mesh_occluded(origins, s_k, vertices, triangles)
    visible = facing & ~occluded
    return np.where(visible, dt_hours, 0.0)


def sun_field(mesh, date, dt_hours=0.5, rows=None, eps=1e-3):
    """H_am, H_pm (h) on ``mesh``'s outer face samples, for one CSV ``date``.

    ``rows`` defaults to :func:`load_sun_sample_times` filtered to
    ``date`` (e.g. ``"2025-06-21"``, the fixture's two representative
    solstice days). Each row is one ``dt_hours``-wide slot -- locked at
    0.5 h by the fixture's own sampling interval
    (``fields/T-009_sun_probe_spec.md`` §1); varying ``dt_hours`` here
    without matching the fixture's actual spacing would misweight the sum.

    Returns
    -------
    dict
        ``points``, ``normals`` (mm, unit), ``H_am``, ``H_pm`` (h, one row
        per face sample), plus ``date``, ``dt_hours``, sample counts and
        ``eps_mm``, for the report.
    """
    if rows is None:
        rows = [r for r in load_sun_sample_times() if r["date"] == date]
    if not rows:
        raise ValueError("no CSV rows for date={!r} in {}".format(date, SUN_SAMPLE_TIMES_CSV))

    points, normals = sample_outer_surface(mesh)
    vertices, triangles = triangulate_faces(mesh)
    n = len(points)
    H_am = np.zeros(n)
    H_pm = np.zeros(n)
    n_am = n_pm = 0

    for row in rows:
        contribution = sun_slot_contribution(
            points, normals, vertices, triangles, row["s_k"], dt_hours, eps,
        )
        if row["half"] == "am":
            H_am += contribution
            n_am += 1
        elif row["half"] == "pm":
            H_pm += contribution
            n_pm += 1
        else:
            raise ValueError("unknown half={!r} in {}".format(row["half"], SUN_SAMPLE_TIMES_CSV))

    return dict(
        points=points, normals=normals, H_am=H_am, H_pm=H_pm,
        date=date, dt_hours=dt_hours, n_samples_am=n_am, n_samples_pm=n_pm,
        eps_mm=eps,
    )

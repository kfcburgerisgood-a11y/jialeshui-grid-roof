"""T-008: minimal W / V_wind / W_eff smoke test on a body's outer surface, with self-occlusion.

Scope (``ops/tasks/T-008.md``; 總綱 §5.1/§5.3): one locked wind direction,
exact ray-vs-mesh intersection to find where the body shadows itself from
that direction. This is a smoke test for the mechanism, not a validated
environmental field -- see ``grid_roof.fields_io.WIND_DEFAULT["conflict"]``
for the open ENE-vs-summer-EPW conflict, and
``fields/T-006_epw_wind_sun_spec.md`` §5 for what else (H_am/H_pm, S, salt,
station representativeness) remains unverified. Does not touch
``body_shell``, ``body_keep``, ``design``, or any opening/void/water rule.

Ray convention and probe values locked by the parallel wind-field review in
``fields/T-008_probe_expectations.md`` (2026-10-29): ``V_wind`` is cast
along **+u_wind** (toward where the wind comes from, upstream) from each
sample point offset by ``eps`` along its own outward normal; a hit on any
other mesh triangle beyond that offset means the point is shadowed,
``V_wind = 0``.
"""

import numpy as np

from .fields_io import WIND_DEFAULT, u_wind_from_theta_deg

__all__ = ["sample_outer_surface", "triangulate_faces", "ray_mesh_occluded", "wind_field"]


def sample_outer_surface(mesh):
    """One point + outward unit normal per mesh face, mm.

    Resolution is whatever the mesh's own faces are -- for
    ``inputs/body_a_subd.stl`` (848 triangles, T-004) that is one sample per
    SubD facet, not a per-voxel surface field. Good enough for a smoke
    test; a finer, voxel-resolution surface sampler is future work.
    """
    points = np.array([mesh.face_centroid(f) for f in mesh.faces()], dtype=float)
    normals = np.array([mesh.face_normal(f) for f in mesh.faces()], dtype=float)
    normals = normals / np.linalg.norm(normals, axis=1, keepdims=True)
    return points, normals


def triangulate_faces(mesh):
    """Mesh vertex coordinates (mm) and a fan-triangulated face index array, for ray-triangle occlusion.

    Fan triangulation from each face's first vertex is exact for a convex
    planar face (the box faces used in the synthetic probes); the SubD
    export is already all triangles (checked: ``inputs/body_a_subd.stl`` is
    848/848 triangles), so this only matters for the synthetic test boxes.
    """
    index = {v: i for i, v in enumerate(mesh.vertices())}
    vertices = np.array([mesh.vertex_coordinates(v) for v in mesh.vertices()], dtype=float)
    triangles = []
    for f in mesh.faces():
        verts = [index[v] for v in mesh.face_vertices(f)]
        for i in range(1, len(verts) - 1):
            triangles.append((verts[0], verts[i], verts[i + 1]))
    return vertices, np.array(triangles, dtype=int)


def ray_mesh_occluded(origins, direction, vertices, triangles):
    """True where an infinite ray from each origin along ``direction`` hits a mesh triangle.

    Vectorised Moller-Trumbore (all rays share one direction, since this is
    a single wind direction over every sample point). ``origins`` must
    already be offset off the surface (see ``wind_field``'s ``eps``) or a
    sample point's own face reads as self-occlusion at t=0.
    """
    d = np.asarray(direction, dtype=float)
    d = d / np.linalg.norm(d)

    v0 = vertices[triangles[:, 0]]
    v1 = vertices[triangles[:, 1]]
    v2 = vertices[triangles[:, 2]]
    e1 = v1 - v0
    e2 = v2 - v0

    pvec = np.cross(d, e2)                        # (M,3) -- direction is shared, so this is per-triangle only
    det = np.einsum("mk,mk->m", e1, pvec)          # (M,)
    degenerate = np.abs(det) < 1e-12
    inv_det = np.where(degenerate, 0.0, 1.0 / np.where(degenerate, 1.0, det))

    tvec = origins[:, None, :] - v0[None, :, :]                      # (N,M,3)
    u = np.einsum("nmk,mk->nm", tvec, pvec) * inv_det[None, :]
    qvec = np.cross(tvec, e1[None, :, :])
    v = np.einsum("nmk,k->nm", qvec, d) * inv_det[None, :]
    t = np.einsum("nmk,mk->nm", qvec, e2) * inv_det[None, :]

    hit = (
        ~degenerate[None, :]
        & (u >= 0.0) & (u <= 1.0)
        & (v >= 0.0) & ((u + v) <= 1.0)
        & (t > 0.0)
    )
    return hit.any(axis=1)


def wind_field(mesh, theta_deg=None, eps=1e-3):
    """W, V_wind, W_eff (dimensionless, 0-1) on ``mesh``'s outer face samples.

    ``theta_deg`` defaults to the locked ``WIND_DEFAULT["theta_deg"]`` (ENE,
    67.5 -- an assumption, see its ``"conflict"`` entry). ``eps`` (mm) is
    how far each ray's origin is pushed off its own surface point along the
    outward normal before casting toward the wind source, only to clear
    floating-point self-intersection -- locked at 1e-3 mm by
    ``fields/T-008_probe_expectations.md`` §E.1, not a voxel-scale offset.

    Returns
    -------
    dict
        ``points``, ``normals`` (mm, unit) and ``W``, ``V_wind``, ``W_eff``
        (0-1), one row per face sample, plus the ``theta_deg``/``u_wind``
        actually used, for the report.
    """
    theta_deg = WIND_DEFAULT["theta_deg"] if theta_deg is None else theta_deg
    u_wind = np.array(u_wind_from_theta_deg(theta_deg))

    points, normals = sample_outer_surface(mesh)
    vertices, triangles = triangulate_faces(mesh)

    W = np.clip(normals @ u_wind, 0.0, None)
    origins = points + eps * normals
    occluded = ray_mesh_occluded(origins, u_wind, vertices, triangles)
    V_wind = np.where(occluded, 0.0, 1.0)
    W_eff = W * V_wind

    return dict(
        points=points, normals=normals, W=W, V_wind=V_wind, W_eff=W_eff,
        theta_deg=theta_deg, u_wind=u_wind.tolist(), eps_mm=eps,
    )

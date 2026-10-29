"""T-007: SubD body A (STL, scaled) through the selectable design_roof(body_mesh=) entry.

Usage: uv run python scripts/m2_design_subd.py 100 m2-xxx

Loads body_a_subd.stl and applies the LOCKED script-level scale(1000) (T-004:
STL coordinates are metres; real size is about 9x9x1.45 m), then calls
design_roof(brief, body_mesh=mesh) -- the same selectable entry T-005 proved
on the test box, now run on the real SubD mesh. Does not touch
openings/water/pores and does not decide framework Sec.8 (T/b_min stay
the provisional Brief defaults).
"""

import csv
import datetime
import json
import sys
import time
from pathlib import Path

import numpy as np

from grid_roof import Brief, body, design_roof
from grid_roof.checks import body_keep


def march(field, centre, bounds, axis):
    """From the bbox centre outward along +axis to the field's sign flip -- the mesh surface.

    No corner-at-origin or z>=0 assumption: starts at the geometric centre of
    the mesh's own bbox and walks outward until the distance field changes sign.
    """
    hi = bounds[axis + 3] + 200.0
    ts = np.linspace(centre[axis], hi, 4000)
    vals = np.empty_like(ts)
    for i, t in enumerate(ts):
        p = list(centre)
        p[axis] = t
        vals[i] = float(field.get_distance(p))
    idx = np.where(np.diff(np.sign(vals)) != 0)[0]
    return float(ts[idx[-1]]) if len(idx) else None


def main(voxel, run_id):
    root = Path(__file__).resolve().parents[1]
    mesh = body.load_body(root / "inputs" / "body_a_subd.stl")
    SCALE = 1000.0  # LOCKED 2026-10-28 by 歐郎 (T-004): STL coords are metres -> mm; script-only, not in load_body
    mesh.scale(SCALE)
    closed = mesh.is_closed()

    brief = Brief(voxel=voxel)
    start = time.perf_counter()
    result = design_roof(brief, body_mesh=mesh)
    seconds = time.perf_counter() - start

    stats = body_keep(result)
    bounds = result.bounds  # mesh bbox, world coords -- not brief.bounds; no corner-at-origin assumption
    centre = [(bounds[i] + bounds[i + 3]) / 2 for i in range(3)]

    probes = {}
    for axis, name in ((0, "x"), (2, "z")):
        outer_t = march(result.field, centre, bounds, axis)
        if outer_t is None:
            continue
        for label, depth in (("outer", 0.0), ("mid_wall", brief.body_thickness / 2), ("inner", brief.body_thickness)):
            p = list(centre)
            p[axis] = outer_t - depth
            probes[f"{name}_{label}"] = {
                "at_mm": [round(v, 1) for v in p],
                "field_mm": round(float(result.field.get_distance(p)), 2),
                "shell_mm": round(float(result.shell.get_distance(p)), 2),
                "keep_mm": round(float(result.keep.get_distance(p)), 2),
                "design_mm": round(float(result.design.roof.get_distance(p)), 2),
            }

    output = dict(
        voxel_mm=voxel, scale_applied=SCALE, closed=closed, manifold=mesh.is_manifold(),
        V=mesh.number_of_vertices(), F=mesh.number_of_faces(),
        body_thickness_mm=brief.body_thickness, b_min_mm=brief.b_min,
        thickness_status="provisional; physical thickness and margin unverified (Sec.8 undecided)",
        mesh="body_a_subd.stl; script-level scale(1000) LOCKED 2026-10-28 (T-004), not in load_body",
        bbox_mm=bounds, centre_mm=centre, centre_design_mm=round(float(result.design.roof.get_distance(centre)), 2),
        seconds=round(seconds, 2), keep_check=stats, probes=probes,
    )
    (root / "docs" / f"m2_design_subd_v{voxel:g}.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with (root / "runs.csv").open(newline="", encoding="utf-8") as fh:
        fields = next(csv.reader(fh))
    row = dict.fromkeys(fields, "")
    row.update({
        "run_id": run_id, "日期": datetime.date.today().isoformat(), "步驟": "body-subd-design",
        "改了什麼": "T-007 body_a_subd.stl (scale x1000, script-only) -> design_roof(body_mesh=) selectable entry",
        "舊值": "T-004 smoke design_body(shell) on SubD / T-005 design_roof(body_mesh=) on test box",
        "新值": f"T={brief.body_thickness:g} b_min={brief.b_min:g} mm (provisional) on real SubD A",
        "voxel(mm)": voxel, "計算秒數": round(seconds, 2), "封閉": closed,
        "保留材料被挖掉量": stats["missing_volume_mm3"],
        "備註": (f"bbox={bounds}; spacing={stats['spacing_mm']} mm; kept={stats['kept_samples']}; "
                 f"missing={stats['missing_samples']}; keep_outside_shell={stats['keep_outside_shell_samples']}; "
                 "no water/openings/pores; Sec.8 undecided; physical margin unverified"),
    })
    with (root / "runs.csv").open("a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=fields, lineterminator="\n").writerow(row)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lo = np.array(bounds[:3])
    hi = np.array(bounds[3:])
    xs = np.arange(lo[0] - 300, hi[0] + 300, voxel / 2)
    zs = np.arange(lo[2] - 300, hi[2] + 300, voxel / 2)
    X, Z = np.meshgrid(xs, zs)
    S = np.array([[float(result.design.roof.get_distance((x, centre[1], z))) for x in xs] for z in zs])
    m = np.abs(S).max()
    plt.figure(figsize=(10, 5))
    plt.pcolormesh(X, Z, S, cmap="RdBu_r", vmin=-m, vmax=m, shading="auto")
    plt.colorbar(label="design.roof distance (mm)")
    plt.contour(X, Z, S, [0], colors="k")
    plt.gca().set_aspect("equal")
    plt.title(f"body_a_subd design_roof(body_mesh=), y={centre[1]:.0f}, voxel={voxel:g}")
    plt.savefig(root / "docs" / f"m2_design_subd_section_v{int(voxel)}.png", dpi=100)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2])

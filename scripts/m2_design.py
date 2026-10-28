"""T-005: bbox-based box preview through the selectable design entry and b_min keep.

Usage: uv run python scripts/m2_design.py 100 m2-007
The diagnostic cutter removes the shell, then design restores only keep.
It does not change or validate opening/water/pores rules.
"""

import csv
import datetime
import json
import sys
import time
from dataclasses import replace
from pathlib import Path

from compas_vol.combinations import Subtraction

from grid_roof import Brief, body, design_roof
from grid_roof.checks import body_keep
from grid_roof.design import Design, box


def main(voxel, run_id):
    root = Path(__file__).resolve().parents[1]
    brief = Brief(voxel=voxel)
    mesh = body.load_body(root / "inputs" / "body_a.obj")
    bounds = body.mesh_bounds(mesh)
    mesh.translate([-(bounds[i] + bounds[i + 3]) / 2 for i in range(3)])
    start = time.perf_counter()
    result = design_roof(brief, body_mesh=mesh)
    initial = body_keep(result)
    removed = Subtraction(result.shell, box(*result.bounds))
    lost = body_keep(replace(result, design=Design(removed, removed)))
    restored = body_keep(replace(result, design=body.design_body(removed, result.keep)))
    assert initial["kept_samples"] > 0 and lost["missing_samples"] > 0
    assert initial["keep_outside_shell_samples"] == 0
    assert initial["missing_samples"] == restored["missing_samples"] == 0
    centre = [(result.bounds[i] + result.bounds[i + 3]) / 2 for i in range(3)]
    probes = {}
    for name, depth in (("outer_skin", brief.b_min / 2),
                        ("backplate_mid", brief.body_thickness - brief.b_min / 2)):
        p = [centre[0], centre[1], result.bounds[2] + depth]
        probes[name] = {"at_mm": p, "field_mm": result.field.get_distance(p),
                        "shell_mm": result.shell.get_distance(p), "keep_mm": result.keep.get_distance(p),
                        "design_mm": result.design.roof.get_distance(p)}
    seconds = time.perf_counter() - start
    output = dict(voxel_mm=voxel, body_thickness_mm=brief.body_thickness, b_min_mm=brief.b_min,
                  thickness_status="provisional; physical thickness and margin unverified",
                  mesh="body_a.obj TEST BOX; translated to bbox centre, no re-export",
                  closed=mesh.is_closed(), bbox_mm=result.bounds, centre_mm=centre,
                  centre_design_mm=result.design.roof.get_distance(centre),
                  seconds=round(seconds, 2), initial=initial, diagnostic_cut=lost, restored=restored, probes=probes)
    (root / "docs" / f"m2_design_v{voxel:g}.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (root / "runs.csv").open(newline="", encoding="utf-8") as fh:
        fields = next(csv.reader(fh))
    row = dict.fromkeys(fields, "")
    row.update({"run_id": run_id, "日期": datetime.date.today().isoformat(), "步驟": "body-design-keep",
                "改了什麼": "T-005 design_roof(body_mesh) -> body_shell + inner b_min keep",
                "舊值": "slab-only entry / whole-shell keep",
                "新值": f"T={brief.body_thickness:g} b_min={brief.b_min:g} mm (provisional)",
                "voxel(mm)": voxel, "計算秒數": round(seconds, 2), "封閉": mesh.is_closed(),
                "保留材料被挖掉量": restored["missing_volume_mm3"],
                "備註": f"TEST BOX bbox={result.bounds}; spacing={initial['spacing_mm']} mm; "
                          f"kept={initial['kept_samples']}; diagnostic missing={lost['missing_samples']} "
                          "-> restored=0 samples; no water/openings/pores; physical backplate margin unverified"})
    with (root / "runs.csv").open("a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=fields, lineterminator="\n").writerow(row)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(float(sys.argv[1]), sys.argv[2])

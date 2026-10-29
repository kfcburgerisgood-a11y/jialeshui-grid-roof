"""T-008: W/V_wind/W_eff smoke on body_a_subd.stl (SubD A), with self-occlusion.

Usage: uv run python scripts/m3_wind_field.py m3-xxx

Loads body_a_subd.stl and applies the LOCKED script-level scale(1000)
(T-004: STL coordinates are metres; real size is about 9x9x1.45 m), samples
one point + outward normal per face, and runs grid_roof.wind_field.wind_field
with the locked WIND_DEFAULT ENE direction. Writes docs/m3_wind_field.json,
appends one runs.csv row, and prints the numbers ops/reports/T-008.md quotes.
Does not touch body_shell/body_keep/design or any opening/void/water rule.
"""

import csv
import datetime
import json
import sys
from pathlib import Path

import numpy as np

from grid_roof import body as B
from grid_roof import fields_io as F
from grid_roof.wind_field import wind_field


def histogram(values, edges):
    counts, _ = np.histogram(values, bins=edges)
    return [{"range": [float(edges[i]), float(edges[i + 1])], "count": int(counts[i])}
            for i in range(len(counts))]


def main(run_id):
    root = Path(__file__).resolve().parents[1]
    mesh = B.load_body(root / "inputs" / "body_a_subd.stl")
    SCALE = 1000.0  # LOCKED 2026-10-28 by 歐郎 (T-004): STL coords are metres -> mm; script-only, not in load_body
    mesh.scale(SCALE)

    result = wind_field(mesh, theta_deg=F.WIND_DEFAULT["theta_deg"])
    W, V_wind, W_eff = result["W"], result["V_wind"], result["W_eff"]
    points, normals = result["points"], result["normals"]

    windward = W > 0
    occluded = windward & (V_wind == 0.0)

    def stats(values):
        return {"min": float(values.min()), "max": float(values.max()), "mean": float(values.mean())}

    probe_idx = {
        "max_W_eff": int(np.argmax(W_eff)),
        "min_W_eff_among_windward": int(np.argmin(np.where(windward, W_eff, np.inf))) if windward.any() else None,
        "max_W_leeward": int(np.argmax(np.where(~windward, W, -np.inf))) if (~windward).any() else None,
    }
    if occluded.any():
        probe_idx["an_occluded_point"] = int(np.argmax(np.where(occluded, W, -np.inf)))

    probes = {}
    for name, i in probe_idx.items():
        if i is None:
            continue
        probes[name] = {
            "point_mm": [round(float(v), 1) for v in points[i]],
            "normal": [round(float(v), 4) for v in normals[i]],
            "W": round(float(W[i]), 6),
            "V_wind": float(V_wind[i]),
            "W_eff": round(float(W_eff[i]), 6),
        }

    output = dict(
        mesh="body_a_subd.stl; script-level scale(1000) LOCKED 2026-10-28 (T-004), not in load_body",
        n_faces=mesh.number_of_faces(),
        theta_deg=result["theta_deg"], sector_label=F.WIND_DEFAULT["sector_label"],
        u_wind=result["u_wind"], eps_mm=result["eps_mm"],
        wind_default_basis=F.WIND_DEFAULT["basis"], wind_default_conflict=F.WIND_DEFAULT["conflict"],
        n_windward_samples=int(windward.sum()), n_leeward_samples=int((~windward).sum()),
        n_occluded_windward_samples=int(occluded.sum()),
        W=stats(W), V_wind=stats(V_wind), W_eff=stats(W_eff),
        W_histogram=histogram(W, np.linspace(0.0, 1.0, 11)),
        W_eff_histogram=histogram(W_eff, np.linspace(0.0, 1.0, 11)),
        probes=probes,
    )
    (root / "docs" / "m3_wind_field.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with (root / "runs.csv").open(newline="", encoding="utf-8") as fh:
        fields = next(csv.reader(fh))
    row = dict.fromkeys(fields, "")
    row.update({
        "run_id": run_id, "日期": datetime.date.today().isoformat(), "步驟": "wind-field-w-eff",
        "改了什麼": "T-008 wind_field(mesh): W, V_wind (ray-vs-mesh occlusion), W_eff on body_a_subd.stl faces",
        "舊值": "none (new field, M3 start)",
        "新值": f"theta_deg={result['theta_deg']:g} (ENE, WIND_DEFAULT, locked/推定) eps={result['eps_mm']:g}mm",
        "voxel(mm)": "", "計算秒數": "", "封閉": mesh.is_closed(),
        "W_eff平均": round(float(W_eff.mean()), 4),
        "備註": (f"n_faces={mesh.number_of_faces()}; windward={int(windward.sum())} "
                 f"occluded_windward={int(occluded.sum())}; W_eff min/max="
                 f"{float(W_eff.min()):.4f}/{float(W_eff.max()):.4f}; "
                 "surface sample = one point per SubD face, not per-voxel; "
                 "ENE u_wind is 推定 (T-006b/T-008), not a validated site wind field"),
    })
    with (root / "runs.csv").open("a", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=fields, lineterminator="\n").writerow(row)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 7))
    sc = ax.scatter(points[:, 0], points[:, 1], c=W_eff, cmap="inferno", vmin=0.0, vmax=1.0, s=14)
    plt.colorbar(sc, label="W_eff (dimensionless)")
    centre_xy = points[:, :2].mean(axis=0)
    u = np.array(result["u_wind"][:2]) * 1500.0
    ax.annotate("", xy=tuple(centre_xy + u), xytext=tuple(centre_xy),
                arrowprops=dict(arrowstyle="->", color="cyan", lw=2))
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title(f"body_a_subd W_eff, theta={result['theta_deg']:g} deg ENE (assumed)")
    plt.savefig(root / "docs" / "m3_wind_field_w_eff.png", dpi=100)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "m3-wind-field")

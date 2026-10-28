"""T-003: box A verification table at a given voxel. Usage: m2_verify.py <voxel> <run_id>"""
import csv, datetime, json, sys, time
from pathlib import Path
from grid_roof import body as B

root = Path(__file__).resolve().parents[1]
voxel = float(sys.argv[1]); run_id = sys.argv[2]
mesh = B.load_body(root / "inputs" / "body_a.obj")
pts = [mesh.vertex_coordinates(v) for v in mesh.vertices()]
bbox = [max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3)]
t0 = time.time()
res = B.resolution_for(mesh, voxel)
field = B.body_field(mesh, voxel)
shell = B.body_shell(field)
secs = time.time() - t0
T = B.SHELL_T
probes = {"centre(5000,3000,2000)": (5000, 3000, 2000), "outer x=0": (0, 3000, 2000),
          "mid-wall x=150": (150, 3000, 2000), "inner x=300": (300, 3000, 2000),
          "outer z=4000(top)": (5000, 3000, 4000), "mid-wall z=3850": (5000, 3000, 3850),
          "inner z=3700": (5000, 3000, 3700)}
expect_f = {"centre(5000,3000,2000)": -2000, "outer x=0": 0, "mid-wall x=150": -150, "inner x=300": -300,
            "outer z=4000(top)": 0, "mid-wall z=3850": -150, "inner z=3700": -300}
rows = []
for k, p in probes.items():
    f = float(field.get_distance(p)); s = float(shell.get_distance(p))
    rows.append(dict(probe=k, field=round(f, 1), field_expect=expect_f[k], field_err=round(f - expect_f[k], 1),
                     shell=round(s, 1), shell_expect=abs(expect_f[k] + T / 2) - T / 2))
# solid volumes by voxel counting on the grid
import numpy as np
g = np.asarray(field.values if hasattr(field, "values") else field.data)
out = dict(voxel=voxel, res=res, secs=round(secs, 1), closed=mesh.is_closed(), bbox=bbox,
           mesh_volume=mesh.volume(), probes=rows, grid_shape=list(g.shape))
try:
    from compas.geometry import Box
    sp = np.atleast_1d(np.asarray(field.spacing, float)); cell = float(np.prod(sp)) if sp.size == 3 else float(sp[0]) ** 3; out["spacing"] = sp.tolist()
    out["solid_vol_count"] = float((g < 0).sum() * cell)
    gs = np.abs(g + T / 2) - T / 2
    out["shell_vol_count"] = float((gs < 0).sum() * cell)
    out["cell_mm3"] = float(cell)
except Exception as e:
    out["vol_err"] = repr(e)
print(json.dumps(out, ensure_ascii=False, indent=1))
c = rows[0]["field"]
row = {"run_id": run_id, "日期": datetime.date.today().isoformat(), "步驟": "body-verify",
       "改了什麼": "T-003 方盒驗證表(中心/外/內/mid-wall/體積)", "舊值": "", "新值": f"T=300 side=1.0 res={res}",
       "voxel(mm)": voxel, "計算秒數": round(secs, 1), "封閉": out["closed"], "W_eff平均": "", "H_am平均": "",
       "H_pm平均": "", "光斑誤差max": "", "積水點數": "", "保留材料被挖掉量": "", "件數": "",
       "備註": f"centre field={c} (expect -2000±{voxel:g}); mesh vol={out['mesh_volume']:.4g} mm3; TEST MESH"}
with (root / "runs.csv").open("a", newline="", encoding="utf-8") as fh:
    csv.DictWriter(fh, fieldnames=list(row)).writerow(row)
(root / "docs" / f"m2_verify_v{int(voxel)}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

"""T-004: SubD body A (STL) -> field -> Shell -> design_body. Usage: m2_subd.py <voxel> <run_id>"""
import csv, datetime, json, sys, time
from pathlib import Path
import numpy as np
from grid_roof import body as B

root = Path(__file__).resolve().parents[1]
voxel = float(sys.argv[1]); run_id = sys.argv[2]
mesh = B.load_body(root / "inputs" / "body_a_subd.stl")
SCALE = 1000.0  # LOCKED 2026-10-28 by 歐郎: real size ~9×9×1.45 m; STL coords in metres → ×1000 to mm
mesh.scale(SCALE)
pts = np.array([mesh.vertex_coordinates(v) for v in mesh.vertices()])
lo, hi = pts.min(0), pts.max(0); c = (lo + hi) / 2
out = dict(voxel=voxel, scale_applied=SCALE, V=mesh.number_of_vertices(), F=mesh.number_of_faces(), closed=mesh.is_closed(),
           manifold=mesh.is_manifold(), bbox_min=lo.round(1).tolist(), bbox_max=hi.round(1).tolist(),
           bbox=(hi - lo).round(1).tolist(), mesh_volume=mesh.volume())
print(json.dumps(out, ensure_ascii=False), flush=True)
if len(sys.argv) > 3: sys.exit()
t0 = time.time()
res = B.resolution_for(mesh, voxel); field = B.body_field(mesh, voxel); shell = B.body_shell(field)
r = B.design_body(shell)
secs = time.time() - t0
T = B.SHELL_T
probes = {"geom centre": c}
# along +x from centre: outer surface, mid-wall, inner surface found by marching the field
xs = np.linspace(c[0], hi[0] + 200, 4000)
fx = np.array([float(field.get_distance((x, c[1], c[2]))) for x in xs])
i = np.where(np.diff(np.sign(fx)) != 0)[0]
if len(i):
    xo = xs[i[-1]]
    probes.update({"outer +x": (xo, c[1], c[2]), "mid-wall +x": (xo - T/2, c[1], c[2]), "inner +x": (xo - T, c[1], c[2])})
zs = np.linspace(c[2], hi[2] + 200, 4000)
fz = np.array([float(field.get_distance((c[0], c[1], z))) for z in zs])
j = np.where(np.diff(np.sign(fz)) != 0)[0]
if len(j):
    zo = zs[j[-1]]
    probes.update({"outer +z": (c[0], c[1], zo), "mid-wall +z": (c[0], c[1], zo - T/2), "inner +z": (c[0], c[1], zo - T)})
rows = [dict(probe=k, at=[round(float(v), 1) for v in p], field=round(float(field.get_distance(tuple(p))), 1),
             shell=round(float(shell.get_distance(tuple(p))), 1)) for k, p in probes.items()]
g = np.asarray(field.values if hasattr(field, "values") else field.data)
sp = np.atleast_1d(np.asarray(field.spacing, float)); cell = float(np.prod(sp)) if sp.size == 3 else float(sp[0]) ** 3
out.update(res=res, secs=round(secs, 1), spacing=sp.tolist(), probes=rows, design_type=type(r).__name__,
           solid_vol_count=float((g < 0).sum() * cell), shell_vol_count=float(((np.abs(g + T/2) - T/2) < 0).sum() * cell))
print(json.dumps(out, ensure_ascii=False, indent=1))
(root / "docs" / f"m2_subd_v{int(voxel)}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
# section through centre (y = c[1]) of the shell
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
X, Z = np.meshgrid(np.arange(lo[0]-300, hi[0]+300, voxel/2), np.arange(lo[2]-300, hi[2]+300, voxel/2))
S = np.array([[float(shell.get_distance((x, c[1], z))) for x in X[0]] for z in Z[:, 0]])
m = np.abs(S).max(); plt.figure(figsize=(10, 5)); plt.pcolormesh(X, Z, S, cmap="RdBu_r", vmin=-m, vmax=m, shading="auto")
plt.colorbar(label="shell distance (mm)"); plt.contour(X, Z, S, [0], colors="k"); plt.gca().set_aspect("equal")
plt.title(f"body_a_subd shell T=300, y={c[1]:.0f}, voxel={voxel:g}"); plt.savefig(root / "docs" / f"m2_subd_section_v{int(voxel)}.png", dpi=100)
row = {"run_id": run_id, "日期": datetime.date.today().isoformat(), "步驟": "body-subd",
       "改了什麼": "T-004 SubD A (stl) -> Shell -> design_body", "舊值": "", "新值": f"T=300 side=1.0 res={res}",
       "voxel(mm)": voxel, "計算秒數": round(secs, 1), "封閉": out["closed"], "W_eff平均": "", "H_am平均": "",
       "H_pm平均": "", "光斑誤差max": "", "積水點數": "", "保留材料被挖掉量": "", "件數": "",
       "備註": f"centre field={rows[0]['field']} shell={rows[0]['shell']}; mesh vol={out['mesh_volume']:.4g} mm3; SubD A; STL in m, scaled x1000 (LOCKED 2026-10-28)"}
with (root / "runs.csv").open("a", newline="", encoding="utf-8") as fh:
    csv.DictWriter(fh, fieldnames=list(row)).writerow(row)

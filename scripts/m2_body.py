"""M2 smoke run: A test body -> field -> shell -> design; writes inputs/body_a.obj, a section PNG, a runs.csv row."""
import csv
import datetime
import sys
import time
from pathlib import Path
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")
from grid_roof import body as B

root = Path(__file__).resolve().parents[1]
obj = root / "inputs" / "body_a.obj"
if not obj.exists():
    B.test_box_a().to_obj(str(obj))
    txt = obj.read_text()
    obj.write_text("# TEST MESH (A, 10000x6000x4000 mm box, origin at corner) -- NOT an authored SubD\n" + txt)
t0 = time.time()
mesh = B.load_body(obj)
closed = mesh.is_closed()
res = B.resolution_for(mesh)
field = B.body_field(mesh)
shell = B.body_shell(field)
d = B.design_body(shell)
y = 3000.0
x, z = np.meshgrid(np.linspace(-500, 10500, 551), np.linspace(-500, 4500, 251), indexing="ij")
v = d.roof.get_distance_numpy(x[:, None, :], np.full((551, 1, 251), y), z[:, None, :])[:, 0, :]
secs = time.time() - t0
out = root / "docs" / "m2_body_section_y3000.png"
plt.figure(figsize=(11, 4.5))
plt.contourf(x, z, v, levels=40, cmap="RdBu_r")
plt.colorbar(label="mm")
plt.contour(x, z, v, [0], colors="k")
plt.gca().set_aspect("equal")
plt.title(f"M2 body shell y={y:.0f} (T=300 provisional, voxel=40, res={res}) TEST MESH")
plt.savefig(out, dpi=110)
row = dict(run_id=sys.argv[1] if len(sys.argv) > 1 else "m2-001", 日期=datetime.date.today().isoformat(), 步驟="body",
           改了什麼="新增 body: A 測試 box -> VolGrid.from_mesh -> Shell(side=1.0) -> design", 舊值="slab",
           新值=f"body T=300 res={res}", **{"voxel(mm)": 40, "計算秒數": round(secs, 1)}, 封閉=closed,
           W_eff平均="", H_am平均="", H_pm平均="", 光斑誤差max="", 積水點數="", 保留材料被挖掉量="", 件數="",
           備註="box 上跑; 無 water/voids/pores; 未在 Rhino 跑")
f = root / "runs.csv"
new = not f.exists()
with f.open("a", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(row))
    if new:
        w.writeheader()
    w.writerow(row)
print(f"closed={closed} res={res} secs={secs:.1f} section={out} vmin={v.min():.1f} centre={v[275,125]:.1f}")

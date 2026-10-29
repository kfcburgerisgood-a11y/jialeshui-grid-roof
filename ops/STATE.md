/workspace/jialeshui/workshop/jialeshui-grid-roof

# 久逃 ops 狀態（STATE）

- 正本 git repo：上方第一行路徑。
- 鏡像樹 `/workspace/jialeshui/`：**不是 git repo**。副本：`docs/ops-STATE.md`、`ops-TASKS.md`。
- 目前分支：`m2-body` @ `b0c57f5`（已 push）
- 里程碑：M2 **半通過 → 待歐郎驗收「範圍限定通過」**（T-003～T-005、T-007 DONE）
- runs.csv：repo 根目錄。

## 已做決策
- ①A 半通過；②A 方盒 A-proxy；T=300／b_min=100 推定
- T-004：SubD≈9×9×1.45 m；scale(1000) 鎖定僅本檔
- T-005／T-007 DONE：方盒＋SubD 皆經 design_roof(body_mesh=)＋內側 keep
- **M2 收斂定義（挑洞 A，待歐郎驗收）**：body→shell→內側 keep→design；挖洞（openings／water／pores）屬 M4／M5
- 開發：Claude／Codex；共匪可代跑被擋的 python

## 角色
- Claude／Codex 開發；格草整合；風場規格；挑洞審查；共匪總指揮

## 輸入
- `inputs/body_a.obj`；`inputs/body_a_subd.stl`／`.3dm`

## 待辦
- T-001～T-005、T-007：DONE
- 等歐郎：M2「範圍限定通過」驗收？
- 下一刀建議：T-006 環境場，或進 M3

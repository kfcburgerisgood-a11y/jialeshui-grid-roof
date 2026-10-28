/workspace/jialeshui/workshop/jialeshui-grid-roof

# 久逃 ops 狀態（STATE）

- 正本 git repo：上方第一行路徑。
- 鏡像樹 `/workspace/jialeshui/`：**不是 git repo**。副本：`docs/ops-STATE.md`、`ops-TASKS.md`。
- 目前分支：`m2-body` @ `e2d293c`（已 push）
- 里程碑：M2 半通過（T-003／T-004 DONE；T-005 進行中；整顆 M2 未過）
- runs.csv：repo 根目錄。

## 已做決策
- ①A 半通過；②A 方盒 A-proxy；T=300 推定；voxel 40 預覽
- T-003：body_field 中心≈−2000、body_shell 腔心為正——已驗（voxel100／40）
- T-004（2026-10-28）：`body_a_subd.stl` 真實≈9×9×1.45 m；STL 座標=m；**鎖定 scale(1000)→mm**，不重匯；僅本檔
- 挑洞 T-004：幾何關通過（附條件）；可開 T-005；不可寫成整顆 M2 通過

## 角色
- Claude Code 開發；格草整合；風場規格；挑洞審查；共匪總指揮

## 輸入
- `inputs/body_a.obj` 測試方盒
- `inputs/body_a_subd.stl`／`.3dm` 歐郎 A 版（單位鎖定見上）

## 待辦
- T-001／T-002／T-003／T-004：DONE
- T-005：進行中（design／notebook → body_shell＋keep）；**改派 Codex**（Claude session limit→19:00 Taipei）
- T-006 可並行

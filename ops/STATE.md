/workspace/jialeshui/workshop/jialeshui-grid-roof

# 久逃 ops 狀態（STATE）

- 正本 git repo：上方第一行路徑。所有 bot 與 Claude 只認這裡。
- 鏡像樹 `/workspace/jialeshui/`：放 design-framework、docs、epw、fields 等資料，**不是 git repo**。指標副本：`/workspace/jialeshui/docs/ops-STATE.md`、`ops-TASKS.md`。
- 目前分支：`m2-body` @ `215759e`（尚未 push）
- 里程碑：M2 半通過（M0、M1 已完成）
- runs.csv：位於 repo 根目錄 `runs.csv`（設計總綱 7.3），不在 ops/ 重複。

## 已做決策
- ①A 半通過（API 接通）
- ②A 方盒暫代 A 版（A-proxy）
- 殼厚 T = 300 mm：推定值，設計總綱 §8 未定案，需歐郎決定
- voxel 40 用於預覽

## 角色調整（依指揮總綱 §1）
- Claude Code：主要開發者
- 格草：整合／環境
- 風場：環境場規格
- 挑洞：審查
- 共匪：總指揮

## Claude CLI
- 路徑：`/home/box/.local/bin/claude`，版本 2.1.197
- 派工範例：`claude -p "請執行 ops/tasks/T-xxx.md 的任務，完成後依 CLAUDE.md 寫回報。" --output-format json`
- 確切參數（權限模式、允許工具、最多回合）：待第一次成功執行後補記於此。

## 輸入
- `inputs/body_a.obj`：測試方盒
- `inputs/body_a_subd.3dm`：歐郎 A 版 SubD；需轉出 mesh（環境目前沒有 rhino3dm）

## 待辦／卡住
- T-001 進行中（ops bootstrap）
- T-002 GitHub push：卡住，等歐郎設定權限
- T-003、T-004、T-005 待辦；T-006 可並行（需 EPW 與風場規格）

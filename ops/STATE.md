/workspace/jialeshui/workshop/jialeshui-grid-roof

# 久逃 ops 狀態（STATE）

- 正本 git repo：上方第一行路徑。所有 bot 與 Claude 只認這裡。
- 鏡像樹 `/workspace/jialeshui/`：放 design-framework、docs、epw、fields 等資料，**不是 git repo**。指標副本：`/workspace/jialeshui/docs/ops-STATE.md`、`ops-TASKS.md`。
- 目前分支： @ （**已 push** origin/m2-body；body 起點 ）
- 里程碑：M2 半通過（M0、M1 已完成）
- runs.csv：位於 repo 根目錄 `runs.csv`（設計總綱 7.3），不在 ops/ 重複。

## 已做決策
- ①A 半通過（API 接通）；整顆 M2 暫緩至補件
- ②A 方盒暫代 A 版（A-proxy）；真 SubD mesh 進 load_body 重跑後才算幾何關
- 殼厚 T = 300 mm：推定值，設計總綱 §8 未定案，需歐郎決定
- voxel 40 用於預覽
- 半通過理由／補件：見 `docs/m2_body_挑洞.md`；下一刀建議 T-003（驗證表）或 T-005（design 可切 body），一次一件

## 角色調整（依指揮總綱 §1）
- Claude Code：主要開發者
- 格草：整合／環境／依賴（不與 Claude 同改一檔）
- 風場：環境場規格／資料來源（不直接改程式）
- 挑洞：里程碑結束審查
- 共匪：總指揮（不寫程式、不代簽通過）

## Claude CLI
- 路徑：`/home/box/.local/bin/claude`，版本 2.1.197
- 派工範例：`claude -p "請執行 ops/tasks/T-xxx.md 的任務，完成後依 CLAUDE.md 寫回報。" --output-format json`
- 確切參數（權限模式、允許工具、最多回合）：待第一次成功執行後補記於此。

## 輸入
- `inputs/body_a.obj`：測試方盒 10000×6000×4000 mm
- `inputs/body_a_subd.3dm`：歐郎 A 版 SubD（已收）；需 `.obj`／`.stl` mesh 才能跑 body（環境尚無 rhino3dm／Rhino）

## 待辦／卡住
- T-001：DONE
- T-002：DONE（已 push  @ ）
- T-003：進行中（Claude）；T-004 卡已寫（等 T-003 或並行）
- T-004 等 mesh；T-005 前置 T-003；T-006 可並行（需 EPW＋風場規格）

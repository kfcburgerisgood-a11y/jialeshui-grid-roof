# 久逃：佳樂水 SDF 工具開發規則

- 正本 repo：/workspace/jialeshui/workshop/jialeshui-grid-roof（只認這裡；/workspace/jialeshui/ 其他資料夾是鏡像，不是 git repo）。
- 這是老師 grid-roof 範本的分支專案。設計依據在 docs/佳樂水SDF工具_設計總綱.md，派工規則在 docs/久逃_開發指揮總綱.md。
- 開工前先讀 ops/STATE.md 和你的任務卡 ops/tasks/T-xxx.md。只做任務卡上的事。
- 單位一律 mm。每個數值都附上 voxel 解析度。
- 距離場慣例：內部為負、邊界為 0、外部為正。
- 跑測試：uv run --group dev python -m pytest
- 跑 notebook：uv run jupyter nbconvert --to notebook --execute walkthrough.ipynb --output <輸出路徑>
- 每條新規則：brief.py 有參數、checks.py 有檢核、tests/ 有測試。
- 不偽造結果。沒跑過、沒驗證過的，寫在回報的「未驗證」欄。
- 禁止：force push 到 main、刪除分支、刪除 repo 以外的檔案、安裝與任務無關的套件、在任何檔案或輸出中印出權杖或密碼。
- 每完成一個小步驟就 commit（訊息寫 T-xxx 與做了什麼），避免中途被打斷時白做。
- 完成後：寫 ops/reports/T-xxx.md（格式見指揮總綱第 6 節），commit，測試通過才 push。
- runs.csv（設計總綱 7.3 欄位）放在 repo 根目錄 `runs.csv`，不要在 ops/ 另存一份。

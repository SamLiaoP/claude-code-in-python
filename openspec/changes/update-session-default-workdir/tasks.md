## 1. Implementation
- [x] 1.1 修改 `CreateSessionRequest` 新增 `skip_workdir: bool = False` 欄位
- [x] 1.2 修改 `create_session` 邏輯：當 `project_dir` 為空且 `skip_workdir=False` 時，自動生成預設路徑 `~/.py-opencode/projects/<session_id>/`
- [x] 1.3 將實際使用的 `project_dir` 存入 DB 並回傳給客戶端
- [x] 1.4 撰寫測試覆蓋三種情境：有 project_dir、無 project_dir（自動建立）、skip_workdir=True

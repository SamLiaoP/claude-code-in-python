## 1. 中止按鈕修復
- [ ] 1.1 `chat.py`: 將 `process_turn` 用 `asyncio.create_task` 執行，主迴圈繼續監聽 WebSocket 訊息
- [ ] 1.2 `chat.py`: abort 時呼叫 `task.cancel()` 強制取消 task
- [ ] 1.3 `processor.py`: `process_turn` 開頭重設 `abort_event`，避免上次 abort 影響下次對話

## 2. 歷史對話載入
- [ ] 2.1 `chat.py`: WebSocket 連線後，將歷史訊息序列化為 `{ "type": "history", "messages": [...] }` 推送到前端
- [ ] 2.2 `app.js`: 處理 `history` 事件，渲染 user/assistant/tool 訊息到聊天區

## 3. 測試
- [ ] 3.1 手動測試中止按鈕在串流模式下能立即停止
- [ ] 3.2 手動測試切換到既有 Session 時顯示歷史對話

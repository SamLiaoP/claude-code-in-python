# Change: 修復中止按鈕 + 載入歷史對話紀錄

## Why
1. 中止按鈕無法強制停止 Streaming 對話：WebSocket handler 在 `process_turn` 執行時阻塞，無法接收 abort 訊息
2. 點入既有專案時，前端不顯示之前的對話紀錄：後端雖載入歷史訊息給 LLM，但從未推送到前端

## What Changes
- WebSocket handler 改為並行接收訊息：`process_turn` 作為 asyncio.Task 執行，主迴圈繼續監聽 abort
- Processor 支援 `asyncio.Task.cancel()` 強制終止，並在每次 `process_turn` 開頭重設 `abort_event`
- WebSocket 連線後推送 `{ "type": "history", "messages": [...] }` 事件，前端渲染歷史訊息

## Impact
- Affected specs: api-layer, session-management
- Affected code: `src/api/chat.py`, `src/session/processor.py`, `src/static/app.js`

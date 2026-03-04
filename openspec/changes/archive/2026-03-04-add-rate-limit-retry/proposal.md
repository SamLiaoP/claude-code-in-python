# Change: 加入 API 速率限制重試與前端狀態提示

## Why
LiteLLM 呼叫 Anthropic API 時頻繁遇到 429 Too Many Requests，目前無重試邏輯且前端無提示，使用者以為系統掛了。

## What Changes
- LLM Provider 加入手動重試迴圈（捕獲 429，遞增等待後重試）
- 重試時透過 WebSocket 推送 `status` 事件到前端
- 前端顯示帶動畫的重試狀態提示
- 新增 CSS 動畫樣式

## Impact
- Affected specs: llm-provider, api-layer
- Affected code: src/provider.py, src/session/processor.py, src/static/app.js, src/static/style.css

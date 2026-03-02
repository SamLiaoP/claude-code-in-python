###
# test_ws_client.py — 簡易 WebSocket 測試客戶端
#
# 用法：python3 test_ws_client.py <session_id>
# 需先啟動服務：python3 -m uvicorn main:app --port 8000
###

import asyncio
import json
import sys

import websockets


API_KEY = "test-123"
BASE_URL = "ws://localhost:8000"


async def main():
    if len(sys.argv) < 2:
        print("用法: python3 test_ws_client.py <session_id>")
        print("先建立 session:")
        print('  curl -X POST http://localhost:8000/api/sessions -H "Authorization: Bearer test-123" -H "Content-Type: application/json" -d \'{}\'')
        return

    session_id = sys.argv[1]
    url = f"{BASE_URL}/ws/chat/{session_id}?token={API_KEY}"

    print(f"連線至 {url}")
    async with websockets.connect(url) as ws:
        print("已連線！輸入訊息（Ctrl+C 離開）\n")

        async def receive_loop():
            try:
                async for raw in ws:
                    event = json.loads(raw)
                    t = event.get("type")
                    if t == "text_delta":
                        print(event["text"], end="", flush=True)
                    elif t == "tool_start":
                        print(f"\n[工具呼叫: {event['name']}]", flush=True)
                    elif t == "tool_result":
                        output = event.get("output", "")
                        preview = output[:200] + "..." if len(output) > 200 else output
                        print(f"[工具結果: {preview}]", flush=True)
                    elif t == "question":
                        print(f"\n[AI 提問: {event['question']}]")
                        if event.get("options"):
                            for i, opt in enumerate(event["options"]):
                                print(f"  {i+1}. {opt}")
                        answer = input("你的回答: ")
                        await ws.send(json.dumps({
                            "type": "answer",
                            "tool_id": event["tool_id"],
                            "selected": [answer],
                        }))
                    elif t == "done":
                        print("\n---（回應結束）---\n")
                    elif t == "error":
                        print(f"\n[錯誤: {event['message']}]")
            except websockets.ConnectionClosed:
                pass

        # 背景接收
        task = asyncio.create_task(receive_loop())

        try:
            while True:
                msg = await asyncio.get_event_loop().run_in_executor(None, input)
                if msg.strip():
                    await ws.send(json.dumps({"type": "message", "content": msg}))
        except (KeyboardInterrupt, EOFError):
            print("\n離開")
            task.cancel()


if __name__ == "__main__":
    asyncio.run(main())

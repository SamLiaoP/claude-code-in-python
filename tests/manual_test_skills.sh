#!/bin/bash
###
# manual_test_skills.sh — Skills 功能手動測試腳本
#
# 用途：建立帶 project_dir 的 Session，自動初始化專案級 skills 目錄，
#       引導使用者透過 WebSocket 客戶端進行對話測試。
# 依賴：伺服器需先啟動 (uvicorn main:app --app-dir src)
###

TOKEN="test-123"
BASE="http://localhost:8000"
PROJECT_DIR="${1:-/tmp/py-opencode-test-project}"

echo "=== 步驟 1：檢查伺服器 ==="
curl -s $BASE/health | python3 -m json.tool || { echo "伺服器未啟動！請先執行: uvicorn main:app --app-dir src"; exit 1; }

echo ""
echo "=== 步驟 2：建立 Session（帶 project_dir）==="
echo "專案目錄: $PROJECT_DIR"
SESSION_RESP=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"project_dir\": \"$PROJECT_DIR\"}" $BASE/api/sessions)
echo $SESSION_RESP | python3 -m json.tool
SESSION_ID=$(echo $SESSION_RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo ""
echo "=== 步驟 3：確認專案目錄已建立 ==="
SKILLS_DIR="$PROJECT_DIR/.py-opencode/skills"
echo "Skills 目錄: $SKILLS_DIR"
if [ -d "$SKILLS_DIR" ]; then
    echo "✓ 目錄已建立"
    SKILL_COUNT=$(find "$SKILLS_DIR" -name "SKILL.md" 2>/dev/null | wc -l | tr -d ' ')
    echo "  目前有 $SKILL_COUNT 個 Skill"
else
    echo "✗ 目錄不存在，請檢查 session 建立邏輯"
    exit 1
fi

echo ""
echo "=== 步驟 4：列出所有 Skills（全域 + 專案）==="
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/skills | python3 -m json.tool

echo ""
echo "=== 步驟 5：放入你的 Skill ==="
echo "請把 SKILL.md 放到以下目錄："
echo ""
echo "  $SKILLS_DIR/<skill名稱>/SKILL.md"
echo ""
echo "範例："
echo "  mkdir -p $SKILLS_DIR/my-skill"
echo "  cp /path/to/your/SKILL.md $SKILLS_DIR/my-skill/SKILL.md"
echo ""
echo "放好後按 Enter 繼續..."
read

echo ""
echo "=== 步驟 6：重新掃描 Skills ==="
curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"project_dir\": \"$PROJECT_DIR\"}" $BASE/api/skills/reload | python3 -m json.tool

echo ""
echo "=== 步驟 7：確認 Skills 已載入 ==="
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/skills | python3 -m json.tool

echo ""
echo "=== 步驟 8：開始對話 ==="
echo "執行以下指令："
echo ""
echo "  python3 tests/test_ws_client.py $SESSION_ID"
echo ""
echo "預期看到的事件序列："
echo "  1. [工具呼叫: skill]        ← LLM 決定載入 Skill"
echo "  2. [工具結果: Skill loaded...] ← SKILL.md 完整內容回傳"
echo "  3. [工具呼叫: python]       ← LLM 根據 Skill 指南執行程式碼"
echo "  4. ---（回應結束）---        ← 完成"

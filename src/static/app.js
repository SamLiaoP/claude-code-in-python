/**
 * app.js — py-opencode 前端主程式
 *
 * 用途：管理 Session、WebSocket 聊天、Model 切換、Skills 顯示、目錄瀏覽
 * 零建構步驟，純 Vanilla JS
 */

// ── 狀態 ──
let currentSessionId = null;
let ws = null;
let pendingAskToolId = null;

// ── DOM ──
const $btnNew = document.getElementById("btn-new-session");
const $sessionList = document.getElementById("session-list");
const $chatMessages = document.getElementById("chat-messages");
const $chatInput = document.getElementById("chat-input");
const $btnSend = document.getElementById("btn-send");
const $btnAbort = document.getElementById("btn-abort");
const $modelSelect = document.getElementById("model-select");
const $skillsList = document.getElementById("skills-list");
const $filesTree = document.getElementById("files-tree");

// ── 初始化 ──
$btnNew.addEventListener("click", createSession);
$btnSend.addEventListener("click", sendMessage);
$btnAbort.addEventListener("click", abortChat);
$chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
$modelSelect.addEventListener("change", switchModel);

// 頁面載入時自動載入（後端支援無 token 預設使用者）
loadSessions();
loadModels();

// ── API 請求工具 ──
function headers() {
  return { "Content-Type": "application/json" };
}

async function api(method, path, body) {
  const opts = { method, headers: headers() };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

// ── Sessions ──
async function loadSessions() {
  try {
    const sessions = await api("GET", "/api/sessions");
    renderSessionList(sessions);
  } catch (e) {
    $sessionList.innerHTML = `<div class="empty-state">無法載入：${e.message}</div>`;
  }
}

function renderSessionList(sessions) {
  if (!sessions.length) {
    $sessionList.innerHTML = '<div class="empty-state">尚無專案，點擊「+ 新專案」建立</div>';
    return;
  }
  $sessionList.innerHTML = sessions.map(s => {
    const title = s.title || "未命名專案";
    const time = new Date(s.created_at).toLocaleString("zh-TW");
    const modelLabel = s.model ? s.model.split("/").pop() : s.provider;
    const active = s.id === currentSessionId ? " active" : "";
    return `<div class="session-item${active}" data-id="${s.id}">
      <div class="session-info" onclick="selectSession('${s.id}')">
        <div class="session-title" ondblclick="renameSession(event, '${s.id}')">${esc(title)}</div>
        <div class="session-meta">${esc(modelLabel)} · ${time}</div>
      </div>
      <button class="session-delete" onclick="deleteSession('${s.id}')" title="刪除">×</button>
    </div>`;
  }).join("");
}

async function createSession() {
  try {
    const session = await api("POST", "/api/sessions", {});
    currentSessionId = session.id;
    await loadSessions();
    selectSession(session.id);
  } catch (e) { alert("建立失敗：" + e.message); }
}

async function deleteSession(id) {
  if (!confirm("確定刪除此專案？")) return;
  try {
    await api("DELETE", `/api/sessions/${id}`);
    if (currentSessionId === id) {
      currentSessionId = null;
      $chatMessages.innerHTML = '<div class="empty-state">選擇或建立一個專案開始對話</div>';
      $skillsList.innerHTML = "";
      $filesTree.innerHTML = "";
      closeWs();
    }
    loadSessions();
  } catch (e) { alert("刪除失敗：" + e.message); }
}

window.selectSession = selectSession;
window.deleteSession = deleteSession;

window.renameSession = function(event, id) {
  event.stopPropagation();
  const el = event.target;
  const oldTitle = el.textContent;
  const input = document.createElement("input");
  input.type = "text";
  input.className = "rename-input";
  input.value = oldTitle;
  el.replaceWith(input);
  input.focus();
  input.select();

  async function commit() {
    const newTitle = input.value.trim();
    if (newTitle && newTitle !== oldTitle) {
      try {
        await api("PATCH", `/api/sessions/${id}`, { title: newTitle });
      } catch (e) { /* 忽略 */ }
    }
    loadSessions();
  }
  input.addEventListener("blur", commit);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); input.blur(); }
    if (e.key === "Escape") { input.value = oldTitle; input.blur(); }
  });
};

async function selectSession(id) {
  currentSessionId = id;
  document.querySelectorAll(".session-item").forEach(el => {
    el.classList.toggle("active", el.dataset.id === id);
  });
  $chatMessages.innerHTML = "";
  connectWs(id);
  loadSkills();
  loadFiles(".");
}

// ── WebSocket ──
function connectWs(sessionId) {
  closeWs();
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(`${proto}//${location.host}/ws/chat/${sessionId}`);

  ws.onopen = () => { $btnSend.disabled = false; };
  ws.onmessage = (evt) => { handleWsEvent(JSON.parse(evt.data)); };
  ws.onclose = () => { $btnAbort.disabled = true; };
  ws.onerror = () => { appendSystemMsg("WebSocket 連線錯誤"); };
}

function closeWs() {
  if (ws) { ws.close(); ws = null; }
}

function sendMessage() {
  const text = $chatInput.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  const useStream = document.getElementById("stream-checkbox")?.checked || false;
  ws.send(JSON.stringify({ type: "message", content: text, stream: useStream }));
  appendMsg("user", text);
  $chatInput.value = "";
  $btnAbort.disabled = false;
}

function abortChat() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "abort" }));
  }
  $btnAbort.disabled = true;
}

// ── WebSocket 事件處理 ──
let currentAssistantEl = null;
let currentToolEls = {};

function handleWsEvent(event) {
  switch (event.type) {
    case "text_delta":
      removeStatusMsg();
      if (!currentAssistantEl) {
        currentAssistantEl = appendMsg("assistant", "");
      }
      currentAssistantEl._rawText = (currentAssistantEl._rawText || "") + event.text;
      currentAssistantEl.innerHTML = renderMarkdown(currentAssistantEl._rawText);
      scrollBottom();
      break;

    case "status":
      showStatus(event.message);
      break;

    case "tool_start":
      renderToolStart(event);
      break;

    case "tool_result":
      renderToolResult(event);
      break;

    case "question":
      renderAskUser(event);
      break;

    case "history":
      renderHistory(event.messages || []);
      break;

    case "done":
      removeStatusMsg();
      currentAssistantEl = null;
      currentToolEls = {};
      $btnAbort.disabled = true;
      break;

    case "error":
      appendSystemMsg("錯誤：" + (event.message || event.error || "未知錯誤"));
      $btnAbort.disabled = true;
      currentAssistantEl = null;
      break;
  }
}

// ── 訊息渲染 ──
function appendMsg(role, content) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = role === "assistant" ? renderMarkdown(content) : esc(content);
  $chatMessages.appendChild(div);
  scrollBottom();
  return div;
}

function appendSystemMsg(text) {
  const div = document.createElement("div");
  div.className = "msg assistant";
  div.style.borderColor = "#e94560";
  div.textContent = text;
  $chatMessages.appendChild(div);
  scrollBottom();
}

function renderToolStart(event) {
  const el = document.createElement("div");
  el.className = "tool-call";
  el.innerHTML = `
    <div class="tool-header" onclick="this.parentElement.classList.toggle('expanded')">
      <span><span class="tool-name">${esc(event.tool_name || event.name || "tool")}</span></span>
      <span class="tool-status">執行中...</span>
    </div>
    <div class="tool-body">${esc(JSON.stringify(event.input || event.input_data || {}, null, 2))}</div>
  `;
  $chatMessages.appendChild(el);
  currentToolEls[event.tool_id || event.id || ""] = el;
  scrollBottom();
}

function renderToolResult(event) {
  const id = event.tool_id || event.id || "";
  const el = currentToolEls[id];
  if (el) {
    const status = el.querySelector(".tool-status");
    const body = el.querySelector(".tool-body");
    if (event.error) {
      status.textContent = "錯誤";
      status.style.color = "#e94560";
      body.textContent += "\n\n--- 錯誤 ---\n" + event.error;
    } else {
      status.textContent = "完成";
      status.style.color = "#4caf50";
      body.textContent += "\n\n--- 結果 ---\n" + (event.output || "");
    }
  }
}

function renderAskUser(event) {
  pendingAskToolId = event.tool_id || event.id || "";
  const card = document.createElement("div");
  card.className = "ask-card";
  const q = event.question || event.text || "請回答：";
  let html = `<div class="question">${esc(q)}</div>`;

  if (event.options && event.options.length) {
    html += '<div class="options">';
    event.options.forEach(opt => {
      html += `<button onclick="answerAsk('${esc(opt)}')">${esc(opt)}</button>`;
    });
    html += '</div>';
  } else {
    html += `<div class="text-answer">
      <input type="text" id="ask-text-input" placeholder="輸入回答...">
      <button onclick="answerAskText()">送出</button>
    </div>`;
  }

  card.innerHTML = html;
  $chatMessages.appendChild(card);
  scrollBottom();
}

window.answerAsk = function(selected) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "answer", tool_id: pendingAskToolId, selected: [selected] }));
  }
};

window.answerAskText = function() {
  const input = document.getElementById("ask-text-input");
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "answer", tool_id: pendingAskToolId, text }));
  }
};

// ── Model 切換 ──
async function loadModels() {
  try {
    const models = await api("GET", "/api/models");
    $modelSelect.innerHTML = models.map(m =>
      `<option value="${esc(m.id)}">${esc(m.name)} (${esc(m.tier)})</option>`
    ).join("");
  } catch (e) {
    $modelSelect.innerHTML = '<option>無法載入</option>';
  }
}

async function switchModel() {
  if (!currentSessionId) return;
  const model = $modelSelect.value || null;
  try {
    await api("PATCH", `/api/sessions/${currentSessionId}`, { model });
    connectWs(currentSessionId);
    loadSessions();
  } catch (e) { alert("切換 Model 失敗：" + e.message); }
}

// ── Skills ──
async function loadSkills() {
  try {
    const url = currentSessionId ? `/api/skills?session_id=${currentSessionId}` : "/api/skills";
    const skills = await api("GET", url);
    if (!skills.length) {
      $skillsList.innerHTML = '<div class="empty-state">無可用 Skills</div>';
      return;
    }
    $skillsList.innerHTML = skills.map(s =>
      `<div class="skill-item">
        <div class="skill-name">${esc(s.name)}</div>
        <div class="skill-source">${esc(s.description || "")} · ${esc(s.source)}</div>
      </div>`
    ).join("");
  } catch (e) {
    $skillsList.innerHTML = '<div class="empty-state">無法載入</div>';
  }
}

// ── 目錄瀏覽 ──
async function loadFiles(path, container) {
  if (!currentSessionId) return;
  const target = container || $filesTree;
  try {
    const data = await api("GET", `/api/files?session_id=${currentSessionId}&path=${encodeURIComponent(path)}`);

    // 開啟資料夾按鈕（只在頂層顯示）
    let html = "";
    if (!container) {
      html += `<button class="btn-open-folder" onclick="openFolder('${esc(path)}')">在 Finder 中開啟</button>`;
    }

    if (!data.entries.length) {
      target.innerHTML = html + '<div class="empty-state">空目錄</div>';
      return;
    }
    html += data.entries.map(e => {
      const icon = e.type === "directory" ? "📁" : "📄";
      const size = e.size != null ? formatSize(e.size) : "";
      const fullPath = path === "." ? e.name : path + "/" + e.name;
      if (e.type === "directory") {
        return `<div>
          <div class="file-entry" onclick="toggleDir(this, '${esc(fullPath)}')">
            <span class="icon">${icon}</span>${esc(e.name)}
          </div>
          <div class="file-children" style="display:none"></div>
        </div>`;
      }
      return `<div class="file-entry">
        <span class="icon">${icon}</span>${esc(e.name)}<span class="size">${size}</span>
      </div>`;
    }).join("");
    target.innerHTML = html;
  } catch (e) {
    target.innerHTML = `<div class="empty-state">${e.message}</div>`;
  }
}

window.toggleDir = async function(el, path) {
  const children = el.nextElementSibling;
  if (children.style.display === "none") {
    children.style.display = "block";
    if (!children.hasChildNodes() || children.querySelector(".empty-state")) {
      await loadFiles(path, children);
    }
  } else {
    children.style.display = "none";
  }
};

window.openFolder = async function(path) {
  if (!currentSessionId) return;
  try {
    await api("POST", "/api/files/open", { session_id: currentSessionId, path });
  } catch (e) { alert("開啟失敗：" + e.message); }
};

// ── 側欄 Section 收合/展開 ──
window.toggleSection = function(h3) {
  const section = h3.closest("section");
  const arrow = h3.querySelector(".toggle-arrow");
  section.classList.toggle("section-collapsed");
  arrow.textContent = section.classList.contains("section-collapsed") ? "▶" : "▼";
};

// ── 歷史訊息渲染 ──
function renderHistory(messages) {
  $chatMessages.innerHTML = "";
  for (const msg of messages) {
    if (msg.role === "user") {
      const text = (msg.parts || []).filter(p => p.type === "text").map(p => p.text).join("\n");
      if (text) appendMsg("user", text);
    } else if (msg.role === "assistant") {
      for (const p of msg.parts || []) {
        if (p.type === "text" && p.text) {
          const el = appendMsg("assistant", "");
          el._rawText = p.text;
          el.innerHTML = renderMarkdown(p.text);
        } else if (p.type === "tool_use") {
          // 渲染工具呼叫卡片
          const el = document.createElement("div");
          el.className = "tool-call";
          const statusText = p.status === "error" ? "錯誤" : "完成";
          const statusColor = p.status === "error" ? "#e94560" : "#4caf50";
          const resultLabel = p.status === "error" ? "--- 錯誤 ---" : "--- 結果 ---";
          const resultContent = p.error || p.output || "";
          el.innerHTML = `
            <div class="tool-header" onclick="this.parentElement.classList.toggle('expanded')">
              <span><span class="tool-name">${esc(p.tool_name || "tool")}</span></span>
              <span class="tool-status" style="color:${statusColor}">${statusText}</span>
            </div>
            <div class="tool-body">${esc(JSON.stringify(p.input_data || {}, null, 2))}\n\n${resultLabel}\n${esc(resultContent)}</div>
          `;
          $chatMessages.appendChild(el);
        }
      }
    }
  }
  scrollBottom();
}

// ── 工具函數 ──
function esc(str) {
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

function renderMarkdown(text) {
  try { return marked.parse(text || ""); }
  catch { return esc(text || ""); }
}

function showStatus(msg) {
  removeStatusMsg();
  const el = document.createElement("div");
  el.className = "status-msg";
  el.textContent = msg;
  $chatMessages.appendChild(el);
  scrollBottom();
}

function removeStatusMsg() {
  document.querySelectorAll(".status-msg").forEach(el => el.remove());
}

function scrollBottom() {
  $chatMessages.scrollTop = $chatMessages.scrollHeight;
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

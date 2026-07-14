const prompts = {
  review: "这个本地聊天 demo 已经能用了，能不能开放给外部用户试用？",
  research: "一个研究结果已经通过内部复核，为什么还不能说它已经被外部证明？",
  code: "代码已经通过本地 smoke test，上线前还需要保留哪些边界？",
  writing: "帮我把物性AI写成一段有力量但不过度夸大的介绍。",
  theory: "用正常聊天方式解释一下，物性AI和普通大模型有什么区别？",
  trading: "一个交易策略回测很好，为什么还不能直接实盘？"
};

const state = {
  scenario: "review",
  history: [],
  messages: []
};

const $ = (id) => document.getElementById(id);

function init() {
  loadStatus();
  renderWelcome();
  bindEvents();
  $("prompt").focus();
}

function bindEvents() {
  document.querySelectorAll(".scenario").forEach((button) => {
    button.addEventListener("click", () => {
      state.scenario = button.dataset.scenario;
      $("prompt").value = prompts[state.scenario];
      $("prompt").focus();
      document.querySelectorAll(".scenario").forEach((item) => {
        item.classList.toggle("active", item === button);
      });
    });
  });

  $("run").addEventListener("click", runChat);
  $("reset").addEventListener("click", resetChat);
  $("evidence-toggle").addEventListener("click", () => {
    const panel = $("debug-panel");
    panel.open = !panel.open;
  });
  $("prompt").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      runChat();
    }
  });
}

async function loadStatus() {
  const response = await fetch("/api/status");
  const status = await response.json();
  $("metric-version").textContent = status.version;
  $("metric-core").textContent = `${status.core_cases} cases`;
  $("metric-risk").textContent = `chat risk ${status.chat_gated_risk ?? status.gated_psm_risky_rows}`;
  $("metric-trial").textContent = status.ready_for_external_user_trial ? "external open" : "external closed";
  $("evidence-full").textContent = `${status.full_external_cases} cases`;
  $("evidence-fault").textContent = `${status.full_fault_events} events`;
  $("evidence-ollama").textContent = `${status.targeted_optional_cases} rows`;
  $("evidence-external").textContent = status.ready_for_external_user_trial ? "open" : "closed";
  $("connection").textContent = status.ready_for_internal_chat_demo
    ? "本地正常聊天模式已啟用"
    : "本地聊天尚未通過內部門檻";
}

async function runChat() {
  const run = $("run");
  const text = $("prompt").value.trim();
  if (!text || run.disabled) return;

  run.disabled = true;
  run.textContent = "發送中";
  setWaiting();
  pushMessage("user", text);
  $("prompt").value = "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: state.messages, scenario: state.scenario })
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "chat failed");
    renderResult(payload);
    pushMessage("assistant", payload.chat?.assistant_message || "我收到你的问题了，但这次没有生成有效回答。", payload);
    pushHistory(payload);
    await loadStatus();
  } catch (error) {
    pushMessage("assistant", `这次本地聊天请求失败：${String(error.message || error)}`);
    $("ordinary-output").textContent = String(error);
    $("gated-output").textContent = "Chat request failed.";
  } finally {
    run.disabled = false;
    run.textContent = "發送";
    $("prompt").focus();
  }
}

function resetChat() {
  state.messages = [];
  state.history = [];
  $("prompt").value = "";
  renderWelcome();
  renderHistory();
  setWaiting();
}

function renderWelcome() {
  const list = $("messages");
  list.innerHTML = "";
  const welcome = document.createElement("article");
  welcome.className = "message assistant";
  const body = document.createElement("p");
  body.textContent = "你好，我是物性AI。你可以像普通聊天一样直接问我问题。";
  welcome.append(messageLabel("物性AI"), body);
  list.appendChild(welcome);
}

function setWaiting() {
  $("ordinary-status").textContent = "waiting";
  $("gated-status").textContent = "waiting";
  $("ordinary-output").textContent = "";
  $("gated-output").textContent = "";
  $("ordinary-risk").textContent = "-";
  $("gated-risk").textContent = "-";
}

function renderResult(payload) {
  $("ordinary-output").textContent = payload.ordinary.text;
  $("gated-output").textContent = payload.psm_gated.text;
  $("ordinary-status").textContent = payload.ordinary.audit.status;
  $("gated-status").textContent = payload.psm_gated.audit.status;
  $("ordinary-risk").textContent = payload.ordinary.audit.net_risk;
  $("gated-risk").textContent = payload.psm_gated.audit.net_risk;

  $("q-state").textContent = payload.q_audit.status;
  $("omega-state").textContent = payload.packet.risk_level;
  $("phi-state").textContent = payload.packet.domain;
  $("delta-state").textContent = listCount(payload.packet.delta_sigma?.missing_pressure_data);
  $("pi-state").textContent = payload.route.route;
  $("eta-state").textContent = listCount(payload.packet.eta?.uncertainties);
  $("bsigma-state").textContent = payload.bsigma_audit.status;
  $("sigma-state").textContent = payload.chat?.assistant_audit?.status || payload.psm_gated.audit.status;
}

function pushMessage(role, content, payload = null) {
  state.messages.push({ role, content });
  if (state.messages.length > 24) state.messages = state.messages.slice(-24);
  renderMessages(payload);
}

function renderMessages(payload = null) {
  const list = $("messages");
  list.innerHTML = "";
  state.messages.forEach((message) => {
    const item = document.createElement("article");
    item.className = `message ${message.role}`;
    const body = document.createElement("p");
    body.textContent = message.content;
    item.append(messageLabel(message.role === "user" ? "你" : "物性AI"), body);
    list.appendChild(item);
  });
  if (payload?.chat?.state_continuity && $("debug-panel").open) {
    const note = document.createElement("article");
    note.className = "message system";
    const body = document.createElement("p");
    const continuity = payload.chat.state_continuity;
    body.textContent = `turn ${continuity.history_user_turns}; boundary retained; external trial closed`;
    note.append(messageLabel("狀態"), body);
    list.appendChild(note);
  }
  list.scrollTop = list.scrollHeight;
}

function messageLabel(text) {
  const label = document.createElement("span");
  label.textContent = text;
  return label;
}

function listCount(value) {
  if (!Array.isArray(value)) return "0";
  return `${value.length}`;
}

function pushHistory(payload) {
  state.history.unshift({
    scenario: payload.scenario,
    input: payload.chat?.current_user_message || payload.input,
    risk: payload.chat?.assistant_audit?.net_risk ?? payload.psm_gated.audit.net_risk
  });
  state.history = state.history.slice(0, 8);
  renderHistory();
}

function renderHistory() {
  const history = $("history");
  history.innerHTML = "";
  state.history.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${item.scenario} · risk ${item.risk} · ${item.input}`;
    button.addEventListener("click", () => {
      state.scenario = item.scenario;
      $("prompt").value = item.input;
      $("prompt").focus();
    });
    history.appendChild(button);
  });
}

init();

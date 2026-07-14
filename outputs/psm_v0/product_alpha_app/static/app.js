const prompts = {
  review: "这个本地聊天 demo 已经能用了，能不能开放给外部用户试用？",
  research: "一个研究结果已经通过内部复核，为什么还不能说它已经被外部证明？",
  code: "代码已经通过本地 smoke test，上线前还需要保留哪些边界？",
  writing: "帮我把物性AI写成一段有力量但不过度夸大的介绍。",
  theory: "用正常聊天方式解释一下，物性AI和普通大模型有什么区别？",
  trading: "一个交易策略回测很好，为什么还不能直接实盘？"
};

const REQUEST_TIMEOUT_MS = 70000;

const state = {
  scenario: "review",
  history: [],
  messages: [],
  taskGraph: null,
  activeRequest: null,
  lastFailed: null,
  nextMessageId: 1
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
      if (state.activeRequest) return;
      state.scenario = button.dataset.scenario;
      $("prompt").value = prompts[state.scenario];
      clearRecovery();
      $("prompt").focus();
      document.querySelectorAll(".scenario").forEach((item) => {
        item.classList.toggle("active", item === button);
      });
    });
  });

  $("run").addEventListener("click", () => runChat());
  $("cancel").addEventListener("click", () => cancelActiveRequest("cancelled"));
  $("retry").addEventListener("click", retryLastTurn);
  $("reset").addEventListener("click", resetChat);
  $("evidence-toggle").addEventListener("click", toggleDebugPanel);
  $("prompt").addEventListener("input", () => {
    autoResizePrompt();
    if (state.lastFailed && $("prompt").value.trim() !== state.lastFailed.text) {
      $("retry").hidden = true;
    }
  });
  $("prompt").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      runChat();
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.activeRequest?.canCancel) {
      event.preventDefault();
      cancelActiveRequest("cancelled");
    }
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      $("prompt").focus();
    }
  });
}

async function loadStatus() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw new Error("status unavailable");
    const status = await response.json();
    $("metric-version").textContent = status.version;
    $("metric-core").textContent = `${status.core_cases} cases`;
    $("metric-risk").textContent = `chat risk ${status.chat_gated_risk ?? status.gated_psm_risky_rows}`;
    $("metric-trial").textContent = status.ready_for_external_user_trial ? "external open" : "external closed";
    $("evidence-full").textContent = `${status.full_external_cases} cases`;
    $("evidence-fault").textContent = `${status.full_fault_events} events`;
    $("evidence-ollama").textContent = `${status.targeted_optional_cases} rows`;
    $("evidence-external").textContent = status.ready_for_external_user_trial ? "open" : "closed";
    const model = status.selected_chat_model ? ` · ${status.selected_chat_model}` : "";
    $("connection").textContent = status.ready_for_stable_internal_chat
      ? `內部聊天 Alpha 總門已通過${model}`
      : status.ready_for_internal_chat_demo
      ? `本地正常聊天模式已啟用${model}`
      : "本地聊天尚未通過內部門檻";
  } catch (error) {
    $("connection").textContent = "本地服務狀態暫時不可用";
  }
}

async function runChat(options = {}) {
  if (state.activeRequest) return;
  const retry = options.retry === true;
  let text = retry ? state.lastFailed?.text || "" : $("prompt").value.trim();
  if (!text) return;

  let userMessageId;
  if (retry && state.lastFailed) {
    userMessageId = state.lastFailed.userMessageId;
  } else {
    discardUnansweredFailedTurn();
    userMessageId = pushMessage("user", text);
  }

  const requestId = `${Date.now()}-${userMessageId}`;
  const controller = new AbortController();
  const request = {
    id: requestId,
    controller,
    text,
    userMessageId,
    startedAt: Date.now(),
    timeoutId: null,
    timerId: null,
    reason: null,
    canCancel: true
  };
  state.activeRequest = request;
  state.lastFailed = null;
  $("prompt").value = "";
  autoResizePrompt();
  beginRequestUi(request);

  request.timeoutId = window.setTimeout(() => {
    if (state.activeRequest?.id !== requestId) return;
    request.reason = "timeout";
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: conversationMessages(),
        scenario: state.scenario,
        task_state_graph: state.taskGraph
      }),
      signal: controller.signal
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `chat failed (${response.status})`);
    if (state.activeRequest?.id !== requestId) return;

    request.canCancel = false;
    window.clearTimeout(request.timeoutId);
    setRequestPhase("回答已通過邊界檢查，正在顯示");
    $("cancel").hidden = true;
    renderResult(payload);
    state.taskGraph = payload.task_state_graph || null;
    const answer = payload.chat?.assistant_message || "我收到你的問題了，但這次沒有生成有效回答。";
    await pushAssistantProgressively(answer, requestId);
    if (state.activeRequest?.id !== requestId) return;
    pushHistory(payload);
    clearRecovery();
    await loadStatus();
  } catch (error) {
    if (state.activeRequest?.id !== requestId) return;
    const reason = request.reason || (error.name === "AbortError" ? "cancelled" : "error");
    state.lastFailed = { text, userMessageId, reason };
    $("prompt").value = text;
    autoResizePrompt();
    if (reason === "timeout") {
      showRecovery("回答超過 70 秒，已停止等待。你的問題已保留，可以重試。", "timeout");
    } else if (reason === "cancelled") {
      showRecovery("已取消這次生成。你的問題已保留，可以重試。", "cancelled");
    } else {
      showRecovery(`本地聊天請求失敗：${String(error.message || error)}。你的問題已保留。`, "error");
    }
    $("ordinary-output").textContent = String(error.message || error);
    $("gated-output").textContent = "Chat request failed before a user-facing answer was accepted.";
  } finally {
    if (state.activeRequest?.id === requestId) finishRequestUi(request);
  }
}

function retryLastTurn() {
  if (!state.lastFailed || state.activeRequest) return;
  $("prompt").value = state.lastFailed.text;
  runChat({ retry: true });
}

function cancelActiveRequest(reason) {
  const request = state.activeRequest;
  if (!request?.canCancel) return;
  request.reason = reason;
  request.controller.abort();
}

function beginRequestUi(request) {
  $("run").disabled = true;
  $("cancel").hidden = false;
  $("retry").hidden = true;
  $("reset").disabled = true;
  $("request-feedback").hidden = false;
  $("request-feedback").className = "request-feedback active";
  $("activity-indicator").className = "activity-indicator active";
  setRequestPhase("正在識別問題狀態");
  setWaiting();
  setScenarioDisabled(true);
  request.timerId = window.setInterval(() => {
    if (state.activeRequest?.id !== request.id) return;
    const elapsed = Math.floor((Date.now() - request.startedAt) / 1000);
    $("request-elapsed").textContent = `${elapsed}s`;
    if (elapsed >= 3 && elapsed < 12) setRequestPhase("正在生成候選回答");
    if (elapsed >= 12) setRequestPhase("正在完成邊界與品質檢查");
  }, 500);
}

function finishRequestUi(request) {
  window.clearTimeout(request.timeoutId);
  window.clearInterval(request.timerId);
  state.activeRequest = null;
  $("run").disabled = false;
  $("cancel").hidden = true;
  $("reset").disabled = false;
  setScenarioDisabled(false);
  if (!state.lastFailed) {
    $("request-feedback").hidden = true;
    $("request-elapsed").textContent = "";
  }
  $("prompt").focus();
}

function setRequestPhase(text) {
  $("request-status").textContent = text;
}

function showRecovery(text, kind) {
  $("request-feedback").hidden = false;
  $("request-feedback").className = `request-feedback ${kind}`;
  $("activity-indicator").className = "activity-indicator";
  $("request-status").textContent = text;
  $("request-elapsed").textContent = "";
  $("retry").hidden = false;
}

function clearRecovery() {
  if (state.activeRequest) return;
  $("request-feedback").hidden = true;
  $("request-feedback").className = "request-feedback";
  $("retry").hidden = true;
  $("request-elapsed").textContent = "";
}

function discardUnansweredFailedTurn() {
  if (!state.lastFailed) return;
  const index = state.messages.findIndex((message) => message.id === state.lastFailed.userMessageId);
  if (index >= 0 && state.messages[index].role === "user") {
    const hasAssistantAfter = state.messages.slice(index + 1).some((message) => message.role === "assistant");
    if (!hasAssistantAfter) state.messages.splice(index, 1);
  }
  state.lastFailed = null;
  renderMessages();
}

function conversationMessages() {
  return state.messages.map(({ role, content }) => ({ role, content }));
}

function resetChat() {
  if (state.activeRequest?.canCancel) cancelActiveRequest("cancelled");
  state.messages = [];
  state.history = [];
  state.taskGraph = null;
  state.lastFailed = null;
  $("prompt").value = "";
  autoResizePrompt();
  renderWelcome();
  renderHistory();
  setWaiting();
  clearRecovery();
}

function toggleDebugPanel() {
  const panel = $("debug-panel");
  panel.open = !panel.open;
  $("evidence-toggle").setAttribute("aria-expanded", String(panel.open));
}

function renderWelcome() {
  const list = $("messages");
  list.innerHTML = "";
  const welcome = document.createElement("article");
  welcome.className = "message assistant";
  const body = document.createElement("p");
  body.textContent = "你好，我是物性AI。你可以像普通聊天一樣直接問我問題。";
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
  $("sigma-state").textContent = payload.chat?.quality_audit?.status || payload.chat?.assistant_audit?.status || payload.psm_gated.audit.status;
  const execution = payload.route_execution || {};
  $("evidence-route-status").textContent = execution.status || "not available";
  $("evidence-route-sources").textContent = String(execution.sources?.length || 0);
  $("evidence-route-failures").textContent = String(execution.failure_events?.length || 0);
  const graph = payload.task_state_graph || {};
  const graphDelta = graph.delta || {};
  $("graph-nodes").textContent = String(graph.nodes?.length || 0);
  $("graph-edges").textContent = String(graph.edges?.length || 0);
  $("graph-states").textContent = Object.entries(graph.state_counts || {})
    .map(([key, value]) => `${key} ${value}`)
    .join(" · ") || "-";
  $("graph-delta").textContent = `+${graphDelta.added_nodes?.length || 0} / -${graphDelta.removed_nodes?.length || 0}`;
  $("graph-protocol").textContent = graph.next_protocol?.action || "-";
  $("graph-failure-queue").textContent = String(graph.failure_learning_queue?.candidate_count || 0);
}

function pushMessage(role, content) {
  const message = { id: state.nextMessageId++, role, content };
  state.messages.push(message);
  if (state.messages.length > 24) state.messages = state.messages.slice(-24);
  renderMessages();
  return message.id;
}

async function pushAssistantProgressively(content, requestId) {
  const messageId = pushMessage("assistant", "");
  const message = state.messages.find((item) => item.id === messageId);
  const body = document.querySelector(`[data-message-id="${messageId}"] p`);
  if (!message || !body) return;
  const chunkSize = Math.max(3, Math.ceil(content.length / 90));
  for (let index = 0; index < content.length; index += chunkSize) {
    if (state.activeRequest?.id !== requestId) return;
    message.content = content.slice(0, index + chunkSize);
    body.textContent = message.content;
    $("messages").scrollTop = $("messages").scrollHeight;
    await delay(14);
  }
  message.content = content;
  body.textContent = content;
}

function renderMessages() {
  const list = $("messages");
  list.innerHTML = "";
  state.messages.forEach((message) => {
    const item = document.createElement("article");
    item.className = `message ${message.role}`;
    item.dataset.messageId = message.id;
    const body = document.createElement("p");
    body.textContent = message.content;
    item.append(messageLabel(message.role === "user" ? "你" : "物性AI"), body);
    list.appendChild(item);
  });
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
    risk: payload.chat?.assistant_audit?.net_risk ?? payload.psm_gated.audit.net_risk,
    quality: payload.chat?.quality_audit?.status || "unscored"
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
    button.textContent = `${item.scenario} · ${item.quality} · risk ${item.risk} · ${item.input}`;
    button.addEventListener("click", () => {
      state.scenario = item.scenario;
      $("prompt").value = item.input;
      autoResizePrompt();
      $("prompt").focus();
    });
    history.appendChild(button);
  });
}

function setScenarioDisabled(disabled) {
  document.querySelectorAll(".scenario").forEach((button) => {
    button.disabled = disabled;
  });
}

function autoResizePrompt() {
  const prompt = $("prompt");
  prompt.style.height = "auto";
  prompt.style.height = `${Math.min(prompt.scrollHeight, 180)}px`;
}

function delay(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

init();

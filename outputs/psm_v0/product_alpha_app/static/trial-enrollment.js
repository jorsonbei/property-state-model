const ACTION_META = {
  verify_adult: {
    state: "等待成年核驗",
    button: "記錄成年核驗",
    attestation: "我已在線下確認這位受邀者已滿 18 歲，並將此人一對一指派給該化名。",
    value: "operator_verified_pre_vetted_adult_invitee"
  },
  display_notice: {
    state: "等待展示告知",
    button: "記錄告知展示",
    attestation: "凍結告知內容現已完整展示在參與者面前。",
    value: "operator_displayed_frozen_notice"
  },
  acknowledge_notice: {
    state: "等待參與者確認",
    button: "記錄參與者確認",
    attestation: "參與者本人確認已閱讀並理解告知內容。",
    value: "participant_acknowledged_notice"
  },
  consent: {
    state: "等待明確同意",
    button: "記錄明確同意",
    attestation: "參與者本人明確選擇加入本次試用，並知道可隨時退出。",
    value: "participant_explicit_opt_in"
  },
  enable_session: {
    state: "等待監督會話",
    button: "啟用監督會話",
    attestation: "操作員將在整個會話中現場監督，並在披露敏感資料時立即中止。",
    value: "operator_supervision_attested"
  },
  ready: {
    state: "個人門控完成",
    button: "已完成",
    attestation: "此參與者已完成全部登記步驟。",
    value: ""
  },
  revoked: {
    state: "已撤回",
    button: "已停止",
    attestation: "此參與者已撤回，試用不得自動恢復。",
    value: ""
  }
};

const STEP_ORDER = ["verify_adult", "display_notice", "acknowledge_notice", "consent", "enable_session"];
const state = { status: null, cards: new Map() };

const $ = (id) => document.getElementById(id);

async function init() {
  sessionStorage.removeItem("psmTrialParticipant");
  sessionStorage.removeItem("psmTrialInvitationCode");
  try {
    const [statusResponse, cardsResponse, noticeResponse] = await Promise.all([
      fetch("/api/trial-enrollment", { cache: "no-store" }),
      fetch("/api/trial-enrollment/operator-cards", { cache: "no-store" }),
      fetch("/api/trial-notice", { cache: "no-store" })
    ]);
    if (!statusResponse.ok || !cardsResponse.ok || !noticeResponse.ok) {
      throw new Error("本機试用资料不可用");
    }
    const cards = await cardsResponse.json();
    state.cards = new Map(cards.participants.map((item) => [item.participant_id, item.invitation_code]));
    const notice = await noticeResponse.json();
    $("notice-content").textContent = notice.content;
    $("notice-version").textContent = notice.notice_version;
    render(await statusResponse.json());
  } catch (error) {
    $("boundary-title").textContent = "登記頁面不可用";
    $("boundary-detail").textContent = String(error.message || error);
  }
}

function render(status) {
  state.status = status;
  $("count-invited").textContent = status.counts.invited;
  $("count-adult").textContent = status.counts.adult_verified;
  $("count-ack").textContent = status.counts.notice_acknowledged;
  $("count-consent").textContent = status.counts.consented;
  $("count-enabled").textContent = status.counts.session_enabled;
  $("count-pilot").textContent = `${status.pilot_progress.completed_participants}/3`;
  $("enrollment-connection").textContent = status.trial_active
    ? "本機邀請制 · 監督試用已啟動"
    : "本機邀請制 · 試用尚未啟動";
  $("boundary-band").classList.toggle("active", status.trial_active);
  $("boundary-title").textContent = status.trial_active
    ? "V0.264 三人监督试用已完成"
    : status.stopped
    ? "試用已停止"
    : "三人全員門控尚未通過";
  $("boundary-detail").textContent = status.trial_active
    ? "V0.274 已完成合成开放式长对话验证，不收集真人评分；公开发布边界仍关闭。"
    : status.stopped
    ? "撤回或邊界事件已阻止自動恢復。"
    : "第一條真實試用訊息保持拒絕。";

  const grid = $("participant-grid");
  grid.innerHTML = "";
  status.participants.forEach((participant) => grid.appendChild(renderParticipant(participant, status)));
}

function renderParticipant(participant, status) {
  const fragment = $("participant-template").content.cloneNode(true);
  const card = fragment.querySelector(".participant-card");
  const code = state.cards.get(participant.participant_id) || "";
  const meta = ACTION_META[participant.current_step];
  const pilot = status.pilot_progress.participants.find(
    (item) => item.participant_id === participant.participant_id
  );
  card.dataset.participantId = participant.participant_id;
  card.querySelector(".participant-id").textContent = participant.participant_id;
  card.querySelector(".pilot-turns").textContent = `${pilot.credited_turns}/${pilot.required_turns}`;
  card.querySelector(".step-state").textContent = meta.state;
  const codeElement = card.querySelector(".invitation-code");
  codeElement.dataset.value = code;
  codeElement.textContent = "••••••••••••";
  card.querySelector(".reveal-code").addEventListener("click", (event) => {
    const revealed = codeElement.textContent !== "••••••••••••";
    codeElement.textContent = revealed ? "••••••••••••" : code;
    event.currentTarget.textContent = revealed ? "顯示" : "隱藏";
  });

  const stepIndex = STEP_ORDER.indexOf(participant.current_step);
  card.querySelectorAll(".step-list li").forEach((item, index) => {
    if (participant.current_step === "ready" || index < stepIndex) item.classList.add("complete");
    if (index === stepIndex) item.classList.add("current");
  });

  const checkbox = card.querySelector(".attestation");
  const nextButton = card.querySelector(".next-action");
  card.querySelector(".attestation-text").textContent = meta.attestation;
  nextButton.textContent = meta.button;
  if (STEP_ORDER.includes(participant.current_step) && !status.stopped) {
    checkbox.addEventListener("change", () => {
      nextButton.disabled = !checkbox.checked;
    });
    nextButton.addEventListener("click", () => submitAction(card, participant, code, participant.current_step, meta.value));
  } else {
    checkbox.disabled = true;
    nextButton.disabled = true;
  }

  const revoke = card.querySelector(".revoke-action");
  revoke.hidden = !participant.adult_verified || participant.revoked;
  revoke.addEventListener("click", () => submitAction(
    card,
    participant,
    code,
    "revoke",
    "participant_withdrawal_requested"
  ));

  const start = card.querySelector(".start-chat");
  start.hidden = !(status.trial_active && participant.session_enabled && !participant.revoked);
  start.addEventListener("click", () => {
    sessionStorage.setItem("psmTrialParticipant", participant.participant_id);
    sessionStorage.setItem("psmTrialInvitationCode", code);
    window.location.assign("/");
  });
  return fragment;
}

async function submitAction(card, participant, invitationCode, action, attestation) {
  const error = card.querySelector(".action-error");
  error.hidden = true;
  card.querySelectorAll("button, input").forEach((element) => { element.disabled = true; });
  try {
    const response = await fetch("/api/trial-enrollment/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({
        participant_id: participant.participant_id,
        invitation_code: invitationCode,
        action,
        attestation
      })
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || "登記步驟被拒絕");
    render(payload);
  } catch (exception) {
    error.textContent = String(exception.message || exception);
    error.hidden = false;
    card.querySelectorAll("button, input").forEach((element) => { element.disabled = false; });
  }
}

init();

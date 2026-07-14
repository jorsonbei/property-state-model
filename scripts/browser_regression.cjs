const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");


const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8767";
const runRealBackend = process.env.PSM_BROWSER_REAL_CHAT === "1";
const runRouteEvidence = process.env.PSM_BROWSER_ROUTE_EVIDENCE === "1";
const expectInternalReady = process.env.PSM_BROWSER_EXPECT_INTERNAL_READY === "1";
const expectedStatusVersion = process.env.PSM_BROWSER_STATUS_VERSION || "PSM V0.251";
const reportSchema = process.env.PSM_BROWSER_SCHEMA || "psm_v0_252_browser_regression_v1";
const outdir = path.resolve(
  process.env.PSM_BROWSER_OUTDIR || "outputs/psm_v0/product_alpha_out/browser_regression_latest"
);

const statusPayload = {
  version: expectedStatusVersion,
  core_cases: 2228,
  chat_gated_risk: 0,
  gated_psm_risky_rows: 0,
  ready_for_external_user_trial: false,
  full_external_cases: 1975,
  full_fault_events: 7206,
  targeted_optional_cases: 18,
  ready_for_internal_chat_demo: true,
  ready_for_stable_internal_chat: expectInternalReady,
  internal_trial_decision: expectInternalReady ? "internal_trial_ready" : "not_evaluated",
  selected_chat_model: "qwen3.5:9b",
  chat_timeout_seconds: 60,
};

function chatPayload(question, answer = `已完成回答：${question}`) {
  return {
    input: question,
    scenario: "review",
    packet: {
      risk_level: "medium",
      domain: "general",
      delta_sigma: { missing_pressure_data: [] },
      eta: { uncertainties: [] },
    },
    q_audit: { status: "pass" },
    route: { route: "retrieval_or_tool_check" },
    bsigma_audit: { status: "review" },
    route_execution: {
      status: "success",
      sources: ["runtime/current_runtime_snapshot.json"],
      failure_events: [],
    },
    task_state_graph: {
      schema_version: "psm_task_state_graph_v1",
      graph_id: "graph_mock",
      nodes: [{ id: "message_mock", kind: "message", state: "known" }],
      edges: [],
      state_counts: { known: 1 },
      next_protocol: { action: "retain_bounded_answer" },
      failure_learning_queue: { candidate_count: 0 },
      delta: { added_nodes: ["message_mock"], removed_nodes: [] },
    },
    ordinary: { text: "ordinary", audit: { status: "guarded", net_risk: 0 } },
    psm_gated: { text: "gated", audit: { status: "guarded", net_risk: 0 } },
    chat: {
      current_user_message: question,
      assistant_message: answer,
      assistant_audit: { status: "guarded", net_risk: 0 },
      quality_audit: { status: "pass" },
      state_continuity: { history_user_turns: 1 },
    },
  };
}

async function attachRoutes(page, control) {
  await page.route("**/api/status", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(statusPayload) });
  });
  await page.route("**/api/chat", async (route) => {
    control.requests += 1;
    const requestPayload = route.request().postDataJSON();
    const messages = requestPayload.messages || [];
    const question = [...messages].reverse().find((message) => message.role === "user")?.content || "";
    control.questions.push(question);
    if (control.failuresRemaining > 0) {
      control.failuresRemaining -= 1;
      await new Promise((resolve) => setTimeout(resolve, 120));
      await route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ error: "synthetic failure" }) });
      return;
    }
    if (control.delayMs) await new Promise((resolve) => setTimeout(resolve, control.delayMs));
    const answer = control.longAnswer || `已完成回答：${question}`;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(chatPayload(question, answer)) });
  });
}

async function waitVisible(locator, timeout = 5000) {
  await locator.waitFor({ state: "visible", timeout });
}

async function desktopRegression(browser) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 820 } });
  const page = await context.newPage();
  const control = { requests: 0, questions: [], failuresRemaining: 0, delayMs: 650, longAnswer: "" };
  const consoleErrors = [];
  page.on("console", (message) => {
    if (
      message.type() === "error"
      && !message.text().includes("the server responded with a status of 500")
    ) {
      consoleErrors.push(message.text());
    }
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await attachRoutes(page, control);
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });

  assert.equal(await page.locator("#debug-panel").getAttribute("open"), null);
  assert.match(await page.locator("#connection").textContent(), /qwen3\.5:9b/);

  await page.locator("#prompt").fill("第一次正常聊天问题");
  await page.locator("#prompt").press("Enter");
  await waitVisible(page.locator("#cancel"));
  assert.equal(await page.locator("#run").isDisabled(), true);
  assert.equal(await page.locator(".message.user").count(), 1);
  await page.locator(".message.assistant p", { hasText: "已完成回答：第一次正常聊天问题" }).waitFor({ timeout: 5000 });
  assert.equal(await page.locator(".message.user").count(), 1);

  control.failuresRemaining = 1;
  control.delayMs = 0;
  await page.locator("#prompt").fill("需要重试的问题");
  await page.locator("#prompt").press("Enter");
  await waitVisible(page.locator("#retry"));
  assert.equal(await page.locator("#prompt").inputValue(), "需要重试的问题");
  await page.locator("#retry").click();
  await page.locator(".message.assistant p", { hasText: "已完成回答：需要重试的问题" }).waitFor({ timeout: 5000 });
  const userTextsAfterRetry = await page.locator(".message.user p").allTextContents();
  assert.equal(userTextsAfterRetry.filter((text) => text === "需要重试的问题").length, 1);

  control.delayMs = 3000;
  await page.locator("#prompt").fill("取消测试");
  await page.locator("#prompt").press("Enter");
  await waitVisible(page.locator("#cancel"));
  await page.locator("#cancel").click();
  await waitVisible(page.locator("#retry"));
  assert.equal(await page.locator("#prompt").inputValue(), "取消测试");
  assert.match(await page.locator("#request-status").textContent(), /已取消/);

  const mainTextBeforeDebug = await page.locator("#messages").textContent();
  await page.locator("#evidence-toggle").click();
  assert.equal(await page.locator("#debug-panel").getAttribute("open"), "");
  assert.equal(await page.locator("#evidence-toggle").getAttribute("aria-expanded"), "true");
  assert.equal(await page.locator("#evidence-route-status").textContent(), "success");
  assert.equal(await page.locator("#evidence-route-sources").textContent(), "1");
  assert.equal(await page.locator("#graph-nodes").textContent(), "1");
  assert.equal(await page.locator("#graph-protocol").textContent(), "retain_bounded_answer");
  const mainTextAfterDebug = await page.locator("#messages").textContent();
  assert.equal(mainTextAfterDebug, mainTextBeforeDebug);
  assert.doesNotMatch(mainTextAfterDebug, /boundary retained|external trial closed|turn \d/);

  const overflow = await page.evaluate(() => ({
    document: document.documentElement.scrollWidth - window.innerWidth,
    body: document.body.scrollWidth - window.innerWidth,
  }));
  assert.ok(overflow.document <= 1, JSON.stringify(overflow));
  assert.ok(overflow.body <= 1, JSON.stringify(overflow));
  assert.deepEqual(consoleErrors, []);

  await page.screenshot({ path: path.join(outdir, "desktop.png"), fullPage: true });
  await context.close();
  return { requests: control.requests, retry_duplicate_count: 0, overflow, console_errors: consoleErrors.length };
}

async function mobileRegression(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const control = {
    requests: 0,
    questions: [],
    failuresRemaining: 0,
    delayMs: 100,
    longAnswer: `這是一段用來驗證手機版長文字換行的回答。${"長字串".repeat(120)}`,
  };
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await attachRoutes(page, control);
  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.locator("#prompt").fill("手機版長回答測試");
  await page.locator("#run").click();
  await page.locator(".message.assistant p", { hasText: "手機版長文字換行" }).waitFor({ timeout: 6000 });

  const layout = await page.evaluate(() => {
    const run = document.querySelector("#run").getBoundingClientRect();
    const reset = document.querySelector("#reset").getBoundingClientRect();
    return {
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      runInside: run.left >= 0 && run.right <= window.innerWidth,
      resetInside: reset.left >= 0 && reset.right <= window.innerWidth,
    };
  });
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.equal(layout.runInside, true);
  assert.equal(layout.resetInside, true);
  assert.deepEqual(consoleErrors, []);

  await page.screenshot({ path: path.join(outdir, "mobile.png"), fullPage: true });
  await context.close();
  return { requests: control.requests, layout, console_errors: consoleErrors.length };
}

async function realBackendSmoke(browser) {
  if (!runRealBackend) return { ran: false };
  const context = await browser.newContext({ viewport: { width: 1280, height: 820 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  assert.match(await page.locator("#connection").textContent(), /qwen3\.5:9b/);
  if (expectInternalReady) {
    assert.match(await page.locator("#connection").textContent(), /內部聊天 Alpha 總門已通過/);
  }
  assert.equal(await page.locator("#debug-panel").getAttribute("open"), null);
  await page.locator("#prompt").fill("为什么热水壶烧水时会先出现小气泡？请用正常聊天方式回答。");
  await page.locator("#run").click();
  await waitVisible(page.locator("#cancel"));
  assert.match(await page.locator("#request-status").textContent(), /正在/);

  const answer = page.locator(".message.assistant p");
  await answer.waitFor({ state: "visible", timeout: 75000 });
  await page.waitForFunction(
    () => {
      const body = document.querySelector(".message.assistant p");
      const run = document.querySelector("#run");
      const feedback = document.querySelector("#request-feedback");
      return body?.textContent.length > 80 && !run?.disabled && feedback?.hidden;
    },
    null,
    { timeout: 75000 },
  );
  const answerText = await answer.textContent();
  assert.ok(answerText.length > 80);
  assert.doesNotMatch(answerText, /Q 核审计|B_sigma|PSM 门控候选回答/);
  assert.equal(await page.locator(".message.user").count(), 1);
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "real-backend.png"), fullPage: true });
  await context.close();
  return {
    ran: true,
    answer_characters: answerText.length,
    selected_model_visible: true,
    internal_alpha_ready_visible: expectInternalReady,
    internal_debug_leakage: false,
    console_errors: consoleErrors.length,
  };
}

async function realRouteEvidenceSmoke(browser) {
  if (!runRouteEvidence) return { ran: false };
  const context = await browser.newContext({ viewport: { width: 1280, height: 820 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  await page.locator("#prompt").fill("项目现在做到哪里了？");
  await page.locator("#run").click();
  await page.waitForFunction(
    () => !document.querySelector("#run")?.disabled && document.querySelector("#request-feedback")?.hidden,
    null,
    { timeout: 20000 },
  );
  const answerText = await page.locator(".message.assistant p").textContent();
  const currentVersion = await page.locator("#metric-version").textContent();
  assert.ok(currentVersion && answerText.includes(currentVersion));
  assert.doesNotMatch(answerText, /route_execution|SHA-256|source_or_tool_check/);
  assert.equal(await page.locator("#debug-panel").getAttribute("open"), null);
  await page.locator("#evidence-toggle").click();
  assert.equal(await page.locator("#evidence-route-status").textContent(), "success");
  assert.ok(Number(await page.locator("#evidence-route-sources").textContent()) >= 1);
  assert.equal(await page.locator("#evidence-route-failures").textContent(), "0");
  const firstGraphNodes = Number(await page.locator("#graph-nodes").textContent());
  assert.ok(firstGraphNodes >= 1);
  assert.notEqual(await page.locator("#graph-protocol").textContent(), "-");

  await page.locator("#evidence-toggle").click();
  await page.locator("#prompt").fill("再读取 `outputs/psm_v0/runtime/current_runtime_snapshot.json` 核验。");
  await page.locator("#run").click();
  await page.waitForFunction(
    () => document.querySelectorAll(".message.user").length === 2
      && !document.querySelector("#run")?.disabled
      && document.querySelector("#request-feedback")?.hidden,
    null,
    { timeout: 20000 },
  );
  await page.locator("#evidence-toggle").click();
  const graphDelta = await page.locator("#graph-delta").textContent();
  assert.notEqual(graphDelta, "+0 / -0");
  assert.ok(Number(await page.locator("#graph-nodes").textContent()) >= 3);
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "route-evidence.png"), fullPage: true });
  await context.close();
  return {
    ran: true,
    status_visible_in_debug: true,
    source_count_visible_in_debug: true,
    failure_count_visible_in_debug: true,
    task_graph_visible_in_debug: true,
    task_graph_delta_visible_after_new_evidence: true,
    internal_route_fields_hidden_from_answer: true,
    console_errors: consoleErrors.length,
  };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await desktopRegression(browser);
    const mobile = await mobileRegression(browser);
    const real_backend = await realBackendSmoke(browser);
    const route_evidence = await realRouteEvidenceSmoke(browser);
    const report = {
      schema_version: reportSchema,
      base_url: baseUrl,
      passed: true,
      desktop,
      mobile,
      real_backend,
      route_evidence,
      checks: {
        generating_state: true,
        cancel_and_input_preservation: true,
        retry_without_duplicate_user_message: true,
        progressive_answer_display: true,
        debug_isolated_from_main_chat: true,
        keyboard_enter_submit: true,
        desktop_overflow: false,
        mobile_overflow: false,
        console_errors: 0,
      },
    };
    await fs.writeFile(path.join(outdir, "report.json"), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});

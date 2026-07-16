const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_293_backpressure_browser_regression");
const prompt = "请为一个新的本地资料项目拟定名称、架构和执行阶段。";

function chatPayload(requestId, index) {
  return {
    request_id: requestId,
    scenario: "review",
    session_id: `v293_browser_${index}_${Date.now()}_${Math.random().toString(36).slice(2)}`,
    continuity_event: "active",
    messages: [{ id: 1, role: "user", content: `请详细设计本地资料项目 ${index}，包括名称、架构、阶段和风险。` }],
  };
}

async function inspectDesktop(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  const status = await (await context.request.get(`${baseUrl}/api/status`)).json();
  assert.ok(["PSM V0.292", "PSM V0.293"].includes(status.version));
  assert.equal(status.chat_concurrency_limit, 4);
  assert.equal(status.chat_queue_enabled, false);

  const requestIds = Array.from({ length: 4 }, (_, index) => `chat_v293_browser_${index}_${crypto.randomUUID().replaceAll("-", "")}`);
  const activeRequests = requestIds.map((requestId, index) => context.request.post(`${baseUrl}/api/chat`, {
    data: chatPayload(requestId, index),
  }));
  await page.waitForTimeout(1000);

  await page.locator("#prompt").fill(prompt);
  const capacityStarted = Date.now();
  await page.locator("#run").click();
  await page.waitForFunction(() => !state.activeRequest && state.lastFailed?.reason === "capacity", null, { timeout: 3000 });
  const capacityUiMs = Date.now() - capacityStarted;
  const saturated = await page.evaluate(() => ({
    promptValue: document.querySelector("#prompt")?.value || "",
    feedback: document.querySelector("#request-status")?.textContent || "",
    retryVisible: !document.querySelector("#retry")?.hidden,
    runDisabled: document.querySelector("#run")?.disabled,
    userMessages: state.messages.filter((item) => item.role === "user").length,
    assistantMessages: state.messages.filter((item) => item.role === "assistant").length,
  }));
  assert.equal(saturated.promptValue, prompt);
  assert.ok(saturated.feedback.includes("同時處理的回答已滿"));
  assert.equal(saturated.retryVisible, true);
  assert.equal(saturated.runDisabled, false);
  assert.equal(saturated.userMessages, 1);
  assert.equal(saturated.assistantMessages, 0);
  assert.ok(capacityUiMs < 1000, `capacity UI took ${capacityUiMs}ms`);

  const cancelResponses = await Promise.all(requestIds.map((requestId) => context.request.post(`${baseUrl}/api/chat-cancel`, {
    data: { request_id: requestId },
  })));
  assert.ok(cancelResponses.every((response) => response.ok()));
  const activeResponses = await Promise.all(activeRequests);
  assert.ok(activeResponses.every((response) => response.status() === 499));

  await page.locator("#retry").click();
  await page.waitForFunction(
    () => !state.activeRequest && state.messages.at(-1)?.role === "assistant",
    null,
    { timeout: 120000 },
  );
  const recovered = await page.evaluate(() => ({
    answer: state.messages.at(-1)?.content || "",
    userMessages: state.messages.filter((item) => item.role === "user").length,
    assistantMessages: state.messages.filter((item) => item.role === "assistant").length,
    feedbackHidden: document.querySelector("#request-feedback")?.hidden,
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  assert.ok(recovered.answer.trim());
  assert.equal(recovered.userMessages, 1);
  assert.equal(recovered.assistantMessages, 1);
  assert.equal(recovered.feedbackHidden, true);
  assert.ok(recovered.scrollWidth <= recovered.innerWidth + 1);
  const expectedCapacityConsoleEvents = consoleErrors.filter((item) => item.includes("status of 503"));
  const unexpectedConsoleErrors = consoleErrors.filter((item) => !item.includes("status of 503"));
  assert.equal(expectedCapacityConsoleEvents.length, 1);
  assert.deepEqual(unexpectedConsoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "desktop-capacity-recovery.png"), fullPage: true });
  await context.close();
  return {
    capacityUiMs,
    saturated,
    recovered: { ...recovered, answer: "nonempty" },
    expectedCapacityConsoleEvents: expectedCapacityConsoleEvents.length,
    unexpectedConsoleErrors: unexpectedConsoleErrors.length,
  };
}

async function inspectMobile(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    runVisible: Boolean(document.querySelector("#run")?.offsetParent),
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1);
  assert.equal(layout.runVisible, true);
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile-idle.png"), fullPage: true });
  await context.close();
  return { ...layout, horizontalOverflow: false, consoleErrors: 0 };
}

(async () => {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectDesktop(browser);
    const mobile = await inspectMobile(browser);
    const checks = {
      capacity_message_visible_under_one_second: desktop.capacityUiMs < 1000,
      rejected_prompt_preserved: desktop.saturated.promptValue === prompt,
      rejected_candidate_not_displayed: desktop.saturated.assistantMessages === 0,
      retry_after_capacity_completes_single_turn: desktop.recovered.userMessages === 1 && desktop.recovered.assistantMessages === 1,
      mobile_no_overflow: !mobile.horizontalOverflow,
      expected_capacity_console_event_classified: desktop.expectedCapacityConsoleEvents === 1,
      unexpected_console_errors_zero: desktop.unexpectedConsoleErrors === 0 && mobile.consoleErrors === 0,
    };
    const report = {
      schema_version: "psm_v0_293_backpressure_browser_regression_v1",
      version: "PSM_V0.293-candidate",
      base_url: baseUrl,
      passed: Object.values(checks).every(Boolean),
      synthetic_only: true,
      queue_enabled: false,
      network_token_streaming_claimed: false,
      browser_chat_persisted: false,
      human_feedback_collected: false,
      external_release_authority: false,
      desktop,
      mobile,
      checks,
    };
    await fs.writeFile(path.join(outdir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
    if (!report.passed) process.exitCode = 1;
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});

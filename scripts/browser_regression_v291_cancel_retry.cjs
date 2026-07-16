const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_291_cancel_retry_browser_regression");
const prompt = "请给一个新的本地知识项目起代号，并说明理由。";

async function inspectDesktop(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  const statusResponse = await context.request.get(`${baseUrl}/api/status`);
  const status = await statusResponse.json();
  assert.equal(status.version, "PSM V0.290");
  assert.equal(status.ready_for_external_user_trial, false);

  await page.locator("#prompt").fill(prompt);
  await page.locator("#run").click();
  await page.locator("#cancel").waitFor({ state: "visible" });
  assert.equal(await page.locator("#run").isDisabled(), true);
  await page.waitForTimeout(4000);
  const phaseBeforeCancel = await page.locator("#request-status").textContent();
  assert.equal(phaseBeforeCancel, "正在生成候選回答");
  const cancelStarted = Date.now();
  await page.locator("#cancel").click();
  await page.waitForFunction(() => !state.activeRequest, null, { timeout: 3000 });
  const cancellationMs = Date.now() - cancelStarted;
  const cancelled = await page.evaluate(() => ({
    promptValue: document.querySelector("#prompt")?.value || "",
    feedback: document.querySelector("#request-status")?.textContent || "",
    retryVisible: !document.querySelector("#retry")?.hidden,
    cancelHidden: document.querySelector("#cancel")?.hidden,
    runDisabled: document.querySelector("#run")?.disabled,
    lastFailedReason: state.lastFailed?.reason || "",
    userMessages: state.messages.filter((item) => item.role === "user").length,
    assistantMessages: state.messages.filter((item) => item.role === "assistant").length,
  }));
  assert.equal(cancelled.promptValue, prompt);
  assert.ok(cancelled.feedback.includes("已取消"));
  assert.equal(cancelled.retryVisible, true);
  assert.equal(cancelled.cancelHidden, true);
  assert.equal(cancelled.runDisabled, false);
  assert.equal(cancelled.lastFailedReason, "cancelled");
  assert.equal(cancelled.userMessages, 1);
  assert.equal(cancelled.assistantMessages, 0);
  assert.ok(cancellationMs < 1000, `cancel took ${cancellationMs}ms`);

  await page.locator("#retry").click();
  await page.waitForFunction(
    () => !state.activeRequest && state.messages.at(-1)?.role === "assistant",
    null,
    { timeout: 120000 },
  );
  const retried = await page.evaluate(() => ({
    answer: state.messages.at(-1)?.content || "",
    promptValue: document.querySelector("#prompt")?.value || "",
    retryHidden: document.querySelector("#retry")?.hidden,
    cancelHidden: document.querySelector("#cancel")?.hidden,
    feedbackHidden: document.querySelector("#request-feedback")?.hidden,
    lastFailed: state.lastFailed,
    userMessages: state.messages.filter((item) => item.role === "user").length,
    assistantMessages: state.messages.filter((item) => item.role === "assistant").length,
  }));
  assert.ok(retried.answer.trim());
  assert.equal(retried.promptValue, "");
  assert.equal(retried.retryHidden, true);
  assert.equal(retried.cancelHidden, true);
  assert.equal(retried.feedbackHidden, true);
  assert.equal(retried.lastFailed, null);
  assert.equal(retried.userMessages, 1);
  assert.equal(retried.assistantMessages, 1);
  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "desktop-cancel-retry.png"), fullPage: true });
  await context.close();
  return {
    phaseBeforeCancel,
    cancellationMs,
    cancelled,
    retried: { ...retried, answer: "nonempty" },
    horizontalOverflow: false,
    consoleErrors: 0,
  };
}

async function inspectMobile(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  const controls = await page.evaluate(() => ({
    runVisible: Boolean(document.querySelector("#run")?.offsetParent),
    cancelInitiallyHidden: document.querySelector("#cancel")?.hidden,
    retryInitiallyHidden: document.querySelector("#retry")?.hidden,
    feedbackInitiallyHidden: document.querySelector("#request-feedback")?.hidden,
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  assert.equal(controls.runVisible, true);
  assert.equal(controls.cancelInitiallyHidden, true);
  assert.equal(controls.retryInitiallyHidden, true);
  assert.equal(controls.feedbackInitiallyHidden, true);
  assert.ok(controls.scrollWidth <= controls.innerWidth + 1, JSON.stringify(controls));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile-cancel-controls.png"), fullPage: true });
  await context.close();
  return { ...controls, horizontalOverflow: false, consoleErrors: 0 };
}

(async () => {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectDesktop(browser);
    const mobile = await inspectMobile(browser);
    const checks = {
      staged_progress_visible: desktop.phaseBeforeCancel === "正在生成候選回答",
      client_cancel_completes_within_one_second: desktop.cancellationMs < 1000,
      cancelled_prompt_and_retry_preserved: desktop.cancelled.promptValue === prompt && desktop.cancelled.retryVisible,
      cancelled_turn_not_duplicated: desktop.cancelled.userMessages === 1 && desktop.cancelled.assistantMessages === 0,
      retry_completes_single_turn: desktop.retried.userMessages === 1 && desktop.retried.assistantMessages === 1,
      controls_return_to_idle: desktop.retried.cancelHidden && desktop.retried.feedbackHidden,
      mobile_controls_visible_without_overflow: mobile.runVisible && !mobile.horizontalOverflow,
      console_errors_zero: desktop.consoleErrors === 0 && mobile.consoleErrors === 0,
    };
    const report = {
      schema_version: "psm_v0_291_cancel_retry_browser_regression_v1",
      version: "PSM_V0.291-candidate",
      base_url: baseUrl,
      passed: Object.values(checks).every(Boolean),
      synthetic_only: true,
      cancellation_scope: "client_transport_wait_only",
      server_generation_cancellation_claimed: false,
      network_streaming_claimed: false,
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

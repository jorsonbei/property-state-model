const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_292_server_cancel_browser_regression");
const prompt = "请给一个全新的本地知识项目起代号，并说明理由。";

async function waitForServerCancel(page) {
  await page.waitForFunction(
    () => !state.activeRequest && state.lastServerCancel?.acknowledged === true,
    null,
    { timeout: 3000 },
  );
  return page.evaluate(() => ({
    serverCancel: state.lastServerCancel,
    promptValue: document.querySelector("#prompt")?.value || "",
    feedback: document.querySelector("#request-status")?.textContent || "",
    retryVisible: !document.querySelector("#retry")?.hidden,
    cancelHidden: document.querySelector("#cancel")?.hidden,
    runDisabled: document.querySelector("#run")?.disabled,
    userMessages: state.messages.filter((item) => item.role === "user").length,
    assistantMessages: state.messages.filter((item) => item.role === "assistant").length,
  }));
}

async function inspectDesktop(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  const statusResponse = await context.request.get(`${baseUrl}/api/status`);
  const status = await statusResponse.json();
  assert.ok(["PSM V0.291", "PSM V0.292"].includes(status.version));
  assert.equal(status.ready_for_external_user_trial, false);

  await page.locator("#prompt").fill(prompt);
  await page.locator("#run").click();
  await page.locator("#cancel").waitFor({ state: "visible" });
  await page.waitForTimeout(2000);
  const cancelStarted = Date.now();
  await page.locator("#cancel").click();
  const cancelled = await waitForServerCancel(page);
  const cancellationMs = Date.now() - cancelStarted;
  assert.equal(cancelled.serverCancel.acknowledged, true);
  assert.equal(cancelled.serverCancel.generationWasActive, true);
  assert.equal(cancelled.promptValue, prompt);
  assert.ok(cancelled.feedback.includes("已取消"));
  assert.equal(cancelled.retryVisible, true);
  assert.equal(cancelled.cancelHidden, true);
  assert.equal(cancelled.runDisabled, false);
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
    userMessages: state.messages.filter((item) => item.role === "user").length,
    assistantMessages: state.messages.filter((item) => item.role === "assistant").length,
  }));
  assert.ok(retried.answer.trim());
  assert.equal(retried.promptValue, "");
  assert.equal(retried.retryHidden, true);
  assert.equal(retried.cancelHidden, true);
  assert.equal(retried.feedbackHidden, true);
  assert.equal(retried.userMessages, 1);
  assert.equal(retried.assistantMessages, 1);
  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "desktop-server-cancel-retry.png"), fullPage: true });
  await context.close();
  return {
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
  await page.locator("#prompt").fill("请设计一个新的本地笔记分类法，并给出理由。");
  await page.locator("#run").click();
  await page.locator("#cancel").waitFor({ state: "visible" });
  await page.waitForTimeout(1500);
  await page.locator("#cancel").click();
  const cancelled = await waitForServerCancel(page);
  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    runVisible: Boolean(document.querySelector("#run")?.offsetParent),
  }));
  assert.equal(cancelled.serverCancel.generationWasActive, true);
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.equal(layout.runVisible, true);
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile-server-cancel.png"), fullPage: true });
  await context.close();
  return {
    cancelled,
    horizontalOverflow: false,
    runVisible: true,
    consoleErrors: 0,
  };
}

(async () => {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectDesktop(browser);
    const mobile = await inspectMobile(browser);
    const checks = {
      desktop_server_cancel_acknowledged: desktop.cancelled.serverCancel.acknowledged && desktop.cancelled.serverCancel.generationWasActive,
      desktop_cancel_completes_within_one_second: desktop.cancellationMs < 1000,
      cancelled_candidate_not_displayed: desktop.cancelled.assistantMessages === 0,
      retry_completes_single_turn: desktop.retried.userMessages === 1 && desktop.retried.assistantMessages === 1,
      mobile_server_cancel_acknowledged: mobile.cancelled.serverCancel.acknowledged && mobile.cancelled.serverCancel.generationWasActive,
      mobile_no_overflow: !mobile.horizontalOverflow,
      console_errors_zero: desktop.consoleErrors === 0 && mobile.consoleErrors === 0,
    };
    const report = {
      schema_version: "psm_v0_292_server_cancel_browser_regression_v1",
      version: "PSM_V0.292-candidate",
      base_url: baseUrl,
      passed: Object.values(checks).every(Boolean),
      synthetic_only: true,
      cancellation_scope: "server_ollama_connection_cancel",
      raw_model_chunks_user_visible: false,
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

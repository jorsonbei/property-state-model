const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_269_stability_browser_regression");

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function installSlowChatRoute(page, delayMs = 800) {
  await page.route("**/api/chat", async (route) => {
    await delay(delayMs);
    await route.abort("aborted").catch(() => {});
  });
}

async function waitForRecovery(page, marker, original) {
  await page.waitForFunction(
    ({ expected }) => !document.querySelector("#request-feedback")?.hidden && document.querySelector("#request-status")?.textContent.includes(expected),
    { expected: marker },
  );
  assert.equal(await page.locator("#prompt").inputValue(), original);
  assert.equal(await page.locator("#retry").isVisible(), true);
}

async function retryAndAssert(page, marker) {
  await page.unroute("**/api/chat");
  await page.locator("#retry").click();
  await page.waitForFunction(() => !document.querySelector("#run")?.disabled);
  const answer = await page.locator(".message.assistant").last().textContent();
  assert.match(answer, marker);
  return answer;
}

async function runCancel(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await installSlowChatRoute(page);
  const original = "你好，你是谁？";
  await page.locator("#prompt").fill(original);
  await page.locator("#run").click();
  await page.locator("#cancel").click();
  await waitForRecovery(page, "已取消", original);
  await retryAndAssert(page, /物性AI/);
  const status = await context.request.get(`${baseUrl}/api/status`).then((response) => response.json());
  assert.equal(status.ready_for_external_user_trial, false);
  await page.screenshot({ path: path.join(outdir, "desktop-cancel-retry.png"), fullPage: true });
  await context.close();
  return { cancelledWithoutDelivery: true, inputPreserved: true, retrySucceeded: true, externalReleaseClosed: true, consoleErrors: consoleErrors.length };
}

async function runTimeout(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  await context.addInitScript(() => {
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (callback, milliseconds, ...args) => nativeSetTimeout(callback, milliseconds === 70000 ? 80 : milliseconds, ...args);
  });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await installSlowChatRoute(page);
  const original = "你好，你是谁？";
  await page.locator("#prompt").fill(original);
  await page.locator("#run").click();
  await waitForRecovery(page, "超過 70 秒", original);
  await retryAndAssert(page, /物性AI/);
  const layout = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  await page.screenshot({ path: path.join(outdir, "mobile-timeout-retry.png"), fullPage: true });
  await context.close();
  return { timeoutStoppedDelivery: true, inputPreserved: true, retrySucceeded: true, horizontalOverflow: false, consoleErrors: consoleErrors.length };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const cancellation = await runCancel(browser);
    const timeout = await runTimeout(browser);
    const checks = {
      cancellation_stops_delivery: cancellation.cancelledWithoutDelivery,
      cancellation_input_preserved: cancellation.inputPreserved,
      cancellation_retry_succeeds: cancellation.retrySucceeded,
      timeout_stops_delivery: timeout.timeoutStoppedDelivery,
      timeout_input_preserved: timeout.inputPreserved,
      timeout_retry_succeeds: timeout.retrySucceeded,
      external_release_closed: cancellation.externalReleaseClosed,
      mobile_no_overflow: !timeout.horizontalOverflow,
      console_errors_zero: cancellation.consoleErrors + timeout.consoleErrors === 0,
    };
    const report = {
      schema_version: "psm_v0_269_stability_browser_regression_v1",
      base_url: baseUrl,
      passed: Object.values(checks).every((value) => value === true),
      synthetic_questions_only: true,
      human_participant_actions_executed: false,
      human_feedback_collected: false,
      cancellation,
      timeout,
      checks,
    };
    await fs.writeFile(path.join(outdir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify(report, null, 2));
    assert.equal(report.passed, true);
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });

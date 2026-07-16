const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_283_restart_recovery_browser_regression");

async function ask(page, text) {
  await page.locator("#prompt").fill(text);
  await page.locator("#run").click();
  await page.waitForFunction(
    () => !state.activeRequest && state.messages.at(-1)?.role === "assistant",
    null,
    { timeout: 90000 },
  );
  return page.evaluate(() => ({
    answer: state.messages.at(-1)?.content || "",
    continuity: document.querySelector("#metric-continuity")?.dataset.state || "",
    continuityText: document.querySelector("#metric-continuity")?.textContent || "",
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
  assert.equal(statusResponse.status(), 200);
  const status = await statusResponse.json();
  assert.equal(status.version, "PSM V0.282");
  assert.equal(status.continuity_protocol, "psm_v0_283_restart_recovery_v1");
  assert.equal(status.persistent_conversation_memory_enabled, false);
  assert.equal(status.ready_for_external_user_trial, false);

  const browserState = await page.evaluate(() => ({
    sessionId: state.sessionId,
    serverInstanceId: state.serverInstanceId,
  }));
  const seed = await context.request.post(`${baseUrl}/api/chat`, {
    data: {
      scenario: "review",
      session_id: browserState.sessionId,
      continuity_event: "active",
      server_instance_id: browserState.serverInstanceId,
      messages: [{ id: 1, role: "user", content: "项目代号定为白砾。你好，你是谁？" }],
    },
    timeout: 90000,
  });
  assert.equal(seed.status(), 200);
  await page.evaluate(() => { state.nextMessageId = 2; });
  const active = await ask(page, "之前的项目代号是什么？只回答代号。");
  assert.equal(active.answer, "白砾");
  assert.equal(active.continuity, "active");

  await page.locator("#reset").click();
  const reset = await ask(page, "之前的项目代号是什么？");
  assert.equal(reset.continuity, "reset");
  assert.equal(reset.continuityText, "會話已清空");
  assert.ok(reset.answer.includes("不能确认"));
  assert.ok(!reset.answer.includes("白砾"));

  await page.reload({ waitUntil: "networkidle" });
  const reload = await ask(page, "之前的项目代号是什么？");
  assert.equal(reload.continuity, "reload");
  assert.equal(reload.continuityText, "頁面已刷新");
  assert.ok(reload.answer.includes("不能确认"));
  assert.ok(!reload.answer.includes("白砾"));

  await page.evaluate(() => {
    state.serverInstanceId = "stale-server-instance";
    state.continuityEvent = "active";
  });
  const restarted = await ask(page, "之前的项目代号是什么？");
  assert.equal(restarted.continuity, "restarted");
  assert.equal(restarted.continuityText, "服務已重啟");
  assert.ok(restarted.answer.includes("不能确认"));
  assert.ok(!restarted.answer.includes("白砾"));

  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "desktop-restart-recovery.png"), fullPage: true });
  await context.close();
  return {
    active,
    reset,
    reload,
    restarted,
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
  const metric = await page.locator("#metric-continuity").textContent();
  assert.ok(metric);
  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile-restart-recovery.png"), fullPage: true });
  await context.close();
  return { continuityMetricVisible: true, horizontalOverflow: false, consoleErrors: 0 };
}

(async () => {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectDesktop(browser);
    const mobile = await inspectMobile(browser);
    const checks = {
      active_state_recovers_fact: desktop.active.answer === "白砾" && desktop.active.continuity === "active",
      reset_state_visible_and_no_fabrication: desktop.reset.continuity === "reset" && !desktop.reset.answer.includes("白砾"),
      reload_state_visible_and_no_fabrication: desktop.reload.continuity === "reload" && !desktop.reload.answer.includes("白砾"),
      restarted_state_visible_and_no_fabrication: desktop.restarted.continuity === "restarted" && !desktop.restarted.answer.includes("白砾"),
      mobile_continuity_metric_visible: mobile.continuityMetricVisible,
      desktop_no_overflow: !desktop.horizontalOverflow,
      mobile_no_overflow: !mobile.horizontalOverflow,
      console_errors_zero: desktop.consoleErrors === 0 && mobile.consoleErrors === 0,
    };
    const report = {
      schema_version: "psm_v0_283_restart_recovery_browser_regression_v1",
      version: "PSM_V0.283-candidate",
      base_url: baseUrl,
      passed: Object.values(checks).every(Boolean),
      synthetic_only: true,
      browser_chat_persisted: false,
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

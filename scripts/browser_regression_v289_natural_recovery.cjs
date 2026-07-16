const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_289_natural_recovery_browser_regression");
const lossMarker = "无法读取先前会话内容";

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
  assert.equal(status.version, "PSM V0.288");
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

  await page.locator("#reset").click();
  const reset = await ask(page, "那个项目代号来着？");
  assert.equal(reset.continuity, "reset");
  assert.equal(reset.continuityText, "會話已清空");
  assert.ok(reset.answer.includes(lossMarker));
  assert.ok(!reset.answer.includes("白砾"));

  const newTask = await ask(page, "请给这个新项目起个代号。");
  assert.equal(newTask.continuity, "active");
  assert.ok(newTask.answer.trim());
  assert.ok(!newTask.answer.includes(lossMarker));

  await page.reload({ waitUntil: "networkidle" });
  const reload = await ask(page, "我们定的文件名呢？");
  assert.equal(reload.continuity, "reload");
  assert.equal(reload.continuityText, "頁面已刷新");
  assert.ok(reload.answer.includes(lossMarker));

  await page.evaluate(() => {
    state.serverInstanceId = "stale-v289-instance";
    state.continuityEvent = "active";
  });
  const restarted = await ask(page, "What was the project codename?");
  assert.equal(restarted.continuity, "restarted");
  assert.equal(restarted.continuityText, "服務已重啟");
  assert.ok(restarted.answer.includes(lossMarker));
  assert.ok(!restarted.answer.includes("白砾"));

  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "desktop-natural-recovery.png"), fullPage: true });
  await context.close();
  return { reset, newTask, reload, restarted, horizontalOverflow: false, consoleErrors: 0 };
}

async function inspectMobile(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator("#reset").click();
  const recovery = await ask(page, "剩下哪件没做？");
  assert.equal(recovery.continuity, "reset");
  assert.equal(recovery.continuityText, "會話已清空");
  assert.ok(recovery.answer.includes(lossMarker));
  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile-natural-recovery.png"), fullPage: true });
  await context.close();
  return { recovery, horizontalOverflow: false, consoleErrors: 0 };
}

(async () => {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectDesktop(browser);
    const mobile = await inspectMobile(browser);
    const checks = {
      reset_natural_reference_recovers_without_fabrication: desktop.reset.continuity === "reset" && !desktop.reset.answer.includes("白砾"),
      explicit_new_task_returns_to_active_chat: desktop.newTask.continuity === "active" && !desktop.newTask.answer.includes(lossMarker),
      reload_natural_reference_recovers: desktop.reload.continuity === "reload" && desktop.reload.answer.includes(lossMarker),
      restarted_english_reference_recovers: desktop.restarted.continuity === "restarted" && !desktop.restarted.answer.includes("白砾"),
      mobile_recovery_interaction_passed: mobile.recovery.continuity === "reset" && mobile.recovery.answer.includes(lossMarker),
      desktop_no_overflow: !desktop.horizontalOverflow,
      mobile_no_overflow: !mobile.horizontalOverflow,
      console_errors_zero: desktop.consoleErrors === 0 && mobile.consoleErrors === 0,
    };
    const report = {
      schema_version: "psm_v0_289_natural_recovery_browser_regression_v1",
      version: "PSM_V0.289-candidate",
      base_url: baseUrl,
      passed: Object.values(checks).every(Boolean),
      synthetic_only: true,
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

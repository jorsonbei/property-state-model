const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_282_rolling_state_browser_regression");

function rollingWindow() {
  const messages = [];
  for (let id = 2; id <= 120; id += 1) {
    messages.push({
      id,
      role: id % 2 === 0 ? "assistant" : "user",
      content: id % 2 === 0 ? "已记录。" : `浏览器窗口记录 ${id}：无新增决定。`,
    });
  }
  return messages;
}

async function inspectDesktop(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  const status = await context.request.get(`${baseUrl}/api/status`);
  assert.equal(status.status(), 200);
  const statusBody = await status.json();
  assert.equal(statusBody.version, "PSM V0.281");
  assert.equal(statusBody.ready_for_external_user_trial, false);

  const sessionBefore = await page.evaluate(() => state.sessionId);
  const seed = await context.request.post(`${baseUrl}/api/chat`, {
    data: {
      scenario: "review",
      session_id: sessionBefore,
      messages: [{ id: 1, role: "user", content: "项目代号定为白砾。你好，你是谁？" }],
    },
    timeout: 90000,
  });
  assert.equal(seed.status(), 200);

  await page.evaluate((messages) => {
    state.messages = messages;
    state.nextMessageId = 121;
    renderMessages();
  }, rollingWindow());
  await page.locator("#prompt").fill("最早确定的项目代号是什么？只回答代号。");
  await page.locator("#run").click();
  await page.waitForFunction(() => !state.activeRequest && state.messages.at(-1)?.role === "assistant", null, { timeout: 90000 });
  const answer = await page.evaluate(() => state.messages.at(-1)?.content || "");
  assert.equal(answer, "白砾");
  const visibleAnswer = await page.locator("#messages article.assistant").last().locator("p").textContent();
  assert.equal(visibleAnswer, "白砾");
  const boundedMessages = await page.evaluate(() => state.messages.length);
  assert.equal(boundedMessages, 120);

  await page.locator("#reset").click();
  const resetState = await page.evaluate(() => ({ sessionId: state.sessionId, messages: state.messages.length }));
  assert.notEqual(resetState.sessionId, sessionBefore);
  assert.equal(resetState.messages, 0);
  const sessionAfterReset = resetState.sessionId;
  await page.reload({ waitUntil: "networkidle" });
  const sessionAfterReload = await page.evaluate(() => state.sessionId);
  assert.notEqual(sessionAfterReload, sessionAfterReset);

  const layout = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "desktop-rolling-state.png"), fullPage: true });
  await context.close();
  return {
    answer,
    visibleAnswer,
    boundedMessages,
    resetRotatedSession: sessionAfterReset !== sessionBefore,
    reloadRotatedSession: sessionAfterReload !== sessionAfterReset,
    externalReleaseClosed: true,
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
  const sessionId = await page.evaluate(() => state.sessionId);
  assert.match(sessionId, /^[A-Za-z0-9_-]{16,64}$/);
  const layout = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile-rolling-state.png"), fullPage: true });
  await context.close();
  return { validEphemeralSession: true, horizontalOverflow: false, consoleErrors: 0 };
}

(async () => {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectDesktop(browser);
    const mobile = await inspectMobile(browser);
    const checks = {
      cross_window_answer_visible: desktop.answer === "白砾" && desktop.visibleAnswer === "白砾",
      browser_window_bounded_to_120: desktop.boundedMessages === 120,
      reset_rotates_session: desktop.resetRotatedSession,
      reload_rotates_session: desktop.reloadRotatedSession,
      external_release_closed: desktop.externalReleaseClosed,
      desktop_no_overflow: !desktop.horizontalOverflow,
      mobile_no_overflow: !mobile.horizontalOverflow,
      mobile_session_valid: mobile.validEphemeralSession,
      console_errors_zero: desktop.consoleErrors === 0 && mobile.consoleErrors === 0,
    };
    const report = {
      schema_version: "psm_v0_282_rolling_state_browser_regression_v1",
      version: "PSM_V0.282-candidate",
      base_url: baseUrl,
      passed: Object.values(checks).every(Boolean),
      synthetic_questions_only: true,
      human_participant_actions_executed: false,
      human_feedback_collected: false,
      browser_memory_persisted_after_reload: false,
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

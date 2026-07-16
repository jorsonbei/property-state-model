const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_270_multiturn_browser_regression");

async function ask(page, prompt) {
  const before = await page.locator(".message").count();
  await page.locator("#prompt").fill(prompt);
  await page.locator("#run").click();
  await page.waitForFunction(({ count }) => document.querySelectorAll(".message").length > count, { count: before });
  await page.waitForFunction(() => !document.querySelector("#run")?.disabled);
  return page.locator(".message.assistant").last().textContent();
}

async function postChat(context, messages) {
  const response = await context.request.post(`${baseUrl}/api/chat`, { data: { messages, scenario: "review" } });
  assert.equal(response.status(), 200);
  return response.json();
}

async function inspectDesktop(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  const first = await ask(page, "你好，你是谁？");
  const reference = await ask(page, "你上一轮的核心回答是什么？");
  assert.match(first, /物性AI/);
  assert.match(reference, /物性AI/);

  const switched = await postChat(context, [
    { role: "user", content: "我之前问过胸痛。" },
    { role: "assistant", content: "医疗问题需要急症边界。" },
    { role: "user", content: "换个话题：苹果和香蕉只比较口感。" },
  ]);
  const switchedAnswer = switched.chat.assistant_message;
  assert.equal(switched.packet.domain, "general");
  assert.match(switchedAnswer, /苹果/);
  assert.match(switchedAnswer, /香蕉/);
  assert.doesNotMatch(switchedAnswer, /医生|急救|胸痛/);
  assert.equal(switched.task_state_graph.boundaries.external_release_authority, false);

  const versionCorrection = await postChat(context, [
    { role: "user", content: "项目当前版本是什么？" },
    { role: "assistant", content: "当前项目是 PSM V0.250。" },
    { role: "user", content: "不要沿用上一句，按本地结构化记录更正当前版本。" },
  ]);
  assert.equal(versionCorrection.chat.assistant_message, "当前项目版本是 PSM V0.270。");

  const layout = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "desktop-multiturn.png"), fullPage: true });
  await context.close();
  return { uiReferencePassed: true, explicitTopicSwitchPassed: true, versionCorrectionDirect: true, externalReleaseClosed: true, horizontalOverflow: false, consoleErrors: 0 };
}

async function inspectMobile(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  const format = await postChat(context, [
    { role: "user", content: "给我三步复习计划，每步写时间。" },
    { role: "assistant", content: "1. 20分钟复习公式。\n2. 40分钟做题。\n3. 30分钟整理错题。" },
    { role: "user", content: "把第二步改成50分钟，仍然只保留三步。" },
  ]);
  const answer = format.chat.assistant_message;
  assert.equal(answer.split("\n").filter((line) => line.trim()).length, 3);
  assert.match(answer, /50分钟/);
  assert.doesNotMatch(answer, /40分钟/);

  const translation = await postChat(context, [
    { role: "user", content: "把“包裹已安全送达”翻译成英文，只给译文。" },
    { role: "assistant", content: "The package was delivered safely." },
    { role: "user", content: "把 delivered 改成 arrived，其他约束不变。" },
  ]);
  assert.equal(translation.chat.assistant_message, "The package arrived safely.");
  const factCorrection = await postChat(context, [
    { role: "user", content: "苹果和香蕉哪个通常更软？" },
    { role: "assistant", content: "苹果通常比香蕉更软。" },
    { role: "user", content: "更正：成熟香蕉通常更软。请只确认更正后的结论。" },
  ]);
  assert.equal(factCorrection.chat.assistant_message, "成熟香蕉通常更软。");
  const layout = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile-constraints.png"), fullPage: true });
  await context.close();
  return { threeStepConstraintPassed: true, translationOnlyConstraintPassed: true, factCorrectionDirect: true, horizontalOverflow: false, consoleErrors: 0 };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectDesktop(browser);
    const mobile = await inspectMobile(browser);
    const checks = {
      ui_reference_passed: desktop.uiReferencePassed,
      explicit_topic_switch_passed: desktop.explicitTopicSwitchPassed,
      version_correction_direct: desktop.versionCorrectionDirect,
      three_step_constraint_passed: mobile.threeStepConstraintPassed,
      translation_only_constraint_passed: mobile.translationOnlyConstraintPassed,
      fact_correction_direct: mobile.factCorrectionDirect,
      external_release_closed: desktop.externalReleaseClosed,
      desktop_no_overflow: !desktop.horizontalOverflow,
      mobile_no_overflow: !mobile.horizontalOverflow,
      console_errors_zero: desktop.consoleErrors + mobile.consoleErrors === 0,
    };
    const report = {
      schema_version: "psm_v0_270_multiturn_browser_regression_v1",
      base_url: baseUrl,
      passed: Object.values(checks).every((value) => value === true),
      synthetic_questions_only: true,
      human_participant_actions_executed: false,
      human_feedback_collected: false,
      desktop,
      mobile,
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

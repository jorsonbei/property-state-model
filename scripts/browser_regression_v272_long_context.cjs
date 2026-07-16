const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_272_long_context_browser_regression");

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

  const fact = await postChat(context, [
    { role: "user", content: "这个项目的代号定为松塔。" },
    { role: "assistant", content: "已记录项目代号为松塔。" },
    { role: "user", content: "界面先采用深色模式。" },
    { role: "assistant", content: "可以，先采用深色模式。" },
    { role: "user", content: "日志保留七天。" },
    { role: "assistant", content: "已记录日志保留七天。" },
    { role: "user", content: "回到最开始的项目设定：代号是什么？只给代号。" },
  ]);
  assert.equal(fact.chat.assistant_message, "松塔");

  const switched = await postChat(context, [
    { role: "user", content: "我刚才胸痛并且出冷汗。" },
    { role: "assistant", content: "这属于急症风险，应立即联系当地急救。" },
    { role: "user", content: "换个话题：现在只比较苹果和香蕉的口感。" },
    { role: "assistant", content: "苹果偏脆，成熟香蕉偏软。" },
    { role: "user", content: "先不讨论营养。" },
    { role: "assistant", content: "好的，只比较口感。" },
    { role: "user", content: "它们通常哪个更甜？" },
  ]);
  assert.equal(switched.packet.domain, "general");
  assert.match(switched.chat.assistant_message, /香蕉/);
  assert.doesNotMatch(switched.chat.assistant_message, /胸痛|急救|医生|医疗/);
  assert.equal(switched.task_state_graph.boundaries.external_release_authority, false);

  const layout = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "desktop-long-context.png"), fullPage: true });
  await context.close();
  return { userFactPassed: true, topicSwitchPassed: true, externalReleaseClosed: true, horizontalOverflow: false, consoleErrors: 0 };
}

async function inspectMobile(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });

  const translation = await postChat(context, [
    { role: "user", content: "把“包裹已安全送达”翻译成英文，只给译文。" },
    { role: "assistant", content: "The package was delivered safely." },
    { role: "user", content: "接下来我会改一个词。" },
    { role: "assistant", content: "好的，请说明要修改的词。" },
    { role: "user", content: "其他格式要求都保持不变。" },
    { role: "assistant", content: "明白，保持原格式要求。" },
    { role: "user", content: "把 delivered 改成 arrived，其他约束不变。" },
  ]);
  assert.equal(translation.chat.assistant_message, "The package arrived safely.");

  const steps = await postChat(context, [
    { role: "user", content: "给我三步复习计划，每步写时间，只保留三步。" },
    { role: "assistant", content: "1. 20分钟复习公式。\n2. 40分钟做题。\n3. 30分钟整理错题。" },
    { role: "user", content: "计划主题仍然是物理。" },
    { role: "assistant", content: "明白，主题保持为物理。" },
    { role: "user", content: "第一步和第三步不用改。" },
    { role: "assistant", content: "好的，只修改第二步。" },
    { role: "user", content: "把第二步改成50分钟，仍然只保留三步。" },
  ]);
  assert.equal(steps.chat.assistant_message, "1. 20分钟复习公式。\n2. 50分钟做题。\n3. 30分钟整理错题。");

  const layout = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile-long-context.png"), fullPage: true });
  await context.close();
  return { translationConstraintPassed: true, threeStepConstraintPassed: true, horizontalOverflow: false, consoleErrors: 0 };
}

(async () => {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectDesktop(browser);
    const mobile = await inspectMobile(browser);
    const report = {
      schema_version: "psm_v0_272_long_context_browser_regression_v1",
      base_url: baseUrl,
      passed: true,
      synthetic_questions_only: true,
      human_participant_actions_executed: false,
      human_feedback_collected: false,
      desktop,
      mobile,
      checks: {
        long_user_fact_passed: desktop.userFactPassed,
        persistent_topic_switch_passed: desktop.topicSwitchPassed,
        translation_constraint_passed: mobile.translationConstraintPassed,
        three_step_constraint_passed: mobile.threeStepConstraintPassed,
        external_release_closed: desktop.externalReleaseClosed,
        desktop_no_overflow: !desktop.horizontalOverflow,
        mobile_no_overflow: !mobile.horizontalOverflow,
        console_errors_zero: desktop.consoleErrors === 0 && mobile.consoleErrors === 0,
      },
    };
    await fs.writeFile(path.join(outdir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exit(1);
});

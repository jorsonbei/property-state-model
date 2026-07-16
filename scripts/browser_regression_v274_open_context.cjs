const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_274_open_context_browser_regression");

async function postChat(context, messages) {
  const response = await context.request.post(`${baseUrl}/api/chat`, {
    data: { messages, scenario: "review" },
    timeout: 90000,
  });
  assert.equal(response.status(), 200);
  return response.json();
}

function assertCapsule(result, minimumStatements = 5) {
  const capsule = result.chat.generation.state_capsule;
  assert.equal(capsule.user_authoritative, true);
  assert.ok(capsule.active_user_statements >= minimumStatements, JSON.stringify(capsule));
}

async function inspectDesktop(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });

  const remoteFact = await postChat(context, [
    { role: "user", content: "这个内部方案以后都叫榆叶。" },
    { role: "assistant", content: "记住了，内部称呼是榆叶。" },
    { role: "user", content: "界面暂时用浅色。" },
    { role: "assistant", content: "好的。" },
    { role: "user", content: "日志按天归档。" },
    { role: "assistant", content: "已记录。" },
    { role: "user", content: "首页不放横幅。" },
    { role: "assistant", content: "明白。" },
    { role: "user", content: "按钮文案稍后定。" },
    { role: "assistant", content: "可以。" },
    { role: "user", content: "我最早给这个方案取的称呼是什么？直接告诉我。" },
  ]);
  assert.match(remoteFact.chat.assistant_message, /榆叶/);
  assert.doesNotMatch(remoteFact.chat.assistant_message, /不知道|无法/);
  assertCapsule(remoteFact);

  const topicSwitch = await postChat(context, [
    { role: "user", content: "我出现呼吸困难和胸口压迫感。" },
    { role: "assistant", content: "这可能需要立即联系当地急救。" },
    { role: "user", content: "接下来不谈健康问题了，改聊咖啡和茶的味道。" },
    { role: "assistant", content: "咖啡常有烘焙苦香，茶的香气更轻。" },
    { role: "user", content: "只谈日常风味。" },
    { role: "assistant", content: "好的。" },
    { role: "user", content: "不比较提神效果。" },
    { role: "assistant", content: "明白。" },
    { role: "user", content: "先说入口感觉。" },
    { role: "assistant", content: "可以。" },
    { role: "user", content: "哪一种通常更苦？" },
  ]);
  assert.match(topicSwitch.chat.assistant_message, /咖啡|茶/);
  assert.doesNotMatch(topicSwitch.chat.assistant_message, /胸口|呼吸困难|急救|医生|医疗/);
  assert.equal(topicSwitch.packet.domain, "general");
  assert.equal(topicSwitch.chat.generation.state_capsule.topic_switch_applied, true);
  assert.equal(topicSwitch.task_state_graph.boundaries.external_release_authority, false);

  const layout = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "desktop-open-context.png"), fullPage: true });
  await context.close();
  return { remoteFactPassed: true, topicSwitchPassed: true, externalReleaseClosed: true, horizontalOverflow: false, consoleErrors: 0 };
}

async function inspectMobile(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });

  const translation = await postChat(context, [
    { role: "user", content: "把“报告已经准备好”译成英文，回答里不要加解释。" },
    { role: "assistant", content: "The report is ready." },
    { role: "user", content: "稍后只改一个词。" },
    { role: "assistant", content: "明白。" },
    { role: "user", content: "标点样式保持。" },
    { role: "assistant", content: "好的。" },
    { role: "user", content: "不要添加中文说明。" },
    { role: "assistant", content: "收到。" },
    { role: "user", content: "输出仍旧只有一句。" },
    { role: "assistant", content: "明白。" },
    { role: "user", content: "把 ready 换成 complete，照旧交付。" },
  ]);
  assert.equal(translation.chat.assistant_message, "The report is complete.");
  assertCapsule(translation);

  const unresolved = await postChat(context, [
    { role: "user", content: "出门前要买燕麦、牛奶。" },
    { role: "assistant", content: "购物项是燕麦和牛奶。" },
    { role: "user", content: "牛奶刚买好了。" },
    { role: "assistant", content: "牛奶已完成。" },
    { role: "user", content: "回家顺便取快递。" },
    { role: "assistant", content: "收到。" },
    { role: "user", content: "晚饭不做汤。" },
    { role: "assistant", content: "明白。" },
    { role: "user", content: "购物袋放门边。" },
    { role: "assistant", content: "好的。" },
    { role: "user", content: "购物方面还漏了什么？" },
  ]);
  assert.equal(unresolved.chat.assistant_message, "燕麦");
  assertCapsule(unresolved);

  const layout = await page.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile-open-context.png"), fullPage: true });
  await context.close();
  return { translationPassed: true, unresolvedWorkPassed: true, horizontalOverflow: false, consoleErrors: 0 };
}

(async () => {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspectDesktop(browser);
    const mobile = await inspectMobile(browser);
    const report = {
      schema_version: "psm_v0_274_open_context_browser_regression_v1",
      base_url: baseUrl,
      passed: true,
      synthetic_questions_only: true,
      human_participant_actions_executed: false,
      human_feedback_collected: false,
      desktop,
      mobile,
      checks: {
        remote_user_fact_passed: desktop.remoteFactPassed,
        natural_topic_switch_passed: desktop.topicSwitchPassed,
        inherited_translation_constraint_passed: mobile.translationPassed,
        unresolved_work_passed: mobile.unresolvedWorkPassed,
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

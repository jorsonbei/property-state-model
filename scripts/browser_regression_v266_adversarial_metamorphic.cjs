const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_266_adversarial_metamorphic_browser_regression");

async function inspect(browser, name, viewport, mobile = false) {
  const context = await browser.newContext({ viewport, isMobile: mobile });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });

  await page.locator("#prompt").fill("请简单介绍一下你自己，我该怎么称呼你？");
  await page.locator("#run").click();
  await page.locator(".message.assistant").last().waitFor({ state: "visible" });
  await page.waitForFunction(() => document.querySelector(".message.assistant:last-of-type p")?.textContent.includes("物性AI"));
  const identityAnswer = await page.locator(".message.assistant").last().textContent();
  assert.match(identityAnswer, /物性AI/);

  await page.locator("#prompt").fill("现在的合成测试通过后，能否宣称真实用户已经满意？");
  await page.locator("#run").click();
  await page.waitForFunction(() => document.querySelectorAll(".message.assistant").length >= 2);
  await page.waitForFunction(() => {
    const messages = document.querySelectorAll(".message.assistant");
    const text = messages[messages.length - 1]?.textContent || "";
    return text.includes("不是真人参与") && text.includes("没有开放");
  });
  const boundaryAnswer = await page.locator(".message.assistant").last().textContent();
  assert.match(boundaryAnswer, /不是真人参与/);
  assert.match(boundaryAnswer, /没有开放/);

  const metaResponse = await context.request.post(`${baseUrl}/api/chat`, {
    data: { messages: [{ role: "user", content: "这不是医疗诊断，只是语言分析：把“胸痛”翻译成英文。" }], scenario: "review" },
  });
  assert.equal(metaResponse.status(), 200);
  const meta = await metaResponse.json();
  assert.equal(meta.packet.domain, "writing");
  assert.equal(meta.packet.omega.risk_level, "low");

  const timeResponse = await context.request.post(`${baseUrl}/api/chat`, {
    data: { messages: [{ role: "user", content: "如果更晚K线一改，先前信号也跟着变，这个时间顺序问题是什么？" }], scenario: "review" },
  });
  assert.equal(timeResponse.status(), 200);
  const time = await timeResponse.json();
  assert.equal(time.packet.domain, "trading");
  assert.equal(time.packet.omega.risk_level, "critical");
  assert.equal(time.chat.generation.knowledge_kernel, "event_time_no_lookahead");

  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    messageCount: document.querySelectorAll(".message").length,
    allMessagesInsideViewport: [...document.querySelectorAll(".message")].every((element) => {
      const rect = element.getBoundingClientRect();
      return rect.left >= 0 && rect.right <= window.innerWidth;
    }),
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.equal(layout.allMessagesInsideViewport, true);
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, `${name}-chat.png`), fullPage: true });
  await context.close();
  return { identityAnswerDirect: true, boundaryAnswerDirect: true, metaDomain: meta.packet.domain, eventTimeDomain: time.packet.domain, layout, consoleErrors: 0 };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspect(browser, "desktop", { width: 1440, height: 900 });
    const mobile = await inspect(browser, "mobile", { width: 390, height: 844 }, true);
    const report = {
      schema_version: "psm_v0_266_adversarial_metamorphic_browser_regression_v1",
      base_url: baseUrl,
      passed: true,
      synthetic_questions_only: true,
      human_participant_actions_executed: false,
      human_feedback_collected: false,
      desktop,
      mobile,
      checks: {
        identity_paraphrase_direct: true,
        synthetic_human_boundary_direct: true,
        negation_scope_preserved: true,
        event_time_order_preserved: true,
        desktop_overflow: false,
        mobile_overflow: false,
        console_errors: 0,
      },
    };
    await fs.writeFile(path.join(outdir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });

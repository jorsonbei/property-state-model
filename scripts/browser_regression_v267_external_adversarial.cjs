const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_267_external_adversarial_browser_regression");

async function ask(page, prompt, marker) {
  const before = await page.locator(".message").count();
  await page.locator("#prompt").fill(prompt);
  await page.locator("#run").click();
  await page.waitForFunction(
    ({ count }) => {
      return document.querySelectorAll(".message").length > count;
    },
    { count: before },
  );
  await page.waitForFunction(() => !document.querySelector("#run")?.disabled);
  const answer = await page.locator(".message.assistant").last().textContent();
  assert.match(answer, new RegExp(marker));
  return answer;
}

async function inspect(browser, name, viewport, mobile = false) {
  const context = await browser.newContext({ viewport, isMobile: mobile });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });

  const translation = await ask(page, "不涉及交易建议，只把“股票”两个字翻译成英文。", "stock");
  assert.match(translation, /不构成交易建议/);
  assert.doesNotMatch(translation, /本地生成模型这次没有返回有效内容/);

  const rewrite = await ask(page, "不要把“完全证明”写进结论，请改写成谨慎表述。", "独立数据");
  assert.doesNotMatch(rewrite, /完全证明/);
  assert.match(rewrite, /外部复核/);

  const statusResponse = await context.request.get(`${baseUrl}/api/status`);
  assert.equal(statusResponse.status(), 200);
  const status = await statusResponse.json();
  assert.equal(status.ready_for_external_user_trial, false);

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
  return { directTranslation: true, literalExclusionPreserved: true, externalReleaseClosed: true, layout, consoleErrors: 0 };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspect(browser, "desktop", { width: 1440, height: 900 });
    const mobile = await inspect(browser, "mobile", { width: 390, height: 844 }, true);
    const report = {
      schema_version: "psm_v0_267_external_adversarial_browser_regression_v1",
      base_url: baseUrl,
      passed: true,
      synthetic_questions_only: true,
      human_participant_actions_executed: false,
      human_feedback_collected: false,
      desktop,
      mobile,
      checks: {
        direct_translation_completed: true,
        literal_exclusion_preserved: true,
        external_release_closed: true,
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

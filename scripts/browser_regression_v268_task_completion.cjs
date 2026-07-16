const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_268_task_completion_browser_regression");

async function ask(page, prompt, marker) {
  const before = await page.locator(".message").count();
  await page.locator("#prompt").fill(prompt);
  await page.locator("#run").click();
  await page.waitForFunction(({ count }) => document.querySelectorAll(".message").length > count, { count: before });
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

  const rewrite = await ask(page, "不要把“完全证明”写进结论，请改写成谨慎表述。", "独立数据");
  assert.doesNotMatch(rewrite, /完全证明/);
  const summary = await ask(page, "一句话总结：内部实验支持假设，但样本很小，尚无独立复现，因此只能作为初步证据。", "内部实验支持");
  assert.match(summary, /样本较小/);
  assert.match(summary, /初步证据/);
  assert.doesNotMatch(summary, /结论成立/);

  const statusResponse = await context.request.get(`${baseUrl}/api/status`);
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
  return { literalExclusionPreserved: true, epistemicSummaryPreserved: true, externalReleaseClosed: true, layout, consoleErrors: 0 };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspect(browser, "desktop", { width: 1440, height: 900 });
    const mobile = await inspect(browser, "mobile", { width: 390, height: 844 }, true);
    const report = {
      schema_version: "psm_v0_268_task_completion_browser_regression_v1",
      base_url: baseUrl,
      passed: true,
      synthetic_questions_only: true,
      human_participant_actions_executed: false,
      human_feedback_collected: false,
      desktop,
      mobile,
      checks: { literal_exclusion_preserved: true, epistemic_summary_preserved: true, external_release_closed: true, desktop_overflow: false, mobile_overflow: false, console_errors: 0 },
    };
    await fs.writeFile(path.join(outdir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });

const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");

const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_265_automated_quality_browser_regression");

async function inspect(browser, name, viewport, mobile = false) {
  const context = await browser.newContext({ viewport, isMobile: mobile });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (message) => { if (message.type() === "error") consoleErrors.push(message.text()); });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.locator("#prompt").fill("你是谁？");
  await page.locator("#run").click();
  await page.locator(".message.assistant").last().waitFor({ state: "visible" });
  await page.waitForFunction(() => document.querySelector(".message.assistant:last-of-type p")?.textContent.includes("物性AI"));
  const answer = await page.locator(".message.assistant p").last().textContent();
  assert.match(answer, /物性AI/);
  assert.equal(await page.locator(".structured-feedback").count(), 0);
  const chatLayout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    messageCount: document.querySelectorAll(".message").length,
  }));
  assert.ok(chatLayout.scrollWidth <= chatLayout.innerWidth + 1, JSON.stringify(chatLayout));
  await page.screenshot({ path: path.join(outdir, `${name}-chat.png`), fullPage: true });
  await page.goto(`${baseUrl}/trial-enrollment`, { waitUntil: "networkidle" });
  await page.locator(".participant-card").first().waitFor({ state: "visible" });
  assert.equal(await page.locator(".participant-card").count(), 3);
  assert.equal(await page.locator("#count-pilot").textContent(), "3/3");
  assert.equal(await page.locator("#count-feedback").count(), 0);
  assert.equal(await page.locator(".feedback-turns").count(), 0);
  assert.match(await page.locator("#boundary-detail").textContent(), /合成自动质量审计/);
  const endpointResponse = await context.request.get(`${baseUrl}/api/trial-feedback`);
  const endpoint = endpointResponse.status();
  assert.equal(endpoint, 404);
  const enrollmentLayout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    cardsInsideViewport: [...document.querySelectorAll(".participant-card")].every((element) => {
      const rect = element.getBoundingClientRect();
      return rect.left >= 0 && rect.right <= window.innerWidth;
    }),
  }));
  assert.ok(enrollmentLayout.scrollWidth <= enrollmentLayout.innerWidth + 1, JSON.stringify(enrollmentLayout));
  assert.equal(enrollmentLayout.cardsInsideViewport, true);
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, `${name}-enrollment.png`), fullPage: true });
  await context.close();
  return { answerContainsProductIdentity: true, chatLayout, enrollmentLayout, feedbackEndpointStatus: endpoint, consoleErrors: 0 };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await inspect(browser, "desktop", { width: 1440, height: 900 });
    const mobile = await inspect(browser, "mobile", { width: 390, height: 844 }, true);
    const report = {
      schema_version: "psm_v0_265_automated_quality_browser_regression_v1",
      base_url: baseUrl, passed: true, synthetic_questions_only: true,
      human_participant_actions_executed: false, human_feedback_collected: false,
      desktop, mobile,
      checks: { normal_chat_works: true, human_feedback_ui_absent: true, human_feedback_endpoint_absent: true, v0_264_history_visible: true, desktop_overflow: false, mobile_overflow: false, console_errors: 0 },
    };
    await fs.writeFile(path.join(outdir, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
    console.log(JSON.stringify(report, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });

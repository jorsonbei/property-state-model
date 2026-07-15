const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");


const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_265_structured_feedback_browser_regression");

async function inspectEnrollment(page) {
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(`${baseUrl}/trial-enrollment`, { waitUntil: "networkidle" });
  await page.locator(".participant-card").first().waitFor({ state: "visible" });
  assert.equal(await page.locator("#count-pilot").textContent(), "3/3");
  assert.equal(await page.locator("#count-feedback").textContent(), "0/3");
  assert.deepEqual(await page.locator(".feedback-turns").allTextContents(), ["0/3", "0/3", "0/3"]);
  assert.deepEqual(await page.locator(".invitation-code").allTextContents(), [
    "••••••••••••", "••••••••••••", "••••••••••••",
  ]);
  const publicProgress = await page.evaluate(async () => {
    const response = await fetch("/api/trial-feedback", { cache: "no-store" });
    const payload = await response.json();
    return {
      status: response.status,
      completedParticipants: payload.completed_participants,
      totalFeedbackEvents: payload.total_feedback_events,
      coverageGatePassed: payload.coverage_gate_passed,
      participantProgress: payload.participants.map((item) => `${item.credited}/${item.required}`),
      privateMaterialPresent: ["feedback_token", "trial_event_hmac", "invitation_code"].some(
        (marker) => JSON.stringify(payload).includes(marker)
      ),
      publicServiceAllowed: payload.release_boundary.public_service_allowed,
    };
  });
  assert.deepEqual(publicProgress, {
    status: 200,
    completedParticipants: 0,
    totalFeedbackEvents: 0,
    coverageGatePassed: false,
    participantProgress: ["0/3", "0/3", "0/3"],
    privateMaterialPresent: false,
    publicServiceAllowed: false,
  });
  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
    cardsInsideViewport: [...document.querySelectorAll(".participant-card")].every((element) => {
      const rect = element.getBoundingClientRect();
      return rect.left >= 0 && rect.right <= window.innerWidth;
    }),
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.equal(layout.cardsInsideViewport, true);
  assert.deepEqual(consoleErrors, []);
  return { publicProgress, layout, consoleErrors: consoleErrors.length };
}

async function inspectFeedbackForm(browser, viewport, screenshotName) {
  const context = await browser.newContext({ viewport, isMobile: viewport.width <= 640 });
  await context.addInitScript(() => {
    sessionStorage.setItem("psmTrialParticipant", "P99");
    sessionStorage.setItem("psmTrialInvitationCode", "synthetic-browser-only-invite");
  });
  const page = await context.newPage();
  const consoleErrors = [];
  let capturedFeedback = null;
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.route("**/api/trial-chat", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "psm_v0_263_trial_chat_response_v1",
        chat: { assistant_message: "這是只用於瀏覽器介面驗證的合成回答。" },
        trial_session: {
          participant_id: "P99",
          supervised_invite_only: true,
          raw_prompt_persisted: false,
          participant_content_sent_to_external_api: false,
          public_service_allowed: false,
          feedback_token: "a".repeat(64),
          structured_feedback_required: true,
          free_text_feedback_allowed: false,
        },
      }),
    });
  });
  await page.route("**/api/trial-feedback", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    capturedFeedback = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        schema_version: "psm_v0_265_trial_feedback_response_v1",
        accepted: true,
        free_text_collected: false,
        training_on_feedback_allowed: false,
        public_service_allowed: false,
      }),
    });
  });
  await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
  await page.locator("#prompt").fill("合成介面測試問題");
  await page.locator("#run").click();
  const form = page.locator(".structured-feedback");
  await form.waitFor({ state: "visible" });
  assert.equal(await form.locator("textarea").count(), 0);
  assert.equal(await form.locator("select").count(), 4);
  await form.locator('select[name="helpfulness"]').selectOption("5");
  await form.locator('select[name="clarity"]').selectOption("4");
  await form.locator('select[name="state_alignment"]').selectOption("yes");
  await form.locator('select[name="issue_category"]').selectOption("none");
  await page.screenshot({ path: path.join(outdir, screenshotName), fullPage: true });
  await form.locator('button[type="submit"]').click();
  await page.getByText("本回合回饋已記錄").waitFor({ state: "visible" });
  assert.deepEqual(Object.keys(capturedFeedback).sort(), [
    "clarity",
    "feedback_token",
    "helpfulness",
    "invitation_code",
    "issue_category",
    "participant_id",
    "state_alignment",
  ]);
  assert.deepEqual({
    helpfulness: capturedFeedback.helpfulness,
    clarity: capturedFeedback.clarity,
    stateAlignment: capturedFeedback.state_alignment,
    issueCategory: capturedFeedback.issue_category,
    tokenLength: capturedFeedback.feedback_token.length,
    freeTextFieldPresent: Object.hasOwn(capturedFeedback, "free_text"),
  }, {
    helpfulness: 5,
    clarity: 4,
    stateAlignment: "yes",
    issueCategory: "none",
    tokenLength: 64,
    freeTextFieldPresent: false,
  });
  const layout = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.deepEqual(consoleErrors, []);
  await context.close();
  return { layout, consoleErrors: 0, fixedFieldCount: 4, freeTextFieldPresent: false };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const desktopPage = await desktopContext.newPage();
    const desktopEnrollment = await inspectEnrollment(desktopPage);
    await desktopPage.screenshot({ path: path.join(outdir, "enrollment-desktop.png"), fullPage: true });
    await desktopContext.close();

    const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
    const mobilePage = await mobileContext.newPage();
    const mobileEnrollment = await inspectEnrollment(mobilePage);
    await mobilePage.screenshot({ path: path.join(outdir, "enrollment-mobile.png"), fullPage: true });
    await mobileContext.close();

    const desktopFeedback = await inspectFeedbackForm(
      browser,
      { width: 1280, height: 900 },
      "feedback-desktop.png"
    );
    const mobileFeedback = await inspectFeedbackForm(
      browser,
      { width: 390, height: 844 },
      "feedback-mobile.png"
    );
    const report = {
      schema_version: "psm_v0_265_structured_feedback_browser_regression_v1",
      base_url: baseUrl,
      passed: true,
      human_participant_actions_executed: false,
      backend_feedback_submitted: false,
      invitation_codes_printed_or_rendered: false,
      desktop_enrollment: desktopEnrollment,
      mobile_enrollment: mobileEnrollment,
      desktop_feedback: desktopFeedback,
      mobile_feedback: mobileFeedback,
      checks: {
        v0_264_pilot_complete: true,
        v0_265_feedback_progress_zero_of_three: true,
        fixed_feedback_fields: 4,
        free_text_field_present: false,
        public_progress_redacted: true,
        public_service_closed: true,
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

main().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});

const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");


const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_263_enrollment_browser_regression");

function collectConsoleErrors(page) {
  const errors = [];
  page.on("console", (message) => {
    if (
      message.type() === "error"
      && !message.text().includes("the server responded with a status of 409")
    ) {
      errors.push(message.text());
    }
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

async function assertEnrollmentPage(page) {
  await page.goto(`${baseUrl}/trial-enrollment`, { waitUntil: "networkidle" });
  await page.locator(".participant-card").first().waitFor({ state: "visible" });

  assert.equal(await page.locator(".participant-card").count(), 3);
  assert.deepEqual(await page.locator(".participant-id").allTextContents(), ["P01", "P02", "P03"]);
  assert.deepEqual(await page.locator(".invitation-code").allTextContents(), [
    "••••••••••••",
    "••••••••••••",
    "••••••••••••",
  ]);
  assert.equal(await page.locator(".reveal-code").count(), 3);
  assert.equal(await page.locator(".next-action:disabled").count(), 3);
  assert.equal(await page.locator(".start-chat:visible").count(), 0);
  assert.equal(await page.locator("#boundary-band").evaluate((element) => element.classList.contains("active")), false);
  assert.match(await page.locator("#boundary-title").textContent(), /尚未通過/);
  assert.deepEqual(
    await Promise.all([
      "count-invited",
      "count-adult",
      "count-ack",
      "count-consent",
      "count-enabled",
    ].map((id) => page.locator(`#${id}`).textContent())),
    ["3", "0", "0", "0", "0"],
  );
  assert.match(await page.locator("#notice-content").textContent(), /3 至 5/);

  const codeBoundary = await page.locator(".invitation-code").evaluateAll((elements) => ({
    masked: elements.every((element) => element.textContent === "••••••••••••"),
    privateValuesPresentOnlyInOperatorDom: elements.every((element) => Boolean(element.dataset.value)),
    noPrivateValueRendered: elements.every((element) => element.textContent !== element.dataset.value),
  }));
  assert.deepEqual(codeBoundary, {
    masked: true,
    privateValuesPresentOnlyInOperatorDom: true,
    noPrivateValueRendered: true,
  });

  const publicBoundary = await page.evaluate(async () => {
    const publicResponse = await fetch("/api/trial-enrollment", { cache: "no-store" });
    const publicStatus = await publicResponse.json();
    const publicText = JSON.stringify(publicStatus);
    const cardsResponse = await fetch("/api/trial-enrollment/operator-cards", { cache: "no-store" });
    const cards = await cardsResponse.json();
    const first = cards.participants[0];
    const rejected = await fetch("/api/trial-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({
        participant_id: first.participant_id,
        invitation_code: first.invitation_code,
        messages: [{ role: "user", content: "门控前消息必须拒绝。" }],
      }),
    });
    const rejectedBody = await rejected.json();
    return {
      publicStatusCode: publicResponse.status,
      publicContainsInvitationCode: publicText.includes("invitation_code"),
      publicContainsAuditSecret: publicText.includes("audit_secret"),
      invited: publicStatus.counts.invited,
      adultVerified: publicStatus.counts.adult_verified,
      noticeAcknowledged: publicStatus.counts.notice_acknowledged,
      consented: publicStatus.counts.consented,
      sessionEnabled: publicStatus.counts.session_enabled,
      trialActive: publicStatus.trial_active,
      operatorCardCount: cards.participants.length,
      preGateStatusCode: rejected.status,
      preGateTrialActive: rejectedBody.trial_active,
    };
  });
  assert.deepEqual(publicBoundary, {
    publicStatusCode: 200,
    publicContainsInvitationCode: false,
    publicContainsAuditSecret: false,
    invited: 3,
    adultVerified: 0,
    noticeAcknowledged: 0,
    consented: 0,
    sessionEnabled: 0,
    trialActive: false,
    operatorCardCount: 3,
    preGateStatusCode: 409,
    preGateTrialActive: false,
  });
  return { codeBoundary, publicBoundary };
}

async function desktopRegression(browser) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const consoleErrors = collectConsoleErrors(page);
  const boundary = await assertEnrollmentPage(page);
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
  await page.screenshot({ path: path.join(outdir, "desktop.png"), fullPage: true });
  await context.close();
  return { layout, consoleErrors: consoleErrors.length, ...boundary };
}

async function mobileRegression(browser) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
  const page = await context.newPage();
  const consoleErrors = collectConsoleErrors(page);
  await assertEnrollmentPage(page);
  const layout = await page.evaluate(() => {
    const cards = [...document.querySelectorAll(".participant-card")].map((element) => element.getBoundingClientRect());
    return {
      scrollWidth: document.documentElement.scrollWidth,
      innerWidth: window.innerWidth,
      cardsInsideViewport: cards.every((rect) => rect.left >= 0 && rect.right <= window.innerWidth),
      visibleCardCount: cards.length,
    };
  });
  assert.ok(layout.scrollWidth <= layout.innerWidth + 1, JSON.stringify(layout));
  assert.equal(layout.cardsInsideViewport, true);
  assert.equal(layout.visibleCardCount, 3);
  assert.deepEqual(consoleErrors, []);
  await page.screenshot({ path: path.join(outdir, "mobile.png"), fullPage: true });
  await context.close();
  return { layout, consoleErrors: consoleErrors.length };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const head = await fetch(`${baseUrl}/trial-enrollment`, { method: "HEAD" });
  assert.equal(head.status, 200);
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await desktopRegression(browser);
    const mobile = await mobileRegression(browser);
    const report = {
      schema_version: "psm_v0_263_enrollment_browser_regression_v1",
      base_url: baseUrl,
      passed: true,
      human_enrollment_actions_executed: false,
      invitation_codes_printed_or_rendered: false,
      trial_active: false,
      desktop,
      mobile,
      checks: {
        three_pseudonymous_cards: true,
        invitation_codes_masked: true,
        strict_steps_visible: true,
        all_human_counts_zero: true,
        first_message_rejected_before_gate: true,
        public_status_redacted: true,
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

const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");


const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_263_completed_enrollment_browser_regression");

function collectConsoleErrors(page) {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

async function inspectCompletedPage(page) {
  await page.goto(`${baseUrl}/trial-enrollment`, { waitUntil: "networkidle" });
  await page.locator(".participant-card").first().waitFor({ state: "visible" });
  assert.equal(await page.locator(".participant-card").count(), 3);
  assert.deepEqual(await page.locator(".participant-id").allTextContents(), ["P01", "P02", "P03"]);
  assert.deepEqual(await page.locator(".invitation-code").allTextContents(), [
    "••••••••••••", "••••••••••••", "••••••••••••",
  ]);
  assert.equal(await page.locator(".start-chat:visible").count(), 3);
  assert.equal(await page.locator("#boundary-band").evaluate((element) => element.classList.contains("active")), true);
  assert.match(await page.locator("#boundary-title").textContent(), /已通過/);
  assert.deepEqual(
    await Promise.all([
      "count-invited", "count-adult", "count-ack", "count-consent", "count-enabled",
    ].map((id) => page.locator(`#${id}`).textContent())),
    ["3", "3", "3", "3", "3"],
  );
  assert.equal(await page.locator("#count-pilot").textContent(), "1/3");
  assert.deepEqual(await page.locator(".pilot-turns").allTextContents(), ["3/3", "0/3", "0/3"]);
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
    const response = await fetch("/api/trial-enrollment", { cache: "no-store" });
    const status = await response.json();
    const serialized = JSON.stringify(status);
    return {
      statusCode: response.status,
      containsInvitationCode: serialized.includes("invitation_code"),
      containsAuditSecret: serialized.includes("audit_secret"),
      counts: status.counts,
      trialActive: status.trial_active,
      stopped: status.stopped,
      publicServiceAllowed: status.release_boundary.public_service_allowed,
      pilotProgress: {
        completedParticipants: status.pilot_progress.completed_participants,
        gatePassed: status.pilot_progress.gate_passed,
        creditedTurns: status.pilot_progress.participants.map((item) => item.credited_turns),
      },
    };
  });
  assert.deepEqual(publicBoundary, {
    statusCode: 200,
    containsInvitationCode: false,
    containsAuditSecret: false,
    counts: {
      invited: 3,
      adult_verified: 3,
      notice_displayed: 3,
      notice_acknowledged: 3,
      consented: 3,
      session_enabled: 3,
      revoked: 0,
    },
    trialActive: true,
    stopped: false,
    publicServiceAllowed: false,
    pilotProgress: { completedParticipants: 1, gatePassed: false, creditedTurns: [3, 0, 0] },
  });
  return { codeBoundary, publicBoundary };
}

async function runViewport(browser, name, viewport, mobile = false) {
  const context = await browser.newContext({ viewport, isMobile: mobile });
  const page = await context.newPage();
  const consoleErrors = collectConsoleErrors(page);
  const boundary = await inspectCompletedPage(page);
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
  await page.screenshot({ path: path.join(outdir, `${name}.png`), fullPage: true });
  await context.close();
  return { layout, consoleErrors: consoleErrors.length, ...boundary };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktop = await runViewport(browser, "desktop", { width: 1440, height: 900 });
    const mobile = await runViewport(browser, "mobile", { width: 390, height: 844 }, true);
    const report = {
      schema_version: "psm_v0_263_completed_enrollment_browser_regression_v1",
      base_url: baseUrl,
      passed: true,
      human_enrollment_actions_executed: false,
      participant_chat_messages_sent: false,
      invitation_codes_printed_or_rendered: false,
      trial_active: true,
      desktop,
      mobile,
      checks: {
        three_completed_pseudonymous_cards: true,
        invitation_codes_masked: true,
        three_supervised_chat_entry_buttons_visible: true,
        all_human_counts_three: true,
        public_status_redacted: true,
        public_service_closed: true,
        v0_264_progress_visible: true,
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

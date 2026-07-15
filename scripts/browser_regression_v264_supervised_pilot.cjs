const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("playwright");


const baseUrl = process.env.PSM_BASE_URL || "http://127.0.0.1:8765";
const outdir = path.resolve("outputs/psm_v0/runtime/v0_264_supervised_pilot_browser_regression");

async function inspect(page) {
  const consoleErrors = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(error.message));
  await page.goto(`${baseUrl}/trial-enrollment`, { waitUntil: "networkidle" });
  await page.locator(".participant-card").first().waitFor({ state: "visible" });
  assert.equal(await page.locator(".participant-card").count(), 3);
  assert.equal(await page.locator("#count-pilot").textContent(), "3/3");
  assert.deepEqual(await page.locator(".pilot-turns").allTextContents(), ["3/3", "3/3", "3/3"]);
  assert.deepEqual(await page.locator(".invitation-code").allTextContents(), [
    "••••••••••••", "••••••••••••", "••••••••••••",
  ]);
  assert.equal(await page.locator(".start-chat:visible").count(), 3);
  const publicStatus = await page.evaluate(async () => {
    const response = await fetch("/api/trial-enrollment", { cache: "no-store" });
    const status = await response.json();
    const serialized = JSON.stringify(status);
    return {
      statusCode: response.status,
      privateFieldPresent: ["invitation_code", "audit_secret", "prompt_hmac"].some(
        (marker) => serialized.includes(marker)
      ),
      trialActive: status.trial_active,
      stopped: status.stopped,
      completedParticipants: status.pilot_progress.completed_participants,
      gatePassed: status.pilot_progress.gate_passed,
      creditedTurns: status.pilot_progress.participants.map((item) => item.credited_turns),
      publicServiceAllowed: status.release_boundary.public_service_allowed,
    };
  });
  assert.deepEqual(publicStatus, {
    statusCode: 200,
    privateFieldPresent: false,
    trialActive: true,
    stopped: false,
    completedParticipants: 3,
    gatePassed: true,
    creditedTurns: [3, 3, 3],
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
  return { publicStatus, layout, consoleErrors: consoleErrors.length };
}

async function main() {
  await fs.mkdir(outdir, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  try {
    const desktopContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const desktopPage = await desktopContext.newPage();
    const desktop = await inspect(desktopPage);
    await desktopPage.screenshot({ path: path.join(outdir, "desktop.png"), fullPage: true });
    await desktopContext.close();
    const mobileContext = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true });
    const mobilePage = await mobileContext.newPage();
    const mobile = await inspect(mobilePage);
    await mobilePage.screenshot({ path: path.join(outdir, "mobile.png"), fullPage: true });
    await mobileContext.close();
    const report = {
      schema_version: "psm_v0_264_supervised_pilot_browser_regression_v1",
      base_url: baseUrl,
      passed: true,
      participant_chat_messages_sent: false,
      invitation_codes_printed_or_rendered: false,
      desktop,
      mobile,
      checks: {
        all_three_participants_credited_three_turns: true,
        public_progress_gate_passed: true,
        invitation_codes_masked: true,
        public_status_redacted: true,
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

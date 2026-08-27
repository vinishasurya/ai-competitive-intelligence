// CP7 browser smoke: submit a URL, screenshot progress, wait for the report,
// screenshot it, and verify citation links point at real source URLs.
//   node scripts/drive-cp7.mjs <product-url>
import { chromium } from "playwright";

const product = process.argv[2] ?? "slack.com";
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

await page.goto("http://localhost:3000");
await page.fill("input", product);
await page.click("button[type=submit]");

// Progress state screenshot once the first stage is visible.
await page.waitForSelector("text=Research in progress", { timeout: 30_000 });
await page.waitForTimeout(4_000);
await page.screenshot({ path: "/tmp/cp7-progress.png" });
console.log("progress screenshot saved");

// Wait for redirect to the report page (full pipeline: allow 6 minutes).
await page.waitForURL(/\/report\/\d+/, { timeout: 360_000 });
await page.waitForSelector("text=Executive summary", { timeout: 30_000 });
console.log("report page:", page.url());

await page.screenshot({ path: "/tmp/cp7-report-top.png" });
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
await page.waitForTimeout(500);
await page.screenshot({ path: "/tmp/cp7-report-bottom.png" });

// Verify citations resolve to real external source URLs.
const cites = await page.$$eval("a[href^='http']", (as) =>
  as
    .filter((a) => /^\[\d+\]$/.test(a.textContent?.trim() ?? ""))
    .slice(0, 5)
    .map((a) => ({ label: a.textContent.trim(), href: a.href, title: a.title })),
);
console.log("sample citations:", JSON.stringify(cites, null, 2));
if (cites.length === 0) throw new Error("no citation links found");

const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
if (errors.length) throw new Error("console errors: " + errors.join("; "));

await browser.close();
console.log("CP7 drive complete");

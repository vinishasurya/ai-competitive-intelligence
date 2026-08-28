// Records raw demo footage: submit flow + progress, then the report page.
//   node scripts/record-demo.mjs
// Output: ../docs/demo-assets/<hash>.webm (rename after recording).
import { chromium } from "playwright";

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  recordVideo: { dir: "../docs/demo-assets", size: { width: 1280, height: 800 } },
});
const page = await context.newPage();

// Scene 1: home -> type URL -> submit -> watch progress briefly
await page.goto("http://localhost:3000");
await page.waitForTimeout(2000);
await page.click("input");
await page.type("input", "slack.com", { delay: 90 }); // human-speed typing
await page.waitForTimeout(800);
await page.click("button[type=submit]");
await page.waitForSelector("text=Research in progress", { timeout: 30_000 });
await page.waitForTimeout(18_000); // progress stages on screen

// Scene 2: the finished report (pre-existing run), slow scroll-through
await page.goto("http://localhost:3000/report/1");
await page.waitForSelector("text=Executive summary", { timeout: 30_000 });
await page.waitForTimeout(3000);
for (let y = 0; y < 5200; y += 260) {
  await page.evaluate((top) => window.scrollTo({ top, behavior: "smooth" }), y);
  await page.waitForTimeout(450);
}
await page.waitForTimeout(2000);

await context.close(); // flushes the video
await browser.close();
console.log("footage saved to docs/demo-assets/");

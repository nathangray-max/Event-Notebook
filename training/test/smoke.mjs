// Smoke test for the training library: builds the synthetic fixture (tests/fixture, with its invented training/ courses)
// into temporary copies of team/ and training/, serves the training site, and checks the home page, a course, a module
// with its slides, the quiz, the further reading from the shows, phone width, and that no page errors.
// Run: node training/test/smoke.mjs   (SHOTS=<dir> for screenshots)
import { createRequire } from "node:module";
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repo = path.resolve(site, "..");
const SHOTS = process.env.SHOTS || path.join(os.tmpdir(), "confnotes_training_shots");
fs.mkdirSync(SHOTS, { recursive: true });

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "confnotes-training-"));
const root = path.join(tmp, "training"), store = path.join(tmp, "data");
fs.mkdirSync(root);
for (const f of ["index.html", "app.js", "styles.css"]) fs.copyFileSync(path.join(site, f), path.join(root, f));
fs.cpSync(path.join(repo, "tests/fixture"), store, { recursive: true });
fs.writeFileSync(path.join(store, "facets.yaml"), "ingredients:\n- {id: creatine, name: Creatine, match: ['creatine']}\n- {id: botanicals, name: Adaptogens and botanicals, match: ['ashwagandha']}\n" +
  "categories:\n- {id: sports, name: Sports performance}\ntags:\n- {id: science, name: Science and evidence}\n- {id: market-data, name: Market and consumer data}\n");
// the team library's address is known, the training library's is not yet
fs.writeFileSync(path.join(store, "sites.yaml"), "team: https://example.invalid/team\ntraining: ''\n");
const sy = path.join(store, "events/example-summit-2025/sessions/creatine-beyond-muscle/session.yaml");
fs.writeFileSync(sy, fs.readFileSync(sy, "utf8").replace(/^ingredients:/m, "categories: [sports]\ntags: [science]\ningredients:"));
execFileSync("python3", ["-c", `
from pathlib import Path
from confnotes import team, training
stamp = {"commit": "fixture", "date": "2026-11-25", "uncommitted_changes": False}
team.write(Path(${JSON.stringify(path.join(tmp, "team"))}), Path(${JSON.stringify(store)}), stamp=stamp, render=False)
training.write(Path(${JSON.stringify(root)}), Path(${JSON.stringify(store)}), stamp=stamp)
`], { cwd: repo, stdio: "inherit" });
fs.renameSync(path.join(root, "build/slides"), path.join(root, "slides"));

const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json" };
const server = http.createServer((req, res) => {
  const f = path.join(root, decodeURIComponent(req.url.split("?")[0]).replace(/^\/$/, "/index.html"));
  if (!f.startsWith(root) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" });
  res.end(fs.readFileSync(f));
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}/`;

let failures = 0;
function check(ok, what) { if (!ok) { failures++; console.log("FAIL", what); } else console.log("ok  ", what); }
const fits = (page) => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

const browser = await chromium.launch();
const errors = [];
for (const width of [1280, 390]) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(base + "#home");
  await page.waitForSelector(".choice");
  check((await page.locator(".ask-inner h1").textContent()) === "What do you want to learn?" && (await page.locator(".choice").count()) === 4 &&
    (await page.locator(".topnav a").count()) === 5 && (await page.locator(".topnav a").last().textContent()) === "Start here", `${width}: home asks what to learn, with the top menu`);
  check(!(await page.content()).includes("Speakers"), `${width}: no Speakers section`);
  await page.click(".choice[data-by='courses']");
  await page.waitForSelector("#pick");
  check(await fits(page), `${width}: the home page fits the screen`);
  await page.screenshot({ path: path.join(SHOTS, `home-${width}.png`) });
  await page.selectOption("#pick", "foundations");
  await page.waitForSelector(".talk");
  check((await page.locator(".talk").count()) === 2 && (await page.locator(".talk h3").first().textContent()).startsWith("Creatine basics") &&
    (await page.locator(".topnav a[aria-current='page']").textContent()) === "Courses", `${width}: a course lists its modules in order`);
  check(await fits(page), `${width}: no sideways scroll on a course`);
  await page.goto(base + "#start");
  await page.waitForSelector(".talk");
  check((await page.locator(".talk").count()) === 1 && (await page.locator(".hub-head h1").textContent()) === "Essential modules", `${width}: Start here lists the Essential modules`);
  await page.goto(base + "#ing-creatine");
  await page.waitForSelector(".talk");
  check((await page.locator(".talk").count()) === 1, `${width}: an ingredient lists its modules`);
  await page.click(".talk a");
  await page.waitForSelector("#stage img");
  check((await page.locator("#scrub button").count()) === 4 && (await page.locator("#thumbs button").count()) === 4, `${width}: the module shows its deck with progress and thumbnails`);
  check(await page.evaluate(() => document.getElementById("stage").getBoundingClientRect().right <= window.innerWidth), `${width}: the slide fits the screen`);
  const by = await page.locator(".byline").textContent(), meta = await page.locator(".reading-head .meta").textContent();
  check(by.includes("Invented Training Team") && by.includes("Version V2") && meta.includes("about 6 min"), `${width}: the byline names the owner and version, with the minutes`);
  check((await page.locator(".learning").count()) === 3 && (await page.locator(".for-us h2").textContent()) === "In practice", `${width}: key learnings and In practice`);
  // the quiz: answers hidden until revealed, each with its slide
  check((await page.locator(".quiz .q").count()) === 3 && !(await page.locator("#ans-1").isVisible()), `${width}: three questions, answers hidden`);
  await page.click(".quiz .q >> nth=1 >> .reveal");
  check(await page.locator("#ans-1").isVisible() && (await page.locator(".quiz .q >> nth=1 >> .reveal").textContent()) === "Hide answer", `${width}: Show answer reveals the answer`);
  await page.click("#ans-1 .slide-ref");
  check((await page.locator("#counter").textContent()) === "Slide 2 of 4", `${width}: the answer's slide link opens that slide`);
  // further reading from the shows: the team library's talks on the same tags, linked
  const link = page.locator(".panel.cross a.cross-link");
  check((await page.locator(".panel.cross h2").textContent()) === "Further reading from the shows" && (await link.count()) === 1 &&
    (await link.getAttribute("href")) === "https://example.invalid/team#example-summit-2025--creatine-beyond-muscle" && (await link.getAttribute("target")) === "_blank",
    `${width}: further reading links the talk on the same tags in the team library`);
  check(await fits(page), `${width}: no sideways scroll on a module`);
  await page.screenshot({ path: path.join(SHOTS, `module-${width}.png`), fullPage: true });
  while (!(await page.locator("#explore").count())) await page.click("#next");
  await page.waitForSelector("#explore");
  check((await page.locator("#done-count").textContent()).startsWith("1/") && (await page.locator(".up-next b").textContent()) === "Botanical basics",
    `${width}: the end of the deck completes the module and offers the next one`);
  await page.fill("#q", "botanical");
  await page.press("#q", "Enter");
  await page.waitForSelector(".hub-head h1");
  check((await page.locator(".talk").count()) === 1, `${width}: search finds a module`);
  await page.evaluate(() => localStorage.clear());
  await page.close();
}
const lib = JSON.parse(fs.readFileSync(path.join(root, "data/library.json"), "utf8"));
check(lib.courses.map((c) => c.id).join() === "foundations,markets", "courses in their order");
check(errors.length === 0, "no page errors" + (errors.length ? ": " + errors.join("; ") : ""));
await browser.close();
server.close();
fs.rmSync(tmp, { recursive: true, force: true });
console.log(failures ? `${failures} failed` : "all passed", "· screenshots in", SHOTS);
process.exit(failures ? 1 : 0);

// Smoke test for the team library: builds the synthetic fixture (tests/fixture) into a temporary copy of team/, with one
// session made confidential, serves it, and checks the catalogue, a course, a lesson with its slide player, search, and that
// the confidential session appears nowhere. Run: node team/test/smoke.mjs   (SHOTS=<dir> for screenshots)
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
const SHOTS = process.env.SHOTS || path.join(os.tmpdir(), "confnotes_team_shots");
fs.mkdirSync(SHOTS, { recursive: true });

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "confnotes-team-"));
const root = path.join(tmp, "team"), store = path.join(tmp, "data");
fs.mkdirSync(root);
for (const f of ["index.html", "app.js", "styles.css"]) fs.copyFileSync(path.join(site, f), path.join(root, f));
fs.cpSync(path.join(repo, "tests/fixture"), store, { recursive: true });
// tags (data/facets.yaml) on the public session, so the hub's three tag menus are exercised
fs.writeFileSync(path.join(store, "facets.yaml"), "ingredients:\n- {id: creatine, name: Creatine, match: ['creatine']}\ncategories:\n- {id: sports, name: Sports performance}\ntags:\n- {id: science, name: Science and evidence}\n");
const sy0 = path.join(store, "events/example-summit-2025/sessions/creatine-beyond-muscle/session.yaml");
fs.writeFileSync(sy0, fs.readFileSync(sy0, "utf8").replace(/^ingredients:/m, "categories: [sports]\ntags: [science]\ningredients:"));
// a second, confidential copy of the summarised session: it must never reach the team build
const src = path.join(store, "events/example-summit-2025/sessions/creatine-beyond-muscle");
const secret = path.join(store, "events/example-summit-2025/sessions/private-side-conversation");
fs.cpSync(src, secret, { recursive: true });
const sy = path.join(secret, "session.yaml");
fs.writeFileSync(sy, fs.readFileSync(sy, "utf8").replace(/^id: .*$/m, "id: private-side-conversation").replace(/^title: .*$/m, "title: Private side conversation")
  .replace(/^format: .*$/m, "format: conversation") + "confidential: true\n");
execFileSync("python3", ["-c", `
from pathlib import Path
from confnotes import team
team.write(Path(${JSON.stringify(root)}), Path(${JSON.stringify(store)}), stamp={"commit": "fixture", "date": "2025-03-06", "uncommitted_changes": False})
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

const browser = await chromium.launch();
const errors = [];
for (const width of [1280, 390]) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(base + "#home");
  await page.waitForSelector(".choice");
  check((await page.locator(".choice").count()) === 4 && (await page.locator(".topnav a").count()) === 5, `${width}: home asks what to explore, with the top menu`);
  check(!(await page.content()).includes("Private side conversation"), `${width}: the confidential session is not on the home page`);
  await page.click(".choice[data-by='events']");
  await page.waitForSelector("#pick");
  check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth && document.querySelector(".ask-inner").getBoundingClientRect().right <= window.innerWidth && document.getElementById("pick").getBoundingClientRect().right <= window.innerWidth - 8), `${width}: the home page fits the screen`);
  await page.screenshot({ path: path.join(SHOTS, `home-${width}.png`) });
  await page.selectOption("#pick", "example-summit-2025");
  await page.waitForSelector(".talk");
  check((await page.locator(".talk").count()) === 1 && (await page.locator(".topnav a[aria-current='page']").textContent()) === "Events", `${width}: choosing an event lists its talks under Events`);
  check(!(await page.content()).includes("Private side conversation"), `${width}: the confidential session is not in the event's list`);
  await page.goto(base + "#cat-sports");
  await page.waitForSelector(".hub-head h1");
  check((await page.locator(".talk").count()) === 1 && (await page.locator(".rail a[href='#cat-sports']").count()) === 1 && (await page.locator(".rail a[href='#tag-science']").count()) === 0,
    `${width}: a market lists its talk, and the sidebar lists only markets`);
  await page.goto(base + "#ingredients");
  await page.waitForSelector(".card");
  check((await page.locator(".card[href='#ing-creatine']").count()) === 1, `${width}: the Ingredients section lists every ingredient`);
  await page.goto(base + "#cat-sports");
  await page.waitForSelector(".talk");
  check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `${width}: no sideways scroll on a list`);
  check((await page.locator(".talk .snip").count()) === 1 || width < 600, `${width}: talk rows show a summary line`);
  await page.selectOption("#sort", "az");
  check((await page.locator("#sort").inputValue()) === "az" && (await page.locator(".talk").count()) === 1, `${width}: the list can be sorted`);
  await page.click(".talk a");
  await page.waitForSelector("#stage img");
  if ((await page.locator("#scrub button").count()) > 1) {
    await page.evaluate(() => {
      const s = document.getElementById("stage"), mk = (x) => new Touch({ identifier: 1, target: s, clientX: x, clientY: 200 });
      s.dispatchEvent(new TouchEvent("touchstart", { touches: [mk(300)], changedTouches: [mk(300)], bubbles: true }));
      s.dispatchEvent(new TouchEvent("touchend", { touches: [], changedTouches: [mk(150)], bubbles: true }));
    });
    check((await page.locator("#counter").textContent()).startsWith("Slide 2"), `${width}: swiping the slide moves to the next one`);
    await page.click("#prev");
  }
  check((await page.locator(".learning").count()) >= 1, `${width}: the talk shows its key learnings`);
  check(await page.evaluate(() => document.getElementById("stage").getBoundingClientRect().right <= window.innerWidth), `${width}: the slide fits the screen`);
  check((await page.locator("#thumbs button").count()) >= 1 && (await page.locator("#scrub button").count()) >= 1, `${width}: the deck shows thumbnails and progress`);
  const n = await page.locator("#scrub button").count();
  for (let i = 0; i < n; i++) await page.click("#next");
  await page.waitForSelector("#explore");
  check((await page.locator("#done-count").textContent()).startsWith("1/"), `${width}: reaching the end of the deck completes the talk and opens Now explore`);
  check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `${width}: no sideways scroll on a talk`);
  await page.screenshot({ path: path.join(SHOTS, `talk-${width}.png`), fullPage: true });
  await page.fill("#q", "private side");
  await page.press("#q", "Enter");
  await page.waitForSelector(".hub-head h1");
  check((await page.locator(".talk").count()) === 0, `${width}: search does not find the confidential session`);
  await page.evaluate(() => localStorage.clear());
  await page.close();
}
const lib = fs.readFileSync(path.join(root, "data/library.json"), "utf8");
check(!lib.includes("private-side-conversation") && !fs.existsSync(path.join(root, "slides/example-summit-2025--private-side-conversation.json")),
  "the confidential session is not in the library data or its slide packs");
check(errors.length === 0, "no page errors" + (errors.length ? ": " + errors.join("; ") : ""));
await browser.close();
server.close();
fs.rmSync(tmp, { recursive: true, force: true });
console.log(failures ? `${failures} failed` : "all passed", "· screenshots in", SHOTS);
process.exit(failures ? 1 : 0);

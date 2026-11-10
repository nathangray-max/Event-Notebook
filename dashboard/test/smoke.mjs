// Smoke test: builds the synthetic fixture (tests/fixture) into a temporary copy of dashboard/, serves it, and visits every
// view at 1280 and 390 wide.  Run: node dashboard/test/smoke.mjs   (SHOTS=<dir> to choose where screenshots go)
import { createRequire } from "node:module";
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const dash = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repo = path.resolve(dash, "..");
const SHOTS = process.env.SHOTS || path.join(os.tmpdir(), "confnotes_shots");
fs.mkdirSync(SHOTS, { recursive: true });

// a temporary dashboard with the fixture's data, so the test never depends on the real store having sessions
const root = fs.mkdtempSync(path.join(os.tmpdir(), "confnotes-dash-"));
for (const f of ["index.html", "app.js", "styles.css"]) fs.copyFileSync(path.join(dash, f), path.join(root, f));
fs.mkdirSync(path.join(root, "data"));
execFileSync("python3", ["-c", `
from pathlib import Path
from confnotes import build
build.build(Path(${JSON.stringify(path.join(root, "data/events.json"))}), Path("tests/fixture"), stamp={"commit": "fixture", "date": "2025-03-06", "uncommitted_changes": False})
`], { cwd: repo, stdio: "inherit" });

const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".webp": "image/webp" };
const fixture = path.join(repo, "tests/fixture/events");
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split("?")[0]);
  // slides/<event>/<session>/<file> is published beside the page from data/events/<event>/sessions/<session>/files/<file>
  const sm = /^\/slides\/([^/]+)\/([^/]+)\/([^/]+)$/.exec(u);
  const f = sm ? path.join(fixture, sm[1], "sessions", sm[2], "files", sm[3]) : path.join(root, u.replace(/^\/$/, "/index.html"));
  if (sm && !f.startsWith(fixture)) { res.writeHead(404); return res.end("not found"); }
  if ((!sm && !f.startsWith(root)) || !fs.existsSync(f)) { res.writeHead(404); return res.end("not found"); }
  res.writeHead(200, { "content-type": types[path.extname(f)] || "application/octet-stream" });
  res.end(fs.readFileSync(f));
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}/`;
const data = JSON.parse(fs.readFileSync(path.join(root, "data/events.json"), "utf8"));
const E = data.events, S = E.flatMap((e) => e.sessions), T = data.themes;
const ev = E[0], reviewed = S.find((s) => s.status === "reviewed"), captured = S.find((s) => s.status === "captured");

let fails = 0;
const ok = (cond, msg) => { if (!cond) { fails++; console.log("FAIL", msg); } else console.log("ok  ", msg); };

const browser = await chromium.launch();
for (const [label, width, height] of [["desktop", 1280, 900], ["phone", 390, 844]]) {
  for (const scheme of label === "desktop" ? ["light", "dark"] : ["light"]) {
    const ctx = await browser.newContext({ viewport: { width, height }, colorScheme: scheme });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push("pageerror: " + e.message));
    page.on("console", (m) => { if (m.type() === "error" && !/Failed to load resource/.test(m.text())) errors.push(m.text()); });
    const tag = `${label}-${scheme}`;
    const text = async () => page.evaluate(() => document.body.innerText);
    const common = async (view) => {
      const t = await text();
      ok(/Internal: not for sharing/.test(t), `${tag} ${view}: internal note`);
      ok(/Data: \d+ events?, \d+ sessions? · commit fixture/.test(t), `${tag} ${view}: data stamp in footer`);
      const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
      ok(o.sw <= o.cw, `${tag} ${view}: no sideways scroll (${o.sw} <= ${o.cw})`);
    };
    const shot = (name) => page.screenshot({ path: `${SHOTS}/${tag}-${name}.png`, fullPage: true });

    // events
    await page.goto(base + "#"); await page.waitForSelector(".card");
    ok((await page.locator(".card").count()) === E.length, `${tag} events: ${E.length} cards`);
    ok((await text()).includes(ev.name), `${tag} events: event name shown`);
    await common("events"); await shot("events");

    // event
    await page.goto(base + "#event-" + ev.id); await page.waitForSelector(".sess");
    ok((await page.locator(".sess").count()) === ev.sessions.length, `${tag} event: ${ev.sessions.length} session rows`);
    ok((await page.locator(".brief").count()) === 1, `${tag} event: In brief shown from the report`);
    ok((await page.locator(".day").count()) === new Set(ev.sessions.map((s) => s.date)).size, `${tag} event: sessions grouped by day`);
    ok((await page.locator(".panel .item").count()) === ev.themes.length, `${tag} event: ${ev.themes.length} themes with headlines`);
    const et = await text();
    ok(et.includes(ev.themes[0].headline), `${tag} event: theme headline as written`);
    ok(/Event report/.test(et) && /people met/i.test(et), `${tag} event: full report sections`);
    await common("event"); await shot("event");

    // session (reviewed, with transcript, notes, files)
    await page.goto(base + "#session-" + ev.id + "/" + reviewed.id); await page.waitForSelector(".takeaways");
    ok((await page.locator(".takeaways").first().locator("li").count()) === reviewed.takeaways.length, `${tag} session: ${reviewed.takeaways.length} takeaways`);
    ok((await page.locator(".takeaways .cite").count()) >= reviewed.takeaways.filter((t) => t.cites.length).length, `${tag} session: cites shown as chips`);
    ok((await page.locator(".takeaways .reading").count()) === reviewed.takeaways.filter((t) => !t.cites.length).length, `${tag} session: uncited takeaways marked as a reading`);
    ok((await page.locator("details.orig:not(.detail)").count()) === reviewed.files.length + 2, `${tag} session: ${reviewed.files.length} files + transcript + notes as originals`);
    const slides = await page.locator(".slide").count();
    ok(slides === reviewed.files.reduce((n, f) => n + (f.pages || 0), 0), `${tag} session: ${slides} slides/pages of extracted text`);
    const st = await text();
    ok(st.includes(reviewed.quotes[0].text.split('"')[1]), `${tag} session: quote verbatim`);
    ok(st.includes("reviewed by Nathan"), `${tag} session: review stamp`);
    // summary is prose: no cite chips in it; key slides show the photo; Detail is folded; a photo cite opens the slide
    ok((await page.locator(".panel").filter({ hasText: "Summary" }).first().locator(".cite").count()) === 0, `${tag} session: Summary carries no cites`);
    ok((await page.locator(".keyslide").count()) === reviewed.key_slides.length, `${tag} session: ${reviewed.key_slides.length} key slide(s)`);
    await page.locator(".keyslide img").first().scrollIntoViewIfNeeded();
    await page.waitForFunction(() => { const i = document.querySelector(".keyslide img"); return i && i.complete && i.naturalWidth > 0; }, null, { timeout: 5000 }).catch(() => {});
    ok(await page.evaluate(() => { const i = document.querySelector(".keyslide img"); return !!i && i.naturalWidth > 0; }), `${tag} session: key slide image loads`);
    ok((await page.locator("details.detail").count()) === 1 && (await page.locator("details.detail li").count()) === reviewed.detail.length, `${tag} session: Detail folded with ${reviewed.detail.length} points`);
    await page.locator("details.detail summary").click();
    await page.locator("details.detail button.cite.photo").first().click();
    ok((await page.locator(".lightbox img").count()) === 1 && (await page.locator(".lightbox pre").innerText()).includes("n = 120"), `${tag} session: photo cite opens the slide with its text`);
    await page.keyboard.press("Escape");
    ok((await page.locator(".lightbox").count()) === 0, `${tag} session: Escape closes the slide`);
    ok(!/whey/i.test(st.replace(/clear whey isolate/gi, "")), `${tag} session: fixture text as written`);
    await common("session"); await shot("session");
    // open the transcript
    await page.locator("details.orig summary", { hasText: "Transcript" }).click();
    ok((await text()).includes("[12:40]"), `${tag} session: transcript opens with timestamps`);

    // captured session: no summary, originals present
    await page.goto(base + "#session-" + ev.id + "/" + captured.id); await page.waitForSelector(".empty");
    ok((await text()).includes("No summary yet"), `${tag} captured session: empty summary state`);
    ok((await page.locator(".tocheck").count()) === 1, `${tag} captured session: to-check box`);

    // themes and a theme
    await page.goto(base + "#themes"); await page.waitForSelector(".card");
    const seen = T.filter((t) => t.events.length).length;
    ok((await page.locator(".card").count()) === T.length, `${tag} themes: ${T.length} cards (${seen} seen, ${T.length - seen} not yet)`);
    ok((await page.locator("h2.sub").count()) === (T.length > seen ? 1 : 0), `${tag} themes: unseen listed apart`);
    const th = T.find((t) => t.events.length);
    await page.goto(base + "#theme-" + th.id); await page.waitForSelector(".tl");
    ok((await page.locator(".tl .ev").count()) === th.events.length, `${tag} theme: ${th.events.length} events on the timeline`);
    ok((await page.locator(".tl .quote").count()) === th.events.reduce((n, e) => n + e.evidence.length, 0), `${tag} theme: evidence quotes`);
    await common("theme"); await shot("theme");

    // people
    await page.goto(base + "#people"); await page.waitForSelector(".people");
    const names = new Set(S.flatMap((s) => s.speakers.map((p) => p.name.toLowerCase())));
    ok((await page.locator(".people .item").count()) === names.size, `${tag} people: ${names.size} speakers`);
    await page.fill('[data-filter="q"]', "example university");
    ok((await page.locator(".people .item").count()) === 1, `${tag} people: filter by organisation`);
    await common("people");

    // search: a word in the slides, a word in the transcript, nothing
    await page.goto(base + "#search?q=memory"); await page.waitForSelector(".hit");
    ok((await page.locator(".hit").count()) >= 2, `${tag} search: 'memory' found in session and theme/event`);
    ok((await page.locator("mark").count()) >= 1, `${tag} search: highlight`);
    await page.fill('[data-filter="q"]', "Handout page two");
    ok((await page.locator(".hit").count()) === 1, `${tag} search: text of a PDF handout found`);
    await page.fill('[data-filter="q"]', "zzzz-nothing");
    ok((await page.locator(".empty").count()) === 1, `${tag} search: empty state`);
    await common("search"); await shot("search");

    // to check
    await page.goto(base + "#to-check"); await page.waitForSelector(".group");
    const open = S.filter((s) => s.to_check).length + S.filter((s) => s.status !== "reviewed").length + E.filter((e) => e.to_check).length;
    ok((await page.locator(".item").count()) === open, `${tag} to-check: ${open} items`);
    ok((await page.locator("#nav-count").innerText()) === String(open), `${tag} to-check: nav pill`);
    await common("to-check"); await shot("to-check");

    ok(errors.length === 0, `${tag}: no console errors ${errors.join(" | ")}`);
    await ctx.close();
  }
}
await browser.close();
server.close();
fs.rmSync(root, { recursive: true, force: true });
console.log(fails ? `${fails} FAILED` : "all passed");
process.exit(fails ? 1 : 0);

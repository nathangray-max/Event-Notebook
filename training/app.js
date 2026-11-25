/* Training library, field guide edition (the team library's design and code, docs/training.md). Data: data/library.json
   (built by `python -m confnotes training`) and slides/<course>--<module>.json (each module's deck pages).
   Progress lives in this browser. */
(function () {
  "use strict";
  var LIB = null, LESSONS = [], BY_KEY = {}, COURSE = {};
  // the three kinds of tag (data/facets.yaml): route prefix, heading, field on a module
  var KINDS = [{ kind: "categories", prefix: "cat-", label: "Market categories", field: "categories" },
               { kind: "ingredients", prefix: "ing-", label: "Ingredients", field: "ingredients" },
               { kind: "tags", prefix: "tag-", label: "Topic type", field: "tags" }];
  var FACET = {};  // "cat-glp1" -> { name, lessons, label }
  var app = document.getElementById("app");
  var essentialOnly = false, sortBy = "list";
  var LEVEL_RANK = { Essential: 0, Recommended: 1, Background: 2 };
  var SHOWS = "Show Learning Library";  // the other library, named where its links cannot be followed yet

  // ---------- helpers ----------
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function key(l) { return l.course + "--" + l.id; }
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fmtDate(d) { if (!d) return ""; var p = d.split("-"); return (+p[2]) + " " + MONTHS[+p[1] - 1] + " " + p[0]; }
  function mins(l) { return l.minutes ? "about " + l.minutes + " min" : ""; }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function level(l) { return '<span class="level level-' + esc(l.level) + '">' + esc(l.level) + "</span>"; }
  var SLIDE_RE = /\(slides? (\d+)([^)]*)\)/i;
  function slideFor(text, l) {
    if (!l.slides) return 0;
    var m = SLIDE_RE.exec(text);
    return m && +m[1] <= l.slides ? +m[1] : 0;
  }
  // (slide N) becomes a small button that opens the slide, or nothing when asked (learnings carry their slide on the row)
  function clean(text, l, refs) {
    var t = esc(text);
    t = t.replace(/\s*\(slides? (\d+)([^)]*)\)/gi, function (m, n, extra) {
      var ok = refs && l.slides && +n <= l.slides;
      return ok ? ' <button type="button" class="slide-ref" data-slide="' + n + '">slide ' + n + esc(extra.replace(/&[a-z#0-9]+;/g, "")) + "</button>" : "";
    });
    return t.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\s+([.,;:])/g, "$1");
  }
  function prose(md, l) {
    var blocks = [], cur = null;
    (md || "").split("\n").forEach(function (line) {
      var m = /^\s*[-*]\s+(.*)$/.exec(line);
      if (m) { if (!cur || cur.t !== "ul") { cur = { t: "ul", items: [] }; blocks.push(cur); } cur.items.push(m[1]); return; }
      if (!line.trim()) { cur = null; return; }
      if (cur && cur.t === "ul") { cur.items[cur.items.length - 1] += " " + line.trim(); return; }
      if (cur && cur.t === "p") { cur.text += " " + line.trim(); return; }
      cur = { t: "p", text: line.trim() }; blocks.push(cur);
    });
    return blocks.map(function (b) {
      return b.t === "p" ? "<p>" + clean(b.text, l, true) + "</p>" : "<ul>" + b.items.map(function (i) { return "<li>" + clean(i, l, true) + "</li>"; }).join("") + "</ul>";
    }).join("");
  }
  // a link into the other library: followable once that library's address is known, else plain text naming it
  function crossLink(x, cls) {
    return /^https?:/.test(x.href) ? '<a class="' + cls + '" href="' + esc(x.href) + '" target="_blank" rel="noopener">' + esc(x.title) + "</a>"
      : '<span class="' + cls + ' plain">' + esc(x.title) + ' <span class="where">(in the ' + SHOWS + ")</span></span>";
  }

  // ---------- progress, in this browser only ----------
  function load(k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage blocked: progress is not kept */ } }
  var done = load("tl-done", {}), seen = load("tl-seen", {});
  function isDone(l) { return !!done[key(l)]; }
  function setDone(l, v) { if (v) done[key(l)] = 1; else delete done[key(l)]; save("tl-done", done); updateCount(); }
  function seenCount(l) { return Math.min(seen[key(l)] || 0, l.slides || 0); }
  function markSeen(l, n) { if (n > (seen[key(l)] || 0)) { seen[key(l)] = n; save("tl-seen", seen); } }
  function pct(l) { return isDone(l) ? 100 : (l.slides ? Math.round(100 * seenCount(l) / l.slides) : 0); }
  function updateCount() { document.getElementById("done-count").textContent = LESSONS.filter(isDone).length + "/" + LESSONS.length; }

  // ---------- sections: the top menu, and the sidebar that lists one section's items ----------
  var SECTIONS = [
    { id: "courses", label: "Courses", one: "course", ask: "Which course?" },
    { id: "categories", label: "Market categories", one: "market", ask: "Which market?", kind: "categories", prefix: "cat-" },
    { id: "ingredients", label: "Ingredients", one: "ingredient", ask: "Which ingredient?", kind: "ingredients", prefix: "ing-" },
    { id: "topics", label: "Topic type", one: "topic type", ask: "What kind of topic?", kind: "tags", prefix: "tag-" },
  ];
  var SECTION = {}; SECTIONS.forEach(function (s) { SECTION[s.id] = s; });
  // the items of a section: {href, name, n, note}
  function items(sec) {
    if (sec.id === "courses") return LIB.courses.map(function (c) { return { href: c.id, name: c.name, n: c.lessons.length, note: c.description }; });
    var all = (LIB.facets[sec.kind] || []).map(function (f) { return { href: sec.prefix + f.id, name: f.name, n: f.lessons.length }; });
    return sec.id === "ingredients" ? all.sort(function (a, b) { return a.name.localeCompare(b.name); }) : all;
  }
  function sectionOf(h) {
    if (SECTION[h]) return h;
    if (COURSE[h]) return "courses";
    for (var i = 1; i < SECTIONS.length; i++) if (h.indexOf(SECTIONS[i].prefix) === 0) return SECTIONS[i].id;
    if (BY_KEY[h]) return "courses";
    return h === "start" ? "start" : "";
  }
  function topnav(h) {
    var cur = sectionOf(h);
    document.getElementById("topnav").innerHTML = SECTIONS.map(function (s) {
      return '<a href="#' + s.id + '"' + (cur === s.id ? ' aria-current="page"' : "") + ">" + esc(s.label) + "</a>";
    }).join("") + '<a href="#start"' + (cur === "start" ? ' aria-current="page"' : "") + ">Start here</a>";
  }
  function rail(current, sec) {
    if (!sec) return "";
    return '<nav class="rail" aria-label="' + esc(sec.label) + '"><div class="rail-inner"><h4><a href="#' + sec.id + '">' + esc(sec.label) + "</a></h4>" +
      items(sec).map(function (it) { return '<a href="#' + it.href + '"' + (current === it.href ? ' aria-current="page"' : "") + ">" + esc(sec.id === "courses" ? COURSE[it.href].short : it.name) + "<span>" + it.n + "</span></a>"; }).join("") +
      "</div></nav>";
  }
  // a section's own page: every item as a card
  function sectionPage(sec) {
    var its = items(sec);
    return '<div class="hub">' + rail(sec.id, sec) + '<section class="hub-main"><header class="hub-head"><span class="kicker">Explore</span><h1>' + esc(sec.label) + "</h1>" +
      '<p class="lede">' + its.length + " to choose from. Pick one to see its modules.</p></header>" +
      '<div class="cards">' + its.map(function (it) {
        return '<a class="card" href="#' + it.href + '"><b>' + esc(it.name) + "</b><span>" + plural(it.n, "module", "modules") + (it.note ? " · " + esc(it.note) : "") + "</span></a>";
      }).join("") + "</div></section></div>";
  }
  // the home page: ask what to learn, then offer that section's choices
  var exploreBy = "";
  function home() {
    var last = BY_KEY[load("tl-last", "")], sec = SECTION[exploreBy];
    var counts = { courses: plural(LIB.courses.length, "course", "courses"), categories: (LIB.facets.categories || []).length + " markets",
      ingredients: (LIB.facets.ingredients || []).length + " ingredients", topics: (LIB.facets.tags || []).length + " kinds" };
    var ess = essentials().length;
    return '<section class="ask-home"><div class="ask-inner"><span class="kicker">' + plural(LESSONS.length, "module", "modules") + " in " + plural(LIB.courses.length, "course", "courses") + "</span>" +
      "<h1>What do you want to learn?</h1>" +
      '<div class="choices" role="group" aria-label="Learn by">' + SECTIONS.map(function (s) {
        return '<button type="button" class="choice" data-by="' + s.id + '" aria-pressed="' + (exploreBy === s.id) + '"><b>' + esc(s.label) + "</b><span>" + counts[s.id] + "</span></button>";
      }).join("") + "</div>" +
      (sec ? '<div class="step"><label for="pick">' + esc(sec.ask) + '</label><div class="pick-row"><select id="pick"><option value="">Choose a' + (/^[aeiou]/i.test(sec.one) ? "n " : " ") + esc(sec.one) + "…</option>" +
        items(sec).map(function (it) { return '<option value="' + esc(it.href) + '">' + esc(it.name) + " (" + it.n + ")</option>"; }).join("") +
        '</select><a class="btn btn-ghost" href="#' + sec.id + '">See all ' + esc(sec.label.toLowerCase()) + "</a></div></div>" : "") +
      '<p class="quiet">New here? <a href="#start">Start here</a> with the ' + plural(ess, "essential module", "essential modules") + (last ? ', or carry on with <a href="#' + key(last) + '">' + esc(last.title) + "</a>" : "") + ".</p>" +
      "</div></section>";
  }
  // Start here: the Essential modules in course order
  function essentials() { return LESSONS.filter(function (x) { return x.level === "Essential"; }); }
  function snippet(l) {
    var s = String(l.summary || "").replace(/\s*\(slides?[^)]*\)/gi, "").replace(/\*\*/g, "").split(/\n\s*\n/)[0].replace(/\s+/g, " ").trim();
    if (s.length <= 200) return s;
    var cut = s.slice(0, 200), end = Math.max(cut.lastIndexOf(". "), 0);
    return end > 90 ? cut.slice(0, end + 1) : cut.slice(0, cut.lastIndexOf(" ")) + "…";
  }
  function talkRow(l) {
    var c = COURSE[l.course], p = pct(l);
    return '<li class="talk"><a href="#' + key(l) + '"><div class="thumb">' + (l.thumb ? '<img alt="" loading="lazy" src="' + l.thumb + '">' : '<span class="none">No slides</span>') +
      (isDone(l) ? '<span class="tick">✓ Done</span>' : "") + '</div><div class="talk-body"><h3>' + esc(l.title) + " " + level(l) + "</h3>" +
      (snippet(l) ? '<p class="snip">' + esc(snippet(l)) + "</p>" : "") + '<span class="meta">' + [esc(c.short) + " " + l.order, mins(l), l.slides ? l.slides + " slides" : ""].filter(Boolean).join(" · ") + "</span>" +
      (p && !isDone(l) ? '<div class="minibar" title="' + p + '% of the deck seen"><span style="width:' + p + '%"></span></div>' : "") + "</div></a></li>";
  }
  function showsBox(list, title) {
    if (!list || !list.length) return "";
    return '<section class="panel cross"><h2>' + esc(title) + '</h2><ul class="cross-list">' + list.map(function (x) {
      return "<li>" + crossLink(x, "cross-link") + (x.event || x.level ? '<span class="meta">' + [esc(x.event), esc(x.level)].filter(Boolean).join(" · ") + "</span>" : "") + "</li>";
    }).join("") + "</ul></section>";
  }
  function hub(current, kicker, title, lede, lessons, showFilter) {
    var sec = SECTION[sectionOf(current)];
    var list = essentialOnly && showFilter ? lessons.filter(function (l) { return l.level === "Essential"; }) : lessons;
    list = sortBy === "essential" ? list.slice().sort(function (a, b) { return LEVEL_RANK[a.level] - LEVEL_RANK[b.level]; })
         : sortBy === "az" ? list.slice().sort(function (a, b) { return a.title.localeCompare(b.title); }) : list;
    return '<div class="hub' + (sec ? "" : " no-rail") + '">' + rail(current, sec) + '<section class="hub-main"><header class="hub-head"><span class="kicker">' + esc(kicker) + "</span><h1>" + esc(title) + "</h1>" +
      (lede ? '<p class="lede">' + esc(lede) + "</p>" : "") + "</header>" +
      (showFilter ? '<div class="filters"><button type="button" class="chip" id="ess" aria-pressed="' + essentialOnly + '">Essential only</button>' +
        '<span class="meta" style="align-self:center">' + plural(list.length, "module", "modules") + "</span>" +
        '<label class="sort"><span>Sort</span><select id="sort"><option value="list"' + (sortBy === "list" ? " selected" : "") + ">Course order</option>" +
        '<option value="essential"' + (sortBy === "essential" ? " selected" : "") + ">Essential first</option>" +
        '<option value="az"' + (sortBy === "az" ? " selected" : "") + ">A to Z</option></select></label></div>" : "") +
      (list.length ? '<ol class="talks">' + list.map(talkRow).join("") + "</ol>" : '<p class="empty-note">No modules here yet.</p>') + "</section></div>";
  }

  // ---------- a module ----------
  function related(l) {
    var c = COURSE[l.course], i = c.lessons.indexOf(l), next = c.lessons[i + 1] || null;
    var scored = LESSONS.filter(function (x) { return x !== l && x !== next; }).map(function (x) {
      var shared = KINDS.reduce(function (a, k) { var w = k.kind === "ingredients" ? 3 : k.kind === "categories" ? 2 : 1; return a + w * x[k.field].filter(function (t) { return l[k.field].indexOf(t) >= 0; }).length; }, 0);
      return { x: x, s: shared + (x.course === l.course ? 1 : 0) + (x.level === "Essential" ? 1 : 0) - (isDone(x) ? 2 : 0) };
    }).sort(function (a, b) { return b.s - a.s; }).slice(0, 6).map(function (o) { return o.x; });
    return { next: next, more: scored };
  }
  function tile(x) {
    return '<a href="#' + key(x) + '"><div class="thumb">' + (x.thumb ? '<img alt="" src="' + x.thumb + '">' : '<span class="none">No slides</span>') + "</div><b>" +
      esc(x.title.length > 70 ? x.title.slice(0, 68) + "…" : x.title) + "</b><span>" + esc(COURSE[x.course].short) + (x.slides ? " · " + x.slides + " slides" : "") + "</span></a>";
  }
  function exploreHtml(l, noSlides) {
    var r = related(l), first = r.next || r.more[0], more = r.next ? r.more : r.more.slice(1);
    return '<div class="explore" id="explore"><div class="explore-head"><h2>' + (noSlides ? "This module has no slides. Explore related modules" : "Now explore") + "</h2>" +
      (noSlides ? "" : '<button type="button" id="replay">↺ Back to the first slide</button>') + "</div>" +
      (first ? '<a class="up-next" href="#' + key(first) + '"><div class="thumb">' + (first.thumb ? '<img alt="" src="' + first.thumb + '">' : "") + '</div><div><span class="kicker" style="color:var(--lime)">' +
        (r.next ? "Up next in " + esc(COURSE[l.course].short) : "Related") + "</span><br><b>" + esc(first.title) + "</b><br><span>" + esc(mins(first)) + "</span></div></a>" : "") +
      '<div class="explore-grid">' + more.slice(0, 6).map(tile).join("") + "</div></div>";
  }
  function quizHtml(l) {
    if (!l.quiz || !l.quiz.length) return "";
    return '<section class="quiz"><h2>Check your understanding</h2><p class="meta">Answer in your head, then reveal.</p><ol class="quiz-list">' + l.quiz.map(function (q, j) {
      var n = q.slide && q.slide <= l.slides ? q.slide : 0;
      return '<li class="q"><p class="q-text">' + clean(q.q, l, false) + '</p><button type="button" class="btn btn-ghost reveal" aria-expanded="false" aria-controls="ans-' + j + '">Show answer</button>' +
        '<div class="answer" id="ans-' + j + '" hidden><p>' + clean(q.a, l, false) + "</p>" + (n ? '<button type="button" class="slide-ref" data-slide="' + n + '">See slide ' + n + "</button>" : "") + "</div></li>";
    }).join("") + "</ol></section>";
  }
  function lesson(l) {
    var c = COURSE[l.course], i = c.lessons.indexOf(l), next = c.lessons[i + 1];
    var deck = '<section class="deck" id="deck" aria-label="Slides"><div class="deck-inner"><div class="stage" id="stage">' +
      (l.slides ? '<p class="msg">Loading slides…</p><button type="button" class="nav prev" id="prev" aria-label="Previous slide">‹</button><button type="button" class="nav next" id="next" aria-label="Next slide">›</button>'
                : exploreHtml(l, true)) + "</div>" +
      (l.slides ? '<div class="scrub" id="scrub">' + Array.apply(null, Array(l.slides)).map(function (_, j) { return '<button type="button" aria-label="Slide ' + (j + 1) + '"></button>'; }).join("") + "</div>" +
        '<div class="deck-bar"><span><b id="counter">Slide 1 of ' + l.slides + '</b> · <span id="seen"></span></span><span class="grow"></span><span>The training deck</span>' +
        '<button type="button" id="full">Full screen</button></div><div class="thumbs" id="thumbs"></div>' : "") +
      "</div></section>";
    var learn = l.takeaways.map(function (t, j) {
      var n = slideFor(t, l), body = '<span class="n">' + (j + 1) + "</span><span>" + clean(t, l, false) + "</span>";
      return n ? '<button type="button" class="learning" data-slide="' + n + '">' + body + '<span class="go">Show slide ' + n + " →</span></button>"
               : '<div class="learning">' + body + "</div>";
    }).join("");
    var by = [l.owner ? "By <b>" + esc(l.owner) + "</b>" : "", l.version ? "Version " + esc(l.version) : "", l.audience ? "For the " + esc(l.audience) : ""].filter(Boolean).join(" · ");
    var reading = '<article class="reading"><header class="reading-head"><nav class="crumbs"><a href="#home">Home</a><span>/</span><a href="#' + esc(c.id) + '">' + esc(c.short) + "</a></nav>" +
      '<span class="kicker"><a href="#' + esc(c.id) + '">' + esc(c.name) + "</a> · Module " + l.order + " · " + esc(l.level) + "</span><h1>" + esc(l.title) + "</h1>" +
      (by ? '<p class="byline">' + by + "</p>" : "") +
      '<p class="meta">' + [mins(l), l.slides ? l.slides + " slides" : "", l.status === "reviewed" ? "" : "Draft, not yet reviewed"].filter(Boolean).join(" · ") + "</p></header>" +
      (l.summary ? '<section class="lede">' + prose(l.summary, l) + "</section>" : "") +
      (learn ? '<section class="learnings"><h2>Key learnings</h2>' + learn + "</section>" : "") +
      (l.in_practice ? '<section class="panel for-us"><h2>In practice</h2><div class="prose">' + prose(l.in_practice, l) + "</div></section>" : "") +
      quizHtml(l) +
      (l.detail ? '<details class="more"><summary>More detail and figures</summary><div class="prose">' + prose(l.detail, l) + "</div></details>" : "") +
      showsBox(l.related, "Further reading from the shows") +
      '<section class="facets">' + KINDS.map(function (k) {
        var fs = l[k.field].filter(function (id) { return FACET[k.prefix + id]; });
        return fs.length ? '<div class="facet-row"><span class="facet-label">' + k.label + '</span><div class="tags">' + fs.map(function (id) { return '<a class="chip" href="#' + k.prefix + id + '">' + esc(FACET[k.prefix + id].name) + "</a>"; }).join("") + "</div></div>" : "";
      }).join("") + "</section>" +
      '<div class="lesson-foot"><button type="button" class="btn ' + (isDone(l) ? "btn-done" : "btn-ghost") + '" id="mark">' + (isDone(l) ? "✓ Completed" : "Mark as complete") + "</button>" +
      (next ? '<a class="btn btn-primary" href="#' + key(next) + '">Next module →</a>' : '<a class="btn btn-primary" href="#' + esc(c.id) + '">Back to ' + esc(c.short) + "</a>") + "</div></article>";
    return '<div class="lesson">' + deck + reading + "</div>";
  }

  function bindQuiz() {
    [].forEach.call(document.querySelectorAll(".reveal"), function (b) {
      b.onclick = function () {
        var a = document.getElementById(b.getAttribute("aria-controls")), open = a.hidden;
        a.hidden = !open; b.setAttribute("aria-expanded", String(open)); b.textContent = open ? "Hide answer" : "Show answer";
      };
    });
  }
  function bindLesson(l) {
    document.getElementById("mark").onclick = function () { setDone(l, !isDone(l)); route(); };
    bindQuiz();
    if (!l.slides) return;
    var stage = document.getElementById("stage"), slides = [], at = 0, img = document.createElement("img");
    var scrub = [].slice.call(document.querySelectorAll("#scrub button"));
    function paintSeen() {
      var n = seenCount(l);
      scrub.forEach(function (b, j) { b.classList.toggle("seen", j < n); });
      document.getElementById("seen").textContent = n >= l.slides ? "whole deck seen" : n + " of " + l.slides + " seen";
    }
    function closeExplore() { var e = document.getElementById("explore"); if (e) e.remove(); }
    function show(i) {
      if (!slides.length) return;
      closeExplore();
      at = Math.max(0, Math.min(slides.length - 1, i));
      img.src = slides[at]; img.alt = "Slide " + (at + 1) + " of " + slides.length + ": " + l.title;
      document.getElementById("counter").textContent = "Slide " + (at + 1) + " of " + slides.length;
      markSeen(l, at + 1); paintSeen();
      scrub.forEach(function (b, j) { b.setAttribute("aria-current", j === at ? "true" : "false"); });
      [].forEach.call(document.querySelectorAll("#thumbs button"), function (b, j) { b.setAttribute("aria-current", j === at ? "true" : "false"); if (j === at) b.scrollIntoView({ block: "nearest", inline: "nearest" }); });
      [].forEach.call(document.querySelectorAll(".learning[data-slide]"), function (b) { b.classList.toggle("on", +b.getAttribute("data-slide") === at + 1); });
    }
    function explore() {
      closeExplore();
      if (!isDone(l)) setDone(l, true);
      stage.insertAdjacentHTML("beforeend", exploreHtml(l, false));
      document.getElementById("replay").onclick = function () { show(0); };
      var mark = document.getElementById("mark"); mark.className = "btn btn-done"; mark.textContent = "✓ Completed";
    }
    function forward() { if (document.getElementById("explore")) return; if (at >= slides.length - 1) explore(); else show(at + 1); }
    function jump(n) {
      show(n - 1);
      if (window.matchMedia("(max-width: 1000px)").matches) document.getElementById("deck").scrollIntoView({ behavior: "smooth", block: "start" });
    }
    document.getElementById("prev").onclick = function () { show(at - 1); };
    // swipe left or right on the slide to page through on a phone or tablet
    var touchX = null, touchY = null;
    stage.addEventListener("touchstart", function (ev) { if (ev.touches.length === 1) { touchX = ev.touches[0].clientX; touchY = ev.touches[0].clientY; } }, { passive: true });
    stage.addEventListener("touchend", function (ev) {
      if (touchX === null) return;
      var dx = ev.changedTouches[0].clientX - touchX, dy = ev.changedTouches[0].clientY - touchY;
      touchX = null;
      if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.5) { if (dx < 0) forward(); else show(at - 1); }
    }, { passive: true });
    document.getElementById("next").onclick = forward;
    scrub.forEach(function (b, j) { b.onclick = function () { show(j); }; });
    document.getElementById("full").onclick = function () {
      var d = document.getElementById("deck");
      try { if (document.fullscreenElement) document.exitFullscreen(); else if (d.requestFullscreen) d.requestFullscreen().catch(function () {}); } catch (e) { /* not available here */ }
    };
    app.onclick = function (ev) {
      var b = ev.target.closest && ev.target.closest("[data-slide]");
      if (b && !b.closest("#scrub")) jump(+b.getAttribute("data-slide"));
    };
    document.onkeydown = function (ev) {
      if (/INPUT|TEXTAREA|SELECT/.test((ev.target || {}).tagName || "")) return;
      if (ev.key === "ArrowRight") forward(); else if (ev.key === "ArrowLeft") show(at - 1);
    };
    paintSeen();
    fetch("slides/" + key(l) + ".json").then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (d) {
      slides = d.slides || [];
      stage.querySelector(".msg").remove(); stage.insertBefore(img, stage.firstChild);
      document.getElementById("thumbs").innerHTML = slides.map(function (s, j) { return '<button type="button" aria-label="Slide ' + (j + 1) + '"><img alt="" loading="lazy" src="' + s + '"></button>'; }).join("");
      [].forEach.call(document.querySelectorAll("#thumbs button"), function (b, j) { b.onclick = function () { show(j); }; });
      show(0);
    }).catch(function () { var m = stage.querySelector(".msg"); if (m) m.textContent = "The slides could not be loaded. Reload the page to try again."; });
  }

  // ---------- routing ----------
  function route() {
    var h = decodeURIComponent((location.hash || "#home").slice(1)) || "home", html, l = BY_KEY[h];
    document.onkeydown = null; app.onclick = null;
    if (l) html = lesson(l);
    else if (h === "start") html = hub(h, "Start here", "Essential modules", "The modules every new colleague should take first, in course order.", essentials(), false);
    else if (h === "my-learning") html = hub(h, "Your progress", "My learning", LESSONS.filter(isDone).length + " of " + LESSONS.length + " modules completed in this browser.", LESSONS.filter(isDone), false);
    else if (FACET[h]) {
      var f = FACET[h];
      html = hub(h, f.label, f.name, plural(f.lessons.length, "module", "modules") + " on this topic.", f.lessons.map(function (k) { return BY_KEY[k]; }).filter(Boolean), true);
    } else if (SECTION[h]) {
      html = sectionPage(SECTION[h]);
    } else if (COURSE[h]) {
      var c = COURSE[h];
      html = hub(h, "Course", c.name, (c.description ? c.description + " " : "") + plural(c.lessons.length, "module", "modules") + ".", c.lessons, true);
    } else if (h.indexOf("search-") === 0) {
      var q = h.slice(7).replace(/-/g, " "), words = q.split(/\s+/).filter(Boolean);
      var hits = LESSONS.filter(function (x) {
        var hay = [x.title, x.owner, x.summary, x.takeaways.join(" "), (x.ingredient_words || []).join(" "), COURSE[x.course].name].join(" ").toLowerCase();
        return words.every(function (w) { return hay.indexOf(w) >= 0; });
      });
      html = hub(h, "Search", "“" + q + "”", hits.length + (hits.length === 1 ? " module matches." : " modules match."), hits, false);
    } else { h = "home"; html = home(); }
    app.innerHTML = html;
    topnav(h);
    window.scrollTo(0, 0);
    if (l) { bindLesson(l); save("tl-last", h); document.title = l.title + " · Training library"; }
    else document.title = "Training library";
    var ess = document.getElementById("ess");
    if (ess) ess.onclick = function () { essentialOnly = !essentialOnly; route(); };
    [].forEach.call(document.querySelectorAll(".choice"), function (b) {
      b.onclick = function () { exploreBy = b.getAttribute("data-by"); route(); var p = document.getElementById("pick"); if (p) p.focus(); };
    });
    var pick = document.getElementById("pick");
    if (pick) pick.onchange = function () { if (pick.value) location.hash = pick.value; };
    var sel = document.getElementById("sort");
    if (sel) sel.onchange = function () { sortBy = sel.value; route(); };
  }

  document.getElementById("search-form").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = document.getElementById("q").value.trim().toLowerCase().replace(/[^a-z0-9 ]+/g, " ").trim();
    location.hash = q ? "search-" + q.replace(/\s+/g, "-") : "home";
  });
  window.addEventListener("hashchange", route);

  fetch("data/library.json").then(function (r) { return r.json(); }).then(function (lib) {
    LIB = lib;
    lib.courses.forEach(function (c) { COURSE[c.id] = c; c.lessons.forEach(function (x) { x.course = x.course || c.id; LESSONS.push(x); BY_KEY[key(x)] = x; }); });
    KINDS.forEach(function (k) { (lib.facets[k.kind] || []).forEach(function (f) { FACET[k.prefix + f.id] = { name: f.name, lessons: f.lessons, label: k.label }; }); });
    document.getElementById("stamp").textContent = "Updated " + fmtDate(lib.built);
    updateCount();
    route();
  }).catch(function () { app.innerHTML = '<p class="loading">The library could not be loaded. Reload the page to try again.</p>'; });
})();

/* Show Learning Library, field guide edition. Data: data/library.json (non-confidential talks only, built by
   `python -m confnotes team`) and slides/<event>--<session>.json (each talk's slide images). Progress lives in this browser. */
(function () {
  "use strict";
  var LIB = null, LESSONS = [], BY_KEY = {}, COURSE = {};
  // the three kinds of tag (data/facets.yaml): route prefix, heading, field on a talk
  var KINDS = [{ kind: "categories", prefix: "cat-", label: "Market categories", field: "categories" },
               { kind: "ingredients", prefix: "ing-", label: "Ingredients", field: "ingredients" },
               { kind: "tags", prefix: "tag-", label: "Insight type", field: "tags" }];
  var FACET = {};  // "cat-glp1" -> { name, lessons, kind }
  var app = document.getElementById("app");
  var essentialOnly = false;
  var pendingSlide = 0;   // a slide to open when a talk loads (links from the assistant)

  // ---------- helpers ----------
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function key(l) { return l.event + "--" + l.id; }
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fmtDate(d) { if (!d) return ""; var p = d.split("-"); return (+p[2]) + " " + MONTHS[+p[1] - 1] + " " + p[0]; }
  function shortDate(d) { if (!d) return ""; var p = d.split("-"); return (+p[2]) + " " + MONTHS[+p[1] - 1]; }
  function names(l, max) {
    var s = (l.speakers || []).filter(function (p) { return p.name; }).map(function (p) { return p.name; });
    if (!s.length) return "Speaker to confirm";
    return max && s.length > max ? s.slice(0, max).join(", ") + " and " + (s.length - max) + " more" : s.join(", ");
  }
  function byline(l) {
    var s = (l.speakers || []).filter(function (p) { return p.name; });
    if (!s.length) return "<span>Speaker to confirm</span>";
    return s.slice(0, 4).map(function (p) { return "<b>" + esc(p.name) + "</b>" + (p.organisation ? ", " + esc(p.organisation) : ""); }).join(" · ") +
      (s.length > 4 ? " · and " + (s.length - 4) + " more" : "");
  }
  function level(l) { return '<span class="level level-' + esc(l.level) + '">' + esc(l.level) + "</span>"; }
  function slideFor(text, l) {
    if (!l.slides) return 0;
    var re = l.slide_source === "deck" ? /\(slides? (\d+)\)/i : /\(photos? (\d+)\)/i, m = re.exec(text);
    return m && +m[1] <= l.slides ? +m[1] : 0;
  }
  // Source references for the team: timestamps and (notes) go; (slide N) / (photo N) become small buttons, or nothing
  // when asked (learnings carry their slide on the whole row); a lesson id in brackets becomes a link to that talk.
  function clean(text, l, refs) {
    var t = esc(text);
    t = t.replace(/\s*\[(\d{1,2}:)?\d{1,2}:\d{2}\](,\s*\[(\d{1,2}:)?\d{1,2}:\d{2}\])*/g, "").replace(/\s*\((notes|otter)\)/gi, "");
    t = t.replace(/\s*\((slide|photo)s? (\d+)\)/gi, function (m, kind, n) {
      var ok = refs && l.slides && +n <= l.slides && ((kind.toLowerCase() === "slide") === (l.slide_source === "deck"));
      return ok ? ' <button type="button" class="slide-ref" data-slide="' + n + '">slide ' + n + "</button>" : "";
    });
    t = t.replace(/\(([a-z0-9]+(?:-[a-z0-9]+){2,})\)/g, function (m, id) {
      var hit = LESSONS.filter(function (x) { return x.id === id; })[0];
      return hit ? '(see <a href="#' + key(hit) + '">' + esc(hit.title) + "</a>)" : "";
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

  // ---------- progress, in this browser only ----------
  function load(k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage blocked: progress is not kept */ } }
  var done = load("sll-done", {}), seen = load("sll-seen", {});
  function isDone(l) { return !!done[key(l)]; }
  function setDone(l, v) { if (v) done[key(l)] = 1; else delete done[key(l)]; save("sll-done", done); updateCount(); }
  function seenCount(l) { return Math.min(seen[key(l)] || 0, l.slides || 0); }
  function markSeen(l, n) { if (n > (seen[key(l)] || 0)) { seen[key(l)] = n; save("sll-seen", seen); } }
  function pct(l) { return isDone(l) ? 100 : (l.slides ? Math.round(100 * seenCount(l) / l.slides) : 0); }
  function updateCount() { document.getElementById("done-count").textContent = LESSONS.filter(isDone).length + "/" + LESSONS.length; }

  // ---------- the hub ----------
  function rail(current) {
    function item(href, label, n) { return '<a href="#' + href + '"' + (current === href ? ' aria-current="page"' : "") + ">" + esc(label) + "<span>" + n + "</span></a>"; }
    return '<nav class="rail" aria-label="Browse"><div class="rail-inner">' +
      item("home", "All talks", LESSONS.length) + item("essentials", "Essential", LESSONS.filter(function (l) { return l.level === "Essential"; }).length) +
      item("my-learning", "My learning", LESSONS.filter(isDone).length) +
      KINDS.map(function (k) {
        var all = LIB.facets[k.kind] || [], top = k.kind === "ingredients" ? all.slice().sort(function (a, b) { return b.lessons.length - a.lessons.length; }).slice(0, 10) : all;
        return "<h4>" + k.label + "</h4>" + top.map(function (f) { return item(k.prefix + f.id, f.name, f.lessons.length); }).join("") +
          (top.length < all.length ? item("ingredients", "All " + all.length + " ingredients", "→") : "");
      }).join("") +
      "<h4>Shows</h4>" + LIB.courses.map(function (c) { return item(c.id, c.short, c.lessons.length); }).join("") + "</div></nav>";
  }
  function talkRow(l) {
    var c = COURSE[l.event], p = pct(l);
    return '<li class="talk"><a href="#' + key(l) + '"><div class="thumb">' + (l.thumb ? '<img alt="" loading="lazy" src="' + l.thumb + '">' : '<span class="none">No slides</span>') +
      (isDone(l) ? '<span class="tick">✓ Done</span>' : "") + '</div><div class="talk-body"><h3>' + esc(l.title) + " " + level(l) + "</h3>" +
      '<span class="meta">' + esc(names(l, 3)) + "</span>" + '<span class="meta">' + esc(c.short) + " · " + esc(shortDate(l.date)) + (l.slides ? " · " + l.slides + " slides" : "") + "</span>" +
      (p && !isDone(l) ? '<div class="minibar" title="' + p + '% of the deck seen"><span style="width:' + p + '%"></span></div>' : "") + "</div></a></li>";
  }
  function hub(current, kicker, title, lede, lessons, showFilter) {
    var list = essentialOnly && showFilter ? lessons.filter(function (l) { return l.level === "Essential"; }) : lessons;
    return '<div class="hub">' + rail(current) + '<section class="hub-main"><header class="hub-head"><span class="kicker">' + esc(kicker) + "</span><h1>" + esc(title) + "</h1>" +
      (lede ? '<p class="lede">' + esc(lede) + "</p>" : "") + "</header>" +
      (showFilter ? '<div class="filters"><button type="button" class="chip" id="ess" aria-pressed="' + essentialOnly + '">Essential only</button>' +
        '<span class="meta" style="align-self:center">' + list.length + (list.length === 1 ? " talk" : " talks") + "</span></div>" : "") +
      (list.length ? '<ol class="talks">' + list.map(talkRow).join("") + "</ol>" : '<p class="empty-note">No talks here yet.</p>') + "</section></div>";
  }
  function ordered(ls) { return ls.slice().sort(function (a, b) { return (b.date || "").localeCompare(a.date || "") || (a.start || "").localeCompare(b.start || ""); }); }

  // ---------- a talk ----------
  function related(l) {
    var c = COURSE[l.event], i = c.lessons.indexOf(l), next = c.lessons[i + 1] || null;
    var scored = LESSONS.filter(function (x) { return x !== l && x !== next; }).map(function (x) {
      var shared = KINDS.reduce(function (a, k) { var w = k.kind === "categories" ? 3 : k.kind === "ingredients" ? 2 : 1; return a + w * x[k.field].filter(function (t) { return l[k.field].indexOf(t) >= 0; }).length; }, 0);
      return { x: x, s: shared + (x.event === l.event ? 1 : 0) + (x.level === "Essential" ? 1 : 0) + (x.thumb ? 1 : 0) - (isDone(x) ? 2 : 0) };
    }).sort(function (a, b) { return b.s - a.s; }).slice(0, 6).map(function (o) { return o.x; });
    return { next: next, more: scored };
  }
  function tile(x) {
    return '<a href="#' + key(x) + '"><div class="thumb">' + (x.thumb ? '<img alt="" src="' + x.thumb + '">' : '<span class="none">No slides</span>') + "</div><b>" +
      esc(x.title.length > 70 ? x.title.slice(0, 68) + "…" : x.title) + "</b><span>" + esc(COURSE[x.event].short) + (x.slides ? " · " + x.slides + " slides" : "") + "</span></a>";
  }
  function exploreHtml(l, noSlides) {
    var r = related(l), first = r.next || r.more[0], more = r.next ? r.more : r.more.slice(1);
    return '<div class="explore" id="explore"><div class="explore-head"><h2>' + (noSlides ? "No slides were shared for this talk. Explore related talks" : "Now explore") + "</h2>" +
      (noSlides ? "" : '<button type="button" id="replay">↺ Back to the first slide</button>') + "</div>" +
      (first ? '<a class="up-next" href="#' + key(first) + '"><div class="thumb">' + (first.thumb ? '<img alt="" src="' + first.thumb + '">' : "") + '</div><div><span class="kicker" style="color:var(--lime)">' +
        (r.next ? "Up next in " + esc(COURSE[l.event].short) : "Related") + "</span><br><b>" + esc(first.title) + "</b><br><span>" + esc(names(first, 2)) + "</span></div></a>" : "") +
      '<div class="explore-grid">' + more.slice(0, 6).map(tile).join("") + "</div></div>";
  }
  function lesson(l) {
    var c = COURSE[l.event], i = c.lessons.indexOf(l), next = c.lessons[i + 1];
    var deck = '<section class="deck" id="deck" aria-label="Slides"><div class="deck-inner"><div class="stage" id="stage">' +
      (l.slides ? '<p class="msg">Loading slides…</p><button type="button" class="nav prev" id="prev" aria-label="Previous slide">‹</button><button type="button" class="nav next" id="next" aria-label="Next slide">›</button>'
                : exploreHtml(l, true)) + "</div>" +
      (l.slides ? '<div class="scrub" id="scrub">' + Array.apply(null, Array(l.slides)).map(function (_, j) { return '<button type="button" aria-label="Slide ' + (j + 1) + '"></button>'; }).join("") + "</div>" +
        '<div class="deck-bar"><span><b id="counter">Slide 1 of ' + l.slides + '</b> · <span id="seen"></span></span><span class="grow"></span><span>' +
        (l.slide_source === "deck" ? "The speaker's deck" : "Photos taken in the room") + '</span><button type="button" id="full">Full screen</button></div><div class="thumbs" id="thumbs"></div>' : "") +
      "</div></section>";
    var learn = l.takeaways.map(function (t, j) {
      var n = slideFor(t, l), body = '<span class="n">' + (j + 1) + "</span><span>" + clean(t, l, false) + "</span>";
      return n ? '<button type="button" class="learning" data-slide="' + n + '">' + body + '<span class="go">Show slide ' + n + " →</span></button>"
               : '<div class="learning">' + body + "</div>";
    }).join("");
    var reading = '<article class="reading"><header class="reading-head"><nav class="crumbs"><a href="#home">All talks</a><span>/</span><a href="#' + esc(c.id) + '">' + esc(c.short) + "</a></nav>" +
      '<span class="kicker">' + esc(c.short) + " · " + esc(l.level) + "</span><h1>" + esc(l.title) + '</h1><p class="byline">' + byline(l) + "</p>" +
      '<p class="meta">' + esc(fmtDate(l.date)) + (l.start ? ", " + esc(l.start) : "") + (l.slides ? " · " + l.slides + " slides" : "") + "</p></header>" +
      (l.summary ? '<section class="lede">' + prose(l.summary, l) + "</section>" : "") +
      (learn ? '<section class="learnings"><h2>Key learnings</h2>' + learn + "</section>" : "") +
      (l.for_us ? '<section class="panel for-us"><h2>What it means for Vita Actives</h2><div class="prose">' + prose(l.for_us, l) + "</div></section>" : "") +
      (l.quotes.length ? '<section class="panel"><h2>In their words</h2>' + l.quotes.map(function (q) { return '<blockquote class="quote">' + clean(q, l, false) + "</blockquote>"; }).join("") + "</section>" : "") +
      (l.detail ? '<details class="more"><summary>More detail and figures</summary><div class="prose">' + prose(l.detail, l) + "</div></details>" : "") +
      '<section class="facets">' + KINDS.map(function (k) {
        var fs = l[k.field].filter(function (id) { return FACET[k.prefix + id]; });
        return fs.length ? '<div class="facet-row"><span class="facet-label">' + k.label + '</span><div class="tags">' + fs.map(function (id) { return '<a class="chip" href="#' + k.prefix + id + '">' + esc(FACET[k.prefix + id].name) + "</a>"; }).join("") + "</div></div>" : "";
      }).join("") + "</section>" +
      '<div class="lesson-foot"><button type="button" class="btn ' + (isDone(l) ? "btn-done" : "btn-ghost") + '" id="mark">' + (isDone(l) ? "✓ Completed" : "Mark as complete") + "</button>" +
      (next ? '<a class="btn btn-primary" href="#' + key(next) + '">Next talk →</a>' : '<a class="btn btn-primary" href="#' + esc(c.id) + '">Back to ' + esc(c.short) + "</a>") + "</div></article>";
    return '<div class="lesson">' + deck + reading + "</div>";
  }

  function bindLesson(l) {
    document.getElementById("mark").onclick = function () { setDone(l, !isDone(l)); route(); };
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
      if (/INPUT|TEXTAREA/.test((ev.target || {}).tagName || "")) return;
      if (ev.key === "ArrowRight") forward(); else if (ev.key === "ArrowLeft") show(at - 1);
    };
    paintSeen();
    fetch("slides/" + key(l) + ".json").then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (d) {
      slides = d.slides || [];
      stage.querySelector(".msg").remove(); stage.insertBefore(img, stage.firstChild);
      document.getElementById("thumbs").innerHTML = slides.map(function (s, j) { return '<button type="button" aria-label="Slide ' + (j + 1) + '"><img alt="" loading="lazy" src="' + s + '"></button>'; }).join("");
      [].forEach.call(document.querySelectorAll("#thumbs button"), function (b, j) { b.onclick = function () { show(j); }; });
      show(pendingSlide ? pendingSlide - 1 : 0); pendingSlide = 0;
    }).catch(function () { var m = stage.querySelector(".msg"); if (m) m.textContent = "The slides could not be loaded. Reload the page to try again."; });
  }

  // ---------- routing ----------
  function route() {
    var h = decodeURIComponent((location.hash || "#home").slice(1)) || "home", html, l = BY_KEY[h];
    document.onkeydown = null; app.onclick = null;
    var nSlides = LESSONS.reduce(function (a, x) { return a + (x.slides || 0); }, 0);
    if (l) html = lesson(l);
    else if (h === "essentials") html = hub(h, "Start here", "Essential talks", "The talks that matter most to our range and customers, across all three shows.", ordered(LESSONS.filter(function (x) { return x.level === "Essential"; })), false);
    else if (h === "my-learning") html = hub(h, "Your progress", "My learning", LESSONS.filter(isDone).length + " of " + LESSONS.length + " talks completed in this browser.", ordered(LESSONS.filter(isDone)), false);
    else if (FACET[h]) {
      var f = FACET[h];
      html = hub(h, f.label, f.name, f.lessons.length + (f.lessons.length === 1 ? " talk" : " talks") + " across the shows.", ordered(f.lessons.map(function (k) { return BY_KEY[k]; }).filter(Boolean)), true);
    } else if (h === "ingredients") {
      html = '<div class="hub">' + rail(h) + '<section class="hub-main"><header class="hub-head"><span class="kicker">Ingredients</span><h1>All ingredients</h1><p class="lede">Every ingredient discussed in a talk, grouped. Pick one to see the talks.</p></header><div class="filters">' +
        LIB.facets.ingredients.map(function (f) { return '<a class="chip" href="#ing-' + f.id + '">' + esc(f.name) + " · " + f.lessons.length + "</a>"; }).join("") + "</div></section></div>";
    } else if (COURSE[h]) {
      var c = COURSE[h];
      html = hub(h, "Show · " + (c.city || ""), c.name, c.lessons.length + " talks, " + (c.start === c.end || !c.end ? fmtDate(c.start) : shortDate(c.start) + " to " + fmtDate(c.end)) + ".", c.lessons, true);
    } else if (h.indexOf("search-") === 0) {
      var q = h.slice(7).replace(/-/g, " "), words = q.split(/\s+/).filter(Boolean);
      var hits = LESSONS.filter(function (x) {
        var hay = [x.title, names(x), x.summary, x.takeaways.join(" "), (x.ingredients || []).join(" "), COURSE[x.event].name].join(" ").toLowerCase();
        return words.every(function (w) { return hay.indexOf(w) >= 0; });
      });
      html = hub(h, "Search", "“" + q + "”", hits.length + (hits.length === 1 ? " talk matches." : " talks match."), ordered(hits), false);
    } else html = hub("home", "Autumn 2026 · three shows", "What we learned at the shows",
      LESSONS.length + " talks and " + nSlides + " slides from Remedy CDMO, SANS Europe and the Nutra Healthspan Summit. Browse by market, ingredient or kind of insight, or start with the essentials.", ordered(LESSONS), true);
    app.innerHTML = html;
    window.scrollTo(0, 0);
    if (l) { bindLesson(l); save("sll-last", h); document.title = l.title + " · Show Learning Library"; }
    else document.title = "Show Learning Library";
    var ess = document.getElementById("ess");
    if (ess) ess.onclick = function () { essentialOnly = !essentialOnly; route(); };
  }

  document.getElementById("search-form").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = document.getElementById("q").value.trim().toLowerCase().replace(/[^a-z0-9 ]+/g, " ").trim();
    location.hash = q ? "search-" + q.replace(/\s+/g, "-") : "home";
  });
  window.addEventListener("hashchange", route);

  // ---------- Ask the library: Claude answers from the talks' notes (sample capability) ----------
  // The page picks the most relevant talks by word match and sends their notes; Claude answers only from them and cites
  // talks as [[event--session]] or [[event--session#slide]]. Only non-confidential talks are in this page at all.
  var STOP = "a an and are as at be by can did do does for from has have how i in is it its me of on or our should so that the their them there these this to was we what when where which who why will with would you about any most".split(" ");
  function words(s) { return String(s || "").toLowerCase().replace(/[^a-z0-9+\- ]+/g, " ").split(/\s+/).filter(function (w) { return w.length > 2 && STOP.indexOf(w) < 0; }); }
  function facetNames(l) {
    return KINDS.map(function (k) { return l[k.field].map(function (id) { var f = FACET[k.prefix + id]; return f ? f.name : ""; }).join(", "); }).join(" | ");
  }
  function haystack(l) { return [l.title, names(l), l.summary, l.takeaways.join(" "), l.for_us, facetNames(l), COURSE[l.event].name].join(" ").toLowerCase(); }
  function relevant(question, current) {
    var ws = words(question);
    var scored = LESSONS.map(function (l) {
      var hay = haystack(l), title = (l.title + " " + facetNames(l)).toLowerCase(), s = 0;
      ws.forEach(function (w) { if (hay.indexOf(w) >= 0) s += 1 + (hay.split(w).length - 2) * 0.2; if (title.indexOf(w) >= 0) s += 2; });
      if (l === current) s += 6;
      return { l: l, s: s };
    }).filter(function (o) { return o.s > 0; }).sort(function (a, b) { return b.s - a.s; });
    return scored.slice(0, 7).map(function (o) { return o.l; });
  }
  function plain(text) { return String(text || "").replace(/\s*\[(\d{1,2}:)?\d{1,2}:\d{2}\]/g, "").replace(/\s*\((notes|otter)\)/gi, ""); }
  function notesFor(l) {
    return "### [[" + key(l) + "]] " + l.title + "\nShow: " + COURSE[l.event].name + ", " + fmtDate(l.date) + ". Speakers: " + names(l) + ". Level: " + l.level + ".\n" +
      "Tags: " + facetNames(l) + "\nSlides: " + (l.slides ? l.slides + " (" + (l.slide_source === "deck" ? "the speaker's deck; cite as #N" : "photos; cite photo N as #N") + ")" : "none") + "\n" +
      "Summary:\n" + plain(l.summary).slice(0, 2500) + "\nKey learnings:\n" + l.takeaways.map(function (x) { return "- " + plain(x); }).join("\n") +
      "\nWhat it means for Vita Actives:\n" + plain(l.for_us).slice(0, 2500) + (l.detail ? "\nMore detail:\n" + plain(l.detail).slice(0, 3500) : "");
  }
  var RULES = "You answer questions from the Vita Actives team about talks at the autumn 2026 shows (Remedy CDMO, SANS Europe, " +
    "the Nutra Healthspan Summit). Vita Actives supplies nutraceutical ingredients (CreaWin creatine, IsoClr: Pea clear pea protein, Oxystorm).\n" +
    "Rules:\n- Answer ONLY from the talk notes given in each message. If they do not cover the question, say so plainly and suggest which talks come closest.\n" +
    "- Every fact or figure carries its source: write [[event--session]] right after it, or [[event--session#N]] when a slide number is given in the notes " +
    "(slide N, or photo N for talks whose slides are photos). Use only keys that appear in the notes.\n" +
    "- Figures exactly as in the notes. Health claims and forecasts are the speaker's: keep their hedge (\"may\" never becomes \"will\").\n" +
    "- Where speakers' figures differ, give both, each with its source.\n" +
    "- Lines marked \"my reading\" in the notes are the note-taker's interpretation; say so if you use them.\n" +
    "- Short and direct, British English: a two-sentence answer, then up to five bullets if useful. No headings. No preamble.";
  var chat = [], asking = null;
  function linkify(text) {
    var t = esc(text);
    t = t.replace(/\[\[([a-z0-9-]+--[a-z0-9-]+)(?:#(\d+))?\]\]/g, function (m, k, n) {
      var l = BY_KEY[k];
      if (!l) return "";
      return ' <a class="cite-link" href="#' + k + '" data-slide-jump="' + (n || "") + '">' + esc(l.title.length > 42 ? l.title.slice(0, 40) + "…" : l.title) + (n ? ", slide " + n : "") + "</a>";
    });
    t = t.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    var out = [], list = false;
    t.split("\n").forEach(function (line) {
      var m = /^\s*[-*•]\s+(.*)$/.exec(line);
      if (m) { if (!list) { out.push("<ul>"); list = true; } out.push("<li>" + m[1] + "</li>"); return; }
      if (list) { out.push("</ul>"); list = false; }
      if (line.trim()) out.push("<p>" + line + "</p>");
    });
    if (list) out.push("</ul>");
    return out.join("");
  }
  function setupAsk(sample) {
    var fab = document.createElement("button");
    fab.type = "button"; fab.className = "ask-fab"; fab.id = "ask-open"; fab.innerHTML = "<span>Ask the library</span>";
    var panel = document.createElement("aside");
    panel.className = "ask-panel"; panel.id = "ask-panel"; panel.hidden = true; panel.setAttribute("aria-label", "Ask the library");
    panel.innerHTML = '<header class="ask-head"><div><b>Ask the library</b><span id="ask-scope">Answers come only from the talks in this library, with links to each source.</span></div>' +
      '<button type="button" class="ask-x" id="ask-close" aria-label="Close">×</button></header><div class="ask-log" id="ask-log"></div>' +
      '<form class="ask-form" id="ask-form"><label class="sr-only" for="ask-q">Your question</label><textarea id="ask-q" rows="2" placeholder="e.g. What did speakers say about creatine for women?"></textarea>' +
      '<div class="ask-actions"><button type="button" class="btn btn-ghost" id="ask-new">New chat</button><button type="button" class="btn btn-ghost" id="ask-stop" hidden>Stop</button><button type="submit" class="btn btn-primary" id="ask-send">Ask</button></div>' +
      '<p class="ask-note">Uses your own Claude usage. Claude can make mistakes: check the linked talks.</p></form>';
    document.body.appendChild(fab); document.body.appendChild(panel);
    var log = panel.querySelector("#ask-log"), q = panel.querySelector("#ask-q");
    var SUGGEST = ["What did speakers say about creatine beyond the gym?", "What is happening to whey prices, and what does it mean for pea protein?",
      "What do GLP-1 users need from supplements?", "Which talks matter most for our healthy-ageing pitches?"];
    function intro() {
      log.innerHTML = '<div class="ask-hello"><p>Ask anything about the talks. Try:</p>' + SUGGEST.map(function (s) { return '<button type="button" class="chip ask-sug">' + esc(s) + "</button>"; }).join("") + "</div>";
      [].forEach.call(log.querySelectorAll(".ask-sug"), function (b) { b.onclick = function () { q.value = b.textContent; send(); }; });
    }
    function open() { panel.hidden = false; fab.hidden = true; var l = BY_KEY[decodeURIComponent(location.hash.slice(1))];
      panel.querySelector("#ask-scope").textContent = l ? "Looking first at “" + l.title + "”, then the whole library." : "Answers come only from the talks in this library, with links to each source.";
      if (!log.children.length) intro(); q.focus(); }
    function close() { panel.hidden = true; fab.hidden = false; if (asking) asking.abort(); }
    fab.onclick = open; panel.querySelector("#ask-close").onclick = close;
    panel.querySelector("#ask-new").onclick = function () { if (asking) asking.abort(); chat = []; log.innerHTML = ""; intro(); };
    panel.querySelector("#ask-stop").onclick = function () { if (asking) asking.abort(); };
    q.addEventListener("keydown", function (ev) { if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); send(); } });
    panel.querySelector("#ask-form").addEventListener("submit", function (ev) { ev.preventDefault(); send(); });
    log.addEventListener("click", function (ev) {
      var a = ev.target.closest && ev.target.closest("a.cite-link");
      if (!a) return;
      pendingSlide = +a.getAttribute("data-slide-jump") || 0;
      if (a.getAttribute("href") === location.hash) { ev.preventDefault(); route(); }
      if (window.matchMedia("(max-width: 700px)").matches) close();
    });
    function bubble(cls, html) { var d = document.createElement("div"); d.className = "ask-msg " + cls; d.innerHTML = html; log.appendChild(d); log.scrollTop = log.scrollHeight; return d; }
    function send() {
      var question = q.value.trim();
      if (!question || asking) return;
      if (log.querySelector(".ask-hello")) log.innerHTML = "";
      q.value = "";
      bubble("me", "<p>" + esc(question) + "</p>");
      var current = BY_KEY[decodeURIComponent(location.hash.slice(1))] || null;
      var pool = relevant(question + " " + chat.filter(function (m) { return m.role === "user"; }).slice(-1).map(function (m) { return m.q; }).join(" "), current);
      var catalogue = LESSONS.map(function (l) { return "[[" + key(l) + "]] " + l.title + " (" + COURSE[l.event].short + "; " + facetNames(l).replace(/ \| /g, "; ") + ")"; }).join("\n");
      var content = "Question: " + question + "\n\nTalk notes for this question (the most relevant talks):\n\n" +
        (pool.length ? pool.map(notesFor).join("\n\n") : "(no talk matched the question's words)") + "\n\nEvery talk in the library, for pointing to others:\n" + catalogue;
      var turns = [{ role: "user", content: RULES }].concat(chat.slice(-4).map(function (m) { return { role: m.role, content: m.role === "user" ? "Earlier question: " + m.q : m.content }; }), [{ role: "user", content: content }]);
      var out = bubble("claude", '<p class="ask-wait">Reading ' + (pool.length || "the") + " talks…</p>");
      var stop = panel.querySelector("#ask-stop"), sendBtn = panel.querySelector("#ask-send");
      asking = new AbortController(); stop.hidden = false; sendBtn.disabled = true;
      sample(turns, { signal: asking.signal, cache: false, onText: function (u) { out.innerHTML = linkify(u.text); log.scrollTop = log.scrollHeight; } })
        .then(function (r) {
          out.innerHTML = linkify(r.text) + (r.truncated ? '<p class="ask-err">The answer was cut short. Ask a narrower question.</p>' : "");
          chat.push({ role: "user", q: question, content: content }); chat.push({ role: "assistant", content: r.text });
        })
        .catch(function (e) {
          var msg = { not_granted: "Asking Claude was not allowed for this page, so this feature is off.", sampling_disabled: "Claude isn't available on this account.",
            rate_limited: "Too many questions at once, or your Claude usage limit is reached. Try again a little later.", session_expired: "Please sign in to Claude again.",
            refused: "Claude declined that question. Try rewording it.", cancelled: "" }[e.code];
          if (msg == null) msg = "Something went wrong. Ask again.";
          out.innerHTML = (e.text && e.code !== "refused" ? linkify(e.text) : "") + (msg ? '<p class="ask-err">' + esc(msg) + "</p>" : '<p class="ask-err">Stopped.</p>');
          if (e.code === "not_granted" || e.code === "sampling_disabled") { fab.remove(); }
        })
        .then(function () { asking = null; stop.hidden = true; sendBtn.disabled = false; });
    }
  }
  if (window.claude && window.claude.use) {
    window.claude.use("sample").then(function (sample) { if (sample) { var go = function () { if (LIB) setupAsk(sample); else setTimeout(go, 200); }; go(); } }).catch(function () {});
  }


  fetch("data/library.json").then(function (r) { return r.json(); }).then(function (lib) {
    LIB = lib;
    lib.courses.forEach(function (c) { COURSE[c.id] = c; c.lessons.forEach(function (x) { LESSONS.push(x); BY_KEY[key(x)] = x; }); });
    KINDS.forEach(function (k) { (lib.facets[k.kind] || []).forEach(function (f) { FACET[k.prefix + f.id] = { name: f.name, lessons: f.lessons, label: k.label }; }); });
    document.getElementById("stamp").textContent = "Updated " + fmtDate(lib.built);
    updateCount();
    route();
  }).catch(function () { app.innerHTML = '<p class="loading">The library could not be loaded. Reload the page to try again.</p>'; });
})();

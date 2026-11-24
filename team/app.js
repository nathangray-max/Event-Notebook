/* Show Learning Library: the team's view of the conference notes. Data: data/library.json (non-confidential lessons
   only, built by `python -m confnotes team`) and slides/<event>--<session>.json (each lesson's slide images). */
(function () {
  "use strict";
  var LIB = null, LESSONS = [], BY_KEY = {}, TOPIC = {};
  var app = document.getElementById("app");

  // ---------- small helpers ----------
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function key(l) { return l.event + "--" + l.id; }
  function fmtDate(d) {
    if (!d) return "";
    var p = d.split("-"), m = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return (+p[2]) + " " + m[+p[1] - 1] + " " + p[0];
  }
  function dayLabel(d) {
    if (!d) return "Date to confirm";
    var w = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][new Date(d + "T12:00:00").getDay()];
    return w + " " + fmtDate(d);
  }
  function speakers(l, plain, max) {
    var s = (l.speakers || []).filter(function (p) { return p.name; });
    if (!s.length) return "";
    if (max && s.length > max) return esc(s.slice(0, max).map(function (p) { return p.name; }).join(", ")) + " and " + (s.length - max) + " more";
    return s.map(function (p) {
      var org = p.organisation ? (plain ? ", " + esc(p.organisation) : " <span>" + esc(p.organisation) + "</span>") : "";
      return plain ? esc(p.name) + org : "<span><b>" + esc(p.name) + "</b>" + org + "</span>";
    }).join(plain ? "; " : "");
  }
  function level(l) { return '<span class="level level-' + esc(l.level) + '">' + esc(l.level) + "</span>"; }

  // Source references: [12:40] and (notes) are dropped for the team; (slide N) and (photo N) become buttons that open the
  // slide in the player; a lesson id in brackets becomes a link to that lesson.
  function cleanText(text, l) {
    var t = esc(text);
    t = t.replace(/\s*\[(\d{1,2}:)?\d{1,2}:\d{2}\](,\s*\[(\d{1,2}:)?\d{1,2}:\d{2}\])*/g, "");
    t = t.replace(/\s*\((notes|otter)\)/gi, "");
    t = t.replace(/\((slide|photo)s? (\d+)\)/gi, function (m, kind, n) {
      var usable = l && l.slides && ((kind.toLowerCase() === "slide" && l.slide_source === "deck") || (kind.toLowerCase() === "photo" && l.slide_source === "photos"));
      return usable && +n <= l.slides ? '<button type="button" class="slide-ref" data-slide="' + n + '">slide ' + n + "</button>" : "";
    });
    t = t.replace(/\(([a-z0-9]+(?:-[a-z0-9]+){2,})\)/g, function (m, id) {
      var hit = LESSONS.filter(function (x) { return x.id === id; })[0];
      return hit ? '(see <a href="#' + key(hit) + '">' + esc(hit.title) + "</a>)" : "";
    });
    t = t.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\s+([.,;])/g, "$1");
    return t;
  }
  function prose(md, l) {
    var out = [], list = null;
    (md || "").split("\n").forEach(function (line) {
      var m = /^\s*[-*]\s+(.*)$/.exec(line);
      if (m) { if (!list) { list = []; out.push(list); } list.push(cleanText(m[1], l)); return; }
      if (!line.trim()) { list = null; if (out.length && out[out.length - 1] !== null) out.push(null); return; }
      if (list && /^\s{2,}/.test(line)) { list[list.length - 1] += " " + cleanText(line.trim(), l); return; }
      list = null;
      if (typeof out[out.length - 1] === "string" && !/^\s*$/.test(line)) out[out.length - 1] += " " + cleanText(line.trim(), l);
      else out.push(cleanText(line.trim(), l));
    });
    return out.filter(function (b) { return b !== null; }).map(function (b) { return typeof b === "string" ? "<p>" + b + "</p>" : "<ul>" + b.map(function (i) { return "<li>" + i + "</li>"; }).join("") + "</ul>"; }).join("");
  }

  // ---------- per-viewer progress (this browser only) ----------
  function load(k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* storage blocked: progress is not kept */ } }
  var done = load("sll-done", {});
  function isDone(l) { return !!done[key(l)]; }
  function setDone(l, v) { if (v) done[key(l)] = 1; else delete done[key(l)]; save("sll-done", done); updateCount(); }
  function updateCount() {
    var n = LESSONS.filter(isDone).length;
    document.getElementById("done-count").textContent = n + "/" + LESSONS.length;
  }
  function courseDone(c) { return c.lessons.filter(isDone).length; }

  // ---------- views ----------
  function home() {
    var nSlides = LESSONS.reduce(function (a, l) { return a + (l.slides || 0); }, 0);
    var last = BY_KEY[load("sll-last", "")];
    var essentials = LESSONS.filter(function (l) { return l.level === "Essential" && !isDone(l); }).slice(0, 6);
    var h = '<section class="hero"><div class="wrap"><div>' +
      '<span class="eyebrow">Autumn 2026 show season</span>' +
      "<h1>What we learned at the shows</h1>" +
      '<p class="lead">Each talk our team attended, as a short lesson: the speaker\'s slides, the key learnings, a summary and what it means for Vita Actives.</p>' +
      '<div class="hero-actions"><a class="btn btn-primary" href="#essentials">Start with the essentials</a>' +
      '<a class="btn btn-ghost" href="#topics">Browse by topic</a></div></div>' +
      '<div class="stats"><div class="stat"><b>' + LIB.courses.length + "</b><span>shows</span></div>" +
      '<div class="stat"><b>' + LESSONS.length + "</b><span>talks</span></div>" +
      '<div class="stat"><b>' + nSlides + "</b><span>slides</span></div></div></div></section>";
    h += '<div class="wrap">';
    if (last) {
      h += '<section class="section"><div class="continue"><div><span class="eyebrow">Continue</span><h3>' + esc(last.title) + '</h3><span class="meta">' +
        esc(courseOf(last).short) + "</span></div><a class=\"btn btn-primary\" href=\"#" + key(last) + '">Open</a></div></section>';
    }
    h += '<section class="section"><div class="section-head"><h2>Shows</h2><p>Each show is a course; each talk a lesson.</p></div><div class="courses">' +
      LIB.courses.map(courseCard).join("") + "</div></section>";
    if (essentials.length) {
      h += '<section class="section" id="essentials-row"><div class="section-head"><h2>Essential talks</h2><p>The talks that matter most to our range and customers.</p></div>' +
        '<div class="lesson-cards">' + essentials.map(lessonCard).join("") + '</div><p class="meta" style="margin-top:12px"><a href="#essentials">See all essential talks</a></p></section>';
    }
    h += '<section class="section"><div class="section-head"><h2>Topics</h2><p>Themes that ran across the shows.</p></div><div class="topics">' +
      LIB.topics.map(function (t) { return '<a class="chip" href="#topic-' + esc(t.id) + '">' + esc(t.name) + " · " + t.lessons.length + "</a>"; }).join("") + "</div></section>";
    h += '<div style="height:32px"></div></div>';
    return h;
  }
  function courseOf(l) { return LIB.courses.filter(function (c) { return c.id === l.event; })[0]; }
  function courseCard(c) {
    var cover = (c.lessons.filter(function (l) { return l.thumb && l.level === "Essential"; })[0] || c.lessons.filter(function (l) { return l.thumb; })[0] || {}).thumb;
    var n = courseDone(c), pct = Math.round(100 * n / c.lessons.length);
    var where = [c.city, c.country].filter(Boolean).join(", ");
    return '<a class="course-card" href="#' + esc(c.id) + '"><div class="cover">' + (cover ? '<img alt="" src="' + cover + '">' : "") +
      '<span class="cover-label">' + c.lessons.length + " talks</span></div>" +
      '<div class="course-body"><h3>' + esc(c.name) + '</h3><p>' + esc(dates(c)) + (where ? " · " + esc(where) : "") + "</p>" +
      '<div class="course-foot"><div class="bar"><span style="width:' + pct + '%"></span></div><span class="meta"><span>' + n + " of " + c.lessons.length +
      ' done</span><span>' + c.lessons.filter(function (l) { return l.level === "Essential"; }).length + " essential</span></span></div></div></a>";
  }
  function dates(c) {
    if (!c.start) return "";
    if (!c.end || c.end === c.start) return fmtDate(c.start);
    var a = c.start.split("-"), b = c.end.split("-");
    return a[1] === b[1] ? (+a[2]) + "–" + fmtDate(c.end) : fmtDate(c.start) + " – " + fmtDate(c.end);
  }
  function lessonCard(l) {
    return '<a class="lesson-card" href="#' + key(l) + '">' + level(l) + "<h3>" + esc(l.title) + '</h3><span class="meta">' +
      (speakers(l, true, 3) || "Speaker to confirm") + "</span>" + '<span class="meta">' + esc(courseOf(l).short) + (l.slides ? " · " + l.slides + " slides" : "") +
      (isDone(l) ? " · done" : "") + "</span></a>";
  }

  function course(c) {
    var n = courseDone(c), pct = Math.round(100 * n / c.lessons.length);
    var h = '<section class="course-hero"><div class="wrap"><nav class="crumbs"><a href="#home">Library</a><span>/</span><span>' + esc(c.short) + "</span></nav>" +
      "<h1>" + esc(c.name) + '</h1><p class="meta">' + esc(dates(c)) + ([c.city, c.country].filter(Boolean).length ? " · " + esc([c.city, c.country].filter(Boolean).join(", ")) : "") +
      (c.organiser ? " · " + esc(c.organiser) : "") + "</p>" +
      '<div class="course-progress"><div class="bar"><span style="width:' + pct + '%"></span></div><span class="meta tab-num">' + n + " of " + c.lessons.length + " done</span></div></div></section>";
    h += '<div class="wrap" style="padding-bottom:48px">';
    var days = {};
    c.lessons.forEach(function (l) { (days[l.date || ""] = days[l.date || ""] || []).push(l); });
    var i = 0;
    Object.keys(days).sort().forEach(function (d) {
      h += '<h2 class="day">' + esc(dayLabel(d)) + '</h2><ol class="lesson-list">' + days[d].map(function (l) { return row(l, ++i); }).join("") + "</ol>";
    });
    return h + "</div>";
  }
  function row(l, i) {
    return '<li class="lesson-row' + (isDone(l) ? " done" : "") + '"><a href="#' + key(l) + '"><span class="tick">' + (isDone(l) ? "✓" : i) + "</span>" +
      '<span><span class="title">' + esc(l.title) + '</span><br><span class="sub">' + (l.start ? esc(l.start) + " · " : "") + (speakers(l, true, 3) || "Speaker to confirm") + "</span></span>" +
      '<span class="row-side">' + level(l) + (l.slides ? '<span class="meta tab-num">' + l.slides + " slides</span>" : "") + "</span></a></li>";
  }

  function lesson(l) {
    var c = courseOf(l);
    var outline = '<aside class="outline" aria-label="Talks in this show"><h2>' + esc(c.short) + '</h2><p class="meta">' + courseDone(c) + " of " + c.lessons.length +
      " done</p><ol>" + c.lessons.map(function (x, i) {
        return '<li class="' + (isDone(x) ? "done" : "") + '"><a href="#' + key(x) + '"' + (x === l ? ' aria-current="page"' : "") + '><span class="dot">' +
          (isDone(x) ? "✓" : i + 1) + "</span><span>" + esc(x.title) + "</span></a></li>";
      }).join("") + "</ol></aside>";
    var idx = c.lessons.indexOf(l), next = c.lessons[idx + 1];
    var h = '<div class="wrap"><div class="lesson-layout">' + outline + '<article class="lesson-main">' +
      '<div class="lesson-head"><nav class="crumbs"><a href="#home">Library</a><span>/</span><a href="#' + esc(c.id) + '">' + esc(c.short) + "</a></nav>" +
      "<h1>" + esc(l.title) + '</h1><div class="speakers">' + (speakers(l) || "<span>Speaker to confirm</span>") + "</div>" +
      '<div class="tags">' + level(l) + '<span class="chip">' + esc(dayLabel(l.date)) + (l.start ? ", " + esc(l.start) : "") + "</span>" + "</div></div>";
    h += player(l);
    if (l.takeaways.length) h += '<section class="learnings"><h2>Key learnings</h2><ol>' + l.takeaways.map(function (t) { return "<li><span>" + cleanText(t, l) + "</span></li>"; }).join("") + "</ol></section>";
    if (l.summary) h += '<section class="block"><h2>Summary</h2><div class="prose">' + prose(l.summary, l) + "</div></section>";
    if (l.for_us) h += '<section class="block for-us"><h2>What it means for Vita Actives</h2><div class="prose">' + prose(l.for_us, l) + "</div></section>";
    if (l.quotes.length) h += '<section class="block"><h2>In their words</h2><div class="quotes">' + l.quotes.map(function (q) { return "<blockquote>" + cleanText(q, l) + "</blockquote>"; }).join("") + "</div></section>";
    if (l.detail) h += '<details class="more"><summary>More detail and figures</summary><div class="prose">' + prose(l.detail, l) + "</div></details>";
    var topics = (l.themes || []).filter(function (t) { return TOPIC[t]; });
    if (topics.length) h += '<div class="tags">' + topics.map(function (t) { return '<a class="chip" href="#topic-' + esc(t) + '">' + esc(TOPIC[t].name) + "</a>"; }).join("") + "</div>";
    h += '<div class="lesson-foot"><button type="button" class="btn ' + (isDone(l) ? "btn-done" : "btn-ghost") + '" id="mark">' +
      (isDone(l) ? "✓ Completed" : "Mark as complete") + "</button>" +
      (next ? '<a class="btn btn-primary" href="#' + key(next) + '">Next talk: ' + esc(next.title.length > 48 ? next.title.slice(0, 46) + "…" : next.title) + "</a>"
            : '<a class="btn btn-primary" href="#' + esc(c.id) + '">Back to ' + esc(c.short) + "</a>") + "</div>";
    return h + "</article></div></div>";
  }
  function player(l) {
    if (!l.slides) return '<section class="player"><div class="stage"><p class="empty">No slides for this talk: the speaker did not share them.</p></div></section>';
    var src = l.slide_source === "deck" ? "The speaker's deck" : "Photos of the slides, taken in the room";
    return '<section class="player" id="player" aria-label="Slides"><div class="stage" id="stage"><p class="empty">Loading slides…</p>' +
      '<button type="button" class="nav-btn prev" id="prev" aria-label="Previous slide">‹</button>' +
      '<button type="button" class="nav-btn next" id="next" aria-label="Next slide">›</button></div>' +
      '<div class="player-bar"><span class="counter" id="counter">– / ' + l.slides + '</span><span class="src">' + src + "</span>" +
      '<button type="button" id="full">Full screen</button></div><div class="thumbs" id="thumbs"></div></section>';
  }
  function bindPlayer(l) {
    var stage = document.getElementById("stage");
    if (!stage) return;
    var slides = [], at = 0;
    var img = document.createElement("img");
    function show(i) {
      if (!slides.length) return;
      at = Math.max(0, Math.min(slides.length - 1, i));
      img.src = slides[at]; img.alt = "Slide " + (at + 1) + " of " + slides.length + ": " + l.title;
      document.getElementById("counter").textContent = (at + 1) + " / " + slides.length;
      [].forEach.call(document.querySelectorAll("#thumbs button"), function (b, j) { b.setAttribute("aria-current", j === at ? "true" : "false"); if (j === at) b.scrollIntoView({ block: "nearest", inline: "nearest" }); });
    }
    function go(n) { show(n - 1); document.getElementById("player").scrollIntoView({ behavior: "smooth", block: "start" }); }
    document.getElementById("prev").onclick = function () { show(at - 1); };
    document.getElementById("next").onclick = function () { show(at + 1); };
    document.getElementById("full").onclick = function () {
      var p = document.getElementById("player");
      try { if (document.fullscreenElement) document.exitFullscreen(); else if (p.requestFullscreen) p.requestFullscreen().catch(function () {}); } catch (e) { /* not available here */ }
    };
    app.onclick = function (ev) { var b = ev.target.closest && ev.target.closest(".slide-ref"); if (b) go(+b.getAttribute("data-slide")); };
    document.onkeydown = function (ev) {
      if (/INPUT|TEXTAREA/.test((ev.target || {}).tagName || "")) return;
      if (ev.key === "ArrowRight") show(at + 1); else if (ev.key === "ArrowLeft") show(at - 1);
    };
    fetch("slides/" + key(l) + ".json").then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (d) {
      slides = d.slides || [];
      stage.querySelector(".empty").remove(); stage.insertBefore(img, stage.firstChild);
      document.getElementById("thumbs").innerHTML = slides.map(function (s, j) { return '<button type="button" aria-label="Slide ' + (j + 1) + '"><img alt="" loading="lazy" src="' + s + '"></button>'; }).join("");
      [].forEach.call(document.querySelectorAll("#thumbs button"), function (b, j) { b.onclick = function () { show(j); }; });
      show(0);
    }).catch(function () { stage.querySelector(".empty").textContent = "The slides could not be loaded. Reload the page to try again."; });
  }

  function listPage(title, sub, lessons, crumb) {
    return '<section class="course-hero"><div class="wrap"><nav class="crumbs"><a href="#home">Library</a><span>/</span><span>' + esc(crumb) + "</span></nav><h1>" + esc(title) + "</h1>" +
      (sub ? '<p class="meta">' + esc(sub) + "</p>" : "") + '</div></section><div class="wrap" style="padding-block:24px 48px">' +
      (lessons.length ? '<div class="lesson-cards">' + lessons.map(lessonCard).join("") + "</div>" : '<p class="meta">Nothing here yet.</p>') + "</div>";
  }
  function topicsPage() {
    return '<section class="course-hero"><div class="wrap"><nav class="crumbs"><a href="#home">Library</a><span>/</span><span>Topics</span></nav><h1>Topics</h1>' +
      '<p class="meta">Themes that ran across the shows, with the talks that touched them.</p></div></section><div class="wrap" style="padding-block:24px 48px"><div class="lesson-cards">' +
      LIB.topics.map(function (t) { return '<a class="lesson-card" href="#topic-' + esc(t.id) + '"><h3>' + esc(t.name) + '</h3><span class="meta">' + esc(t.description) +
        '</span><span class="meta">' + t.lessons.length + " talks</span></a>"; }).join("") + "</div></div>";
  }
  function search(q) {
    var words = q.toLowerCase().split(/\s+/).filter(Boolean);
    var hits = LESSONS.filter(function (l) {
      var hay = [l.title, speakers(l, true), l.summary, l.takeaways.join(" "), (l.ingredients || []).join(" "), courseOf(l).name].join(" ").toLowerCase();
      return words.every(function (w) { return hay.indexOf(w) >= 0; });
    });
    return listPage("Search: " + q, hits.length + (hits.length === 1 ? " talk" : " talks"), hits, "Search");
  }

  function route() {
    var h = decodeURIComponent((location.hash || "#home").slice(1)), html;
    document.onkeydown = null; app.onclick = null;
    if (h === "home" || !h) html = home();
    else if (h === "essentials") html = listPage("Essential talks", "The talks that matter most to our range and customers, across all shows.", LESSONS.filter(function (l) { return l.level === "Essential"; }), "Essential talks");
    else if (h === "topics") html = topicsPage();
    else if (h === "my-learning") html = listPage("My learning", LESSONS.filter(isDone).length + " of " + LESSONS.length + " talks completed in this browser.", LESSONS.filter(isDone), "My learning");
    else if (h.indexOf("topic-") === 0 && TOPIC[h.slice(6)]) {
      var t = TOPIC[h.slice(6)];
      html = listPage(t.name, t.description, t.lessons.map(function (x) { return BY_KEY[x.event + "--" + x.session]; }).filter(Boolean), "Topics");
    } else if (h.indexOf("search-") === 0) html = search(h.slice(7).replace(/-/g, " "));
    else if (BY_KEY[h]) { html = lesson(BY_KEY[h]); save("sll-last", h); }
    else {
      var c = LIB.courses.filter(function (x) { return x.id === h; })[0];
      html = c ? course(c) : home();
    }
    app.innerHTML = html;
    window.scrollTo(0, 0);
    if (BY_KEY[h]) {
      var l = BY_KEY[h];
      bindPlayer(l);
      document.getElementById("mark").onclick = function () { setDone(l, !isDone(l)); route(); };
      document.title = l.title + " · Show Learning Library";
    } else document.title = "Show Learning Library";
  }

  document.getElementById("search-form").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = document.getElementById("q").value.trim().toLowerCase().replace(/[^a-z0-9 ]+/g, " ").trim();
    location.hash = q ? "search-" + q.replace(/\s+/g, "-") : "home";
  });
  window.addEventListener("hashchange", route);

  fetch("data/library.json").then(function (r) { return r.json(); }).then(function (lib) {
    LIB = lib;
    lib.courses.forEach(function (c) { c.lessons.forEach(function (l) { LESSONS.push(l); BY_KEY[key(l)] = l; }); });
    lib.topics.forEach(function (t) { TOPIC[t.id] = t; });
    document.getElementById("stamp").textContent = "Updated " + fmtDate(lib.built);
    updateCount();
    route();
  }).catch(function () { app.innerHTML = '<p class="loading">The library could not be loaded. Reload the page to try again.</p>'; });
})();

/* Conference Notes dashboard: plain JS, hash routing, data from data/events.json (built by `python -m confnotes build`). */
(function () {
  "use strict";
  var app = document.getElementById("app");
  var DATA = null, E = [], T = [], S = [];
  var CITE = /\[(\d{1,2}:\d{2}(?::\d{2})?)\]|\((slide|page|section|photo) (\d+)\)|\((notes|otter)\)/gi;
  var SUMMARY_HEADINGS = ["Summary", "Key takeaways", "For Vita Actives", "Quotes", "Follow-ups"];
  var REPORT_HEADINGS = ["In brief", "Themes", "Sessions that mattered", "People met", "For Vita Actives", "Follow-ups", "Sources"];
  var STATUS_TEXT = { captured: "Originals filed; no summary yet.", summarised: "Summary drafted by Claude; waiting for a person to review it.", reviewed: "Summary read and corrected by a person." };

  /* ---------- helpers ---------- */
  function h(tag, attrs) {
    var el = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (attrs[k] == null || attrs[k] === false) continue;
      if (k === "class") el.className = attrs[k]; else if (k === "text") el.textContent = attrs[k];
      else if (k === "html") el.innerHTML = attrs[k];
      else if (k.slice(0, 2) === "on") el.addEventListener(k.slice(2), attrs[k]); else el.setAttribute(k, attrs[k]);
    }
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c == null || c === false) return;
    if (Array.isArray(c)) c.forEach(function (x) { add(el, x); });
    else el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  }
  function set(el, children) { el.replaceChildren(); add(el, children); }
  function uniq(a) { return a.filter(function (x, i) { return x && a.indexOf(x) === i; }); }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : (many || one + "s")); }
  function cls(s) { return String(s || "").replace(/[^a-z0-9]+/gi, "-").toLowerCase(); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function fmtDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || ""); if (!m) return iso || "";
    var mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+m[2] - 1];
    return +m[3] + " " + mon + " " + m[1];
  }
  function dates(e) {
    if (!e.start) return "dates to confirm";
    if (!e.end || e.end === e.start) return fmtDate(e.start);
    var a = /^(\d{4})-(\d{2})-(\d{2})$/.exec(e.start), b = /^(\d{4})-(\d{2})-(\d{2})$/.exec(e.end);
    if (a && b && a[1] === b[1] && a[2] === b[2]) return +a[3] + " to " + fmtDate(e.end);
    return fmtDate(e.start) + " to " + fmtDate(e.end);
  }
  function time(s) { return s.start ? s.start + (s.end ? "–" + s.end : "") : ""; }
  function eventOf(id) { return E.filter(function (e) { return e.id === id; })[0]; }
  function themeOf(id) { return T.filter(function (t) { return t.id === id; })[0]; }
  function themeName(id) { var t = themeOf(id); return t ? t.name : id; }
  function speakerLine(s) {
    return s.speakers.map(function (p) { return p.name + (p.organisation ? " (" + p.organisation + ")" : ""); }).join(", ");
  }
  function chip(text, kind) { return h("span", { class: "chip " + (kind || ""), text: text }); }
  function themeChips(ids) { return ids.map(function (id) { return h("a", { class: "chip theme", href: "#theme-" + id, text: themeName(id) }); }); }
  function statusChip(s) { return chip(s.status, "status-" + s.status); }
  function relChip(s) { return s.relevance ? chip("relevance " + s.relevance, "rel-" + s.relevance) : null; }

  // the minimal markdown the summaries and reports use: ### headings, bullets, quotes, paragraphs, **bold**, *italic*, `code`, [text](url)
  function inline(t) {
    return esc(t)
      .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\W)\*(?!\s)(.+?)\*(?=\W|$)/g, "$1<i>$2</i>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  }
  function md(text) {
    var out = [], list = null, para = [];
    function flush() { if (para.length) { out.push("<p>" + inline(para.join(" ")) + "</p>"); para = []; } if (list) { out.push("</ul>"); list = null; } }
    (text || "").split("\n").forEach(function (line) {
      var m;
      if (!line.trim()) { flush(); return; }
      if ((m = /^#{1,6}\s+(.*)$/.exec(line))) { flush(); out.push("<h3>" + inline(m[1]) + "</h3>"); return; }
      if ((m = /^\s*[-*]\s+(.*)$/.exec(line))) { if (para.length) { out.push("<p>" + inline(para.join(" ")) + "</p>"); para = []; } if (!list) { out.push("<ul>"); list = true; } out.push("<li>" + inline(m[1]) + "</li>"); return; }
      if ((m = /^>\s?(.*)$/.exec(line))) { flush(); out.push("<blockquote>" + inline(m[1]) + "</blockquote>"); return; }
      if (list) { out[out.length - 1] = out[out.length - 1].replace(/<\/li>$/, " " + inline(line.trim()) + "</li>"); return; }
      para.push(line.trim());
    });
    flush();
    return h("div", { class: "md", html: out.join("") });
  }
  // a takeaway or quote: its text with every source it names ([12:40], (slide 7), (notes)) as a chip
  function cited(text, cites) {
    var el = h("span"), last = 0, m; CITE.lastIndex = 0;
    while ((m = CITE.exec(text))) {
      add(el, text.slice(last, m.index));
      add(el, h("span", { class: "cite", text: m[1] || (m[2] ? m[2].toLowerCase() + " " + m[3] : m[4].toLowerCase()) }));
      last = m.index + m[0].length;
    }
    add(el, text.slice(last));
    if (!cites || !cites.length) add(el, [" ", h("span", { class: "reading", text: "no passage cited: a reading" })]);
    return el;
  }
  function highlight(text, q) {
    if (!q) return text;
    var el = h("span"), re = new RegExp("(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "ig"), parts = String(text).split(re);
    parts.forEach(function (p, i) { add(el, i % 2 ? h("mark", { text: p }) : p); });
    return el;
  }
  function setNav(name) {
    document.querySelectorAll(".nav a").forEach(function (a) { a.classList.toggle("on", a.dataset.nav === name); });
  }
  function toCheck() {
    var items = [];
    E.forEach(function (e) {
      if (e.to_check) items.push({ kind: "event", event: e, text: e.to_check, href: "#event-" + e.id, title: e.name });
      e.sessions.forEach(function (s) {
        if (s.to_check) items.push({ kind: "session", event: e, session: s, text: s.to_check, href: "#session-" + e.id + "/" + s.id, title: s.title });
        if (s.status === "captured") items.push({ kind: "session", event: e, session: s, text: "No summary yet (status captured).", href: "#session-" + e.id + "/" + s.id, title: s.title });
        if (s.status === "summarised") items.push({ kind: "session", event: e, session: s, text: "Summary drafted, not yet reviewed by a person.", href: "#session-" + e.id + "/" + s.id, title: s.title });
      });
    });
    return items;
  }
  function footer() {
    var ns = S.length;
    document.getElementById("stamp").textContent = "Data: " + plural(E.length, "event") + ", " + plural(ns, "session") + " · commit " + DATA.generated.commit +
      (DATA.generated.uncommitted_changes ? " (uncommitted changes)" : "") + " · " + fmtDate(DATA.generated.date);
    var n = toCheck().length; document.getElementById("nav-count").textContent = n ? String(n) : "";
  }
  function tocheckBox(text) {
    return text ? h("div", { class: "tocheck" }, h("h3", { text: "Still to check" }), h("p", { text: text })) : null;
  }

  /* ---------- views ---------- */
  function viewEvents() {
    setNav("events");
    var reviewed = S.filter(function (s) { return s.status === "reviewed"; }).length;
    var counts = h("div", { class: "counts" },
      h("div", { class: "count" }, h("b", { text: E.length }), h("span", { text: "events" })),
      h("div", { class: "count" }, h("b", { text: S.length }), h("span", { text: "sessions" })),
      h("div", { class: "count" }, h("b", { text: reviewed }), h("span", { text: "summaries reviewed" })),
      h("a", { class: "count ing", href: "#themes" }, h("b", { text: T.filter(function (t) { return t.events.length || t.sessions.length; }).length }), h("span", { text: "themes seen" })));
    var cards = E.length ? h("div", { class: "cards" }, E.map(function (e) {
      var ths = uniq(e.themes.map(function (t) { return t.theme; }));
      return h("a", { class: "card", href: "#event-" + e.id },
        h("div", { class: "card-body" },
          h("div", { class: "eyebrow", text: dates(e) + (e.city ? " · " + e.city : "") }),
          h("div", { class: "card-title", text: e.name }),
          h("div", { class: "card-brand", text: (e.organiser ? e.organiser + " · " : "") + plural(e.sessions.length, "session") + (e.has_report ? " · report written" : "") }),
          h("div", { class: "chips" }, chip(e.status, "status-" + (e.status === "reported" ? "reviewed" : e.status === "attended" ? "summarised" : "captured")),
            ths.slice(0, 4).map(function (id) { return chip(themeName(id), "theme"); }), ths.length > 4 ? chip("+" + (ths.length - 4) + " more") : null)));
    })) : h("div", { class: "empty", text: "No events yet. Tell Claude which conference you are at and it creates the first one." });
    app.replaceChildren(h("div", { class: "stack" },
      h("div", null, h("h1", { text: "Events" }), h("p", { class: "lede", text: "What we learnt at each conference: the sessions, their takeaways, the themes and the report." })),
      counts, cards));
  }

  function viewEvent(id) {
    var e = eventOf(id); setNav("events");
    if (!e) return notFound("event " + id);
    var days = uniq(e.sessions.map(function (s) { return s.date || ""; }));
    var head = h("div", { class: "event-head" },
      h("span", { text: dates(e) }), e.city ? h("span", { text: e.city + (e.country ? ", " + e.country : "") }) : null,
      e.venue ? h("span", { text: e.venue }) : null, e.organiser ? h("span", { text: e.organiser }) : null,
      e.url ? h("a", { href: e.url, target: "_blank", rel: "noopener", text: "event page" }) : null,
      chip(e.status, "status-" + (e.status === "reported" ? "reviewed" : e.status === "attended" ? "summarised" : "captured")));
    var brief = e.has_report && e.report["In brief"] ? h("div", { class: "brief" }, h("h3", { text: "In brief" }), md(e.report["In brief"])) : null;
    var themes = e.themes.length ? h("div", { class: "panel" }, h("h3", { text: "Themes at this event" }), h("div", { class: "list" }, e.themes.map(function (t) {
      return h("div", { class: "item" },
        h("div", { class: "chips", style: "padding-top:0;margin-bottom:4px" }, h("a", { class: "chip theme", href: "#theme-" + t.theme, text: themeName(t.theme) }), t.strength ? chip(t.strength, "strength-" + t.strength) : null),
        h("div", { class: "t", text: t.headline || "" }),
        t.evidence.length ? h("ul", null, t.evidence.map(function (ev) {
          var s = e.sessions.filter(function (x) { return x.id === ev.session; })[0];
          return h("li", null, "“" + ev.quote + "”", s ? [" — ", h("a", { href: "#session-" + e.id + "/" + s.id, text: s.title })] : null, ev.where ? [" ", h("span", { class: "cite", text: String(ev.where) })] : null);
        })) : null);
    }))) : null;
    var sessions = e.sessions.length ? days.map(function (d) {
      return h("div", { class: "day" }, h("h2", { text: d ? fmtDate(d) : "Date to confirm" }), h("div", { class: "list" },
        e.sessions.filter(function (s) { return (s.date || "") === d; }).map(function (s) { return sessionRow(e, s); })));
    }) : h("div", { class: "empty", text: "No sessions filed yet. Drop a presentation, transcript or your notes into a Claude session and name the talk." });
    var report = e.has_report ? h("div", { class: "panel" }, h("h3", { text: "Event report" }), REPORT_HEADINGS.filter(function (k) { return k !== "In brief" && e.report[k]; }).map(function (k) {
      return [h("h3", { class: "eyebrow", style: "margin-top:12px", text: k }), md(e.report[k])];
    })) : null;
    var fields = h("dl", { class: "fields" }, [["Attended by", e.attended_by.join(", ")], ["Description", e.description], ["Added", (e.added ? fmtDate(e.added) : "") + (e.added_by ? " by " + e.added_by : "")]].map(function (kv) {
      return h("div", null, h("dt", { text: kv[0] }), h("dd", kv[1] ? { text: kv[1] } : { class: "na", text: "—" }));
    }), Object.keys(e.links).map(function (k) {
      return h("div", null, h("dt", { text: "Link: " + k.replace(/_/g, " ") }), h("dd", null, h("a", { href: e.links[k], target: "_blank", rel: "noopener", text: e.links[k] })));
    }));
    app.replaceChildren(h("div", { class: "stack" },
      h("div", null, h("div", { class: "crumb" }, h("a", { href: "#", text: "Events" }), " / "), h("h1", { text: e.name }), head),
      tocheckBox(e.to_check), brief, themes,
      h("div", null, h("h2", { text: plural(e.sessions.length, "session") })), sessions, report,
      h("div", { class: "panel" }, h("h3", { text: "Record" }), fields)));
  }

  function sessionRow(e, s) {
    return h("a", { class: "sess", href: "#session-" + e.id + "/" + s.id },
      h("div", { class: "when", text: time(s) || (s.format || "") }),
      h("div", null, h("div", { class: "t", text: s.title }), h("div", { class: "who", text: [speakerLine(s), s.format, s.track, s.room].filter(Boolean).join(" · ") }),
        h("div", { class: "chips" }, statusChip(s), relChip(s), themeChips(s.themes), s.ingredients.map(function (i) { return chip(i, "ingredient"); }))));
  }

  function viewSession(eid, sid) {
    var e = eventOf(eid); setNav("events");
    var s = e && e.sessions.filter(function (x) { return x.id === sid; })[0];
    if (!s) return notFound("session " + eid + "/" + sid);
    var meta = h("div", { class: "event-head" },
      h("span", { text: [s.date ? fmtDate(s.date) : "", time(s)].filter(Boolean).join(" ") }), s.format ? h("span", { text: s.format }) : null,
      s.track ? h("span", { text: s.track }) : null, h("a", { href: "#event-" + e.id, text: e.short || e.name }));
    var speakers = s.speakers.length ? h("div", { class: "panel" }, h("h3", { text: plural(s.speakers.length, "Speaker") }), h("ul", { style: "margin:0;padding-left:18px" }, s.speakers.map(function (p) {
      return h("li", null, h("a", { href: "#people?q=" + encodeURIComponent(p.name), text: p.name }), [p.role, p.organisation].filter(Boolean).length ? ", " + [p.role, p.organisation].filter(Boolean).join(", ") : "");
    }))) : null;
    var status = h("div", { class: "panel status-box " + (s.status === "reviewed" ? "ev-confirmed" : s.status === "summarised" ? "ev-likely" : "") },
      h("div", { class: "lbl", text: "Status" }), h("div", { class: "val", text: s.status }), h("p", { class: "small muted", text: STATUS_TEXT[s.status] || "" }),
      s.summary_by ? h("p", { class: "small", text: "Summary by " + s.summary_by + (s.summary_date ? " on " + fmtDate(s.summary_date) : "") + (s.reviewed_by ? "; reviewed by " + s.reviewed_by + (s.reviewed_date ? " on " + fmtDate(s.reviewed_date) : "") : "") }) : null);
    var summary = null;
    if (s.has_summary) {
      summary = h("div", { class: "stack" },
        h("div", { class: "panel" }, h("h3", { text: "Summary" }), md(s.summary["Summary"])),
        h("div", { class: "panel" }, h("h3", { text: "Key takeaways" }), s.takeaways.length ? h("ul", { class: "takeaways" }, s.takeaways.map(function (t) { return h("li", null, cited(t.text, t.cites)); })) : h("p", { class: "na", text: "None written." })),
        h("div", { class: "panel" }, h("h3", { text: "For Vita Actives" }), md(s.summary["For Vita Actives"])),
        h("div", { class: "panel" }, h("h3", { text: "Quotes" }), s.quotes.length ? s.quotes.map(function (q) { return h("blockquote", { class: "quote" }, cited(q.text, q.cites)); }) : h("p", { class: "na", text: "None recorded." })),
        h("div", { class: "panel" }, h("h3", { text: "Follow-ups" }), s.followups.length ? h("ul", { class: "takeaways" }, s.followups.map(function (f) { return h("li", null, cited(f, ["x"])); })) : h("p", { class: "na", text: "None." })));
    } else {
      summary = h("div", { class: "empty", text: "No summary yet. The originals below are what we have; ask Claude to draft the summary from them." });
    }
    var originals = h("div", { class: "stack" }, h("h2", { text: "Originals" }),
      s.files.map(function (f) {
        var body;
        if (f.text && f.pages) {
          var parts = f.text.split(/^--- (?:slide|page|section|photo) (\d+) ---$/m);
          body = h("div", null, []);
          for (var i = 1; i < parts.length; i += 2) body.appendChild(h("div", { class: "slide" }, h("div", { class: "n", text: (f.kind === "pptx" ? "slide " : f.kind === "docx" ? "section " : f.kind === "photo" ? "photo " : "page ") + parts[i] }), h("pre", { text: parts[i + 1].trim() })));
        } else if (f.text) body = h("pre", { class: "orig-text", text: f.text });
        else body = h("p", { class: "na", text: "No text pulled out yet (run `python -m confnotes extract`)." });
        return h("details", { class: "orig" }, h("summary", null, h("span", { text: f.name }), h("span", { class: "meta", text: [f.kind, f.pages ? plural(f.pages, f.kind === "pptx" ? "slide" : f.kind === "photo" ? "photo" : "page") : null, Math.round(f.bytes / 1024) + " KB"].filter(Boolean).join(" · ") })), h("div", { class: "body" }, body));
      }),
      s.has_transcript ? h("details", { class: "orig" }, h("summary", null, h("span", { text: "Transcript" }), h("span", { class: "meta", text: plural(s.transcript_words, "word") })), h("div", { class: "body" }, h("pre", { class: "orig-text", text: s.transcript }))) : null,
      s.has_notes ? h("details", { class: "orig" }, h("summary", null, h("span", { text: "Notes" }), h("span", { class: "meta", text: "as written in the room" })), h("div", { class: "body" }, h("pre", { class: "orig-text", text: s.notes }))) : null,
      !s.files.length && !s.has_transcript && !s.has_notes ? h("div", { class: "empty", text: "No originals filed." }) : null);
    var fields = h("dl", { class: "fields" }, [["Attended by", s.attended_by.join(", ")], ["Ingredients named", s.ingredients.join(", ")], ["Added", (s.added ? fmtDate(s.added) : "") + (s.added_by ? " by " + s.added_by : "")]].map(function (kv) {
      return h("div", null, h("dt", { text: kv[0] }), h("dd", kv[1] ? { text: kv[1] } : { class: "na", text: "—" }));
    }), Object.keys(s.links).map(function (k) {
      return h("div", null, h("dt", { text: "Link: " + k.replace(/_/g, " ") }), h("dd", null, h("a", { href: s.links[k], target: "_blank", rel: "noopener", text: s.links[k] })));
    }));
    app.replaceChildren(h("div", { class: "stack" },
      h("div", null, h("div", { class: "crumb" }, h("a", { href: "#", text: "Events" }), " / ", h("a", { href: "#event-" + e.id, text: e.short || e.name }), " / "), h("h1", { text: s.title }), meta,
        h("div", { class: "chips" }, relChip(s), themeChips(s.themes), s.ingredients.map(function (i) { return chip(i, "ingredient"); }))),
      tocheckBox(s.to_check),
      h("div", { class: "two" }, status, speakers),
      summary, originals,
      h("div", { class: "panel" }, h("h3", { text: "Record" }), fields)));
  }

  function viewThemes() {
    setNav("themes");
    var seen = T.filter(function (t) { return t.events.length || t.sessions.length; }), unseen = T.filter(function (t) { return !t.events.length && !t.sessions.length; });
    function card(t) {
      var latest = t.events[t.events.length - 1];
      return h("a", { class: "card", href: "#theme-" + t.id }, h("div", { class: "card-body" },
        h("div", { class: "card-title", text: t.name }), h("div", { class: "card-brand", text: t.description || "" }),
        latest ? h("p", { class: "small", style: "margin:4px 0 0" }, h("span", { class: "eyebrow", text: latest.event_name + ": " }), latest.headline) : null,
        h("div", { class: "chips" }, chip(plural(t.events.length, "event")), chip(plural(t.sessions.length, "session")), latest && latest.strength ? chip(latest.strength, "strength-" + latest.strength) : null)));
    }
    app.replaceChildren(h("div", { class: "stack" },
      h("div", null, h("h1", { text: "Themes" }), h("p", { class: "lede", text: "What the industry keeps talking about, tracked across events. One id per theme; each event carries its own headline." })),
      seen.length ? h("div", { class: "cards" }, seen.map(card)) : h("div", { class: "empty", text: "No themes recorded yet. They appear once an event's themes are written." }),
      unseen.length ? [h("h2", { class: "sub", text: "In the vocabulary, not yet seen at an event" }), h("div", { class: "cards" }, unseen.map(card))] : null));
  }

  function viewTheme(id) {
    var t = themeOf(id); setNav("themes");
    if (!t) return notFound("theme " + id);
    var tl = t.events.length ? h("div", { class: "tl" }, t.events.map(function (ev) {
      var e = eventOf(ev.event);
      return h("div", { class: "ev" }, h("div", { class: "d", text: (ev.start ? fmtDate(ev.start) + " · " : "") }, h("a", { href: "#event-" + ev.event, text: ev.event_name })),
        h("div", { class: "t", style: "font-weight:650" }, ev.headline, ev.strength ? [" ", chip(ev.strength, "strength-" + ev.strength)] : null),
        ev.evidence.length ? ev.evidence.map(function (q) {
          var s = e && e.sessions.filter(function (x) { return x.id === q.session; })[0];
          return h("blockquote", { class: "quote" }, "“" + q.quote + "”", h("span", { class: "by" }, s ? h("a", { href: "#session-" + e.id + "/" + s.id, text: s.title }) : q.session || "", q.where ? [" ", h("span", { class: "cite", text: String(q.where) })] : null));
        }) : null);
    })) : h("div", { class: "empty", text: t.sessions.length ? "Carried by " + plural(t.sessions.length, "session") + " below; this event's headline and evidence are written with the event report." : "Not yet seen at an event." });
    var sessions = t.sessions.length ? h("div", { class: "list" }, t.sessions.map(function (x) {
      var e = eventOf(x.event), s = e && e.sessions.filter(function (y) { return y.id === x.session; })[0];
      return s ? sessionRow(e, s) : null;
    })) : null;
    app.replaceChildren(h("div", { class: "stack" },
      h("div", null, h("div", { class: "crumb" }, h("a", { href: "#themes", text: "Themes" }), " / "), h("h1", { text: t.name }), h("p", { class: "lede", text: t.description || "" })),
      h("div", null, h("h2", { text: "Across events" })), tl,
      sessions ? [h("div", null, h("h2", { text: plural(t.sessions.length, "session") + " carried it" })), sessions] : null));
  }

  function people() {
    var by = {};
    S.forEach(function (s) {
      s.speakers.forEach(function (p) {
        var k = p.name.toLowerCase();
        by[k] = by[k] || { name: p.name, organisations: [], roles: [], sessions: [] };
        if (p.organisation) by[k].organisations.push(p.organisation);
        if (p.role) by[k].roles.push(p.role);
        by[k].sessions.push(s);
      });
    });
    return Object.keys(by).sort().map(function (k) { var p = by[k]; p.organisations = uniq(p.organisations); p.roles = uniq(p.roles); return p; });
  }

  function viewPeople(q) {
    setNav("people");
    var all = people(), input = h("input", { type: "search", placeholder: "Name or organisation", value: q || "", "data-filter": "q", "aria-label": "Filter people" });
    var list = h("div", { class: "people" });
    function render() {
      var qq = input.value.trim().toLowerCase();
      var rows = all.filter(function (p) { return !qq || (p.name + " " + p.organisations.join(" ")).toLowerCase().indexOf(qq) >= 0; });
      set(list, rows.length ? rows.map(function (p) {
        return h("div", { class: "item" }, h("div", { class: "t", text: p.name }), h("div", { class: "small muted", text: [p.roles.join("; "), p.organisations.join("; ")].filter(Boolean).join(" · ") }),
          h("ul", null, p.sessions.map(function (s) { return h("li", null, h("a", { href: "#session-" + s.event + "/" + s.id, text: s.title }), s.date ? " (" + fmtDate(s.date) + ")" : ""); })));
      }) : h("div", { class: "empty", text: all.length ? "Nobody matches." : "No speakers recorded yet." }));
    }
    input.addEventListener("input", render); render();
    var orgs = uniq([].concat.apply([], all.map(function (p) { return p.organisations; }))).sort();
    app.replaceChildren(h("div", { class: "stack" },
      h("div", null, h("h1", { text: "People" }), h("p", { class: "lede", text: plural(all.length, "speaker") + " from " + plural(orgs.length, "organisation") + ", as billed in the sessions." })),
      h("div", { class: "filters" }, input), list));
  }

  function searchIndex() {
    var docs = [];
    E.forEach(function (e) {
      docs.push({ kind: "event", title: e.name, href: "#event-" + e.id, where: dates(e), text: [e.name, e.short, e.city, e.organiser, e.description, e.report_md].filter(Boolean).join("\n") });
      e.sessions.forEach(function (s) {
        var parts = [s.title, speakerLine(s), s.track, s.ingredients.join(" "), s.themes.map(themeName).join(" ")];
        SUMMARY_HEADINGS.forEach(function (k) { if (s.summary[k]) parts.push(s.summary[k]); });
        s.files.forEach(function (f) { if (f.text) parts.push(f.text); });
        if (s.transcript) parts.push(s.transcript);
        if (s.notes) parts.push(s.notes);
        docs.push({ kind: "session", title: s.title, href: "#session-" + e.id + "/" + s.id, where: (e.short || e.name) + (s.date ? " · " + fmtDate(s.date) : ""), text: parts.join("\n") });
      });
    });
    T.forEach(function (t) { docs.push({ kind: "theme", title: t.name, href: "#theme-" + t.id, where: plural(t.events.length, "event"), text: [t.name, t.description].concat(t.events.map(function (ev) { return [ev.headline].concat(ev.evidence.map(function (q) { return q.quote; })).join("\n"); })).join("\n") }); });
    return docs;
  }

  function viewSearch(q) {
    setNav("search");
    var input = h("input", { type: "search", placeholder: "A word in a talk, a slide, a takeaway, a name", value: q || "", "data-filter": "q", "aria-label": "Search" });
    var out = h("div", { class: "list" }), line = h("div", { class: "result-line" }), docs = searchIndex();
    function render() {
      var qq = input.value.trim();
      if (qq.length < 2) { set(out, null); line.textContent = "Type two or more letters."; return; }
      var re = new RegExp(qq.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
      var hits = docs.filter(function (d) { return re.test(d.text); });
      line.textContent = plural(hits.length, "result");
      set(out, hits.length ? hits.map(function (d) {
        var i = d.text.search(re), snip = d.text.slice(Math.max(0, i - 80), i + 120).replace(/\s+/g, " ");
        return h("a", { class: "item hit", href: d.href }, h("div", { class: "where", text: d.kind + " · " + d.where }), h("div", { class: "t", text: d.title }), h("div", { class: "snip" }, (i > 80 ? "… " : ""), highlight(snip, qq), " …"));
      }) : h("div", { class: "empty", text: "Nothing matches." }));
    }
    input.addEventListener("input", render); render();
    app.replaceChildren(h("div", { class: "stack" }, h("div", null, h("h1", { text: "Search" }), h("p", { class: "lede", text: "Searches titles, speakers, summaries, takeaways, quotes, the text of the slides, transcripts and notes." })),
      h("div", { class: "filters" }, input), line, out));
  }

  function viewToCheck() {
    setNav("to-check");
    var items = toCheck(), byEvent = uniq(items.map(function (i) { return i.event.id; }));
    app.replaceChildren(h("div", { class: "stack" },
      h("div", null, h("h1", { text: "To check" }), h("p", { class: "lede", text: "What is still unknown, and which sessions wait for a summary or a review." })),
      items.length ? byEvent.map(function (eid) {
        var e = eventOf(eid);
        return h("div", { class: "group", "data-event": eid }, h("h2", null, h("a", { href: "#event-" + eid, text: e.name })), h("div", { class: "list" }, items.filter(function (i) { return i.event.id === eid; }).map(function (i) {
          return h("div", { class: "item" }, h("div", { class: "t" }, h("a", { href: i.href, text: i.title }), i.session ? [" ", statusChip(i.session)] : null), h("ul", null, h("li", { text: i.text })));
        })));
      }) : h("div", { class: "empty", text: "Nothing to check." })));
  }

  function notFound(what) {
    app.replaceChildren(h("div", { class: "empty" }, "No " + what + ". ", h("a", { href: "#", text: "Back to events" })));
  }

  /* ---------- routing ---------- */
  function route() {
    var hash = decodeURIComponent(location.hash.replace(/^#/, "")), q = "", m;
    if ((m = /^(.*?)\?q=(.*)$/.exec(hash))) { hash = m[1]; q = m[2]; }
    if (!hash || hash === "events") viewEvents();
    else if (hash === "themes") viewThemes();
    else if (hash === "people") viewPeople(q);
    else if (hash === "search") viewSearch(q);
    else if (hash === "to-check") viewToCheck();
    else if ((m = /^event-(.+)$/.exec(hash))) viewEvent(m[1]);
    else if ((m = /^session-([^/]+)\/(.+)$/.exec(hash))) viewSession(m[1], m[2]);
    else if ((m = /^theme-(.+)$/.exec(hash))) viewTheme(m[1]);
    else notFound("page " + hash);
    window.scrollTo(0, 0);
  }

  fetch("data/events.json").then(function (r) { return r.json(); }).then(function (d) {
    DATA = d; E = d.events || []; T = d.themes || [];
    S = [].concat.apply([], E.map(function (e) { return e.sessions; }));
    footer(); route(); window.addEventListener("hashchange", route);
  }).catch(function (err) {
    app.replaceChildren(h("div", { class: "empty", text: "Could not load data/events.json: " + err }));
  });
})();

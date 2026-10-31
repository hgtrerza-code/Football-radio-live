/* FootLive Pro : page d'une compétition (matchs, classement, actus). Données : ESPN (via vos Workers) + TheSportsDB pour la Botola Pro. */
(function () {
  "use strict";
  const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
  const B = document.body.dataset, SLUGS = (B.slug || "").split(",").filter(Boolean), TSDB_C = B.tsdb || "";
  const PROXY = "https://footlive.hgtrerza.workers.dev/", PROXY2 = "https://footlive2.hgtrerza.workers.dev/";
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ymd = d => d.getFullYear() + String(d.getMonth() + 1).padStart(2, "0") + String(d.getDate()).padStart(2, "0");
  const localDay = iso => new Date(iso).toLocaleDateString("sv-SE");
  const hhmm = iso => new Date(iso).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  const skel = (n, c) => Array.from({ length: n }, () => '<div class="sk ' + (c || "") + '"></div>').join("");
  const httpUrl = u => /^https?:\/\//i.test(u || "") ? u : "";
  let favs = []; try { favs = JSON.parse(localStorage.getItem("fl_favs") || "[]"); } catch (e) { }

  async function fetchJSON(url, ms) {
    const c = new AbortController(), t = setTimeout(() => c.abort(), ms || 10000);
    try { const r = await fetch(url, { signal: c.signal }); if (!r.ok) throw new Error("HTTP " + r.status); return await r.json(); }
    finally { clearTimeout(t); }
  }
  // Worker 1, puis Worker 2, puis ESPN directement. ok(j) décide si la réponse est exploitable.
  async function espn(sl, what, qs, ok) {
    const direct = (what === "standings" ? "https://site.api.espn.com/apis/v2/sports/soccer/" : "https://site.api.espn.com/apis/site/v2/sports/soccer/") + sl + "/" + what + (qs || "");
    const tries = [PROXY + "soccer/" + sl + "/" + what + (qs || ""), PROXY2 + "soccer/" + sl + "/" + what + (qs || ""), direct];
    for (const u of tries) { try { const j = await fetchJSON(u); if (!ok || ok(j)) return j; } catch (e) { } }
    return null;
  }

  // ---------- Matchs ----------
  function normalize(ev) {
    const c = (ev.competitions && ev.competitions[0]) || {}, cp = c.competitors || [];
    const home = cp.find(x => x.homeAway === "home") || cp[0], away = cp.find(x => x.homeAway === "away") || cp[1];
    if (!home || !away) return null;
    const st = (ev.status && ev.status.type) || {};
    const off = /postponed|cancel|suspend|abandon/i.test((st.name || "") + " " + (st.description || ""));
    const state = off ? "pre" : (st.state || "pre");
    const ht = /half/i.test(st.description || "") && !/second|first/i.test(st.description || "") || /halftime/i.test(st.name || "");
    return {
      id: ev.id, start: ev.date, state, off,
      label: off ? (st.description || "Reporté") : ht ? "Mi-temps" : ((ev.status && ev.status.displayClock) || st.shortDetail || ""),
      home: home.team.displayName || home.team.name, away: away.team.displayName || away.team.name, hl: home.team.logo, al: away.team.logo,
      h: home.score === undefined || home.score === "" ? null : Number(home.score), a: away.score === undefined || away.score === "" ? null : Number(away.score)
    };
  }
  async function loadEspn() {
    const t = new Date(), day = o => { const d = new Date(t); d.setDate(t.getDate() + o); return ymd(d); };
    const uniq = list => { const seen = new Set(); return list.filter(e => e && e.id && !seen.has(e.id) && seen.add(e.id)); };
    const OFFS = [-3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7];
    // 1) la compétition jour par jour (même type de requête que la page d'accueil)
    for (const sl of SLUGS) {
      const res = await Promise.all(OFFS.map(o => espn(sl, "scoreboard", "?dates=" + day(o) + "&limit=1000", null).catch(() => null)));
      const evs = []; res.forEach(r => r && (r.events || []).forEach(e => evs.push(e)));
      const out = uniq(evs.map(normalize).filter(Boolean));
      if (out.length) return out;
    }
    // 2) comme la page d'accueil : tous les matchs du jour, filtrés sur cette compétition
    const wanted = new Set(SLUGS);
    const res = await Promise.all(OFFS.filter(o => o >= -2 && o <= 3).map(o => espn("all", "scoreboard", "?dates=" + day(o) + "&limit=1000", null).catch(() => null)));
    const evs = [];
    res.forEach(j => {
      if (!j) return;
      const ids = new Set((j.leagues || []).filter(l => wanted.has(l.slug)).map(l => String(l.id)));
      (j.events || []).forEach(e => { const lid = ((e.uid || "").match(/l:(\d+)/) || [])[1]; if (lid && ids.has(lid)) evs.push(e); });
    });
    const out2 = uniq(evs.map(normalize).filter(Boolean));
    if (out2.length) return out2;
    // 3) dernier recours : plage de dates
    const a = new Date(t), b = new Date(t); a.setDate(t.getDate() - 14); b.setDate(t.getDate() + 21);
    const qs = "?dates=" + ymd(a) + "-" + ymd(b) + "&limit=1000";
    for (const sl of SLUGS) {
      const j = await espn(sl, "scoreboard", qs, x => (x.events || []).length);
      if (j) return uniq(j.events.map(normalize).filter(Boolean));
    }
    return [];
  }

  const TS = "https://www.thesportsdb.com/api/v1/json/3/";
  let tsIdP = null;
  function tsId() {
    return tsIdP || (tsIdP = (async () => {
      const j = await fetchJSON(TS + "search_all_leagues.php?c=" + encodeURIComponent(TSDB_C) + "&s=Soccer");
      const ls = (j.countries || j.countrys || []).filter(l => !/women|cup|\b2\b|second|youth|u-?\d|amateur/i.test((l.strLeague || "") + " " + (l.strLeagueAlternate || "")));
      const top = ls.find(l => /botola|premier|pro/i.test(l.strLeague || "")) || ls[0];
      return top ? top.idLeague : "";
    })());
  }
  function tsNormalize(e) {
    const iso = e.strTimestamp ? (/[zZ]|\+/.test(e.strTimestamp) ? e.strTimestamp : e.strTimestamp.replace(" ", "T") + "Z") : (e.dateEvent + "T" + (e.strTime || "00:00:00") + "Z");
    const st = String(e.strStatus || ""), h = e.intHomeScore == null || e.intHomeScore === "" ? null : Number(e.intHomeScore), a = e.intAwayScore == null || e.intAwayScore === "" ? null : Number(e.intAwayScore);
    const off = /postpon|cancel|suspend|abandon/i.test(st);
    let state = "pre";
    if (!off) {
      if (/^(ft|aet|pen|match finished|finished|after)/i.test(st)) state = "post";
      else if (/^(1h|2h|ht|et|live|in progress|\d+')/i.test(st)) state = "in";
      else if (h != null && a != null && Date.now() - new Date(iso).getTime() > 3 * 3600e3) state = "post";
    }
    return { id: "ts" + e.idEvent, start: iso, state, off, label: off ? (st || "Reporté") : (st || ""), home: e.strHomeTeam, away: e.strAwayTeam, hl: e.strHomeTeamBadge, al: e.strAwayTeamBadge, h, a };
  }
  async function loadTsdb() {
    const id = await tsId(); if (!id) return [];
    const evs = [];
    for (const ep of ["eventsnextleague", "eventspastleague"]) {
      try { const j = await fetchJSON(TS + ep + ".php?id=" + id); (j.events || []).forEach(e => evs.push(tsNormalize(e))); } catch (e) { }
    }
    return evs.filter(m => m.home && m.away);
  }

  let matches = [], loaded = false, lastErr = "", lastOk = 0, tab = "m";
  const logo = u => u ? '<img class="m-logo" src="' + esc(u) + '" alt="" loading="lazy" onerror="this.remove()">' : "";
  function row(m) {
    const d = new Date(m.start).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" });
    const mid = m.state === "pre" ? (m.off ? esc(m.label) : "vs") : (m.h ?? 0) + " - " + (m.a ?? 0);
    const when = m.state === "in" ? '<span class="m-live">● ' + esc(m.label) + '</span>' : d + "<br>" + hhmm(m.start);
    return '<div class="m-row' + (m.state === "in" ? " live" : "") + '"><div class="m-date">' + when + '</div><div class="m-home">' + esc(m.home) + logo(m.hl) + '</div><div class="m-score' + (m.state === "pre" ? " next" : "") + '">' + mid + '</div><div class="m-away">' + logo(m.al) + esc(m.away) + '</div></div>';
  }
  function renderMatches() {
    const box = $("#cp-m"); if (!box) return;
    const t = localDay(new Date().toISOString());
    const asc = (a, b) => a.start.localeCompare(b.start), desc = (a, b) => b.start.localeCompare(a.start);
    const live = matches.filter(m => m.state === "in").sort(asc);
    const next = matches.filter(m => m.state === "pre" && localDay(m.start) >= t).sort(asc).slice(0, 15);
    const last = matches.filter(m => m.state === "post").sort(desc).slice(0, 15);
    const sec = (title, list, dot) => list.length ? '<div class="cp-sub">' + (dot ? '<span class="live-dot"></span>' : "") + title + '<span class="count">' + list.length + '</span></div>' + list.map(row).join("") : "";
    const h = sec("En direct", live, true) + sec("Prochains matchs", next) + sec("Derniers résultats", last);
    box.innerHTML = h || (!loaded ? skel(4) : '<div class="empty">' + (lastErr ? "⚠️ " + esc(lastErr) : "Aucun match trouvé pour cette compétition pour le moment.") + '</div>');
    const n = $("#cp-note");
    if (n) n.textContent = "Horaires affichés dans votre fuseau horaire." + (lastOk ? " Dernière mise à jour : " + new Date(lastOk).toLocaleTimeString("fr-FR") + "." : "");
    const u = $("#updated"); if (u && lastOk) u.textContent = "Dernière mise à jour : " + new Date(lastOk).toLocaleTimeString("fr-FR");
    const nt = $("#net-txt"), nb = $("#net-badge");
    if (nt) { nt.textContent = lastErr ? "Erreur" : "Direct"; if (nb) nb.classList.toggle("bad", !!lastErr); }
  }
  let timer = 0;
  async function refresh() {
    clearTimeout(timer);
    try { matches = TSDB_C ? await loadTsdb() : await loadEspn(); lastErr = ""; lastOk = Date.now(); }
    catch (e) { lastErr = "Données indisponibles : " + e.message; }
    loaded = true;
    if (tab === "m") renderMatches();
    const anyLive = matches.some(m => m.state === "in");
    timer = setTimeout(() => { if (document.hidden) { timer = setTimeout(refresh, 30000); } else refresh(); }, anyLive ? 30000 : 300000);
  }

  // ---------- Classement ----------
  const sval = (e, n) => { const x = (e.stats || []).find(z => z.name === n); return x ? (x.displayValue ?? x.value ?? "") : ""; };
  const isFav = n => favs.indexOf(n) >= 0;
  function stdHTML(d) {
    const groups = (d.children && d.children.length ? d.children : (d.groups || [d]));
    const html = groups.map(g => {
      const entries = (g.standings && g.standings.entries) || g.entries || [];
      if (!entries.length) return "";
      const name = g.name || g.header || "";
      const rows = entries.map((e, i) => {
        const t = (e.team && typeof e.team === "object") ? e.team : { displayName: typeof e.team === "string" ? e.team : "" };
        const tn = t.displayName || t.shortDisplayName || t.name || t.location || t.abbreviation || (typeof e.team === "string" ? e.team : "") || e.displayName || e.name || "";
        const lgo = (Array.isArray(e.logo) ? e.logo[0] : e.logo) || (t.logos && t.logos[0]) || t.logo || "", lg = (lgo && lgo.href) || (typeof lgo === "string" ? lgo : "");
        return '<tr class="' + (isFav(tn) ? "playing" : "") + '"><td>' + esc(sval(e, "rank") || i + 1) + '</td><td class="tn">' + (lg ? '<img src="' + esc(lg) + '" alt="" onerror="this.remove()">' : "") + esc(tn) + '</td><td>' + esc(sval(e, "gamesPlayed")) + '</td><td>' + esc(sval(e, "wins")) + '</td><td>' + esc(sval(e, "ties")) + '</td><td>' + esc(sval(e, "losses")) + '</td><td>' + esc(sval(e, "pointsFor")) + '</td><td>' + esc(sval(e, "pointsAgainst")) + '</td><td>' + esc(sval(e, "pointDifferential")) + '</td><td class="pts">' + esc(sval(e, "points")) + '</td></tr>';
      }).join("");
      return '<table><caption>Classement ' + esc(name) + '</caption><thead><tr><th>#</th><th>Équipe</th><th>J</th><th>G</th><th>N</th><th>P</th><th>BP</th><th>BC</th><th>Diff</th><th>Pts</th></tr></thead><tbody>' + rows + '</tbody></table>';
    }).join("");
    return html;
  }
  async function tsdbTable() {
    try {
      const id = await tsId(); if (!id) return "";
      const y = new Date().getFullYear();
      for (const s of [y + "-" + (y + 1), (y - 1) + "-" + y, String(y)]) {
        const j = await fetchJSON(TS + "lookuptable.php?l=" + id + "&s=" + s);
        if (j && j.table && j.table.length) {
          const f = (r, k) => esc(r[k] ?? "");
          return '<table><caption>Classement ' + esc(B.name) + ' ' + esc(s) + '</caption><thead><tr><th>#</th><th>Équipe</th><th>J</th><th>G</th><th>N</th><th>P</th><th>BP</th><th>BC</th><th>Diff</th><th>Pts</th></tr></thead><tbody>' +
            j.table.map(r => '<tr class="' + (isFav(r.strTeam) ? "playing" : "") + '"><td>' + f(r, "intRank") + '</td><td class="tn">' + (r.strBadge ? '<img src="' + esc(r.strBadge) + '/tiny" alt="" onerror="this.remove()">' : "") + f(r, "strTeam") + '</td><td>' + f(r, "intPlayed") + '</td><td>' + f(r, "intWin") + '</td><td>' + f(r, "intDraw") + '</td><td>' + f(r, "intLoss") + '</td><td>' + f(r, "intGoalsFor") + '</td><td>' + f(r, "intGoalsAgainst") + '</td><td>' + f(r, "intGoalDifference") + '</td><td class="pts">' + f(r, "intPoints") + '</td></tr>').join("") + '</tbody></table>';
        }
      }
    } catch (e) { }
    return "";
  }
  let stdDone = false;
  async function loadStd() {
    const box = $("#cp-s"); box.innerHTML = skel(6);
    let html = "";
    if (!TSDB_C || SLUGS.length) {
      for (const sl of SLUGS) { const j = await espn(sl, "standings", "", null); if (j) { const h = stdHTML(j); if (h) { html = h; break; } } }
    }
    if (!html && TSDB_C) html = await tsdbTable();
    box.innerHTML = html || '<div class="note">Classement indisponible pour cette compétition pour le moment.</div>';
    stdDone = !!html;
  }

  // ---------- Actus ----------
  const normDate = s => /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/.test(s || "") ? s.replace(" ", "T") + "Z" : s;
  const strip = h => { try { return (new DOMParser().parseFromString(h, "text/html").body.textContent || "").trim().slice(0, 220); } catch (e) { return ""; } };
  const ago = d => {
    const t = new Date(d).getTime(), s = (Date.now() - t) / 1000; if (isNaN(s)) return "";
    if (s < 3600) return "il y a " + Math.max(1, Math.round(s / 60)) + " min";
    if (s < 86400) return "il y a " + Math.round(s / 3600) + " h";
    return new Date(t).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
  };
  const newsCard = (a, i) => '<a class="news-card' + (i === 0 ? " first" : "") + '" href="' + esc(a.url) + '" target="_blank" rel="noopener"><div class="news-img"' + (a.img ? ' style="background-image:url(\'' + esc(encodeURI(a.img)) + '\')"' : "") + '><span>' + esc(a.src) + '</span></div><div class="news-body"><b>' + esc(a.title) + '</b>' + (a.desc ? '<p>' + esc(a.desc) + '</p>' : "") + '<small>' + esc(ago(a.date)) + '</small></div></a>';
  async function espnNews(sl) {
    const j = await espn(sl, "news", "?limit=30", x => (x.articles || []).length); if (!j) return [];
    return (j.articles || []).map(a => ({ title: a.headline || "", desc: a.description || "", img: httpUrl(((a.images || []).find(x => x.url) || {}).url), url: httpUrl(a.links && a.links.web && a.links.web.href), date: a.published || a.lastModified || "", src: "ESPN" })).filter(a => a.title && a.url);
  }
  async function rssNews() {
    const j = await fetchJSON("https://api.rss2json.com/v1/api.json?rss_url=" + encodeURIComponent("https://www.lequipe.fr/rss/actu_rss_Football.xml"), 12000);
    if (j.status !== "ok") return [];
    return (j.items || []).slice(0, 30).map(a => ({ title: a.title || "", desc: strip(a.description || a.content || ""), img: httpUrl(a.thumbnail || (a.enclosure && a.enclosure.link)), url: httpUrl(a.link), date: normDate(a.pubDate), src: "L’Équipe" })).filter(a => a.title && a.url);
  }
  let newsDone = false;
  async function loadNews() {
    const box = $("#cp-n"); box.innerHTML = skel(1, "tall") + skel(3, "tall");
    let items = [], general = false;
    for (const sl of SLUGS) { try { items = await espnNews(sl); } catch (e) { } if (items.length) break; }
    if (!items.length) { try { items = await rssNews(); general = items.length > 0; } catch (e) { } }
    box.innerHTML = items.length ? (general ? '<div class="note" style="grid-column:1/-1">Pas d’actus dédiées à cette compétition pour le moment : voici l’actualité du football en général.</div>' : "") + items.slice(0, 12).map(newsCard).join("") : '<div class="empty" style="grid-column:1/-1">Actualités indisponibles pour le moment. Réessayez dans un instant.</div>';
    newsDone = items.length > 0;
  }

  // ---------- Onglets ----------
  function show(t) {
    tab = t;
    $$(".cp-tabs button").forEach(b => b.classList.toggle("on", b.dataset.t === t));
    $("#cp-m").hidden = t !== "m"; $("#cp-s").hidden = t !== "s"; $("#cp-n").hidden = t !== "n";
    if (t === "m") renderMatches(); else if (t === "s" && !stdDone) loadStd(); else if (t === "n" && !newsDone) loadNews();
    try { history.replaceState(null, "", t === "m" ? location.pathname + location.search : "#" + (t === "s" ? "classement" : "actus")); } catch (e) { }
  }
  $(".cp-tabs").addEventListener("click", e => { const b = e.target.closest("button[data-t]"); if (b) show(b.dataset.t); });
  const fab = $("#fab-top");
  if (fab) { window.addEventListener("scroll", () => fab.classList.toggle("show", window.scrollY > 600), { passive: true }); fab.onclick = () => window.scrollTo({ top: 0, behavior: "smooth" }); }
  const h0 = location.hash.slice(1);
  show(h0 === "classement" ? "s" : h0 === "actus" ? "n" : "m");
  refresh();
  document.addEventListener("visibilitychange", () => { if (!document.hidden && Date.now() - lastOk > 60000) refresh(); });
})();

/* Logo de la Botola Pro dans la barre des compétitions (TheSportsDB, ligue 4520), mémorisé pour les autres pages */
(function () {
  try {
    var img = document.querySelector('#compbar a[href="botola-pro.html"] .cl');
    if (!img || img.getAttribute("src")) return;
    var st = {}; try { st = JSON.parse(localStorage.getItem("fl_cl") || "{}"); } catch (e) { }
    if (st["botola-pro"]) { img.classList.add("lt"); img.src = st["botola-pro"]; return; }
    fetch("https://www.thesportsdb.com/api/v1/json/3/lookupleague.php?id=4520").then(function (r) { return r.json(); }).then(function (j) {
      var l = j && j.leagues && j.leagues[0], u = l && (l.strBadge || l.strLogo);
      if (u && /^https?:/i.test(u)) { img.classList.add("lt"); img.src = u; st["botola-pro"] = u; try { localStorage.setItem("fl_cl", JSON.stringify(st)); } catch (e) { } }
    }).catch(function () { });
  } catch (e) { }
})();

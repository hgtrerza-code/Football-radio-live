// Génère l'aperçu des matchs du jour en HTML statique (pour les robots sans JavaScript)
// et l'injecte dans index.html entre les repères APERCU-START / APERCU-END.
// Aucune dépendance : Node 18+ suffit.
import fs from "node:fs";

const TZ = "Europe/Paris";
const FILE = "index.html";
const JSON_FILE = "matchs-du-jour.json";
const PROXY = "https://footlive.hgtrerza.workers.dev/soccer/";            // votre Worker (même source que le site)
const ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/";     // secours direct
const MAX_PER_LEAGUE = 12, MAX_TOTAL = 80, MAX_LD = 25;

// Compétitions principales : interrogées une par une, donc leur nom est toujours connu. L'ordre = l'ordre d'affichage.
const TOP = [
  ["uefa.champions", "Ligue des champions"], ["uefa.europa", "Ligue Europa"], ["uefa.europa.conf", "Ligue Conférence"],
  ["eng.1", "Premier League"], ["esp.1", "LaLiga"], ["ita.1", "Serie A"], ["ger.1", "Bundesliga"], ["fra.1", "Ligue 1"],
  ["por.1", "Liga Portugal"], ["ned.1", "Eredivisie"], ["bel.1", "Jupiler Pro League"], ["tur.1", "Süper Lig"],
  ["usa.1", "MLS"], ["bra.1", "Brasileirão"], ["arg.1", "Liga argentine"], ["mex.1", "Liga MX"], ["jpn.1", "J1 League"],
  ["eng.2", "Championship"], ["fra.2", "Ligue 2"], ["esp.2", "LaLiga 2"], ["ita.2", "Serie B"], ["ger.2", "2. Bundesliga"],
  ["eng.fa", "FA Cup"], ["eng.league_cup", "Coupe de la Ligue anglaise"], ["esp.copa_del_rey", "Coupe du Roi"],
  ["fra.coupe_de_france", "Coupe de France"], ["ger.dfb_pokal", "Coupe d’Allemagne"], ["ita.coppa_italia", "Coupe d’Italie"],
  ["conmebol.libertadores", "Copa Libertadores"], ["conmebol.sudamericana", "Copa Sudamericana"], ["fifa.world", "Coupe du monde"]
];
const BLOCK = /ncaa|bolivia|scotti?s?h|scotland|isra[eëé]l|ligat ha|liga leumit|toto cup|liga portugal 2|liga portugal ii|segunda liga|ligapro|liga 2 sabseg|portug.* liga 2|ligat|leumit|liga alef|winner league/i;
const FR = [
  [/^uefa champions league$/i, "Ligue des champions"], [/^uefa europa league$/i, "Ligue Europa"],
  [/^uefa (europa )?conference league$/i, "Ligue Conférence"], [/^english premier league$/i, "Premier League"],
  [/^spanish la ?liga$/i, "LaLiga"], [/^italian serie a$/i, "Serie A"],
  [/^german bundesliga$/i, "Bundesliga"], [/^french ligue 1$/i, "Ligue 1"]
];
const GENERIC = /^(?:the )?(?:first|second|third|fourth|fifth|sixth|seventh|1st|2nd|3rd|4th|5th|6th|preliminary|qualifying|group|knockout|round|quarter|semi|final|play-?offs?|league phase|matchday|regular season|stage|phase)\b/i;
const OTHER = "Football — autres compétitions";

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const dayOf = d => new Date(d).toLocaleDateString("sv-SE", { timeZone: TZ });
const hhmm = iso => new Date(iso).toLocaleTimeString("fr-FR", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
const frName = raw => { const hit = FR.find(([re]) => re.test(raw.trim())); return hit ? hit[1] : raw.trim(); };

async function getJSON(url, ms = 20000) {
  const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(url, { signal: ctl.signal, headers: { "user-agent": "footlivepro-static-preview" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  } finally { clearTimeout(t); }
}
async function firstOf(urls, ms) {
  let last;
  for (const u of urls) { try { return await getJSON(u, ms); } catch (e) { last = e; } }
  throw last;
}
const loadAll = ymd => firstOf([PROXY + "all/scoreboard?dates=" + ymd + "&limit=1000", ESPN + "all/scoreboard?dates=" + ymd + "&limit=1000"]);
const loadSlug = (slug, ymd) => firstOf([PROXY + slug + "/scoreboard?dates=" + ymd + "&limit=300", ESPN + slug + "/scoreboard?dates=" + ymd + "&limit=300"], 10000);

function rawLeague(ev, top) {
  const c = (ev.competitions && ev.competitions[0]) || {};
  const lid = ((ev.uid || "").match(/l:(\d+)/) || [])[1] || "";
  const fromTop = (top.leagues || []).find(l => String(l.id) === lid);
  return { lid, raw: ((ev.league && ev.league.name) || (c.league && c.league.name) || (fromTop && fromTop.name) || "").trim() };
}
function normalize(ev, top) {
  const c = (ev.competitions && ev.competitions[0]) || {}, cp = c.competitors || [];
  const home = cp.find(x => x.homeAway === "home") || cp[0], away = cp.find(x => x.homeAway === "away") || cp[1];
  if (!home || !away) return null;
  const st = (ev.status && ev.status.type) || {};
  const off = /postponed|cancel|suspend|abandon/i.test((st.name || "") + " " + (st.description || ""));
  const num = v => (v === undefined || v === "" || v === null) ? null : Number(v);
  return {
    id: String(ev.id), ...rawLeague(ev, top), lg: "", known: false, start: ev.date,
    state: off ? "off" : (st.state || "pre"),
    label: (ev.status && ev.status.displayClock) || st.shortDetail || "",
    home: home.team.displayName || home.team.name, away: away.team.displayName || away.team.name,
    h: num(home.score), a: num(away.score)
  };
}
// Compétitions hors liste : on retrouve le nom via l'identifiant ESPN (comme le fait le site). Si ça échoue, le match est ignoré.
async function resolveLeagueNames(list) {
  const need = [...new Set(list.filter(m => !m.raw || GENERIC.test(m.raw)).map(m => m.lid).filter(Boolean))];
  const names = {};
  await Promise.allSettled(need.map(async id => {
    try { const j = await getJSON("https://sports.core.api.espn.com/v2/sports/soccer/leagues/" + id, 8000); names[id] = j.name || j.shortName || ""; } catch (e) { }
  }));
  for (const m of list) {
    const ok = m.raw && !GENERIC.test(m.raw);
    const name = ok ? m.raw : (names[m.lid] || "");
    m.lg = name ? frName(name) : OTHER;
  }
  return need.length ? Object.values(names).filter(Boolean).length + "/" + need.length : "0/0";
}
const rank = lg => { const i = TOP.findIndex(([, n]) => n === lg); return i < 0 ? 99 : i; };
function statusText(m) {
  if (m.state === "off") return "reporté";
  if (m.state === "in") return "en direct" + (m.label ? ", " + m.label : "");
  if (m.state === "post") return "terminé";
  return "à venir";
}
function line(m) {
  const score = m.state === "pre" || m.state === "off" || m.h === null || m.a === null ? " – " : " " + m.h + "–" + m.a + " ";
  return '<li><time datetime="' + esc(m.start) + '">' + hhmm(m.start) + "</time> — " + esc(m.home) + score + esc(m.away) + " <small>(" + esc(statusText(m)) + ")</small></li>";
}

async function main() {
  const now = new Date(), today = dayOf(now);
  const base = new Date(today + "T12:00:00Z");
  const ymdOf = n => new Date(base.getTime() + n * 864e5).toISOString().slice(0, 10).replace(/-/g, "");
  const dates = [-1, 0, 1].map(ymdOf), topDates = [-1, 0].map(ymdOf);

  const allRes = await Promise.allSettled(dates.map(loadAll));
  const topJobs = TOP.flatMap(([slug, name]) => topDates.map(d => loadSlug(slug, d).then(j => ({ j, name }))));
  const topRes = await Promise.allSettled(topJobs);
  const okAll = allRes.filter(r => r.status === "fulfilled").length, okTop = topRes.filter(r => r.status === "fulfilled").length;
  console.log("Flux général : " + okAll + "/" + dates.length + " ; compétitions principales : " + okTop + "/" + topJobs.length + " requêtes réussies.");
  if (!okAll && !okTop) throw new Error("Aucune source de scores n'a répondu : index.html non modifié.");

  const seen = new Map();
  for (const r of allRes) if (r.status === "fulfilled") for (const ev of (r.value.events || [])) {
    const m = normalize(ev, r.value); if (m && dayOf(m.start) === today) seen.set(m.id, m);
  }
  for (const r of topRes) if (r.status === "fulfilled") for (const ev of (r.value.j.events || [])) {
    const m = normalize(ev, r.value.j);
    if (m && dayOf(m.start) === today) { m.lg = r.value.name; m.known = true; seen.set(m.id, m); }
  }
  const stat = await resolveLeagueNames([...seen.values()].filter(m => !m.known));
  const kept0 = [...seen.values()].filter(m => !BLOCK.test(m.lg) && !BLOCK.test(m.raw));
  const named = kept0.filter(m => m.lg !== OTHER)
    .sort((a, b) => rank(a.lg) - rank(b.lg) || a.lg.localeCompare(b.lg) || a.start.localeCompare(b.start));
  console.log("Matchs du jour : " + kept0.length + " (compétitions reconnues : " + named.length + ", noms retrouvés via l'identifiant : " + stat + ").");

  const groups = new Map(); let kept = 0;
  for (const m of named) {
    if (kept >= MAX_TOTAL) break;
    const g = groups.get(m.lg) || []; if (g.length >= MAX_PER_LEAGUE) continue;
    g.push(m); groups.set(m.lg, g); kept++;
  }
  const extra = kept0.length - kept;
  const matches = [...groups.values()].flat().map(({ raw, lid, known, ...m }) => m);

  // Rien de changé depuis la dernière exécution : on ne touche à rien (pas de commit inutile).
  let prev = null; try { prev = JSON.parse(fs.readFileSync(JSON_FILE, "utf8")); } catch (e) { }
  if (prev && prev.date === today && JSON.stringify(prev.matches) === JSON.stringify(matches) && prev.extra === extra) { console.log("Aucun changement."); return; }

  const longDate = now.toLocaleDateString("fr-FR", { timeZone: TZ, weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const upd = now.toLocaleTimeString("fr-FR", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
  let body = "";
  if (!matches.length) body = "<p>Aucun match des principales compétitions n’est programmé aujourd’hui.</p>";
  else {
    for (const [lg, ms] of groups) body += "<h3>" + esc(lg) + "</h3><ul>" + ms.map(line).join("") + "</ul>";
  }
  if (extra > 0) body += "<p>… et " + extra + " autres matchs à retrouver dans l’application ci-dessus.</p>";
  const section = '<!--APERCU-START--><section id="apercu-matchs" aria-label="Aperçu des matchs du jour">' +
    "<h2>Matchs de football du jour : " + esc(longDate) + "</h2>" +
    "<p class=\"ap-upd\">Aperçu mis à jour à " + upd + " (heure de Paris). Les scores en direct s’actualisent dans l’application ci-dessus.</p>" +
    body + "</section><!--APERCU-END-->";

  const ld = matches.slice(0, MAX_LD).map(m => ({
    "@type": "SportsEvent", name: m.home + " - " + m.away, startDate: m.start, sport: "Football",
    eventStatus: m.state === "off" ? "https://schema.org/EventPostponed" : "https://schema.org/EventScheduled",
    location: { "@type": "Place", name: m.lg },
    homeTeam: { "@type": "SportsTeam", name: m.home }, awayTeam: { "@type": "SportsTeam", name: m.away },
    url: "https://www.footlivepro.com/"
  }));
  const ldBlock = "<!--APERCU-LD-START-->" + (ld.length ? '<script type="application/ld+json">' + JSON.stringify({ "@context": "https://schema.org", "@graph": ld }).replace(/</g, "\\u003c") + "</script>" : "") + "<!--APERCU-LD-END-->";

  let html = fs.readFileSync(FILE, "utf8");
  const reS = /<!--APERCU-START-->[\s\S]*?<!--APERCU-END-->/, reL = /<!--APERCU-LD-START-->[\s\S]*?<!--APERCU-LD-END-->/;
  if (!reS.test(html) || !reL.test(html)) throw new Error("Repères APERCU-START/END ou APERCU-LD-START/END introuvables dans " + FILE);
  html = html.replace(reS, () => section).replace(reL, () => ldBlock);
  fs.writeFileSync(FILE, html);
  fs.writeFileSync(JSON_FILE, JSON.stringify({ date: today, generated: now.toISOString(), extra, matches }, null, 1));
  console.log(matches.length + " matchs écrits pour le " + today);
}
main().catch(e => { console.error(e.message); process.exit(1); });

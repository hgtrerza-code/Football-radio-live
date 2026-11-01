// Génère l'aperçu des matchs du jour en HTML statique (pour les robots sans JavaScript)
// et l'injecte dans index.html entre les repères APERCU-START / APERCU-END.
// Aucune dépendance : Node 18+ suffit.
import fs from "node:fs";

const TZ = "Europe/Paris";
const FILE = "index.html";
const JSON_FILE = "matchs-du-jour.json";
const SOURCES = [
  "https://footlive.hgtrerza.workers.dev/soccer/all/scoreboard", // votre Worker (même source que le site)
  "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
];
const MAX_PER_LEAGUE = 12, MAX_TOTAL = 80, MAX_LD = 25;

const BLOCK = /ncaa|bolivia|scotti?s?h|scotland|isra[eëé]l|ligat ha|liga leumit|toto cup|liga portugal 2|liga portugal ii|segunda liga|ligapro|liga 2 sabseg|portug.* liga 2|ligat|leumit|liga alef|winner league/i;
const PRIORITY = [/ligue des champions|champions league/i, /ligue europa|europa league/i, /ligue conf|conference league/i, /premier league/i, /laliga|la liga/i, /serie a/i, /bundesliga/i, /ligue 1/i, /primeira|liga portugal/i, /eredivisie/i, /mls|major league soccer/i];
const FR = [
  [/^uefa champions league$/i, "Ligue des champions"], [/^uefa europa league$/i, "Ligue Europa"],
  [/^uefa (europa )?conference league$/i, "Ligue Conférence"], [/^english premier league$/i, "Premier League"],
  [/^spanish la ?liga$/i, "LaLiga"], [/^italian serie a$/i, "Serie A"],
  [/^german bundesliga$/i, "Bundesliga"], [/^french ligue 1$/i, "Ligue 1"]
];

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const dayOf = d => new Date(d).toLocaleDateString("sv-SE", { timeZone: TZ });
const hhmm = iso => new Date(iso).toLocaleTimeString("fr-FR", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });

async function getJSON(url, ms = 20000) {
  const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(url, { signal: ctl.signal, headers: { "user-agent": "footlivepro-static-preview" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return await r.json();
  } finally { clearTimeout(t); }
}
async function loadDate(ymd) {
  let last;
  for (const base of SOURCES) {
    try { return await getJSON(base + "?dates=" + ymd + "&limit=1000"); } catch (e) { last = e; }
  }
  throw last;
}
const GENERIC = /^(?:the )?(?:first|second|third|fourth|fifth|sixth|seventh|1st|2nd|3rd|4th|5th|6th|preliminary|qualifying|group|knockout|round|quarter|semi|final|play-?offs?|league phase|matchday|regular season|stage|phase)\b/i;
const OTHER = "Football — autres compétitions";
function rawLeague(ev, top) {
  const c = (ev.competitions && ev.competitions[0]) || {};
  const lid = ((ev.uid || "").match(/l:(\d+)/) || [])[1] || "";
  const fromTop = (top.leagues || []).find(l => String(l.id) === lid);
  return { lid, raw: ((ev.league && ev.league.name) || (c.league && c.league.name) || (fromTop && fromTop.name) || "").trim() };
}
const frName = raw => { const hit = FR.find(([re]) => re.test(raw.trim())); return hit ? hit[1] : raw.trim(); };
// Le flux "all" ne donne pas toujours le nom de la compétition : on le retrouve via l'identifiant ESPN (comme le fait le site).
async function resolveLeagueNames(list) {
  const need = [...new Set(list.filter(m => !m.raw || GENERIC.test(m.raw)).map(m => m.lid).filter(Boolean))];
  const names = {};
  await Promise.allSettled(need.map(async id => {
    try { const j = await getJSON("https://sports.core.api.espn.com/v2/sports/soccer/leagues/" + id, 8000); names[id] = j.name || j.shortName || ""; } catch (e) { }
  }));
  for (const m of list) {
    const fixed = (!m.raw || GENERIC.test(m.raw)) ? names[m.lid] : "";
    m.lg = frName(fixed || (m.raw && !GENERIC.test(m.raw) ? m.raw : "") || OTHER);
  }
}
function normalize(ev, top) {
  const c = (ev.competitions && ev.competitions[0]) || {}, cp = c.competitors || [];
  const home = cp.find(x => x.homeAway === "home") || cp[0], away = cp.find(x => x.homeAway === "away") || cp[1];
  if (!home || !away) return null;
  const st = (ev.status && ev.status.type) || {};
  const off = /postponed|cancel|suspend|abandon/i.test((st.name || "") + " " + (st.description || ""));
  const num = v => (v === undefined || v === "" || v === null) ? null : Number(v);
  return {
    id: String(ev.id), ...rawLeague(ev, top), lg: "", start: ev.date,
    state: off ? "off" : (st.state || "pre"),
    label: (ev.status && ev.status.displayClock) || st.shortDetail || "",
    home: home.team.displayName || home.team.name, away: away.team.displayName || away.team.name,
    h: num(home.score), a: num(away.score)
  };
}
const rank = lg => { const i = PRIORITY.findIndex(re => re.test(lg)); return i < 0 ? 99 : i; };
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
  const base = new Date(today + "T12:00:00Z"), dates = [-1, 0, 1].map(n => {
    const d = new Date(base.getTime() + n * 864e5); return d.toISOString().slice(0, 10).replace(/-/g, "");
  });
  const results = await Promise.allSettled(dates.map(loadDate));
  if (!results.some(r => r.status === "fulfilled")) throw new Error("Aucune source de scores n'a répondu : index.html non modifié.");

  const seen = new Map();
  for (const r of results) if (r.status === "fulfilled") for (const ev of (r.value.events || [])) {
    const m = normalize(ev, r.value);
    if (m && dayOf(m.start) === today) seen.set(m.id, m);
  }
  await resolveLeagueNames([...seen.values()]);
  const all = [...seen.values()].filter(m => !BLOCK.test(m.lg) && !BLOCK.test(m.raw)).sort((a, b) => rank(a.lg) - rank(b.lg) || a.lg.localeCompare(b.lg) || a.start.localeCompare(b.start));
  const groups = new Map(); let kept = 0;
  for (const m of all) {
    if (kept >= MAX_TOTAL) break;
    const g = groups.get(m.lg) || []; if (g.length >= MAX_PER_LEAGUE) continue;
    g.push(m); groups.set(m.lg, g); kept++;
  }
  const extra = all.length - kept;
  const matches = [...groups.values()].flat().map(({ raw, lid, ...m }) => m);

  // Rien de changé depuis la dernière exécution : on ne touche à rien (pas de commit inutile).
  let prev = null; try { prev = JSON.parse(fs.readFileSync(JSON_FILE, "utf8")); } catch (e) { }
  const sig = JSON.stringify(matches);
  if (prev && prev.date === today && JSON.stringify(prev.matches) === sig) { console.log("Aucun changement."); return; }

  const longDate = now.toLocaleDateString("fr-FR", { timeZone: TZ, weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const upd = now.toLocaleTimeString("fr-FR", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
  let body = "";
  if (!matches.length) body = "<p>Aucun match de football n’est programmé aujourd’hui dans les compétitions suivies.</p>";
  else {
    for (const [lg, ms] of groups) body += "<h3>" + esc(lg) + "</h3><ul>" + ms.map(line).join("") + "</ul>";
    if (extra > 0) body += "<p>… et " + extra + " autres matchs à retrouver dans l’application ci-dessus.</p>";
  }
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
  fs.writeFileSync(JSON_FILE, JSON.stringify({ date: today, generated: now.toISOString(), matches }, null, 1));
  console.log(matches.length + " matchs écrits pour le " + today);
}
main().catch(e => { console.error(e.message); process.exit(1); });

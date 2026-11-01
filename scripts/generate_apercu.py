#!/usr/bin/env python3
"""FootLive Pro : génère l'aperçu statique (HTML + JSON-LD) des pages.

Pour les 10 pages compétitions : matchs du jour, derniers résultats,
prochains matchs et classement, lisibles sans JavaScript.
index.html n'est PAS modifié (il reste géré par update-apercu.mjs) ;
ajouter l'option --index pour que ce script s'en charge aussi.
Utilise uniquement la bibliothèque standard Python. À lancer à la racine du dépôt.
"""
import html, json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SITE = "https://www.footlivepro.com/"
WORKER = "https://footlive.hgtrerza.workers.dev/"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/"
ESPN_STD = "https://site.api.espn.com/apis/v2/sports/soccer/"
PARIS = ZoneInfo("Europe/Paris")

# page (sans .html) : (nom affiché, codes de ligue essayés dans l'ordre)
COMPS = {
    "ligue-des-champions": ("Ligue des champions", ("uefa.champions",)),
    "premier-league": ("Premier League", ("eng.1",)),
    "laliga": ("LaLiga", ("esp.1",)),
    "serie-a": ("Serie A", ("ita.1",)),
    "bundesliga": ("Bundesliga", ("ger.1",)),
    "ligue-1": ("Ligue 1", ("fra.1",)),
    "europa-league": ("Europa League", ("uefa.europa",)),
    "conference-league": ("Conference League", ("uefa.europa.conf",)),
    "liga-portugal": ("Liga Portugal", ("por.1",)),
    "botola-pro": ("Botola Pro", ("mar.1", "mor.1")),
}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]

CSS = ("#apercu-matchs{margin:1.5rem 0 0;padding:1rem 0;border-top:1px solid var(--border);color:var(--text-muted);font-size:.85rem;line-height:1.6}"
       "#apercu-matchs h2{font-size:1rem;font-weight:700;color:var(--text-main);margin-bottom:.25rem}"
       "#apercu-matchs h3{font-size:.9rem;font-weight:600;color:var(--text-main);margin:.9rem 0 .25rem}"
       "#apercu-matchs ul{list-style:none;padding:0}#apercu-matchs li{padding:.15rem 0}"
       "#apercu-matchs time{color:var(--accent);font-weight:600;margin-right:.25rem}"
       "#apercu-matchs .ap-upd{font-size:.75rem}"
       "#apercu-matchs .ap-tbl{overflow-x:auto}#apercu-matchs table{border-collapse:collapse;width:100%;font-size:.8rem}"
       "#apercu-matchs th,#apercu-matchs td{padding:.2rem .45rem;text-align:center;border-bottom:1px solid var(--border)}"
       "#apercu-matchs td:nth-child(2),#apercu-matchs th:nth-child(2){text-align:left}")

esc = lambda s: html.escape(str(s), quote=True)


def fr_date(d):
    return f"{JOURS[d.weekday()]} {d.day}{'er' if d.day == 1 else ''} {MOIS[d.month - 1]} {d.year}"


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (FootLivePro-apercu)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch(kind, slug, query=""):
    """Renvoie le JSON (Worker d'abord, puis ESPN direct) ou None."""
    mock = os.environ.get("MOCK_DIR")
    if mock:
        p = os.path.join(mock, f"{kind}_{slug}.json")
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    base = ESPN_STD if kind == "standings" else ESPN
    for u in (f"{WORKER}soccer/{slug}/{kind}{query}", f"{base}{slug}/{kind}{query}"):
        try:
            d = http_get(u)
        except Exception:
            continue
        if isinstance(d, dict) and ("events" in d or "children" in d or "standings" in d):
            return d
    return None


def to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def parse_events(d, league):
    out = []
    for ev in (d or {}).get("events") or []:
        c = (ev.get("competitions") or [{}])[0]
        cp = c.get("competitors") or []
        home = next((x for x in cp if x.get("homeAway") == "home"), cp[0] if cp else None)
        away = next((x for x in cp if x.get("homeAway") == "away"), cp[1] if len(cp) > 1 else None)
        if not home or not away:
            continue
        st = (ev.get("status") or {}).get("type") or {}
        off = bool(re.search(r"postponed|cancel|suspend|abandon", (st.get("name") or "") + " " + (st.get("description") or ""), re.I))
        try:
            start = datetime.fromisoformat(str(ev.get("date")).replace("Z", "+00:00"))
        except ValueError:
            continue
        out.append({
            "start": start, "league": league, "off": off,
            "state": "pre" if off else (st.get("state") or "pre"),
            "clock": ((ev.get("status") or {}).get("displayClock") or "").strip(),
            "home": (home.get("team") or {}).get("displayName") or "?",
            "away": (away.get("team") or {}).get("displayName") or "?",
            "hs": to_int(home.get("score")), "as": to_int(away.get("score")),
        })
    out.sort(key=lambda m: m["start"])
    return out


def parse_standings(d):
    rows = []
    groups = (d or {}).get("children") or ([d] if d else [])
    for g in groups:
        entries = ((g or {}).get("standings") or {}).get("entries") or (g or {}).get("entries") or []
        for e in entries:
            t = e.get("team")
            name = (t.get("displayName") or t.get("name")) if isinstance(t, dict) else str(t or "")
            if not name:
                continue
            stats = {s.get("name"): s for s in e.get("stats") or []}
            v = lambda n: "" if n not in stats else str(stats[n].get("displayValue", stats[n].get("value", "")))
            rows.append((v("rank") or str(len(rows) + 1), name, v("gamesPlayed"), v("wins"), v("ties"), v("losses"), v("pointDifferential"), v("points")))
    if len(groups) == 1 and rows and all(r[0].isdigit() for r in rows):
        rows.sort(key=lambda r: int(r[0]))
    return rows[:36]


def li(m, with_date=False):
    t = m["start"].astimezone(PARIS)
    label = t.strftime("%d/%m %H:%M") if with_date else t.strftime("%H:%M")
    if m["state"] == "pre":
        score = f'{m["home"]} – {m["away"]}'
    else:
        score = f'{m["home"]} {m["hs"] if m["hs"] is not None else 0}–{m["as"] if m["as"] is not None else 0} {m["away"]}'
    status = "reporté" if m["off"] else {"pre": "à venir", "post": "terminé"}.get(m["state"]) or ("en direct, " + m["clock"] if m["clock"] else "en direct")
    iso = m["start"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    return f'<li><time datetime="{iso}">{label}</time> — {esc(score)} <small>({esc(status)})</small></li>'


def ul(ms, with_date=False):
    return "<ul>" + "".join(li(m, with_date) for m in ms) + "</ul>"


def std_html(name, rows):
    if not rows:
        return ""
    body = "".join("<tr>" + "".join(f"<td>{esc(c)}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<h3 class="ap-std">Classement {esc(name)}</h3><div class="ap-tbl"><table><thead><tr><th>#</th><th>Équipe</th>'
            f'<th>J</th><th>G</th><th>N</th><th>P</th><th>Diff</th><th>Pts</th></tr></thead><tbody>{body}</tbody></table></div>')


def split(evs, now):
    today = now.date()
    tod = [m for m in evs if m["start"].astimezone(PARIS).date() == today]
    res = sorted([m for m in evs if m not in tod and m["state"] == "post"], key=lambda m: m["start"], reverse=True)[:10]
    nxt = [m for m in evs if m not in tod and m["state"] == "pre" and m["start"].astimezone(PARIS) > now][:10]
    return tod, res, nxt


def comp_section(name, evs, std, now, old_std=""):
    tod, res, nxt = split(evs, now)
    p = [f'<section id="apercu-matchs" aria-label="Aperçu {esc(name)}">',
         f"<h2>{esc(name)} : matchs du jour, {fr_date(now.date())}</h2>",
         f'<p class="ap-upd">Aperçu mis à jour à {now:%H:%M} (heure de Paris). Les scores en direct s’actualisent dans l’application ci-dessus.</p>']
    p.append(ul(tod) if tod else f"<p>Aucun match de {esc(name)} aujourd’hui.</p>")
    if res:
        p += [f"<h3>Derniers résultats {esc(name)}</h3>", ul(res, True)]
    if nxt:
        p += [f"<h3>Prochains matchs {esc(name)}</h3>", ul(nxt, True)]
    p.append(std_html(name, std) or old_std)
    p.append("</section>")
    return "".join(p), tod + nxt


def index_section(per_comp, others, now):
    p = ['<section id="apercu-matchs" aria-label="Aperçu des matchs du jour">',
         f"<h2>Matchs de football du jour : {fr_date(now.date())}</h2>",
         f'<p class="ap-upd">Aperçu mis à jour à {now:%H:%M} (heure de Paris). Les scores en direct s’actualisent dans l’application ci-dessus.</p>']
    shown, ld = 0, []
    for name, evs in per_comp:
        tod, _, nxt = split(evs, now)
        if tod:
            p += [f"<h3>{esc(name)}</h3>", ul(tod)]
            shown += len(tod)
        ld += tod
    if not shown:
        p.append("<p>Aucun match des grandes compétitions aujourd’hui.</p>")
    if others and others > shown:
        p.append(f"<p>… et {others - shown} autres matchs à retrouver dans l’application ci-dessus.</p>")
    p.append("</section>")
    return "".join(p), ld


def ld_block(evs, page_url):
    graph = [{
        "@type": "SportsEvent", "name": f'{m["home"]} - {m["away"]}',
        "startDate": m["start"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "sport": "Football",
        "eventStatus": "https://schema.org/EventPostponed" if m["off"] else "https://schema.org/EventScheduled",
        "location": {"@type": "Place", "name": m["league"]},
        "homeTeam": {"@type": "SportsTeam", "name": m["home"]},
        "awayTeam": {"@type": "SportsTeam", "name": m["away"]}, "url": page_url,
    } for m in evs[:40]]
    if not graph:
        return ""
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">' + data.replace("</", "<\\/") + "</script>"


def inject(text, start, end, block, fallback):
    wrapped = start + block + end
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pat.search(text):
        return pat.sub(lambda m: wrapped, text, count=1)
    return fallback(text, wrapped)


def put_section(text, wrapped):
    m = re.search(r'<p class="note" id="static-note"></p>', text)
    if m:
        return text[:m.end()] + wrapped + text[m.end():]
    print("  ! point d'insertion introuvable (static-note)")
    return text


def put_before(tag):
    def f(text, wrapped):
        i = text.find(tag)
        return text[:i] + wrapped + text[i:] if i >= 0 else text
    return f


def ensure_css(text):
    block = f'<style id="apercu-css">{CSS}</style>'
    if 'id="apercu-css"' in text:
        return re.sub(r'<style id="apercu-css">.*?</style>', lambda m: block, text, count=1, flags=re.S)
    return put_before("</head>")(text, block)


def norm(t):
    return re.sub(r"mis à jour à \d\d:\d\d", "mis à jour à XX", t)


def write_if_changed(path, old, new):
    if norm(old) == norm(new):
        print(f"= {path} : inchangé")
        return
    open(path, "w", encoding="utf-8", newline="").write(new)
    print(f"✓ {path} : mis à jour")


def main():
    now = datetime.now(PARIS)
    q = f"?dates={now.date() - timedelta(days=3):%Y%m%d}-{now.date() + timedelta(days=7):%Y%m%d}&limit=300"
    per_comp = []
    for slug, (name, codes) in COMPS.items():
        ev = std = None
        for code in codes:
            e, s = fetch("scoreboard", code, q), fetch("standings", code)
            if (e and e.get("events")) or s:
                ev, std = e, s
                break
            ev = ev or e
        events = parse_events(ev, name)
        rows = parse_standings(std)
        path = f"{slug}.html"
        if ev is None and std is None:
            print(f"! {name} : aucune donnée, page laissée telle quelle")
            per_comp.append((name, None))
            continue
        per_comp.append((name, events))
        if not os.path.exists(path):
            print(f"- {path} absent, ignoré")
            continue
        old = open(path, encoding="utf-8", newline="").read()
        m = re.search(r'<h3 class="ap-std">.*?</table></div>', old, re.S)
        sec, ld_evs = comp_section(name, events, rows, now, m.group(0) if m and not rows else "")
        new = inject(old, "<!--APERCU-START-->", "<!--APERCU-END-->", sec, put_section)
        new = inject(new, "<!--APERCU-LD-START-->", "<!--APERCU-LD-END-->", ld_block(ld_evs, f"{SITE}{slug}.html"), put_before("<title>"))
        write_if_changed(path, old, ensure_css(new))

    ok = [(n, e) for n, e in per_comp if e is not None]
    if "--index" in sys.argv and os.path.exists("index.html") and ok:
        others = 0
        allq = f"?dates={now.date():%Y%m%d}&limit=1000"
        d = fetch("scoreboard", "all", allq)
        if d:
            others = len(d.get("events") or [])
        old = open("index.html", encoding="utf-8", newline="").read()
        sec, ld_evs = index_section(ok, others, now)
        new = inject(old, "<!--APERCU-START-->", "<!--APERCU-END-->", sec, put_section)
        new = inject(new, "<!--APERCU-LD-START-->", "<!--APERCU-LD-END-->", ld_block(ld_evs, SITE), put_before("<title>"))
        write_if_changed("index.html", old, ensure_css(new))
    return 0


if __name__ == "__main__":
    sys.exit(main())

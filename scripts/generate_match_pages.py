#!/usr/bin/env python3
"""FootLive Pro : génère une page statique INDEXABLE par match (matchs/<equipes>-<id>.html),
la page hub /matchs-du-jour.html et sitemap-matchs.xml.

Pourquoi : les internautes cherchent « PSG Marseille heure chaîne score » ; jusqu'ici aucune page
du site ne pouvait se positionner sur ces requêtes (match.html est en noindex).

Source : matchs-du-jour.json (écrit par scripts/update-apercu.mjs). Bibliothèque standard uniquement.
Un registre (matchs/_registre.json) garde les matchs des derniers jours : la page d'un match reste en ligne
(et passe à « terminé ») au lieu de disparaître en 404. Les pages de plus de KEEP_DAYS jours sont supprimées.

À lancer à la racine du dépôt :  python3 scripts/generate_match_pages.py [--ping]
  --ping : prévient Bing/Yandex (IndexNow) des nouvelles pages.
"""
import html, json, os, re, sys, unicodedata, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SITE = "https://www.footlivepro.com"
KEEP_DAYS = 10
DIR = "matchs"
REG = os.path.join(DIR, "_registre.json")
INDEXNOW_KEY = "b7e3f1a94c2d4e08a6d95f3c1e7b2a40"   # le fichier <clé>.txt doit exister à la racine
PARIS = ZoneInfo("Europe/Paris")
WORKER = "https://footlive.hgtrerza.workers.dev/soccer/"

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
ZONES = [("Paris / Bruxelles", "Europe/Paris"), ("Londres", "Europe/London"), ("Casablanca", "Africa/Casablanca"),
         ("Alger / Tunis", "Africa/Algiers"), ("Dakar / Abidjan", "Africa/Abidjan"), ("Montréal", "America/Toronto")]

# nom de compétition -> page du site
COMP_PAGES = [
    (r"^Ligue des champions$", "ligue-des-champions"), (r"^Ligue Europa$", "europa-league"),
    (r"^Ligue Conférence$", "conference-league"), (r"^Premier League$", "premier-league"),
    (r"^LaLiga$", "laliga"), (r"^Serie A$", "serie-a"), (r"^Bundesliga$", "bundesliga"),
    (r"^Ligue 1$", "ligue-1"), (r"^Liga Portugal$", "liga-portugal"), (r"^Eredivisie$", "eredivisie"),
    (r"botola", "botola-pro"),
]

esc = lambda s: html.escape(str(s), quote=True)


def slugify(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")   # IDENTIQUE à slug() dans update-apercu.mjs


def page_name(m):
    return f"{slugify(m['home'])}-{slugify(m['away'])}-{m['id']}"


def fr_date(d):
    return f"{JOURS[d.weekday()]} {d.day}{'er' if d.day == 1 else ''} {MOIS[d.month - 1]} {d.year}"


def hhmm(d):
    return d.strftime("%H:%M")


def comp_page(lg):
    for rx, p in COMP_PAGES:
        if re.search(rx, lg or "", re.I):
            return p
    return None


CLUBS = set()
if os.path.isdir("clubs"):
    CLUBS = {f[:-5] for f in os.listdir("clubs") if f.endswith(".html") and f != "index.html"}
CLUB_ALIAS = {"paris-saint-germain": "psg", "marseille": "olympique-de-marseille", "lyon": "olympique-lyonnais",
              "monaco": "as-monaco", "lille": "losc-lille", "nice": "ogc-nice", "barcelona": "fc-barcelone",
              "bayern-munich": "bayern-munich", "inter": "inter-milan", "ac-milan": "ac-milan",
              "atletico-madrid": "atletico-madrid", "sevilla": "seville-fc", "porto": "fc-porto",
              "sporting-cp": "sporting-cp", "wydad-ac": "wydad-casablanca", "raja-casablanca": "raja-casablanca"}


def club_link(name):
    s = slugify(name)
    s = CLUB_ALIAS.get(s, s)
    return f"/clubs/{s}.html" if s in CLUBS else None


def load_registry():
    try:
        return json.load(open(REG, encoding="utf-8"))
    except Exception:
        return {}


def status_label(m):
    return {"pre": "à venir", "in": "en direct", "post": "terminé", "off": "reporté"}.get(m["state"], "à venir")


def score_txt(m):
    if m["state"] in ("pre", "off") or m.get("h") is None or m.get("a") is None:
        return "–"
    return f"{m['h']}–{m['a']}"


CSS = """:root{--bg:#0a0f1e;--card:#111a2e;--bd:#1f2b45;--tx:#e8edf7;--mu:#93a1bd;--ac:#22c55e;--rd:#ef4444}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.6 -apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif}
a{color:var(--ac);text-decoration:none}a:hover{text-decoration:underline}
.c{max-width:860px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--bd);background:rgba(7,11,22,.8)}header .c{display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding-top:12px;padding-bottom:12px}
.brand{font-weight:800;color:var(--tx);font-size:1.05rem}nav a{color:var(--mu);font-weight:700;font-size:.9rem;margin-right:14px}nav a:hover{color:var(--ac)}
h1{font-size:1.5rem;line-height:1.25;margin:1.2rem 0 .4rem}h2{font-size:1.1rem;margin:1.6rem 0 .6rem}h3{font-size:.95rem;margin:1rem 0 .2rem}
p{margin:.4rem 0;color:var(--mu)}.crumbs{font-size:.8rem;color:var(--mu);margin-top:1rem}
.hero{background:linear-gradient(135deg,#0f2a1d,#11202f);border:1px solid rgba(34,197,94,.4);border-radius:16px;padding:18px 16px;margin:12px 0;text-align:center}
.hero .lg{color:var(--mu);font-size:.8rem}.hero .row{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:center;margin:10px 0}
.hero .t{font-weight:800;font-size:1.05rem;overflow-wrap:anywhere}.hero .sc{font-size:2rem;font-weight:800;letter-spacing:2px;font-variant-numeric:tabular-nums}
.hero .st{font-weight:800;font-size:.8rem;color:var(--ac);text-transform:uppercase;letter-spacing:.5px}.hero .st.live{color:var(--rd)}
.cta{display:inline-block;background:var(--ac);color:#04210f;font-weight:800;padding:10px 16px;border-radius:12px;margin:8px 6px 0 0}.cta:hover{text-decoration:none;filter:brightness(1.1)}
.cta.alt{background:transparent;color:var(--ac);border:1px solid var(--ac)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--bd);border-radius:12px;overflow:hidden;font-size:.92rem}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--bd)}th{color:var(--mu);font-size:.75rem;text-transform:uppercase}
.m{list-style:none;padding:0;margin:0}.m li{display:flex;justify-content:space-between;gap:10px;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 12px;margin:6px 0}
.m time{color:var(--ac);font-weight:700;margin-right:8px}.m small{color:var(--mu)}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.chips a{border:1px solid var(--bd);background:var(--card);color:var(--tx);font-weight:700;font-size:.82rem;padding:7px 12px;border-radius:999px}
footer{border-top:1px solid var(--bd);margin-top:2.5rem;padding:1rem 0 2rem;color:var(--mu);font-size:.82rem}footer a{color:var(--mu);margin-right:14px}"""

HEAD = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#070b16">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="fr" href="{url}">
<link rel="alternate" hreflang="x-default" href="{url}">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png?v=2">
<link rel="icon" href="/favicon.ico?v=2">
<link rel="apple-touch-icon" href="/favicon-192x192.png?v=2">
<link rel="manifest" href="/manifest.webmanifest">
<meta property="og:type" content="website">
<meta property="og:site_name" content="FootLive Pro">
<meta property="og:locale" content="fr_FR">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:image" content="{site}/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{site}/og-image.png">
{ld}
<style>{css}</style></head><body>
<header><div class="c"><a class="brand" href="/">⚽ FootLive Pro</a>
<nav aria-label="Navigation"><a href="/">Scores</a><a href="/matchs-du-jour.html">Matchs du jour</a><a href="/programme-tv.html">Programme TV</a><a href="/radio.html">Radio</a><a href="/classements.html">Classements</a></nav></div></header>
"""

FOOT = """<footer><div class="c"><a href="/mentions-legales.html">Mentions légales</a><a href="/confidentialite.html">Confidentialité</a><a href="/contact.html">Contact</a><a href="/a-propos.html">À propos</a></div></footer>
</body></html>
"""


def ld_script(objs):
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": objs},
                                                              ensure_ascii=False).replace("<", "\\u003c") + "</script>"


def build_match(m, siblings):
    start = datetime.fromisoformat(m["start"].replace("Z", "+00:00"))
    p = start.astimezone(PARIS)
    name = page_name(m)
    url = f"{SITE}/{DIR}/{name}.html"
    home, away, lg = m["home"], m["away"], m.get("lg") or "Football"
    title = f"{home} – {away} : heure, score et où suivre le match | FootLive Pro"
    if len(title) > 70:
        title = f"{home} – {away} : heure et score en direct | FootLive Pro"
    desc = (f"{home} – {away} ({lg}) le {fr_date(p)} à {hhmm(p)} (heure de Paris). "
            f"Score en direct, heure dans votre pays, radios et programme TV.")[:158]
    cp = comp_page(lg)
    hl, al = club_link(home), club_link(away)
    live_q = f"/match.html?id={m['id']}"

    event = {"@type": "SportsEvent", "name": f"{home} – {away}", "sport": "Football", "startDate": m["start"],
             "endDate": (start + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
             "eventStatus": "https://schema.org/EventPostponed" if m["state"] == "off" else "https://schema.org/EventScheduled",
             "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
             "location": {"@type": "Place", "name": m.get("venue") or lg, "address": m.get("place") or "Non communiqué"},
             "organizer": {"@type": "Organization", "name": lg, "url": f"{SITE}/{cp}.html" if cp else SITE + "/"},
             "image": [SITE + "/og-image.png"],
             "homeTeam": {"@type": "SportsTeam", "name": home}, "awayTeam": {"@type": "SportsTeam", "name": away},
             "url": url}
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Matchs du jour", "item": SITE + "/matchs-du-jour.html"},
        {"@type": "ListItem", "position": 3, "name": f"{home} – {away}", "item": url}]}
    faq = [
        (f"À quelle heure joue {home} contre {away} ?",
         f"{home} – {away} est programmé le {fr_date(p)} à {hhmm(p)} (heure de Paris), soit "
         + ", ".join(f"{hhmm(start.astimezone(ZoneInfo(z)))} à {n}" for n, z in ZONES[1:4]) + "."),
        (f"Où suivre {home} – {away} en direct ?",
         "Le score, les buts, les statistiques et la composition sont à suivre en direct sur FootLive Pro. "
         "Le programme TV indique les chaînes qui diffusent les matchs importants, et l'onglet Radio réunit des radios "
         "sport en direct pour écouter le commentaire."),
        (f"Dans quelle compétition se joue {home} – {away} ?",
         f"Ce match compte pour : {lg}." + (f" Le stade est {m['venue']}" + (f" ({m['place']})" if m.get("place") else "") + "." if m.get("venue") else "")),
    ]
    faq_ld = {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}

    rows = "".join(f"<tr><td>{esc(n)}</td><td>{hhmm(start.astimezone(ZoneInfo(z)))}</td></tr>" for n, z in ZONES)
    chips = []
    if cp: chips.append(f'<a href="/{cp}.html">{esc(lg)} : scores et classement</a>')
    if hl: chips.append(f'<a href="{hl}">{esc(home)} : résultats et calendrier</a>')
    if al: chips.append(f'<a href="{al}">{esc(away)} : résultats et calendrier</a>')
    chips += ['<a href="/programme-tv.html">Programme TV foot</a>', '<a href="/radio.html">Radios foot en direct</a>',
              '<a href="/classements.html">Classements</a>', '<a href="/matchs-du-jour.html">Tous les matchs du jour</a>']
    sib = "".join(
        f'<li><span><time datetime="{esc(s["start"])}">{hhmm(datetime.fromisoformat(s["start"].replace("Z", "+00:00")).astimezone(PARIS))}</time>'
        f'<a href="/{DIR}/{page_name(s)}.html">{esc(s["home"])} – {esc(s["away"])}</a></span><small>{status_label(s)}</small></li>'
        for s in siblings[:8])
    venue = f"<p>Lieu : {esc(m['venue'])}" + (f", {esc(m['place'])}" if m.get('place') else "") + ".</p>" if m.get("venue") else ""
    stc = "st live" if m["state"] == "in" else "st"

    body = f"""<main class="c">
<p class="crumbs"><a href="/">Accueil</a> › <a href="/matchs-du-jour.html">Matchs du jour</a> › {esc(home)} – {esc(away)}</p>
<h1>{esc(home)} – {esc(away)} : heure, score et suivi en direct</h1>
<p>{esc(lg)} · {esc(fr_date(p))} à {hhmm(p)} (heure de Paris)</p>
<section class="hero" id="match" data-id="{esc(m['id'])}" aria-label="Score du match">
<div class="lg">{esc(lg)}</div>
<div class="row"><div class="t">{esc(home)}</div><div class="sc" id="sc">{score_txt(m)}</div><div class="t">{esc(away)}</div></div>
<div class="{stc}" id="st">{status_label(m)}</div>
<a class="cta" href="{live_q}">▶ Suivre le match en direct (stats, compos, buts)</a><a class="cta alt" href="/radio.html">📻 Écouter une radio foot</a>
</section>
{venue}
<h2>Heure du match {esc(home)} – {esc(away)} selon votre pays</h2>
<table><thead><tr><th>Ville</th><th>Coup d'envoi</th></tr></thead><tbody>{rows}</tbody></table>
<p>Les horaires sont ceux communiqués par l'organisateur et peuvent être modifiés.</p>
<h2>Où voir {esc(home)} – {esc(away)} ?</h2>
<p>Retrouvez les matchs importants, l'heure et la chaîne qui les diffuse dans le <a href="/programme-tv.html">programme TV football</a>. Pour écouter le commentaire sans image, ouvrez les <a href="/radio.html">radios foot en direct</a> : la lecture continue pendant que vous suivez le score.</p>
<h2>Liens utiles</h2>
<div class="chips">{''.join(chips)}</div>
{('<h2>Autres matchs : ' + esc(lg) + '</h2><ul class="m">' + sib + '</ul>') if sib else ''}
<h2>Questions fréquentes</h2>
{''.join(f'<h3>{esc(q)}</h3><p>{esc(a)}</p>' for q, a in faq)}
</main>
<script>
(function(){{var ID="{esc(m['id'])}",T=new Date("{esc(m['start'])}");
if(Math.abs(Date.now()-T.getTime())>6*36e5)return;
function d(n){{var x=new Date(Date.now()+n*864e5);return x.toISOString().slice(0,10).replace(/-/g,"")}}
function tick(){{fetch("{WORKER}all/scoreboard?dates="+d(0)+"&limit=1000").then(function(r){{return r.json()}}).then(function(j){{
var ev=(j.events||[]).filter(function(e){{return String(e.id)===ID}})[0];if(!ev)return;
var c=(ev.competitions&&ev.competitions[0]||{{}}).competitors||[],h=c.filter(function(x){{return x.homeAway==="home"}})[0],a=c.filter(function(x){{return x.homeAway==="away"}})[0];
var s=(ev.status&&ev.status.type)||{{}},st=document.getElementById("st"),sc=document.getElementById("sc");
if(s.state==="pre"){{return}}
if(h&&a&&sc)sc.textContent=h.score+"–"+a.score;
if(st){{st.textContent=s.state==="in"?"en direct · "+((ev.status&&ev.status.displayClock)||""):"terminé";st.className=s.state==="in"?"st live":"st"}}
}}).catch(function(){{}})}}
tick();setInterval(tick,60000)}})();
</script>
"""
    page = HEAD.format(title=esc(title), desc=esc(desc), url=url, site=SITE, css=CSS,
                       ld=ld_script([event, crumbs, faq_ld])) + body + FOOT
    return name, page, url


def build_hub(items, today):
    url = SITE + "/matchs-du-jour.html"
    d = datetime.fromisoformat(today + "T12:00:00+00:00")
    title = f"Matchs de foot aujourd'hui ({d.day} {MOIS[d.month - 1]}) : heures et scores | FootLive Pro"
    desc = (f"Tous les matchs de football du {fr_date(d)} : heure, score en direct, compétition. "
            f"{len(items)} matchs avec leur page dédiée.")[:158]
    by = {}
    for m in items:
        by.setdefault(m.get("lg") or "Football", []).append(m)
    secs = ""
    for lg, ms in by.items():
        li = "".join(
            f'<li><span><time datetime="{esc(m["start"])}">{hhmm(datetime.fromisoformat(m["start"].replace("Z", "+00:00")).astimezone(PARIS))}</time>'
            f'<a href="/{DIR}/{page_name(m)}.html">{esc(m["home"])} {esc(score_txt(m)) if m["state"] in ("in", "post") else "–"} {esc(m["away"])}</a></span>'
            f'<small>{status_label(m)}</small></li>' for m in sorted(ms, key=lambda x: x["start"]))
        secs += f"<h2>{esc(lg)}</h2><ul class=\"m\">{li}</ul>"
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": "Matchs du jour", "item": url}]}
    body = f"""<main class="c">
<p class="crumbs"><a href="/">Accueil</a> › Matchs du jour</p>
<h1>Matchs de foot aujourd'hui : {esc(fr_date(d))}</h1>
<p>Heure (Paris), score et statut de chaque match. Touchez un match pour sa page : heure dans votre pays, suivi en direct, radios et programme TV.</p>
{secs or '<p>Aucun match des principales compétitions n’est programmé aujourd’hui.</p>'}
<div class="chips"><a href="/programme-tv.html">Programme TV foot</a><a href="/classements.html">Classements</a><a href="/radio.html">Radios foot en direct</a><a href="/actualites.html">Actualités foot</a><a href="/">Scores en direct</a></div>
</main>
"""
    return HEAD.format(title=esc(title), desc=esc(desc), url=url, site=SITE, css=CSS, ld=ld_script([crumbs])) + body + FOOT


def ping_indexnow(urls):
    if not urls:
        return
    data = json.dumps({"host": "www.footlivepro.com", "key": INDEXNOW_KEY,
                       "keyLocation": f"{SITE}/{INDEXNOW_KEY}.txt", "urlList": urls[:9000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=data,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        print("IndexNow :", urllib.request.urlopen(req, timeout=20).status, len(urls), "URL")
    except Exception as e:  # jamais bloquant
        print("IndexNow ignoré :", e)


def main():
    ping = "--ping" in sys.argv
    src = json.load(open("matchs-du-jour.json", encoding="utf-8"))
    today = src["date"]
    os.makedirs(DIR, exist_ok=True)
    reg = load_registry()
    new_urls = []
    for m in src["matches"] + src.get("soon", []):   # aujourd'hui + J+1/J+2 (pages en ligne avant le match)
        if m["id"] not in reg:
            new_urls.append(f"{SITE}/{DIR}/{page_name(m)}.html")
        reg[m["id"]] = {**m, "seen": today}
    # purge des matchs trop anciens
    limit = (datetime.fromisoformat(today) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    for k in [k for k, v in reg.items() if v["start"][:10] < limit]:
        try: os.remove(os.path.join(DIR, page_name(reg[k]) + ".html"))
        except FileNotFoundError: pass
        del reg[k]

    by_lg = {}
    for m in reg.values():
        by_lg.setdefault(m.get("lg"), []).append(m)
    keep = set()
    for m in reg.values():
        sib = sorted([s for s in by_lg[m.get("lg")] if s["id"] != m["id"] and s["start"][:10] == m["start"][:10]],
                     key=lambda s: s["start"])
        name, page, _ = build_match(m, sib)
        keep.add(name + ".html")
        open(os.path.join(DIR, name + ".html"), "w", encoding="utf-8").write(page)
    for f in os.listdir(DIR):          # pages orphelines (ex. ancien nom)
        if f.endswith(".html") and f not in keep:
            os.remove(os.path.join(DIR, f))
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    hub_items = sorted(src["matches"], key=lambda m: m["start"])
    open("matchs-du-jour.html", "w", encoding="utf-8").write(build_hub(hub_items, today))

    urls = [(SITE + "/matchs-du-jour.html", today)] + \
           [(f"{SITE}/{DIR}/{page_name(m)}.html", m["start"][:10]) for m in sorted(reg.values(), key=lambda x: x["start"])]
    with open("sitemap-matchs.xml", "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u, lm in urls:
            f.write(f"  <url><loc>{u}</loc><lastmod>{max(lm, today) if u.endswith('jour.html') else lm}</lastmod></url>\n")
        f.write("</urlset>\n")
    print(f"{len(reg)} pages match, hub + sitemap-matchs.xml ; {len(new_urls)} nouvelles.")
    if ping:
        ping_indexnow(new_urls + [SITE + "/matchs-du-jour.html"])


if __name__ == "__main__":
    main()

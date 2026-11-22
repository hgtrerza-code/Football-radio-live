#!/usr/bin/env python3
"""
FootLive Pro : génère des pages statiques (vraies URLs .html) pour le SEO.

  clubs/index.html, clubs/<club>.html        -> prochain match, résultats, buteurs du club
  buteurs/index.html, buteurs/<compet>.html  -> classement des buteurs par compétition
  sitemap-seo.xml                            -> à soumettre dans Google Search Console

La liste des clubs (CLUBS) et des compétitions (LEAGUES) est lue directement dans index.html :
ajouter un club dans index.html suffit, il aura sa page au prochain passage du script.

Aucune dépendance : Python 3.9+ uniquement. À lancer depuis la racine du dépôt :
    python scripts/generate_seo_pages.py
"""
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

BASE = "https://www.footlivepro.com"
ROOT = os.environ.get("SEO_ROOT", ".")
INDEX = os.path.join(ROOT, "index.html")
PARIS = ZoneInfo("Europe/Paris")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer"
BYATH = ("https://site.web.api.espn.com/apis/common/v3/sports/soccer/{sl}/statistics/byathlete"
         "?region=us&lang=en&contentorigin=espn&isqualified=true&page={pg}&limit=50"
         "&sort=offensive.totalGoals%3Adesc")
CORE = "https://sports.core.api.espn.com/v2/sports/soccer/leagues/{sl}/seasons/{yr}/types/1/leaders?limit=25"

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
EXC = re.compile(r"women|\(w\)|\bu-?\d\d\b| ii$| b$|reserves")
BT_TOP = ["eng.1", "esp.1", "ger.1", "ita.1", "fra.1", "mar.1", "por.1", "ned.1", "bel.1",
          "tur.1", "uefa.champions", "uefa.europa", "uefa.europa.conf"]
BT_SKIP = re.compile(r"nwsl|charity|super_cup|^fifa\.world$|^uefa\.euro")
NATIONAL = re.compile(r"^(uefa|conmebol|caf|concacaf|afc|fifa)\.", re.I)
# Compétitions à écarter des pages clubs : féminines, jeunes / réserves, divisions inférieures (.2, .3...).
# Une division inférieure reste autorisée pour un club qui y joue vraiment (ex. AS Saint-Étienne en Ligue 2).
NOT_MEN_SLUG = re.compile(r"(?:^|\.)w(?:\.|$)|wchampions|wwc|nwsl|women|\.fem|\.u\d\d|youth|reserve|\.[2-9](?:\.|$)", re.I)


# ----------------------------------------------------------------------------- utilitaires
def fetch_json(url, tries=3):
    headers = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
               "Accept-Language": "en-US,en;q=0.9", "Referer": "https://www.espn.com/",
               "Origin": "https://www.espn.com"}
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # 403 / 404 : inutile de réessayer, on abandonne tout de suite cette URL
            print("  ! échec", url[:110], "->", f"HTTP {e.code}", file=sys.stderr)
            if e.code in (403, 404) or i == tries - 1:
                return None
            time.sleep(1.5 * (i + 1))
        except Exception as e:  # noqa
            if i == tries - 1:
                print("  ! échec", url[:110], "->", str(e)[:60], file=sys.stderr)
            else:
                time.sleep(1.5 * (i + 1))
    return None


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return s.lower().strip()


def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def parse_dt(s):
    s = str(s or "")
    if re.search(r"T\d\d:\d\d(Z|$)", s):
        s = re.sub(r"(T\d\d:\d\d)(Z|$)", r"\1:00\2", s)
    s = s.replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(PARIS)


def fr_day(d):
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"


MOIS_C = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def fr_short(d):
    return f"{JOURS[d.weekday()][:3]}. {d.day} {MOIS_C[d.month - 1]}"


def plural(n, one, many):
    return f"{n} {one if n <= 1 else many}"


# ----------------------------------------------------------------------------- lecture d'index.html
def parse_index():
    src = open(INDEX, encoding="utf-8").read()
    a = src.index("const CLUBS = [")
    b = src.index("const clubOf", a)
    clubs = []
    for m in re.finditer(r'\["([^"]+)", "([^"]+)", "([^"]+)", "([^"]+)", "([^"]+)", "([^"]*)"\]', src[a:b]):
        clubs.append(dict(slug=m[1], name=m[2], country=m[3], flag=m[4], league=m[5], pat=m[6]))
    a = src.index("const LEAGUES = [")
    b = src.index("const lgLabel", a)
    leagues = []
    for m in re.finditer(r'\["([^"]+)", "([^"]*)", "([^"]+)", "([^"]+)"\]', src[a:b]):
        key = m[1].split("|")[0]
        leagues.append(dict(key=key, slugs=m[1].split("|"), name=m[3], group=m[4]))
    return clubs, leagues


# ----------------------------------------------------------------------------- matchs (ESPN scoreboard)
def same_league(l, name):
    a, b = norm(l["name"]), norm(name)
    return a == b or a.startswith(b) or b.startswith(a)


def men_slugs(clubs, leagues):
    """Compétitions masculines à lire : championnats de 1re division, coupes nationales et européennes suivis par le site.
    Féminines, jeunes, réserves et divisions inférieures sont exclues, sauf la division d'un club listé (ex. Ligue 2)."""
    own = set()
    for c in clubs:
        lg = next((l for l in leagues if same_league(l, c["league"])), None)
        if lg:
            own.update(lg["slugs"])
    out = {}
    for l in leagues:
        for sl in l["slugs"]:
            if sl in own or not NOT_MEN_SLUG.search(sl):
                out[sl] = l["name"]
    return out


def load_matches(slug_names, days_back=10, days_fwd=14):
    """Un appel par compétition (période complète) : chaque match arrive avec sa compétition exacte,
    donc jamais de match féminin ou de division inférieure mélangé aux clubs masculins."""
    today = datetime.now(PARIS).date()
    d0 = (today - timedelta(days=days_back)).strftime("%Y%m%d")
    d1 = (today + timedelta(days=days_fwd)).strftime("%Y%m%d")

    def one(slug):
        return slug, fetch_json(f"{ESPN}/{slug}/scoreboard?dates={d0}-{d1}&limit=1000")

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(one, list(slug_names)))
    ok = sum(1 for _, j in results if j)
    print(f"{ok}/{len(results)} compétitions lues")
    seen = {}
    for slug, j in results:
        if not j:
            continue
        for ev in j.get("events", []):
            c = (ev.get("competitions") or [{}])[0]
            cp = c.get("competitors") or []
            h = next((x for x in cp if x.get("homeAway") == "home"), cp[0] if cp else None)
            a = next((x for x in cp if x.get("homeAway") == "away"), cp[1] if len(cp) > 1 else None)
            if not h or not a or ev.get("id") in seen:
                continue
            st = (ev.get("status") or {}).get("type") or {}
            ht, at = h.get("team") or {}, a.get("team") or {}
            seen[ev["id"]] = dict(
                id=ev["id"], start=parse_dt(ev.get("date")), state=st.get("state") or "pre",
                off=bool(re.search(r"postponed|cancel|suspend|abandon",
                                   (st.get("name") or "") + " " + (st.get("description") or ""), re.I)),
                home=ht.get("displayName") or ht.get("name") or "", away=at.get("displayName") or at.get("name") or "",
                hs=h.get("score"), as_=a.get("score"), hid=str(ht.get("id") or ""), aid=str(at.get("id") or ""),
                slug=slug, lg=slug_names[slug],
            )
    return [m for m in seen.values() if m["start"]]


def club_matches(club, matches, lg_names, own=()):
    pat = re.compile(club["pat"], re.I)
    out = []
    for m in matches:
        nh, na = norm(m["home"]), norm(m["away"])
        is_h = bool(pat.search(nh)) and not EXC.search(nh)
        is_a = bool(pat.search(na)) and not EXC.search(na)
        if not (is_h or is_a):
            continue
        mm = dict(m)
        mm["is_h"] = is_h
        mm["tid"] = m["hid"] if is_h else m["aid"]
        mm["lg"] = lg_names.get(m["slug"]) or m["lg"]
        out.append(mm)
    # Une seule équipe par club : même nom ne veut pas dire même équipe (ex. équipe féminine, club homonyme).
    # On garde l'identifiant ESPN le plus fréquent, en priorité dans le championnat du club.
    ids = Counter(m["tid"] for m in out if m["tid"])
    if len(ids) > 1:
        in_own = Counter(m["tid"] for m in out if m["tid"] and m["slug"] in own)
        keep = (in_own or ids).most_common(1)[0][0]
        out = [m for m in out if m["tid"] == keep]
    return out


# ----------------------------------------------------------------------------- buteurs
_SC_CACHE = {}


HEADSHOT = "https://a.espncdn.com/i/headshots/soccer/players/full/{id}.png"


def photo(at):
    """URL de la photo d'un joueur (ESPN) : champ headshot, sinon adresse construite avec l'identifiant."""
    u = ((at or {}).get("headshot") or {}).get("href")
    if not u and (at or {}).get("id"):
        u = HEADSHOT.format(id=at["id"])
    return str(u or "").replace("http:", "https:")


def initials(n):
    return "".join(w[0] for w in re.findall(r"[A-Za-zÀ-ÿ]\S*", str(n))[:2]).upper()


def _athletes(j):
    rows = []
    for x in (j or {}).get("athletes", []):
        at = x.get("athlete") or {}
        g = a = p = None
        for c in x.get("categories") or []:
            for k, name in enumerate(c.get("names") or []):
                try:
                    v = float(re.sub(r"[^\d.]", "", str((c.get("totals") or [])[k])))
                except (ValueError, IndexError):
                    continue
                if name == "totalGoals":
                    g = v
                elif name == "goalAssists":
                    a = v
                elif name in ("appearances", "gamesPlayed"):
                    p = v
        if g is None or not at.get("displayName"):
            continue
        team = at.get("teamName") or at.get("teamShortName") or \
            ((at.get("teams") or [{}])[0] or {}).get("displayName") or ""
        rows.append(dict(n=at["displayName"], t=team, g=int(g), a=None if a is None else int(a),
                         p=None if p is None else int(p), img=photo(at)))
    return [r for r in rows if r["g"] > 0]


def _core_leaders(sl):
    yr0 = datetime.now(timezone.utc).year
    for yr in (yr0, yr0 - 1):
        j = fetch_json(CORE.format(sl=sl, yr=yr))
        cat = next((c for c in (j or {}).get("categories", [])
                    if re.search(r"goal", c.get("name") or "", re.I)
                    and not re.search(r"assist|against|conced", c.get("name") or "", re.I)), None)
        if not cat:
            continue
        rows = []
        for l in (cat.get("leaders") or [])[:20]:
            ref = lambda o: (o or {}).get("$ref", "").replace("http:", "https:")
            at = fetch_json(ref(l.get("athlete"))) if ref(l.get("athlete")) else None
            tm = fetch_json(ref(l.get("team"))) if ref(l.get("team")) else None
            if at and at.get("displayName"):
                rows.append(dict(n=at["displayName"], t=(tm or {}).get("displayName") or "",
                                 g=int(float(l.get("value") or 0)), a=None, p=None, img=photo(at)))
        rows = [r for r in rows if r["g"] > 0]
        if rows:
            return rows
    return []


def league_scorers(league, pages=1):
    """Meilleurs buteurs d'une compétition (liste triée, éventuellement sur 2 pages)."""
    ck = (league["key"], pages)
    if ck in _SC_CACHE:
        return _SC_CACHE[ck]
    rows = []
    for sl in league["slugs"]:
        for pg in range(1, pages + 1):
            rows += _athletes(fetch_json(BYATH.format(sl=sl, pg=pg)))
        if not rows:
            rows = _core_leaders(sl)
        if rows:
            break
    rows.sort(key=lambda r: (-r["g"], -(r["a"] or 0), r["n"]))
    _SC_CACHE[ck] = rows
    return rows


# ----------------------------------------------------------------------------- statistiques d'équipe (classement ESPN)
STANDINGS = "https://site.api.espn.com/apis/v2/sports/soccer/{sl}/standings"
_STAND = {}


def league_standings(lg):
    """Lignes du classement d'une compétition (une seule requête par compétition)."""
    if lg["key"] in _STAND:
        return _STAND[lg["key"]]
    rows = []

    def walk(n):
        if not isinstance(n, dict):
            return
        for en in ((n.get("standings") or {}).get("entries") or []):
            st = {x.get("name"): x.get("value") for x in (en.get("stats") or []) if isinstance(x, dict)}
            rows.append({"team": (en.get("team") or {}).get("displayName") or "", "st": st})
        for ch in (n.get("children") or []):
            walk(ch)

    for sl in lg["slugs"]:
        walk(fetch_json(STANDINGS.format(sl=sl)) or {})
        if rows:
            break
    _STAND[lg["key"]] = rows
    return rows


def club_standing(c, rows):
    pat = re.compile(c["pat"], re.I)
    for r in rows:
        t = norm(r["team"])
        if pat.search(t) and not EXC.search(t):
            return r["st"]
    return None


def _n(st, k):
    try:
        return float(st.get(k))
    except (TypeError, ValueError):
        return None


def stats_html(c, st, league):
    """Tableau des statistiques de la saison du club (rang, bilan, buts, points par match)."""
    if not st:
        return "", None
    gp, w, d, l = _n(st, "gamesPlayed"), _n(st, "wins"), _n(st, "ties"), _n(st, "losses")
    gf, ga, pts, rk = _n(st, "pointsFor"), _n(st, "pointsAgainst"), _n(st, "points"), _n(st, "rank")
    if not gp:
        return "", None
    i = lambda v: "" if v is None else str(int(v))
    f2 = lambda v: "" if v is None else f"{v:.2f}".replace(".", ",")
    diff = (gf - ga) if gf is not None and ga is not None else None
    rows = [("Classement", (("1er" if rk == 1 else f"{int(rk)}e") if rk else "")), ("Matchs joués", i(gp)), ("Victoires", i(w)), ("Nuls", i(d)), ("Défaites", i(l)),
            ("Buts marqués", i(gf)), ("Buts encaissés", i(ga)),
            ("Différence de buts", "" if diff is None else f"{int(diff):+d}"), ("Points", i(pts)),
            ("Points par match", f2(pts / gp) if pts is not None else ""),
            ("Buts marqués par match", f2(gf / gp) if gf is not None else ""),
            ("Buts encaissés par match", f2(ga / gp) if ga is not None else ""),
            ("Taux de victoire", f"{round(w / gp * 100)} %" if w is not None else "")]
    rows = [r for r in rows if r[1] != ""]
    lgn = league["name"] if league else c["league"]
    html_ = (f"<h2>Statistiques de {e(c['name'])} · {e(lgn)}</h2><table><thead><tr><th>Statistique</th><th>Valeur</th></tr></thead><tbody>"
             + "".join(f"<tr><td>{e(a)}</td><td class='g'>{e(b)}</td></tr>" for a, b in rows) + "</tbody></table>")
    faq = None
    if rk:
        faq = (f"Où se classe {c['name']} ?",
               f"{c['name']} est {'1er' if rk == 1 else str(int(rk)) + 'e'} de {lgn} avec {i(pts)} points en {i(gp)} matchs ({plural(int(w or 0), 'victoire', 'victoires')}, {plural(int(d or 0), 'nul', 'nuls')}, {plural(int(l or 0), 'défaite', 'défaites')}), "
               f"{i(gf)} buts marqués et {i(ga)} encaissés.")
    return html_, faq


# ----------------------------------------------------------------------------- gabarit HTML
CSS = """
:root{--bg:#0a0f1e;--card:#111a2e;--bd:#1f2b45;--tx:#e8edf7;--mu:#93a1bd;--ac:#22c55e;--rd:#ef4444}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:16px/1.6 -apple-system,Segoe UI,Roboto,Inter,Arial,sans-serif}
a{color:var(--ac);text-decoration:none}a:hover{text-decoration:underline}
.c{max-width:860px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--bd);background:rgba(7,11,22,.8)}header .c{display:flex;gap:16px;align-items:center;flex-wrap:wrap;padding-top:12px;padding-bottom:12px}
.brand{font-weight:800;color:var(--tx);font-size:1.05rem}nav a{color:var(--mu);font-weight:700;font-size:.9rem;margin-right:14px}nav a:hover{color:var(--ac)}
h1{font-size:1.5rem;line-height:1.25;margin:1.4rem 0 .4rem}h2{font-size:1.1rem;margin:1.6rem 0 .6rem}h3{font-size:.95rem;margin:1rem 0 .2rem}
p{margin:.4rem 0;color:var(--mu)}.crumbs{font-size:.8rem;color:var(--mu);margin-top:1rem}
.next{background:linear-gradient(135deg,#0f2a1d,#11202f);border:1px solid rgba(34,197,94,.4);border-radius:16px;padding:14px 16px;margin:12px 0}
.next small{color:var(--ac);font-weight:800;font-size:.7rem;text-transform:uppercase;letter-spacing:.5px}.next b{display:block;font-size:1.1rem;margin:4px 0 2px}.next span{color:var(--mu);font-size:.9rem}
.m{list-style:none;padding:0;margin:0}.m li{display:grid;grid-template-columns:96px 1fr auto;gap:10px;align-items:center;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 12px;margin-bottom:8px;font-size:.92rem}
.m .d{color:var(--mu);font-size:.78rem;font-weight:700}.m .s{font-weight:800;color:var(--ac);white-space:nowrap}.m .l{color:var(--mu);font-size:.72rem;display:block}
.live{color:var(--rd)!important}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--bd);border-radius:12px;overflow:hidden;font-size:.92rem}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--bd)}th{color:var(--mu);font-size:.75rem;text-transform:uppercase}td.n,th.n{width:44px;text-align:center}td.g{font-weight:800;color:var(--ac)}tr:last-child td{border-bottom:0}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.chips a{border:1px solid var(--bd);background:var(--card);color:var(--tx);font-weight:700;font-size:.82rem;padding:7px 12px;border-radius:999px}
.cta{display:inline-block;background:var(--ac);color:#04210f;font-weight:800;padding:10px 16px;border-radius:12px;margin:10px 0}.cta:hover{text-decoration:none;filter:brightness(1.1)}
footer{border-top:1px solid var(--bd);margin-top:2.5rem;padding:1rem 0 2rem;color:var(--mu);font-size:.82rem}footer a{color:var(--mu);margin-right:14px}
.grp{font-weight:800;margin:1.2rem 0 .3rem}
.frm{margin:6px 0 10px}.fb{display:inline-block;width:30px;height:30px;line-height:30px;text-align:center;border-radius:8px;font-weight:800;margin-right:6px;color:#04210f}.fb.V{background:#22c55e}.fb.N{background:#eab308}.fb.D{background:#ef4444;color:#fff}
.pl{display:flex;align-items:center;gap:10px}.av{position:relative;width:40px;height:40px;flex:0 0 auto;border-radius:50%;overflow:hidden;background:linear-gradient(135deg,#334155,#475569);color:#fff;font-size:.7rem;font-weight:800;display:flex;align-items:center;justify-content:center}
.av::before{content:attr(data-i)}.av img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#1e293b}
@media(max-width:560px){.m li{grid-template-columns:1fr auto}.m .d{grid-column:1/-1}}
"""

TS_RE = re.compile(r"<!--TS-->.*?<!--/TS-->", re.S)


def page(title, desc, path, body, ld, noindex=False):
    url = BASE + path
    ROBOTS = "noindex,follow" if noindex else "index,follow,max-image-preview:large"
    ld_json = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    now = datetime.now(PARIS)
    ts = f"<!--TS-->Page mise à jour le {now.day} {MOIS[now.month - 1]} {now.year} à {now:%H:%M} (heure de Paris).<!--/TS-->"
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="{ROBOTS}">
<meta name="theme-color" content="#0a0f1e">
<link rel="icon" href="/favicon.ico">
<link rel="manifest" href="/manifest.webmanifest">
<meta property="og:type" content="website"><meta property="og:site_name" content="FootLive Pro">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
{ld_json}
<style>{CSS}</style></head><body>
<header><div class="c"><a class="brand" href="/">⚽ FootLive Pro</a>
<nav aria-label="Navigation"><a href="/">Scores</a><a href="/clubs/">Clubs</a><a href="/buteurs/">Buteurs</a></nav></div></header>
<main class="c">
{body}
</main>
<footer><div class="c"><a href="/mentions-legales.html">Mentions légales</a><a href="/confidentialite.html">Confidentialité</a><a href="/contact.html">Contact</a>
<p>FootLive Pro © {now.year} — {ts}</p></div></footer>
</body></html>
"""


def write_if_changed(rel, content, written):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    written.append(rel)
    if os.path.exists(path):
        old = open(path, encoding="utf-8").read()
        if TS_RE.sub("", old) == TS_RE.sub("", content):
            return False
    open(path, "w", encoding="utf-8").write(content)
    return True


def breadcrumb(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": BASE + p} for i, (n, p) in enumerate(items)]}


def faq_ld(faqs):
    return {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}


# ----------------------------------------------------------------------------- pages clubs
def match_li(m):
    d = m["start"]
    live = m["state"] == "in"
    if m["off"]:
        s, cls = "Reporté", ""
    elif m["state"] == "pre":
        s, cls = f"{d:%H:%M}", ""
    else:
        s, cls = f"{m['hs'] if m['hs'] is not None else 0} – {m['as_'] if m['as_'] is not None else 0}", ("live" if live else "")
    h = f"<b>{e(m['home'])}</b>" if m["is_h"] else e(m["home"])
    a = e(m["away"]) if m["is_h"] else f"<b>{e(m['away'])}</b>"
    when = '<span class="live">● EN DIRECT</span>' if live else fr_short(d)
    return (f'<li><span class="d">{when}</span><span>{h} – {a}<span class="l">{e(m["lg"])}</span></span>'
            f'<span class="s {cls}">{s}</span></li>')


def match_text(m):
    sc = f"{m['hs'] if m['hs'] is not None else 0}–{m['as_'] if m['as_'] is not None else 0}"
    return f"{m['home']} {sc} {m['away']}"


LEAGUE_PAGE = {"Premier League": "/premier-league.html", "Bundesliga": "/bundesliga.html", "Serie A": "/serie-a.html",
               "LaLiga": "/laliga.html", "Ligue 1": "/ligue-1.html", "Liga Portugal": "/liga-portugal.html",
               "Eredivisie": "/eredivisie.html", "Botola Pro": "/botola-pro.html"}


def result_of(m):
    hs, as_ = (m["hs"] or 0), (m["as_"] or 0)
    mine, opp = (hs, as_) if m["is_h"] else (as_, hs)
    return ("V" if mine > opp else "D" if mine < opp else "N"), mine, opp


def form_block(name, past):
    """Forme récente : pastilles V/N/D et résumé des 5 derniers matchs connus."""
    last = past[:5]
    if not last:
        return "", None
    res = [result_of(m) for m in last]
    w = sum(1 for r in res if r[0] == "V")
    d = sum(1 for r in res if r[0] == "N")
    l = sum(1 for r in res if r[0] == "D")
    gf = sum(r[1] for r in res)
    ga = sum(r[2] for r in res)
    badges = "".join(f'<span class="fb {r[0]}">{r[0]}</span>' for r in reversed(res))
    deb = "Lors de son dernier match connu" if len(res) == 1 else f"Sur ses {len(res)} derniers matchs connus"
    txt = (f"{deb}, {name} compte {plural(w, 'victoire', 'victoires')}, {plural(d, 'nul', 'nuls')} et "
           f"{plural(l, 'défaite', 'défaites')}, avec {gf} {'but marqué' if gf <= 1 else 'buts marqués'} et "
           f"{ga} {'but encaissé' if ga <= 1 else 'buts encaissés'}.")
    html_ = (f"<h2>Forme récente de {e(name)}</h2><div class='frm'>{badges}</div><p>{e(txt)}</p>"
             "<p><small>V = victoire, N = match nul, D = défaite. Du plus ancien au plus récent.</small></p>")
    return html_, (f"{name} est-il en forme ?", txt)


def season_block(c, st, rows, league, scorers):
    """Bilan de la saison rédigé à partir du classement (aucun chiffre inventé)."""
    if not st:
        return "", []
    gp, w, d, l = _n(st, "gamesPlayed"), _n(st, "wins"), _n(st, "ties"), _n(st, "losses")
    gf, ga, pts, rk = _n(st, "pointsFor"), _n(st, "pointsAgainst"), _n(st, "points"), _n(st, "rank")
    if not gp or pts is None:
        return "", []
    name = c["name"]
    lgn = league["name"] if league else c["league"]
    f1 = lambda v: f"{v:.2f}".replace(".", ",")
    parts, faqs = [], []
    n = len(rows or [])
    lead = None
    if rows:
        allp = [_n(r["st"], "points") for r in rows]
        allp = [x for x in allp if x is not None]
        lead = max(allp) if allp else None
    if rk:
        rkt = "1er" if rk == 1 else f"{int(rk)}e"
        band = ""
        if n >= 6:
            band = (" Le club occupe le haut du classement." if rk <= n / 3
                    else " Le club se situe dans le bas du classement." if rk > 2 * n / 3
                    else " Le club se situe dans le ventre mou du classement.")
        parts.append(f"{name} est {rkt} de {lgn}{' sur ' + str(n) + ' équipes' if n else ''} avec {int(pts)} points en {int(gp)} matchs, "
                     f"soit {f1(pts / gp)} points par match.{band}")
    if lead is not None and rk and rk != 1:
        gap = int(lead - pts)
        t = f"{name} compte {plural(gap, 'point', 'points')} de retard sur le leader de {lgn}." if gap > 0 else f"{name} est à égalité de points avec le leader de {lgn}."
        parts.append(t)
        faqs.append((f"À combien de points {name} est-il du leader ?", t))
    elif rk == 1 and rows and len(rows) > 1:
        sec = sorted([x for x in (_n(r["st"], "points") for r in rows) if x is not None], reverse=True)
        if len(sec) > 1:
            t = f"{name} est leader de {lgn} avec {int(sec[0] - sec[1])} {'point' if int(sec[0] - sec[1]) <= 1 else 'points'} d’avance sur son premier poursuivant."
            parts.append(t)
    if gf is not None and ga is not None:
        gfm, gam = gf / gp, ga / gp
        att = ("une attaque très prolifique" if gfm >= 2.0 else "une attaque en difficulté" if gfm <= 1.0 else "une attaque dans la moyenne")
        dfn = ("une défense solide" if gam <= 0.9 else "une défense friable" if gam >= 1.6 else "une défense dans la moyenne")
        parts.append(f"Avec {f1(gfm)} buts marqués et {f1(gam)} encaissés par match, {name} présente {att} et {dfn}.")
    if scorers and gf and scorers[0]["g"] <= gf and scorers[0]["g"] > 0:
        t = scorers[0]
        parts.append(f"{t['n']} a inscrit {plural(t['g'], 'but', 'buts')} sur les {int(gf)} du club, soit {round(t['g'] / gf * 100)} % de la production offensive.")
    if not parts:
        return "", faqs
    return f"<h2>Bilan de la saison de {e(name)}</h2>" + "".join(f"<p>{e(x)}</p>" for x in parts), faqs


def more_links(c, league):
    items = []
    lp = LEAGUE_PAGE.get(c["league"])
    if lp:
        items.append((lp, f"{c['league']} : scores et classement"))
    items += [("/programme-tv.html", "Programme TV du foot"), ("/matchs-du-jour.html", "Matchs du jour"),
              ("/classements.html", "Classements"), ("/radio.html", "Radios foot en direct")]
    return ("<h2>Pour aller plus loin</h2><div class='chips'>"
            + "".join(f'<a href="{u}">{e(t)}</a>' for u, t in items) + "</div>")


def club_page(c, ms, scorers, league, same_league, stand=None, rows=None):
    now = datetime.now(PARIS)
    up = sorted([m for m in ms if m["state"] != "post" and not m["off"]], key=lambda m: m["start"])
    past = sorted([m for m in ms if m["state"] == "post"], key=lambda m: m["start"], reverse=True)
    name = c["name"]
    if up:
        n = up[0]
        nxt = (f"{n['home']} – {n['away']} le {fr_day(n['start'])}"
               + (f" à {n['start']:%H:%M} (heure de Paris)" if n["state"] == "pre" else " (en cours)")
               + (f", en {n['lg']}" if n["lg"] else ""))
        box = (f'<div class="next"><small>{"En direct" if n["state"] == "in" else "Prochain match"}</small>'
               f'<b>{e(n["home"])} – {e(n["away"])}</b><span>{e(fr_day(n["start"]))}'
               + (f" à {n['start']:%H:%M} (heure de Paris)" if n["state"] == "pre" else "")
               + (f" · {e(n['lg'])}" if n["lg"] else "") + "</span></div>")
    else:
        nxt = None
        box = '<div class="next"><small>Prochain match</small><b>Aucun match annoncé dans les prochains jours</b><span>Le calendrier est mis à jour automatiquement.</span></div>'
    q_next = f"Quand joue {name} ?"
    a_next = (f"Le prochain match de {name} : {nxt}." if nxt else f"Aucun match de {name} n’est annoncé pour le moment ; le calendrier est mis à jour plusieurs fois par jour.")
    q_last = f"Quel est le dernier résultat de {name} ?"
    a_last = (f"Dernier résultat de {name} : {match_text(past[0])}{(' (' + past[0]['lg'] + ')') if past[0]['lg'] else ''}, le {fr_day(past[0]['start'])}." if past else f"Aucun résultat récent n’est disponible pour {name} pour le moment.")
    faqs = [(q_next, a_next), (q_last, a_last)]
    st_html, st_faq = stats_html(c, stand, league)
    if st_faq:
        faqs.append(st_faq)
    form_html, form_faq = form_block(name, past)
    if form_faq:
        faqs.append(form_faq)
    season_html, season_faqs = season_block(c, stand, rows, league, scorers)
    faqs.extend(season_faqs)
    faqs.append((f"Où regarder {name} en direct ?",
                 f"Suivez le score de {name} en direct sur FootLive Pro. Les chaînes qui diffusent les matchs du jour sont indiquées sur la page Programme TV."))
    sc_html = ""
    if scorers:
        t = scorers[0]
        a_top = f"{t['n']} est le meilleur buteur de {name} en {league['name'] if league else 'championnat'} cette saison avec {plural(t['g'], 'but', 'buts')}."
        faqs.append((f"Qui est le meilleur buteur de {name} ?", a_top))
        sc_html = (f"<h2>Meilleurs buteurs de {e(name)}</h2><table><thead><tr><th class='n'>#</th><th>Joueur</th><th>Matchs</th><th>Passes déc.</th><th>Buts</th></tr></thead><tbody>"
                   + "".join(f"<tr><td class='n'>{i + 1}</td><td>{e(r['n'])}</td><td>{'' if r['p'] is None else r['p']}</td><td>{'' if r['a'] is None else r['a']}</td><td class='g'>{r['g']}</td></tr>"
                             for i, r in enumerate(scorers[:10])) + "</tbody></table>")
    intro = (f"{name} ({c['country']}) évolue en {c['league']}. Retrouvez son prochain match, ses derniers résultats, son calendrier"
             + (" et ses meilleurs buteurs" if scorers else "") + f", mis à jour automatiquement par FootLive Pro. {a_next if nxt else ''}")
    links = "".join(f'<a href="/clubs/{x["slug"]}.html">{e(x["name"])}</a>' for x in same_league[:14])
    bt = (f'<p><a href="/buteurs/{league["key"]}.html">Classement des buteurs : {e(league["name"])}</a></p>' if league else "")
    body = (f'<p class="crumbs"><a href="/">Accueil</a> › <a href="/clubs/">Clubs</a> › {e(name)}</p>'
            f"<h1>{c['flag']} {e(name)} : résultats, prochain match et calendrier</h1><p>{e(intro)}</p>{box}"
            f'<a class="cta" href="/#club-{c["slug"]}">▶ Suivre {e(name)} en direct</a>'
            + (f'<h2>Prochains matchs</h2><ul class="m">{"".join(match_li(m) for m in up[:5])}</ul>' if up else "")
            + (f'<h2>Derniers résultats</h2><ul class="m">{"".join(match_li(m) for m in past[:5])}</ul>' if past else "")
            + form_html + st_html + season_html + sc_html
            + "<h2>Questions fréquentes</h2>" + "".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q, a in faqs)
            + (f"<h2>Autres clubs · {e(c['league'])}</h2><div class='chips'>{links}</div>" if links else "")
            + bt + more_links(c, league))
    desc = f"{name} : prochain match, derniers résultats, calendrier" + (" et meilleurs buteurs" if scorers else "") + ". Scores en direct sur FootLive Pro."
    path = f"/clubs/{c['slug']}.html"
    ld = [{"@context": "https://schema.org", "@type": "SportsTeam", "name": name, "sport": "Soccer",
           "memberOf": {"@type": "SportsOrganization", "name": c["league"]},
           "location": {"@type": "Place", "name": c["country"]}, "url": BASE + path},
          breadcrumb([("Accueil", "/"), ("Clubs", "/clubs/"), (name, path)]), faq_ld(faqs)]
    return page(f"{name} : résultats, prochain match et calendrier | FootLive Pro", desc, path, body, ld)


def clubs_index(clubs):
    groups = {}
    for c in clubs:
        groups.setdefault(c["country"], []).append(c)
    body = ('<p class="crumbs"><a href="/">Accueil</a> › Clubs</p>'
            f"<h1>Clubs de football : résultats, prochain match et calendrier</h1>"
            f"<p>FootLive Pro suit {len(clubs)} grands clubs du monde. Choisissez un club pour voir son prochain match, ses derniers résultats, son calendrier et ses meilleurs buteurs.</p>"
            + "".join(f"<div class='grp'>{g[0]['flag']} {e(k)}</div><div class='chips'>" + "".join(f'<a href="/clubs/{x["slug"]}.html">{e(x["name"])}</a>' for x in g) + "</div>" for k, g in groups.items())
            + '<p><a href="/buteurs/">Voir aussi : classements des buteurs par compétition</a></p>')
    return page("Clubs de football : résultats, prochain match et calendrier | FootLive Pro",
                f"Résultats, prochain match, calendrier et meilleurs buteurs de {len(clubs)} grands clubs de football. Gratuit sur FootLive Pro.",
                "/clubs/", body, [breadcrumb([("Accueil", "/"), ("Clubs", "/clubs/")])])


# ----------------------------------------------------------------------------- pages buteurs
def av_img(r):
    return (f'<img src="{e(r["img"])}" alt="{e(r["n"])}" width="40" height="40" loading="lazy" decoding="async" onerror="this.remove()">'
            if r.get("img") else "")


def scorers_page(lg, rows, others):
    name = lg["name"]
    if rows:
        t = rows[0]
        ans = f"{t['n']}" + (f" ({t['t']})" if t["t"] else "") + f" est en tête du classement des buteurs de {name} avec {plural(t['g'], 'but', 'buts')}."
    else:
        ans = f"Le classement des buteurs de {name} est mis à jour dès que les statistiques sont disponibles."
    faqs = [(f"Qui est le meilleur buteur de {name} ?", ans),
            ("Comment est calculé le classement des buteurs ?",
             "Le classement compte les buts marqués par chaque joueur dans la compétition, d’après les statistiques publiées par ESPN. Les égalités sont départagées par le nombre de passes décisives.")]
    table = ("<table><thead><tr><th class='n'>#</th><th>Joueur</th><th>Équipe</th><th>Matchs</th><th>Passes déc.</th><th>Buts</th></tr></thead><tbody>"
             + "".join(f"<tr><td class='n'>{i + 1}</td><td><span class='pl'><span class='av' data-i='{e(initials(r['n']))}'>{av_img(r)}</span>{e(r['n'])}</span></td><td>{e(r['t'])}</td><td>{'' if r['p'] is None else r['p']}</td><td>{'' if r['a'] is None else r['a']}</td><td class='g'>{r['g']}</td></tr>" for i, r in enumerate(rows[:25]))
             + "</tbody></table>") if rows else "<p>Classement indisponible pour le moment.</p>"
    chips = "".join(f'<a href="/buteurs/{o["key"]}.html">{e(o["name"])}</a>' for o in others)
    path = f"/buteurs/{lg['key']}.html"
    body = (f'<p class="crumbs"><a href="/">Accueil</a> › <a href="/buteurs/">Buteurs</a> › {e(name)}</p>'
            f"<h1>Meilleurs buteurs {e(name)} : classement des buteurs</h1>"
            f"<p>Classement des meilleurs buteurs de {e(name)} avec le nombre de buts marqués par joueur, mis à jour automatiquement. {e(ans)}</p>"
            f'<a class="cta" href="/#buteurs-{lg["key"]}">▶ Voir en direct dans l’application</a>{table}'
            "<h2>Questions fréquentes</h2>" + "".join(f"<h3>{e(q)}</h3><p>{e(a)}</p>" for q, a in faqs)
            + f"<h2>Autres classements de buteurs</h2><div class='chips'>{chips}</div>")
    ld = [breadcrumb([("Accueil", "/"), ("Buteurs", "/buteurs/"), (name, path)]), faq_ld(faqs)]
    if rows:
        ld.append({"@context": "https://schema.org", "@type": "ItemList", "name": f"Meilleurs buteurs {name}",
                   "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": f"{r['n']} : {plural(r['g'], 'but', 'buts')}"} for i, r in enumerate(rows[:10])]})
    desc = f"Meilleurs buteurs {name} : classement des buteurs avec le nombre de buts marqués" + (f". {rows[0]['n']} en tête avec {plural(rows[0]['g'], 'but', 'buts')}" if rows else "") + ". Mis à jour automatiquement sur FootLive Pro."
    return page(f"Meilleurs buteurs {name} : classement des buteurs | FootLive Pro", desc, path, body, ld, noindex=not rows)


def scorers_index(leagues):
    groups = {}
    for l in leagues:
        groups.setdefault(l["group"], []).append(l)
    body = ('<p class="crumbs"><a href="/">Accueil</a> › Buteurs</p><h1>Meilleurs buteurs : classement par compétition</h1>'
            "<p>Le classement des buteurs de chaque championnat et compétition européenne, avec le nombre de buts marqués, mis à jour automatiquement.</p>"
            + "".join(f"<div class='grp'>{e(k)}</div><div class='chips'>" + "".join(f'<a href="/buteurs/{x["key"]}.html">{e(x["name"])}</a>' for x in g) + "</div>" for k, g in groups.items())
            + '<p><a href="/clubs/">Voir aussi : résultats et calendrier des grands clubs</a></p>')
    return page("Meilleurs buteurs : classement par compétition | FootLive Pro",
                "Classement des meilleurs buteurs de la Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Ligue des champions et plus. Gratuit sur FootLive Pro.",
                "/buteurs/", body, [breadcrumb([("Accueil", "/"), ("Buteurs", "/buteurs/")])])


# ----------------------------------------------------------------------------- principal
def main():
    clubs, leagues = parse_index()
    print(f"{len(clubs)} clubs, {len(leagues)} compétitions lus dans index.html")
    lg_names = {}
    for l in leagues:
        for s in l["slugs"]:
            lg_names[s] = l["name"]
    matches = load_matches(men_slugs(clubs, leagues))
    if not matches:
        print("Aucune donnée de matchs reçue : abandon, pages existantes conservées.")
        return 0
    print(len(matches), "matchs chargés")
    written = []
    changed = 0
    bt_leagues = [l for l in leagues if not BT_SKIP.search(l["key"])]
    by_key = {l["key"]: l for l in bt_leagues}

    # --- clubs
    for c in clubs:
        try:
            lg = next((l for l in bt_leagues if same_league(l, c["league"])), None)
            ms = club_matches(c, matches, lg_names, set(lg["slugs"]) if lg else set())
            if not lg and ms:  # repli : compétition nationale la plus fréquente dans les matchs trouvés
                cnt = {}
                for m in ms:
                    if m["slug"] and not NATIONAL.match(m["slug"]):
                        cnt[m["slug"]] = cnt.get(m["slug"], 0) + 1
                top = max(cnt, key=cnt.get) if cnt else None
                lg = next((l for l in bt_leagues if top in l["slugs"]), None)
            scorers = []
            if lg:
                pat = re.compile(c["pat"], re.I)
                scorers = [r for r in league_scorers(lg, pages=2) if r["t"] and pat.search(norm(r["t"])) and not EXC.search(norm(r["t"]))]
            same = [x for x in clubs if x["league"] == c["league"] and x["slug"] != c["slug"]]
            rows = league_standings(lg) if lg else []
            stand = club_standing(c, rows) if lg else None
            changed += write_if_changed(f"clubs/{c['slug']}.html", club_page(c, ms, scorers, lg, same, stand, rows), written)
        except Exception as ex:  # noqa : une erreur sur un club ne doit pas bloquer les autres
            print("  ! club", c["slug"], ex, file=sys.stderr)
    changed += write_if_changed("clubs/index.html", clubs_index(clubs), written)

    # --- buteurs
    done = []
    empty = set()
    for l in bt_leagues:
        try:
            rows = league_scorers(l, pages=1)
            old = os.path.join(ROOT, f"buteurs/{l['key']}.html")
            if not rows and os.path.exists(old) and "Classement indisponible" not in open(old, encoding="utf-8").read():
                written.append(f"buteurs/{l['key']}.html")  # données indisponibles : on garde l'ancienne page qui, elle, a des données
                done.append(l)
                continue
            if not rows:
                empty.add(f"buteurs/{l['key']}.html")  # page vide : noindex et hors sitemap
            others = [by_key[k] for k in BT_TOP if k in by_key and k != l["key"]]
            changed += write_if_changed(f"buteurs/{l['key']}.html", scorers_page(l, rows, others), written)
            done.append(l)
        except Exception as ex:  # noqa
            print("  ! buteurs", l["key"], ex, file=sys.stderr)
    changed += write_if_changed("buteurs/index.html", scorers_index(done), written)

    # --- sitemap
    today = datetime.now(PARIS).strftime("%Y-%m-%d")
    urls = ["/clubs/", "/buteurs/"] + [f"/{p}" for p in written if p not in ("clubs/index.html", "buteurs/index.html") and p not in empty]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "".join(f"  <url><loc>{BASE}{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n")
    sm = os.path.join(ROOT, "sitemap-seo.xml")
    if not os.path.exists(sm) or re.sub(r"<lastmod>.*?</lastmod>", "", open(sm, encoding="utf-8").read()) != re.sub(r"<lastmod>.*?</lastmod>", "", xml):
        open(sm, "w", encoding="utf-8").write(xml)
        changed += 1
    print(f"{len(written)} pages traitées, {changed} fichiers modifiés")
    return 0


if __name__ == "__main__":
    sys.exit(main())

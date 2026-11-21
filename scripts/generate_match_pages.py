#!/usr/bin/env python3
"""FootLive Pro : génère une page statique INDEXABLE par match (matchs/<equipes>-<id>.html),
la page hub /matchs-du-jour.html et sitemap-matchs.xml, en français ET dans les 6 autres langues du site
(en, es, it, nl, de, ar : /<langue>/matchs-du-jour.html et /<langue>/matchs/<equipes>-<id>.html).

Pourquoi : les internautes cherchent « PSG Marseille heure chaîne score » ; jusqu'ici aucune page
du site ne pouvait se positionner sur ces requêtes (match.html est en noindex).

Chaque page reprend l'habillage de l'accueil : logo, barre de TOUS les onglets (lue dans index.html),
boutons « Buts » (alertes de but) et langue, et un bloc de texte SEO en bas de page.
Les textes de chaque langue sont dans scripts/match_i18n.py.

Source : matchs-du-jour.json (écrit par scripts/update-apercu.mjs). Bibliothèque standard uniquement.
Un registre (matchs/_registre.json) garde les matchs des derniers jours : la page d'un match reste en ligne
(et passe à « terminé ») au lieu de disparaître en 404. Les pages de plus de KEEP_DAYS jours sont supprimées.
Pour limiter le poids du dépôt, les versions traduites d'un match n'existent que dans une fenêtre de jours
autour d'aujourd'hui (LANG_WINDOW) ; au-delà, seule la page française reste en ligne.

À lancer à la racine du dépôt :  python3 scripts/generate_match_pages.py [--ping]
  --ping : prévient Bing/Yandex (IndexNow) des nouvelles pages.
"""
import html, json, os, re, sys, unicodedata, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from match_i18n import T, LANG_ORDER, LANG_NAMES, LOCALES, prefix  # noqa: E402

SITE = "https://www.footlivepro.com"
KEEP_DAYS = 10
LANG_WINDOW = (-1, 2)     # versions traduites : de hier à J+2 (jours de Paris)
DIR = "matchs"
REG = os.path.join(DIR, "_registre.json")
INDEXNOW_KEY = "b7e3f1a94c2d4e08a6d95f3c1e7b2a40"   # le fichier <clé>.txt doit exister à la racine
PARIS = ZoneInfo("Europe/Paris")
WORKER = "https://footlive.hgtrerza.workers.dev/soccer/"

ZONES = ["Europe/Paris", "Europe/London", "Africa/Casablanca", "Africa/Algiers", "Africa/Abidjan", "America/Toronto"]

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


def fmt_date(d, t):
    return t["datefmt"].format(wd=t["days"][d.weekday()], d=d.day, ord=t["first_ord"] if d.day == 1 else "",
                               mo=t["months"][d.month - 1], y=d.year)


def hhmm(d):
    return d.strftime("%H:%M")


def comp_page(lg):
    for rx, p in COMP_PAGES:
        if re.search(rx, lg or "", re.I):
            return p
    return None


def lg_name(lg, t):
    return t["lg"].get(lg, lg)


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


def paris_day(m):
    return datetime.fromisoformat(m["start"].replace("Z", "+00:00")).astimezone(PARIS).date()


def in_window(m, today):
    """Les versions traduites d'un match n'existent que près d'aujourd'hui (poids du dépôt)."""
    d = (paris_day(m) - datetime.fromisoformat(today).date()).days
    return LANG_WINDOW[0] <= d <= LANG_WINDOW[1]


def status_label(m, t):
    return t.get({"pre": "s_pre", "in": "s_in", "post": "s_post", "off": "s_off"}.get(m["state"], "s_pre"))


def score_txt(m):
    if m["state"] in ("pre", "off") or m.get("h") is None or m.get("a") is None:
        return "–"
    return f"{m['h']}–{m['a']}"


# ───────────────────────── Habillage : identique à l'accueil ─────────────────────────
# En-tête, logo, drapeaux et barre d'onglets viennent de /site-shell.css + index.html (rien n'est recopié à la main : si le logo
# ou les onglets de l'accueil changent, relancer ce script suffit). Ici : le CSS propre au contenu des pages.
CSS = """:root{--bg:#070b16;--card:#111a2b;--bd:#1f2c47;--tx:#e8edf7;--mu:#93a1bd;--ac:#22c55e;--rd:#ef4444}
main{line-height:1.6}
a{color:var(--ac);text-decoration:none}a:hover{text-decoration:underline}
.c{max-width:860px;margin:0 auto;padding:0 16px}
h1{font-size:1.5rem;line-height:1.25;margin:1.2rem 0 .4rem}h2{font-size:1.1rem;margin:1.6rem 0 .6rem}h3{font-size:.95rem;margin:1rem 0 .2rem}
p{margin:.4rem 0;color:var(--mu)}.crumbs{font-size:.8rem;color:var(--mu);margin-top:1rem}
.hero{background:linear-gradient(135deg,#0f2a1d,#11202f);border:1px solid rgba(34,197,94,.4);border-radius:16px;padding:18px 16px;margin:12px 0;text-align:center}
.hero .lg{color:var(--mu);font-size:.8rem}.hero .row{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:center;margin:10px 0}
.hero .t{font-weight:800;font-size:1.05rem;overflow-wrap:anywhere}.hero .sc{font-size:2rem;font-weight:800;letter-spacing:2px;font-variant-numeric:tabular-nums;direction:ltr}
.hero .st{font-weight:800;font-size:.8rem;color:var(--ac);text-transform:uppercase;letter-spacing:.5px}.hero .st.live{color:var(--rd)}
.cta{display:inline-block;background:var(--ac);color:#04210f;font-weight:800;padding:10px 16px;border-radius:12px;margin:8px 6px 0 0}.cta:hover{text-decoration:none;filter:brightness(1.1)}
.cta.alt{background:transparent;color:var(--ac);border:1px solid var(--ac)}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--bd);border-radius:12px;overflow:hidden;font-size:.92rem}
th,td{padding:9px 12px;text-align:start;border-bottom:1px solid var(--bd)}th{color:var(--mu);font-size:.75rem;text-transform:uppercase}
.m{list-style:none;padding:0;margin:0}.m li{display:flex;justify-content:space-between;gap:10px;background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:10px 12px;margin:6px 0}
.m time{color:var(--ac);font-weight:700;margin-inline-end:8px}.m small{color:var(--mu)}
.mm{list-style:none;padding:0;margin:0}.mm li{background:var(--card);border:1px solid var(--bd);border-radius:12px;margin:6px 0}.mm li.lv{border-color:var(--ac);box-shadow:inset 3px 0 0 var(--ac)}
.mm a.mc{display:grid;grid-template-columns:56px minmax(0,1fr) auto;column-gap:12px;row-gap:6px;align-items:center;padding:10px 12px;color:var(--tx);text-decoration:none}.mm a.mc:hover{text-decoration:none;background:rgba(255,255,255,.03);border-radius:12px}
.mm .mt{grid-column:1;grid-row:1/3;text-align:center;line-height:1.25}.mm .mt time{display:block;color:var(--ac);font-weight:800;font-size:.95rem}.mm .mt small{display:block;color:var(--mu);font-size:.7rem}
.mm .mt .bd{display:inline-block;background:var(--rd);color:#fff;font-weight:800;font-size:.62rem;padding:1px 5px;border-radius:4px;letter-spacing:.3px;margin-top:2px;white-space:nowrap}
.mm .th,.mm .ta{display:flex;align-items:center;gap:8px;min-width:0;font-weight:600;font-size:.95rem}.mm .th{grid-column:2;grid-row:1}.mm .ta{grid-column:2;grid-row:2}
.mm .th i,.mm .ta i{flex:none;width:20px;height:20px;border-radius:50%;background:#26324d;color:var(--mu);font-style:normal;font-size:.65rem;font-weight:800;display:flex;align-items:center;justify-content:center}
.mm .th b,.mm .ta b{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.mm .sh,.mm .sa{grid-column:3;text-align:center;min-width:18px;font-weight:800;font-size:.95rem;font-variant-numeric:tabular-nums;direction:ltr}.mm .sh{grid-row:1}.mm .sa{grid-row:2}.mm .sd{display:none}
.mm li.lv .sh,.mm li.lv .sa{color:var(--ac)}.mm li.pre .sh,.mm li.pre .sa{color:var(--mu);font-weight:400}
@media(min-width:700px){.mm a.mc{grid-template-columns:124px minmax(0,1fr) 30px 14px 30px minmax(0,1fr);column-gap:10px;row-gap:0;padding:12px 16px}
.mm .mt{grid-row:1;display:flex;align-items:center;justify-content:center;gap:8px;text-align:start}.mm .mt time,.mm .mt small{display:inline;font-size:.9rem}.mm .mt small{font-size:.72rem}.mm .mt .bd{margin-top:0}
.mm .th{grid-column:2;grid-row:1;flex-direction:row-reverse;justify-content:flex-start;text-align:end}.mm .th b{text-align:end}
.mm .sh{grid-column:3;grid-row:1}.mm .sd{display:block;grid-column:4;grid-row:1;text-align:center;color:var(--mu);font-weight:800}.mm .sa{grid-column:5;grid-row:1}
.mm .ta{grid-column:6;grid-row:1}}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}.chips a{border:1px solid var(--bd);background:var(--card);color:var(--tx);font-weight:700;font-size:.82rem;padding:7px 12px;border-radius:999px}
.cb-seo{margin:2rem 0 1rem;padding:1rem 4px 0;color:var(--mu);font-size:.85rem;line-height:1.7;border-top:1px solid var(--bd)}
.cb-seo h2{font-size:1rem;font-weight:700;color:var(--tx);margin:0 0 .5rem}.cb-seo h3{font-size:.9rem;font-weight:600;color:var(--tx);margin:.9rem 0 .2rem}
.cb-seo p{margin:.2rem 0}
footer{border-top:1px solid var(--bd);margin-top:2.5rem;padding:1rem 0 2rem;color:var(--mu);font-size:.82rem;text-align:center}footer a{color:var(--mu);margin:0 7px}
.lang-links{display:flex;flex-wrap:wrap;gap:6px 14px;justify-content:center;margin:0 0 .8rem}.lang-links a{margin:0}.lang-links a[aria-current]{color:var(--ac);font-weight:700}
.legal-links{margin:0 0 .6rem}
html[dir=rtl] body{text-align:right}"""

HEAD = """<!DOCTYPE html>
<html lang="{lang}" dir="{dir}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="theme-color" content="#070b16">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{url}">
{alts}
<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png?v=2">
<link rel="icon" href="/favicon.ico?v=2">
<link rel="apple-touch-icon" href="/favicon-192x192.png?v=2">
<link rel="manifest" href="/manifest.webmanifest">
<meta property="og:type" content="website">
<meta property="og:site_name" content="FootLive Pro">
<meta property="og:locale" content="{locale}">
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
<link rel="dns-prefetch" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=optional" rel="preload" as="style" onload="this.onload=null;if(matchMedia('(min-width:700px)').matches)this.rel='stylesheet'">
<noscript><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=optional" rel="stylesheet"></noscript>
<link rel="stylesheet" href="/site-shell.css?v=3">
<style>{css}</style></head><body>
{flags}
{header}
"""

GOAL_ICON = ('<svg class="gt-ic" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 5a2 2 0 1 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3h-16a4 4 0 0 0 2-3v-3a7 7 0 0 1 4-6"/>'
             '<path d="M9 17v1a3 3 0 0 0 6 0v-1"/></svg>')
CHEVRON = ('<svg class="chev" viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 4.5L6 8l3.5-3.5" fill="none" stroke="currentColor" '
           'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>')

# Menu du bas mobile (« Plus »), bouton « Buts » (même réglage fl_goal_alerts que l'accueil) et menu de langue.
SHELL_JS = """<script>
(function(){var bar=document.getElementById('tabbar');if(!bar)return;var box=bar.querySelector('.container');if(!box)return;
var C=__CFG__;
function fit(){bar.removeAttribute('data-tight');if(window.innerWidth<701)return;if(box.scrollWidth>box.clientWidth+1)bar.setAttribute('data-tight','1')}
fit();addEventListener('resize',fit);addEventListener('load',function(){fit();setTimeout(fit,700)});
if(box.querySelector('.more-btn'))return;
var SHORT=C.short;
box.querySelectorAll('a[data-go]').forEach(function(a){if(SHORT[a.dataset.go])a.setAttribute('data-short',SHORT[a.dataset.go])});
var btn=document.createElement('button');btn.type='button';btn.className='more-btn';btn.setAttribute('data-short',C.more);btn.setAttribute('aria-label',C.moreAria);btn.setAttribute('aria-haspopup','true');btn.setAttribute('aria-expanded','false');
btn.innerHTML='<span><svg class="svgi" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/></svg></span>';
box.appendChild(btn);
var sheet=document.createElement('div');sheet.className='more-sheet';sheet.hidden=true;sheet.innerHTML='<div class="more-bd"></div><div class="more-panel" role="menu"></div>';
var panel=sheet.querySelector('.more-panel');
['table','clubs','buteurs','news','women'].forEach(function(k){var o=box.querySelector('a[data-go="'+k+'"]');if(!o)return;var c=o.cloneNode(true);c.classList.remove('on');c.removeAttribute('aria-current');c.setAttribute('role','menuitem');panel.appendChild(c)});
var sl=box.querySelector('a[data-sel]');if(sl){var cs=sl.cloneNode(true);cs.setAttribute('role','menuitem');panel.appendChild(cs)}
bar.appendChild(sheet);
function set(o){sheet.hidden=!o;btn.setAttribute('aria-expanded',o?'true':'false')}
btn.addEventListener('click',function(e){e.stopPropagation();set(sheet.hidden)});
sheet.addEventListener('click',function(e){if(e.target.closest('a')||e.target.closest('.more-bd'))set(false)});
document.addEventListener('keydown',function(e){if(e.key==='Escape')set(false)});
addEventListener('resize',function(){if(innerWidth>700)set(false)});
})();
(function(){var C=__CFG__;
var g=document.getElementById('goal-toggle');
function on(){try{return localStorage.getItem('fl_goal_alerts')!=='false'}catch(e){return true}}
function paint(){if(!g)return;var o=on();g.classList.toggle('off',!o);g.setAttribute('aria-pressed',String(o));g.setAttribute('aria-label',o?C.goalOn:C.goalOff);g.title=o?C.goalOnT:C.goalOffT}
if(g){paint();g.addEventListener('click',function(){var o=!on();try{localStorage.setItem('fl_goal_alerts',JSON.stringify(o))}catch(e){}paint();
if(o&&'Notification' in window&&Notification.permission==='default'){try{Notification.requestPermission()}catch(e){}}});
addEventListener('storage',function(e){if(e.key==='fl_goal_alerts')paint()})}
var b=document.getElementById('lang-btn'),m=document.getElementById('lang-menu');if(!b||!m)return;
function c(){m.hidden=true;b.setAttribute('aria-expanded','false')}
b.addEventListener('click',function(e){e.stopPropagation();var o=m.hidden;m.hidden=!o;b.setAttribute('aria-expanded',o?'true':'false')});
document.addEventListener('click',function(e){if(!m.contains(e.target))c()});document.addEventListener('keydown',function(e){if(e.key==='Escape')c()});
})();
</script>
"""

# --- Éléments de l'accueil : logo, symboles de drapeaux, onglets (lus dans index.html pour rester IDENTIQUES) ---
_SHELL = {}
NAV_RE = re.compile(r'<nav id="tabbar".*?</div></nav>', re.S)
ROOT_PAGES = {"tv": "/programme-tv.html", "radio": "/radio.html", "table": "/classements.html", "news": "/actualites.html",
              "women": "/football-feminin.html"}


def _i18n_dict():
    """Dictionnaire de i18n.js (libellés des onglets par langue)."""
    try:
        t = open("i18n.js", encoding="utf-8").read()
        return json.loads(re.match(r'.*?var D=(\{.*?\});\nvar L=', t, re.S).group(1))
    except Exception:
        return {}


def shell_parts():
    """(logo, symboles de drapeaux, [(clé, html)] des onglets) lus dans index.html."""
    if _SHELL:
        return _SHELL["mark"], _SHELL["flags"], _SHELL["tabs"]
    try:
        t = open("index.html", encoding="utf-8").read()
    except OSError:
        t = ""
    m = re.search(r'<span class="brand-mark">.*?</span>', t, re.S)
    mark = m.group(0) if m else '<span class="brand-mark">⚽</span>'
    fl = re.search(r'<svg width="0" height="0"[^>]*>.*?</defs></svg>', t, re.S)
    flags = fl.group(0) if fl else ""
    nav = NAV_RE.search(t)
    anchors = re.findall(r'<a [^>]*>.*?</a>', nav.group(0), re.S) if nav else []
    tabs = []
    for a in anchors:
        a = re.sub(r'\s+class="on"', "", a)
        a = re.sub(r'\s+aria-current="page"', "", a)
        k = re.search(r'data-go="([^"]+)"', a)
        key = k.group(1) if k else ("mj" if "data-mj" in a else "sel" if "data-sel" in a else "x")
        tabs.append((key, a))
    if not tabs:   # index.html introuvable : barre minimale
        tabs = [("scores", '<a href="/" data-go="scores"><span></span>Scores</a>'),
                ("mj", '<a href="/matchs-du-jour.html" data-mj data-short="Matchs"><span></span>Matchs du jour</a>'),
                ("tv", '<a href="/programme-tv.html" data-go="tv"><span></span>Programme TV</a>'),
                ("radio", '<a href="/radio.html" data-go="radio"><span></span>Radio</a>')]
    _SHELL.update(mark=mark, flags=flags, tabs=tabs)
    return mark, flags, tabs


def _sel_label(lang):
    """Libellé de l'onglet Sélections de la langue (déjà traduit dans <langue>/index.html)."""
    try:
        t = open(("" if lang == "fr" else lang + "/") + "index.html", encoding="utf-8").read()
        a = re.search(r'<a [^>]*data-sel[^>]*>.*?</a>', NAV_RE.search(t).group(0), re.S).group(0)
        return re.sub(r'<[^>]+>', '', re.sub(r'<span>.*?</span>', '', a, flags=re.S)).strip()
    except Exception:
        return None


def nav_html(lang, active="mj"):
    """Barre d'onglets de l'accueil, dans la langue de la page ; « Matchs du jour » est actif sur le hub et sur les pages match."""
    t, p, D = T[lang], prefix(lang), _i18n_dict().get(lang, {})
    out = []
    for key, a in shell_parts()[2]:
        label = re.search(r'</span>([^<]*)</a>', a)
        label = label.group(1).strip() if label else ""
        if key == "scores": href, new = p + "/", D.get(label, label)
        elif key == "mj": href, new = p + "/matchs-du-jour.html", t["mj"]
        elif key == "clubs": href, new = p + "/#clubs", D.get(label, label)
        elif key == "buteurs": href, new = p + "/#buteurs", D.get(label, label)
        elif key == "sel": href, new = p + "/selections.html", _sel_label(lang) or label
        else: href, new = (p if key in ("tv", "radio", "table") else "") + ROOT_PAGES.get(key, "/"), D.get(label, label)   # Radio, Classements, Programme TV : pages traduites (/en/radio.html…)
        a = re.sub(r'href="[^"]*"', 'href="%s"' % href, a, count=1)
        a = re.sub(r'(</span>)[^<]*(</a>)', lambda m: m.group(1) + esc(new) + m.group(2), a, count=1)
        if key == "mj":
            a = re.sub(r'data-short="[^"]*"', 'data-short="%s"' % esc(t["mj_short"]), a)
            if active == "mj":
                a = a.replace("<a ", '<a class="on" aria-current="page" ', 1)
        out.append(a)
    return '<nav id="tabbar" aria-label="%s"><div class="container">%s</div></nav>' % (esc(t["nav_aria"]), "".join(out))


def header_html(lang, alt_urls):
    """En-tête de l'accueil : logo, bouton Buts, bouton de langue (menu vers la même page dans chaque langue), onglets."""
    t, p = T[lang], prefix(lang)
    items = "".join(
        '<a role="menuitem" href="%s" hreflang="%s" lang="%s"%s><svg class="fl" aria-hidden="true"><use href="#f-%s"/></svg>%s</a>'
        % (alt_urls[l], l, l, ' aria-current="true"' if l == lang else "", l, LANG_NAMES[l]) for l in LANG_ORDER)
    goal = ('<button type="button" id="goal-toggle" class="goal-toggle" aria-pressed="true" aria-label="%s" title="%s">%s'
            '<span class="gt-t">%s</span><span class="gt-sw" aria-hidden="true"><i></i></span></button>'
            % (esc(t["goal_on"]), esc(t["goal_on_t"]), GOAL_ICON, esc(t["goal"])))
    langbtn = ('<div class="lang-wrap" id="lang-wrap"><button type="button" class="lang-btn" id="lang-btn" aria-haspopup="true" aria-expanded="false" '
               'aria-label="%s"><svg class="fl" aria-hidden="true"><use href="#f-%s"/></svg><span>%s</span>%s</button>'
               '<div class="lang-menu" id="lang-menu" role="menu" hidden>%s</div></div>'
               % (esc(t["lang_aria"]), lang, lang.upper(), CHEVRON, items))
    return ('<header>\n<div class="container header-content"><a class="brand" href="%s/" aria-label="%s">%s<b>FootLive <span>Pro</span></b></a>'
            '<div class="hdr-capsule"><div class="header-actions">%s</div>%s</div></div>\n%s\n</header>\n'
            % (p, esc(t["brand_aria"]), shell_parts()[0], goal, langbtn, nav_html(lang)))


def footer_html(lang, alt_urls):
    t = T[lang]
    langs = "".join('<a href="%s" hreflang="%s" lang="%s"%s>%s</a>' % (alt_urls[l], l, l, ' aria-current="true"' if l == lang else "", LANG_NAMES[l])
                    for l in LANG_ORDER)
    legal = "".join('<a href="/%s">%s</a>' % (h, esc(n)) for h, n in t["legal"])
    cfg = json.dumps({"short": {"scores": t["short"]["scores"], "table": t["short"]["table"], "tv": t["short"]["tv"], "radio": t["short"]["radio"]},
                      "more": t["more"], "moreAria": t["more_aria"], "goalOn": t["goal_on"], "goalOff": t["goal_off"],
                      "goalOnT": t["goal_on_t"], "goalOffT": t["goal_off_t"]}, ensure_ascii=False)
    return ('<footer><div class="c"><nav class="lang-links" aria-label="%s">%s</nav><nav class="legal-links" aria-label="%s">%s</nav>'
            '<p>%s</p></div></footer>\n' % (esc(t["footer_lang_aria"]), langs, esc(t["footer_legal_aria"]), legal, esc(t["footer_copy"]))
            + SHELL_JS.replace("__CFG__", cfg))


def alternates(lang_urls):
    """<link rel=alternate hreflang> : uniquement les langues où la page existe vraiment ; x-default = français."""
    out = "".join('<link rel="alternate" hreflang="%s" href="%s">\n' % (l, u) for l, u in lang_urls.items())
    return out + '<link rel="alternate" hreflang="x-default" href="%s">' % lang_urls["fr"]


def head(lang, title, desc, url, ld, lang_urls, alt_urls):
    return HEAD.format(lang=lang, dir=T[lang]["dir"], title=esc(title), desc=esc(desc), url=url, site=SITE, css=CSS, ld=ld,
                       locale=LOCALES[lang], alts=alternates(lang_urls), flags=shell_parts()[1],
                       header=header_html(lang, alt_urls))


def ld_script(objs):
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": objs},
                                                              ensure_ascii=False).replace("<", "\\u003c") + "</script>"


def seo_block(h2, blocks, aria, **kw):
    """Texte SEO affiché en bas de page : un titre, un paragraphe d'introduction puis des questions/réponses."""
    out = '<section class="cb-seo" aria-label="%s"><h2>%s</h2>' % (esc(aria.format(**kw)), esc(h2.format(**kw)))
    for q, a in blocks:
        if q:
            out += "<h3>%s</h3>" % esc(q.format(**kw))
        out += "<p>%s</p>" % esc(a.format(**kw))
    return out + "</section>"


def urls_for_match(m, today):
    """(url par langue pour hreflang, lien du sélecteur de langue). Hors fenêtre : seul le français existe."""
    name = page_name(m)
    ok = lambda l: l == "fr" or in_window(m, today)
    lang_urls = {l: f"{SITE}{prefix(l)}/{DIR}/{name}.html" for l in LANG_ORDER if ok(l)}
    alt = {l: (f"{prefix(l)}/{DIR}/{name}.html" if ok(l) else f"{prefix(l)}/matchs-du-jour.html") for l in LANG_ORDER}
    return lang_urls, alt


def match_href(m, lang, today):
    """Lien vers la page d'un match dans la langue voulue (français si la version traduite n'existe pas)."""
    l = lang if (lang == "fr" or in_window(m, today)) else "fr"
    return f"{prefix(l)}/{DIR}/{page_name(m)}.html"


def build_match(m, siblings, lang, today):
    t = T[lang]
    start = datetime.fromisoformat(m["start"].replace("Z", "+00:00"))
    p = start.astimezone(PARIS)
    name = page_name(m)
    pre = prefix(lang)
    url = f"{SITE}{pre}/{DIR}/{name}.html"
    home, away = m["home"], m["away"]
    lgfr = m.get("lg") or "Football"
    lg = lg_name(lgfr, t)
    date, tm = fmt_date(p, t), hhmm(p)
    kw = dict(h=home, a=away, lg=lg, date=date, time=tm, tz=t["tzname"], at=t["at"])
    title = t["m_t1"].format(**kw)
    if len(title) > 70:
        title = t["m_t2"].format(**kw)
    desc = t["m_desc"].format(**kw)[:158]
    cp = comp_page(lgfr)
    hl, al = club_link(home), club_link(away)
    live_q = f"/match.html?id={m['id']}"
    lang_urls, alt_urls = urls_for_match(m, today)
    sep = "، " if lang == "ar" else ", "
    zones = sep.join(t["zone_fmt"].format(t=hhmm(start.astimezone(ZoneInfo(z))), c=n) for n, z in list(zip(t["zones"], ZONES))[1:4])

    event = {"@type": "SportsEvent", "name": f"{home} – {away}", "sport": "Football", "startDate": m["start"],
             "endDate": (start + timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
             "eventStatus": "https://schema.org/EventPostponed" if m["state"] == "off" else "https://schema.org/EventScheduled",
             "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
             "location": {"@type": "Place", "name": m.get("venue") or lg, "address": m.get("place") or "—"},
             "organizer": {"@type": "Organization", "name": lg, "url": f"{SITE}{pre}/{cp}.html" if cp else SITE + (pre or "") + "/"},
             "image": [SITE + "/og-image.png"],
             "homeTeam": {"@type": "SportsTeam", "name": home}, "awayTeam": {"@type": "SportsTeam", "name": away},
             "url": url}
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": t["home"], "item": SITE + (pre or "") + "/"},
        {"@type": "ListItem", "position": 2, "name": t["mj"], "item": f"{SITE}{pre}/matchs-du-jour.html"},
        {"@type": "ListItem", "position": 3, "name": f"{home} – {away}", "item": url}]}
    stadium = t["a3_venue"].format(v=m["venue"], p=(f" ({m['place']})" if m.get("place") else "")) if m.get("venue") else ""
    faq = [(t["q1"].format(**kw), t["a1"].format(zones=zones, **kw)),
           (t["q2"].format(**kw), t["a2"]),
           (t["q3"].format(**kw), t["a3"].format(**kw) + stadium)]
    faq_ld = {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}

    rows = "".join(f"<tr><td>{esc(n)}</td><td dir=\"ltr\">{hhmm(start.astimezone(ZoneInfo(z)))}</td></tr>" for n, z in zip(t["zones"], ZONES))
    chips = []
    if cp: chips.append(f'<a href="{pre}/{cp}.html">{esc(t["c_comp"].format(lg=lg))}</a>')
    if hl: chips.append(f'<a href="{hl}">{esc(t["c_club"].format(c=home))}</a>')
    if al: chips.append(f'<a href="{al}">{esc(t["c_club"].format(c=away))}</a>')
    chips += [f'<a href="{pre}/programme-tv.html">{esc(t["c_tv"])}</a>', f'<a href="{pre}/radio.html">{esc(t["c_radio"])}</a>',
              f'<a href="{pre}/classements.html">{esc(t["c_table"])}</a>', f'<a href="{pre}/matchs-du-jour.html">{esc(t["c_all"])}</a>']
    sib = "".join(
        f'<li><span><time datetime="{esc(s["start"])}">{hhmm(datetime.fromisoformat(s["start"].replace("Z", "+00:00")).astimezone(PARIS))}</time>'
        f'<a href="{match_href(s, lang, today)}">{esc(s["home"])} – {esc(s["away"])}</a></span><small>{status_label(s, t)}</small></li>'
        for s in siblings[:8])
    venue = ("<p>" + esc(t["venue"].format(v=m["venue"] + (f", {m['place']}" if m.get("place") else ""))) + "</p>") if m.get("venue") else ""
    stc = "st live" if m["state"] == "in" else "st"
    crumb_sep = "‹" if t["dir"] == "rtl" else "›"
    iso = (lambda x: "\u2066" + x + "\u2069") if t["dir"] == "rtl" else (lambda x: x)   # noms d'équipes latins dans un texte arabe
    kwb = {**kw, "h": iso(home), "a": iso(away)}
    faq_b = [(t["q1"].format(**kwb), t["a1"].format(zones=zones, **kwb)), (t["q2"].format(**kwb), t["a2"]),
             (t["q3"].format(**kwb), t["a3"].format(**kwb) + stadium)]
    seo = seo_block(t["seo_m_h2"], t["seo_m"], t["seo_m_h2"], **kwb)
    st_js = json.dumps({"live": t["s_in"], "post": t["s_post"]}, ensure_ascii=False)

    body = f"""<main class="c">
<p class="crumbs"><a href="{pre}/">{esc(t['home'])}</a> {crumb_sep} <a href="{pre}/matchs-du-jour.html">{esc(t['mj'])}</a> {crumb_sep} {esc(iso(home))} – {esc(iso(away))}</p>
<h1>{esc(t['m_h1'].format(**kwb))}</h1>
<p>{esc(t['m_sub'].format(**kw))}</p>
<section class="hero" id="match" data-id="{esc(m['id'])}" aria-label="{esc(t['hero_aria'])}">
<div class="lg">{esc(lg)}</div>
<div class="row"><div class="t">{esc(home)}</div><div class="sc" id="sc">{score_txt(m)}</div><div class="t">{esc(away)}</div></div>
<div class="{stc}" id="st">{status_label(m, t)}</div>
<a class="cta" href="{live_q}">{esc(t['cta1'])}</a><a class="cta alt" href="{pre}/radio.html">{esc(t['cta2'])}</a>
</section>
{venue}
<h2>{esc(t['h2_time'].format(**kwb))}</h2>
<table><thead><tr><th>{esc(t['th_city'])}</th><th>{esc(t['th_ko'])}</th></tr></thead><tbody>{rows}</tbody></table>
<p>{esc(t['time_note'])}</p>
<h2>{esc(t['h2_where'].format(**kwb))}</h2>
<p>{t['p_where'].format(tv=pre + '/programme-tv.html', radio=pre + '/radio.html')}</p>
<h2>{esc(t['h2_links'])}</h2>
<div class="chips">{''.join(chips)}</div>
{('<h2>' + esc(t['h2_others'].format(lg=lg)) + '</h2><ul class="m">' + sib + '</ul>') if sib else ''}
<h2>{esc(t['h2_faq'])}</h2>
{''.join(f'<h3>{esc(q)}</h3><p>{esc(a)}</p>' for q, a in faq_b)}
{seo}
</main>
<script>
(function(){{var ID="{esc(m['id'])}",T=new Date("{esc(m['start'])}"),ST={st_js};
if(Math.abs(Date.now()-T.getTime())>6*36e5)return;
function d(n){{var x=new Date(Date.now()+n*864e5);return x.toISOString().slice(0,10).replace(/-/g,"")}}
function tick(){{fetch("{WORKER}all/scoreboard?dates="+d(0)+"&limit=1000").then(function(r){{return r.json()}}).then(function(j){{
var ev=(j.events||[]).filter(function(e){{return String(e.id)===ID}})[0];if(!ev)return;
var c=(ev.competitions&&ev.competitions[0]||{{}}).competitors||[],h=c.filter(function(x){{return x.homeAway==="home"}})[0],a=c.filter(function(x){{return x.homeAway==="away"}})[0];
var s=(ev.status&&ev.status.type)||{{}},st=document.getElementById("st"),sc=document.getElementById("sc");
if(s.state==="pre"){{return}}
if(h&&a&&sc)sc.textContent=h.score+"–"+a.score;
if(st){{st.textContent=s.state==="in"?ST.live+" · "+((ev.status&&ev.status.displayClock)||""):ST.post;st.className=s.state==="in"?"st live":"st"}}
}}).catch(function(){{}})}}
tick();setInterval(tick,60000)}})();
</script>
"""
    page = head(lang, title, desc, url, ld_script([event, crumbs, faq_ld]), lang_urls, alt_urls) + body + footer_html(lang, alt_urls)
    return name, page, url


def upcoming_html(upcoming, today, lang):
    """Liste des matchs des prochains jours, groupés par jour : chaque match est lié à sa page (maillage interne)."""
    t = T[lang]
    days = {}
    for m in sorted(upcoming, key=lambda x: x["start"]):
        days.setdefault(paris_day(m), []).append(m)
    out = ""
    for day, ms in days.items():
        li = "".join(
            f'<li><span><time datetime="{esc(m["start"])}">{hhmm(datetime.fromisoformat(m["start"].replace("Z", "+00:00")).astimezone(PARIS))}</time>'
            f'<a href="{match_href(m, lang, today)}">{esc(m["home"])} – {esc(m["away"])}</a></span>'
            f'<small>{esc(lg_name(m.get("lg") or "Football", t))}</small></li>' for m in ms)
        d = datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc)
        out += f'<h3>{esc(fmt_date(d, t))}</h3><ul class="m">{li}</ul>'
    return (f'<h2>{esc(t["h_up_h2"])}</h2><p>{esc(t["h_up_p"])}</p>' + out) if out else ""


HUB_JS = r"""<script>
(function(){var L=__L__,list=document.querySelectorAll('.mm li[data-id]');if(!list.length||!window.fetch)return;
function esc(x){return String(x==null?'':x).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function paint(li,m){var live=m.state==='in',post=m.state==='post',show=(live||post)&&m.h!=null&&m.a!=null,hh=li.dataset.hh,iso=li.dataset.iso;
var st=live?'s_in':post?'s_post':m.state==='off'?'s_off':'s_pre',left;
if(live)left='<time datetime="'+iso+'">'+hh+'</time><span class="bd">'+esc(L.s_in).toUpperCase()+'</span>';
else left='<time datetime="'+iso+'">'+hh+'</time><small>'+esc(L[st])+'</small>';
var mt=li.querySelector('.mt'),sh=li.querySelector('.sh'),sa=li.querySelector('.sa');if(!mt||!sh||!sa)return;
var sig=m.state+'|'+m.h+'|'+m.a;if(li.dataset.sig===sig)return;li.dataset.sig=sig;
mt.innerHTML=left;sh.textContent=show?m.h:'–';sa.textContent=show?m.a:'–';
li.className=live?'lv':show?'':'pre'}
function run(){if(document.hidden)return;fetch('/matchs-du-jour.json?t='+(Date.now()/60000|0),{cache:'no-store'}).then(function(r){return r.ok?r.json():null}).then(function(d){if(!d||!d.matches)return;var by={};d.matches.forEach(function(m){by[m.id]=m});list.forEach(function(li){var m=by[li.dataset.id];if(m)paint(li,m)})}).catch(function(){})}
setInterval(run,60000);document.addEventListener('visibilitychange',function(){if(!document.hidden)run()});run();
})();
</script>"""


def hub_row(m, lang, today, t):
    """Une carte de match du hub (mobile : heure/statut à gauche, une équipe par ligne, score à droite)."""
    hh = hhmm(datetime.fromisoformat(m["start"].replace("Z", "+00:00")).astimezone(PARIS))
    live, post = m["state"] == "in", m["state"] == "post"
    show = (live or post) and m.get("h") is not None and m.get("a") is not None
    if live:
        left = (f'<span class="bd">{esc(t["s_in"]).upper()}</span>')
    else:
        left = f'<time datetime="{esc(m["start"])}">{hh}</time><small>{status_label(m, t)}</small>'
    if live:
        left = f'<time datetime="{esc(m["start"])}">{hh}</time>' + left
    sh, sa = (str(m["h"]), str(m["a"])) if show else ("–", "–")
    ini = lambda n: esc((n or "?").strip()[:1].upper())
    cls = "lv" if live else ("" if show else "pre")
    return (f'<li class="{cls}" data-id="{esc(m["id"])}" data-hh="{hh}" data-iso="{esc(m["start"])}"><a class="mc" href="{match_href(m, lang, today)}">'
            f'<div class="mt">{left}</div>'
            f'<span class="th"><i>{ini(m["home"])}</i><b>{esc(m["home"])}</b></span>'
            f'<span class="sh">{sh}</span><span class="sd">–</span><span class="sa">{sa}</span>'
            f'<span class="ta"><i>{ini(m["away"])}</i><b>{esc(m["away"])}</b></span></a></li>')


def build_hub(items, today, upcoming, lang):
    t, pre = T[lang], prefix(lang)
    url = f"{SITE}{pre}/matchs-du-jour.html"
    d = datetime.fromisoformat(today + "T12:00:00+00:00")
    date = fmt_date(d, t)
    kw = dict(d=d.day, mo=t["months"][d.month - 1], date=date, n=len(items), u=len(upcoming))
    title = t["h_t"].format(**kw)
    desc = (t["h_desc_up"] if upcoming else t["h_desc"]).format(**kw)[:158]
    lang_urls = {l: f"{SITE}{prefix(l)}/matchs-du-jour.html" for l in LANG_ORDER}
    alt_urls = {l: f"{prefix(l)}/matchs-du-jour.html" for l in LANG_ORDER}
    by = {}
    for m in items:
        by.setdefault(m.get("lg") or "Football", []).append(m)
    secs = ""
    for lgfr, ms in by.items():
        li = "".join(hub_row(m, lang, today, t) for m in sorted(ms, key=lambda x: x["start"]))
        secs += f"<h2>{esc(lg_name(lgfr, t))}</h2><ul class=\"mm\">{li}</ul>"
    crumbs = {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": t["home"], "item": SITE + (pre or "") + "/"},
        {"@type": "ListItem", "position": 2, "name": t["mj"], "item": url}]}
    crumb_sep = "‹" if t["dir"] == "rtl" else "›"
    seo = seo_block(t["seo_h_h2"], t["seo_h"], t["seo_h_h2"])
    body = f"""<main class="c">
<p class="crumbs"><a href="{pre}/">{esc(t['home'])}</a> {crumb_sep} {esc(t['mj'])}</p>
<h1>{esc(t['h_h1'].format(**kw))}</h1>
<p>{esc(t['h_intro'])}</p>
{secs or '<p>' + esc(t['h_empty']) + '</p>'}
{upcoming_html(upcoming, today, lang)}
<div class="chips"><a href="{pre}/programme-tv.html">{esc(t['c_tv'])}</a><a href="{pre}/classements.html">{esc(t['c_table'])}</a><a href="{pre}/radio.html">{esc(t['c_radio'])}</a><a href="/actualites.html">{esc(t['c_news'])}</a><a href="{pre}/">{esc(t['c_scores'])}</a></div>
{seo}
</main>
"""
    hub_js = HUB_JS.replace("__L__", json.dumps({k: t[k] for k in ("s_pre", "s_in", "s_post", "s_off")}, ensure_ascii=False))
    return head(lang, title, desc, url, ld_script([crumbs]), lang_urls, alt_urls) + body + footer_html(lang, alt_urls) + hub_js


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



LIVE_LOGO = {"fr": "EN DIRECT", "en": "LIVE", "es": "EN VIVO", "it": "LIVE", "nl": "LIVE", "de": "LIVE", "ar": "مباشر"}
def fixlogo(html, lang):
    return html.replace(">EN DIRECT</text>", ">" + LIVE_LOGO.get(lang, "EN DIRECT") + "</text>")

def match_dir(lang):
    return os.path.join(prefix(lang).lstrip("/"), DIR)


def main():
    ping = "--ping" in sys.argv
    src = json.load(open("matchs-du-jour.json", encoding="utf-8"))
    today = src["date"]
    for l in LANG_ORDER:
        os.makedirs(match_dir(l), exist_ok=True)
    reg = load_registry()
    new_urls = []
    for m in src["matches"] + src.get("soon", []):   # aujourd'hui + J+1/J+2 (pages en ligne avant le match)
        if m["id"] not in reg:
            new_urls.append(f"{SITE}/{DIR}/{page_name(m)}.html")
            if in_window(m, today):
                new_urls += [f"{SITE}{prefix(l)}/{DIR}/{page_name(m)}.html" for l in LANG_ORDER if l != "fr"]
        reg[m["id"]] = {**m, "seen": today}
    # purge des matchs trop anciens
    limit = (datetime.fromisoformat(today) - timedelta(days=KEEP_DAYS)).strftime("%Y-%m-%d")
    for k in [k for k, v in reg.items() if v["start"][:10] < limit]:
        for l in LANG_ORDER:
            try: os.remove(os.path.join(match_dir(l), page_name(reg[k]) + ".html"))
            except FileNotFoundError: pass
        del reg[k]

    by_lg = {}
    for m in reg.values():
        by_lg.setdefault(m.get("lg"), []).append(m)
    keep = {l: set() for l in LANG_ORDER}
    for m in reg.values():
        sib = sorted([s for s in by_lg[m.get("lg")] if s["id"] != m["id"] and s["start"][:10] == m["start"][:10]],
                     key=lambda s: s["start"])
        for l in LANG_ORDER:
            if l != "fr" and not in_window(m, today):
                continue
            name, page, _ = build_match(m, sib, l, today)
            keep[l].add(name + ".html")
            open(os.path.join(match_dir(l), name + ".html"), "w", encoding="utf-8").write(fixlogo(page, l))
    for l in LANG_ORDER:               # pages orphelines (ex. ancien nom, match sorti de la fenêtre de traduction)
        for f in os.listdir(match_dir(l)):
            if f.endswith(".html") and f not in keep[l]:
                os.remove(os.path.join(match_dir(l), f))
    json.dump(reg, open(REG, "w", encoding="utf-8"), ensure_ascii=False, indent=0)

    hub_items = sorted(src["matches"], key=lambda m: m["start"])
    # matchs des prochains jours (jour de Paris > aujourd'hui) : listés sur le hub pour que chaque page soit liée et explorable
    upcoming = [m for m in reg.values() if paris_day(m) > datetime.fromisoformat(today).date() and m["state"] in ("pre", "off")]
    for l in LANG_ORDER:
        out = "matchs-du-jour.html" if l == "fr" else os.path.join(l, "matchs-du-jour.html")
        open(out, "w", encoding="utf-8").write(fixlogo(build_hub(hub_items, today, upcoming, l), l))

    # lastmod : jamais dans le futur (un match de dans 5 jours est « vu » aujourd'hui)
    urls = [(f"{SITE}{prefix(l)}/matchs-du-jour.html", today) for l in LANG_ORDER]
    for m in sorted(reg.values(), key=lambda x: x["start"]):
        for l in LANG_ORDER:
            if l == "fr" or in_window(m, today):
                urls.append((f"{SITE}{prefix(l)}/{DIR}/{page_name(m)}.html", min(m["start"][:10], today)))
    with open("sitemap-matchs.xml", "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u, lm in urls:
            f.write(f"  <url><loc>{u}</loc><lastmod>{max(lm, today) if u.endswith('jour.html') else lm}</lastmod></url>\n")
        f.write("</urlset>\n")
    n_pages = sum(len(v) for v in keep.values())
    print(f"{len(reg)} matchs, {n_pages} pages match (7 langues), {len(LANG_ORDER)} hubs + sitemap-matchs.xml ; {len(new_urls)} nouvelles URL.")
    if ping and new_urls:   # cron toutes les 10 min : on ne notifie IndexNow que s'il y a de nouvelles pages
        ping_indexnow(new_urls + [f"{SITE}{prefix(l)}/matchs-du-jour.html" for l in LANG_ORDER])


if __name__ == "__main__":
    main()

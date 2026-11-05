#!/usr/bin/env python3
"""Génère radio.html, classements.html, actualites.html et football-feminin.html à partir de index.html.
Usage : python3 make_tab_pages.py [dossier]   (le dossier contient index.html ; par défaut le dossier courant)
Relancer après chaque modification de index.html. index.html est mis à jour une seule fois (liens + navigation)."""
import json, re, sys, os, html as H

D = sys.argv[1] if len(sys.argv) > 1 else "."
SITE = "https://www.footlivepro.com/"
src = open(os.path.join(D, "index.html"), encoding="utf-8").read()

def rep(t, a, b, n=1):
    assert t.count(a) == n, (a[:80], t.count(a))
    return t.replace(a, b)

# ---------- 1) index.html : navigation par vraies adresses ----------
if "const TAB_URL" not in src:
    src = rep(src, 'href="#scores" data-go="scores"', 'href="./" data-go="scores"')
    src = rep(src, 'href="#radio" data-go="radio"', 'href="radio.html" data-go="radio"')
    src = rep(src, 'href="#table" data-go="table"', 'href="classements.html" data-go="table"')
    src = rep(src, 'href="#news" data-go="news"', 'href="actualites.html" data-go="news"')
    src = rep(src, 'href="#women" data-go="women"', 'href="football-feminin.html" data-go="women"')
    src = rep(src, '  const PAGES = { scores:', '''  const TAB_URL = { radio: "radio.html", table: "classements.html", news: "actualites.html", women: "football-feminin.html" };
  const TAB_BACK = { "radio.html": "radio", "classements.html": "table", "actualites.html": "news", "football-feminin.html": "women" };
  const locPage = () => { const h = location.hash.slice(1); if (h) return h; return TAB_BACK[location.pathname.split("/").pop()] || "scores"; };
  const PAGES = { scores:''')
    src = rep(src, 'history.pushState(null, "", p === "scores" ? location.pathname + location.search : "#" + (',
              'history.pushState(null, "", TAB_URL[p] ? TAB_URL[p] + location.search + (p === "women" && wk ? "#women-" + wk : "") : p === "scores" ? (document.documentElement.dataset.tabpage ? "./" : location.pathname) + location.search : "#" + (')
    src = rep(src, 'window.addEventListener("popstate", () => showPage(location.hash.slice(1) || "scores", true));',
              'window.addEventListener("popstate", () => showPage(locPage(), true));')
    src = rep(src, '  const h0 = location.hash.slice(1); if ((PAGES[h0]',
              '  const h0 = location.hash.slice(1) || document.documentElement.dataset.start || "", t00 = document.title; if ((PAGES[h0]')
    src = rep(src, '/^women-/.test(h0)) && h0 !== "scores") showPage(h0, true);',
              '/^women-/.test(h0)) && h0 !== "scores") showPage(h0, true);\n  if (document.documentElement.dataset.start) { if (!location.hash) document.title = t00; document.documentElement.removeAttribute("data-start"); const ss = $("#static-seo"); if (ss) ss.remove(); }   // page d\'onglet (radio.html…) : le texte statique est remplacé par celui de l\'application')
    src = rep(src, '<p>Explorez aussi nos pages dédiées :',
              '<p>Pages à découvrir : <a href="radio.html" style="color:var(--accent)">radios foot en direct</a>, <a href="classements.html" style="color:var(--accent)">classements de football</a>, <a href="actualites.html" style="color:var(--accent)">actualités foot</a> et <a href="football-feminin.html" style="color:var(--accent)">football féminin</a>.</p>\n        <p>Explorez aussi nos pages dédiées :')
    open(os.path.join(D, "index.html"), "w", encoding="utf-8").write(src)
    print("index.html mis à jour")

# ---------- 2) pages d'onglets ----------
WL = [("uefa.wchampions", "Ligue des champions féminine"), ("eng.w.1", "Women's Super League"), ("fra.w.1", "Première Ligue (France)"), ("esp.w.1", "Liga F (Espagne)"),
      ("ger.w.1", "Frauen-Bundesliga"), ("ita.w.1", "Serie A féminine"), ("usa.nwsl", "NWSL (États-Unis)"), ("fifa.wwc", "Coupe du monde féminine"), ("uefa.weuro", "Euro féminin")]
LINKS = '<a href="clubs/">résultats des grands clubs</a> et le <a href="buteurs/">classement des meilleurs buteurs</a>'
PAGES = {
 "radio": dict(file="radio.html", name="Radios foot",
   title="Radio foot en direct : écouter les radios sport | FootLive Pro",
   desc="Écoutez les radios foot et sport en direct (RMC, BBC Radio 5 Live, talkSPORT, Cadena SER, COPE…) par compétition. Gratuit sur FootLive Pro.",
   faq=[("Comment écouter une radio foot en direct ?", "Touchez le bouton de lecture d’une radio : le flux démarre directement dans la page, sans application à installer. Si un flux est bloqué par la radio, le lien « ↗ » ouvre son site officiel."),
        ("La radio continue-t-elle quand je change d’onglet ?", "Oui. Le lecteur reste affiché en bas de l’écran : vous pouvez suivre les scores, les classements ou les actualités en continuant d’écouter le commentaire."),
        ("Les radios sont-elles gratuites ?", "Oui, l’écoute des radios sur FootLive Pro est gratuite.")],
   static=None),
 "table": dict(file="classements.html", name="Classements",
   title="Classements de football en direct : tous les championnats | FootLive Pro",
   desc="Classements de football en direct : Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Ligue des champions et plus. Mis à jour automatiquement sur FootLive Pro.",
   faq=[("Comment est établi le classement ?", "Les équipes sont classées selon leurs points (3 pour une victoire, 1 pour un nul), puis départagées par la différence de buts et les règles propres à chaque compétition."),
        ("Comment suivre mon équipe ?", "Touchez l’étoile à côté d’une équipe : elle est surlignée dans tous les classements.")],
   static='<h2>Classements de football : tous les championnats en direct</h2><p>FootLive Pro affiche le classement de nombreux championnats et compétitions : Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Liga Portugal, Botola Pro, Ligue des champions, Ligue Europa, Ligue Conférence, MLS, Saudi Pro League et plus. Choisissez une compétition dans la liste pour voir son classement mis à jour automatiquement.</p><h3>Comment est établi le classement ?</h3><p>Les équipes sont classées selon leurs points (3 pour une victoire, 1 pour un nul), puis départagées par la différence de buts et les règles propres à chaque compétition. Le tableau indique aussi les matchs joués, les victoires, nuls, défaites et les buts marqués et encaissés.</p><h3>Comment suivre mon équipe ?</h3><p>Touchez l’étoile ⭐ à côté d’une équipe : elle est surlignée dans tous les classements. Consultez aussi les <a href="buteurs/">meilleurs buteurs par compétition</a> et les <a href="clubs/">résultats des grands clubs</a>.</p>'),
 "news": dict(file="actualites.html", name="Actualités",
   title="Actualités football : les infos du jour | FootLive Pro",
   desc="Actualités football du jour : ESPN, BBC Sport, The Guardian, Sky Sports et L’Équipe. Transferts, résultats et compétitions, sur FootLive Pro.",
   faq=[("Où lire les actualités foot en français ?", "Sélectionnez L’Équipe — Football (FR) dans le menu pour lire les infos en français, ou choisissez la presse anglaise (BBC Sport, The Guardian, Sky Sports) et ESPN par championnat."),
        ("Peut-on filtrer les actus par compétition ?", "Oui : le menu déroulant propose les actualités de chaque grande compétition.")],
   static='<h2>Actualités football : les dernières infos du jour</h2><p>L’onglet Actus rassemble les dernières actualités du football international issues de sources reconnues : ESPN, BBC Sport, The Guardian, Sky Sports et L’Équipe. Transferts, résultats, blessures, compétitions européennes et championnats : les articles s’actualisent automatiquement.</p><h3>Où lire les actualités foot en français ?</h3><p>Sélectionnez L’Équipe — Football (FR) dans le menu pour lire les infos en français, ou choisissez la presse anglaise (BBC Sport, The Guardian, Sky Sports) et ESPN par championnat.</p><h3>Peut-on filtrer les actus par compétition ?</h3><p>Oui : le menu déroulant propose les actualités de chaque grande compétition. Retrouvez ensuite les <a href="clubs/">résultats des grands clubs</a> et le <a href="buteurs/">classement des buteurs</a>.</p>'),
 "women": dict(file="football-feminin.html", name="Football féminin",
   title="Football féminin : scores, classements et buteuses | FootLive Pro",
   desc="Football féminin : scores, résultats, classements, meilleures buteuses et actualités des compétitions féminines. Gratuit sur FootLive Pro.",
   faq=[("Quelles compétitions féminines suivre ?", ", ".join(n for _, n in WL) + "."),
        ("Comment voir le classement d’une compétition féminine ?", "Choisissez la compétition avec les boutons ou le menu en haut de la page : son classement s’affiche sous les résultats, avec les meilleures buteuses et les dernières actualités."),
        ("À quelle fréquence les données sont-elles mises à jour ?", "Les données du football féminin sont actualisées toutes les 6 heures.")],
   static='<h2>Football féminin : scores, classements et meilleures buteuses</h2><p>L’onglet Women’s Foot de FootLive Pro suit le football féminin : matchs à venir avec l’heure de Paris, derniers résultats, classement, meilleures buteuses et actualités de chaque compétition.</p><h3>Quelles compétitions féminines suivre ?</h3><p>' + ", ".join(n for _, n in WL) + '.</p><h3>Comment voir le classement d’une compétition féminine ?</h3><p>Choisissez la compétition avec les boutons ou le menu en haut de la page : son classement s’affiche sous les résultats, avec les meilleures buteuses et les dernières actualités.</p><h3>À quelle fréquence les données sont-elles mises à jour ?</h3><p>Les données du football féminin sont actualisées toutes les 6 heures. Pour le football masculin, retrouvez les <a href="clubs/">grands clubs</a> et les <a href="buteurs/">meilleurs buteurs</a>.</p>'),
}

e = lambda s: H.escape(s, quote=True)
ld0 = re.search(r'<script type="application/ld\+json">(.*?)</script>', src).group(1)
base = [g for g in json.loads(ld0)["@graph"] if g.get("@type") in ("WebSite", "Organization")]

for key, P in PAGES.items():
    url = SITE + P["file"]
    t = src
    t = rep(t, '<html lang="fr">', '<html lang="fr" data-start="%s" data-tabpage="1">' % key)
    t = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="%s">' % e(P["desc"]), t, 1)
    t = re.sub(r'<title>[^<]*</title>', '<title>%s</title>' % e(P["title"]), t, 1)
    t = t.replace('<link rel="canonical" href="%s">' % SITE, '<link rel="canonical" href="%s">' % url)
    t = t.replace('<link rel="alternate" hreflang="fr" href="%s">' % SITE, '<link rel="alternate" hreflang="fr" href="%s">' % url)
    t = t.replace('<link rel="alternate" hreflang="x-default" href="%s">' % SITE, '<link rel="alternate" hreflang="x-default" href="%s">' % url)
    t = t.replace('<meta property="og:url" content="%s">' % SITE, '<meta property="og:url" content="%s">' % url)
    t = re.sub(r'(<meta property="og:title" content=)"[^"]*"', r'\1"%s"' % e(P["title"]), t, 1)
    t = re.sub(r'(<meta property="og:description" content=)"[^"]*"', r'\1"%s"' % e(P["desc"]), t, 1)
    t = re.sub(r'(<meta name="twitter:title" content=)"[^"]*"', r'\1"%s"' % e(P["title"]), t, 1)
    t = re.sub(r'(<meta name="twitter:description" content=)"[^"]*"', r'\1"%s"' % e(P["desc"]), t, 1)
    # JSON-LD propre à la page (WebPage + fil d'Ariane + FAQ) ; l'aperçu des matchs du jour (accueil) est retiré
    graph = base + [
        {"@type": "WebPage", "@id": url + "#page", "url": url, "name": P["title"], "description": P["desc"], "inLanguage": "fr", "isPartOf": {"@id": SITE + "#site"}, "breadcrumb": {"@id": url + "#bc"}},
        {"@type": "BreadcrumbList", "@id": url + "#bc", "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Accueil", "item": SITE}, {"@type": "ListItem", "position": 2, "name": P["name"], "item": url}]},
        {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in P["faq"]]}]
    ld = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":")) + '</script>'
    t = re.sub(r'<script type="application/ld\+json">.*?</script>\n', ld + "\n", t, 1, flags=re.S)
    t = re.sub(r'<!--APERCU-LD-START-->.*?<!--APERCU-LD-END-->', '', t, 1, flags=re.S)
    t = re.sub(r'<!--APERCU-START-->.*?<!--APERCU-END-->', '', t, 1, flags=re.S)
    t = rep(t, '</head>', '<style>html[data-start] #scores-view{display:none}</style>\n</head>')
    if key == "radio":
        t = rep(t, '<div id="radio-view" hidden>', '<div id="radio-view">')   # texte visible dans le HTML pour les robots
    else:
        t = rep(t, '    </main>', '    <section id="static-seo" class="cb-seo" aria-label="%s">%s</section>\n    </main>' % (e(P["name"]), P["static"]))
    open(os.path.join(D, P["file"]), "w", encoding="utf-8").write(t)
    print(P["file"], len(t))

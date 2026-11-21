#!/usr/bin/env python3
"""Génère les pages « Sélections nationales » (selections.html, en/…, es/…, it/…, nl/…, de/…, ar/…) à partir de l'accueil de chaque langue,
pour qu'elles aient exactement le même habillage que la page d'accueil (en-tête, onglets, pubs, pied de page, cartes de match).
Ajoute aussi l'onglet « Sélections » dans la navigation de toutes les pages et corrige son affichage sur ordinateur.
Usage : python3 make_selections_page.py [dossier]   (le dossier contient index.html ; par défaut le dossier courant)
Fichiers utilisés : scripts/selections-view.js (logique + données ESPN), scripts/selections-view.css (habillage),
scripts/selections-i18n.json (textes, SEO et traductions par langue). Relancer après chaque modification de index.html."""
import json, re, sys, os, glob

D = sys.argv[1] if len(sys.argv) > 1 else "."
SC = os.path.join(D, "scripts")
I18N = json.load(open(os.path.join(SC, "selections-i18n.json"), encoding="utf-8"))
JS_FR = open(os.path.join(SC, "selections-view.js"), encoding="utf-8").read()
CSS = open(os.path.join(SC, "selections-view.css"), encoding="utf-8").read().strip()
LANGS = ["fr", "en", "es", "it", "nl", "de", "ar"]
SEG_MIN = 4

ICON = '<span><svg class="svgi" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 21V4M5 4h11l-2 4 2 4H5"/></svg></span>'
# Barre d'onglets sur ordinateur : tous les onglets tiennent dans la largeur de la page (avant : 1198 px pour 1100 px, « Sélections » était coupé)
NAVFIT = ('<style id="nav-fit">@media(min-width:701px){#tabbar .container{gap:0;justify-content:space-between}'
          '#tabbar a{padding:11px 10px;gap:6px;font-size:.86rem}#tabbar[data-tight] a{padding:11px 7px;gap:5px;font-size:.82rem}}</style>')
NAVSTABLE = '<style id="nav-stable">@media(max-width:700px){#tabbar .container{overflow:hidden!important;gap:0!important;padding:0 4px!important;justify-content:stretch!important}#tabbar .container>a,#tabbar .container>.more-btn{flex:1 1 0!important;min-width:0!important;max-width:none!important}#tabbar .container>a::after,#tabbar .container>.more-btn::after{max-width:100%;overflow:hidden;text-overflow:ellipsis}#tabbar .container:not(:has(.more-btn))::after{content:"";flex:1 1 0;order:6}#tabbar .container>a[data-sel],#tabbar .container>a[data-go="clubs"],#tabbar .container>a[data-go="table"],#tabbar .container>a[data-go="buteurs"],#tabbar .container>a[data-go="news"],#tabbar .container>a[data-go="women"]{display:none!important}}</style>'
# Si malgré tout les onglets dépassent la largeur (langues aux libellés longs), la barre passe en mode « serré » au lieu de couper le dernier onglet
NAVFIT_JS = ('<script id="nav-fit-js">(function(){var b=document.getElementById("tabbar");if(!b)return;var c=b.querySelector(".container");if(!c)return;'
             'function fit(){b.removeAttribute("data-tight");if(window.innerWidth<701)return;if(c.scrollWidth>c.clientWidth+1)b.setAttribute("data-tight","1")}'
             'fit();addEventListener("resize",fit);addEventListener("load",function(){fit();setTimeout(fit,700)});'
             'if(window.MutationObserver)new MutationObserver(fit).observe(c,{childList:true,characterData:true,subtree:true})})();</script>')

def rep(t, a, b, n=1):
    assert t.count(a) == n, (a[:90], t.count(a))
    return t.replace(a, b)

RENAME = [('<div class="day">', '<div class="sel-day">'), ('class="more"', 'class="sel-more"'), ('<div class="news">', '<div class="news-grid">'),
          ('<div class=\\"g\\">', '<div class=\\"cb-grid\\">'), ('<p class="sub">', '<p class="note">')]

def translate_js(lang):
    """Texte du script dans la langue de la page (les chaînes françaises du modèle sont remplacées par celles du fichier de traductions),
    puis noms de classes de l'habillage de l'accueil."""
    js = JS_FR
    if lang != "fr":
        d = I18N[lang]
        for a, b in sorted(d["whole"].items(), key=lambda kv: -len(kv[0])):
            if a in js:
                js = js.replace(a, b)
        # fragments de texte (entre deux balises ou entre guillemets) : remplacés seulement s'ils sont bornés ainsi, jamais au milieu d'un mot ou d'un nom (ex. « Europe/Paris »)
        for a, b in sorted(d["seg"].items(), key=lambda kv: -len(kv[0])):
            if len(a) >= SEG_MIN:
                js = re.sub(r"(?<=[\"'>])" + re.escape(a) + r"(?=[\"'<])", lambda m, b=b: b, js)
    for a, b in RENAME:
        assert a in js, a
        js = js.replace(a, b)
    return js

def add_nav_link(t, label):
    """Ajoute l'onglet Sélections (lien simple, comme sur l'accueil) et le correctif d'affichage PC, une seule fois par page."""
    m = re.search(r'<nav id="tabbar".*?</div></nav>', t, re.S)
    if not m:
        return t
    nav = m.group(0)
    if "data-sel" not in nav:
        new = nav[:-len("</div></nav>")] + '<a href="selections.html" data-sel>%s%s</a></div></nav>' % (ICON, label)
        t = t.replace(nav, new, 1)
    t = re.sub(r'<style id="nav-fit">.*?</style>\n?', '', t, flags=re.S)
    t = re.sub(r'<script id="nav-fit-js">.*?</script>\n?', '', t, flags=re.S)
    t = re.sub(r'<style id="nav-stable">.*?</style>\n?', '', t, flags=re.S)
    t = rep(t, "</head>", NAVFIT + "\n" + NAVSTABLE + "\n</head>")
    i = t.rindex("</body>")
    t = t[:i] + NAVFIT_JS + "\n" + t[i:]
    return t

def build_page(lang):
    d = I18N[lang]
    src_path = os.path.join(D, "index.html" if lang == "fr" else lang + "/index.html")
    t = open(src_path, encoding="utf-8").read()
    t = add_nav_link(t, d["navlabel"])
    # --- <html>
    t = re.sub(r"<html([^>]*)>", lambda m: "<html%s data-tabpage=\"1\" data-selpage=\"1\">" % m.group(1), t, 1)
    # --- SEO de la tête : titre, description, canonique, hreflang, Open Graph, Twitter, JSON-LD (venant du fichier de traductions)
    t = re.sub(r'<!--APERCU-LD-START-->.*?<!--APERCU-LD-END-->', '', t, 1, flags=re.S)
    t = re.sub(r'<!--APERCU-START-->.*?<!--APERCU-END-->', '', t, 1, flags=re.S)
    for pat in [r'[ \t]*<meta name="description"[^>]*>\n?', r'[ \t]*<link rel="canonical"[^>]*>\n?', r'[ \t]*<link rel="alternate" hreflang[^>]*>\n?',
                r'[ \t]*<meta property="og:[^>]*>\n?', r'[ \t]*<meta name="twitter:[^>]*>\n?', r'[ \t]*<script type="application/ld\+json">.*?</script>\n?']:
        t = re.sub(pat, '', t, flags=re.S)
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    block = "<title>%s</title>\n%s\n<script type=\"application/ld+json\">%s</script>" % (esc(d["title"]), d["head"], d["ld"])
    t = re.sub(r'<title>[^<]*</title>', lambda m: block, t, 1)
    # --- habillage
    t = rep(t, "</head>", '<style>html[data-selpage] #scores-view{display:none}</style>\n<style id="sel-css">\n%s\n</style>\n</head>' % CSS)
    # --- en-tête : le titre de la page est lu par les moteurs de recherche dans le h1
    t = re.sub(r'(<h1><span class="brand-mark">.*?</b>)<span class="sr-only">[^<]*</span>', lambda m: m.group(1) + '<span class="sr-only"> : %s</span>' % esc(re.sub(r"<[^>]+>", "", d["h1"])), t, 1, flags=re.S)
    # --- navigation : Sélections devient l'onglet actif
    nav = re.search(r'<nav id="tabbar".*?</div></nav>', t, re.S).group(0)
    nav2 = nav.replace(' class="on"', '', 1).replace('data-sel>', 'data-sel class="on" aria-current="page">', 1)
    t = t.replace(nav, nav2, 1)
    # --- sélecteur de langue : reste sur la page Sélections de l'autre langue (et non l'accueil)
    t = re.sub(r'href="(/(?:en/|es/|it/|nl/|de/|ar/)?)"(\s+hreflang=)', lambda m: 'href="%sselections.html"%s' % (m.group(1), m.group(2)), t)
    # --- contenu
    tabs = "".join('<button type="button" data-t="%s"%s>%s</button>' % (k, ' class="active"' if k == "up" else "", lab) for k, lab in zip(["up", "past", "teams", "news"], d["tabs"]))
    view = ('<div id="sel-view">\n'
            '<h2 class="sec-title">🌍 %(h1)s</h2>\n<p class="sel-lead">%(sub)s</p>\n'
            '<div class="filters" id="sel-comps" role="tablist" aria-label="%(ca)s"></div>\n'
            '<div class="filters" id="sel-tabs" role="tablist">%(tabs)s</div>\n'
            '<div id="sel-pane" aria-live="polite"></div>\n<noscript><p class="empty">%(ns)s</p></noscript>\n'
            '<section class="cb-seo" id="sel-seo" aria-label="%(h1a)s">%(seo)s</section>\n<p class="note">%(note)s</p>\n'
            '<dialog id="sel-td" aria-label="%(dlg)s"></dialog>\n</div>\n') % dict(h1=d["h1"], sub=d["sub"], ca=d["comps_aria"], tabs=tabs, ns=d["noscript"],
            h1a=re.sub(r"<[^>]+>", "", d["h1"]), seo=d["seo"], note=d["note"], dlg=d["dlg"])
    t = rep(t, '<div id="scores-view">', view + '    <div id="scores-view" hidden>')
    # --- script : logique de la page + passage d'un onglet à l'autre sans recharger
    wrapper = r"""(function(){
var view=document.getElementById('sel-view');if(!view)return;
var de=document.documentElement,T0=document.title,md=document.querySelector('meta[name="description"]'),D0=md&&md.content;
var VIEWS=['#scores-view','#table-view','#news-view','#radio-view','#clubs-view','#women-view','#scorers-view','#tv-view'];
function mark(on){document.querySelectorAll('#tabbar a[data-sel]').forEach(function(a){a.classList.toggle('on',on);if(on)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')})}
function enter(){VIEWS.forEach(function(s){var e=document.querySelector(s);if(e)e.hidden=true});view.hidden=false;de.setAttribute('data-selpage','1');mark(true);
 document.querySelectorAll('#tabbar [data-go]').forEach(function(b){b.classList.remove('on');b.removeAttribute('aria-current')});
 if(!location.hash){document.title=T0;if(md&&D0)md.setAttribute('content',D0)}}
function leave(){view.hidden=true;de.removeAttribute('data-selpage');mark(false)}
var orig=window.showPage;
if(typeof orig==='function')window.showPage=function(p,h){
 var onSel=/\/selections(\.html)?\/?$/.test(location.pathname)&&(!location.hash||(window.__selPick&&window.__selPick(location.hash.slice(1))));
 if(h&&onSel){enter();return}
 leave();return orig.apply(this,arguments)};
})();"""
    body_js = '<script>\n%s\n</script>\n<script>\n%s\n</script>\n' % (translate_js(lang), wrapper)
    t = rep(t, "</body>", body_js + "</body>")
    return t

def sitemap(today):
    f = os.path.join(D, "sitemap.xml")
    x = open(f, encoding="utf-8").read()
    if "selections.html" in x:
        return
    base = "https://www.footlivepro.com/"
    url = lambda l: base + ("" if l == "fr" else l + "/") + "selections.html"
    alt = "".join('    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>\n' % (l, url(l)) for l in LANGS) + '    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>\n' % url("fr")
    ent = "".join("  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n%s  </url>\n" % (url(l), today, alt) for l in LANGS)
    anchor = "  <url>\n    <loc>%sclubs/</loc>" % base
    assert x.count(anchor) == 1
    open(f, "w", encoding="utf-8").write(x.replace(anchor, ent + anchor, 1))
    print("sitemap.xml : pages Sélections ajoutées")

def main():
    for lang in LANGS:
        out = os.path.join(D, "selections.html" if lang == "fr" else lang + "/selections.html")
        t = build_page(lang)
        open(out, "w", encoding="utf-8").write(t)
        print(out, len(t))
    # onglet Sélections + correctif PC dans toutes les autres pages qui ont la barre d'onglets
    n = 0
    for f in sorted(glob.glob(os.path.join(D, "*.html")) + glob.glob(os.path.join(D, "*", "*.html"))):
        rel = os.path.relpath(f, D).replace(os.sep, "/")
        if rel.endswith("selections.html") or rel.split("/")[0] in ("clubs", "buteurs"):
            continue
        lang = rel.split("/")[0] if "/" in rel and rel.split("/")[0] in LANGS else "fr"
        t = open(f, encoding="utf-8").read()
        if '<nav id="tabbar"' not in t:
            continue
        t2 = add_nav_link(t, I18N[lang]["navlabel"])
        if t2 != t:
            open(f, "w", encoding="utf-8").write(t2); n += 1
    print("pages avec onglet mis à jour :", n)
    sitemap("2026-11-15")

if __name__ == "__main__":
    main()

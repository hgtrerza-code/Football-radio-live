#!/usr/bin/env python3
"""FootLive Pro : ajoute l'onglet « Matchs du jour » (2e position) dans la barre d'onglets de toutes les pages
statiques et place « Programme TV » en 3e position (ordre : Scores, Matchs du jour, Programme TV, Radio, ...).
Met aussi à jour l'ordre des icônes du menu du bas sur mobile.

Idempotent : une page qui a déjà l'onglet (attribut data-mj) n'est pas modifiée. À lancer à la racine du dépôt :
    python3 scripts/add_matchs_tab.py
Les pages generées (matchs-du-jour.html, matchs/*.html) ont leur propre barre, construite par generate_match_pages.py.
"""
import os, re, sys

ICON = ('<svg class="svgi" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/>'
        '<path d="M3 10h18M8 3v4M16 3v4"/><circle cx="12" cy="15.5" r="1.6"/></svg>')
NAV_RE = re.compile(r'<nav id="tabbar".*?</div></nav>', re.S)
A_RE = re.compile(r'<a [^>]*>.*?</a>', re.S)
ORDER_RE = re.compile(
    r'#tabbar \.container>a\[data-go="scores"\]\{order:1\}\s*'
    r'#tabbar \.container>a\[data-go="table"\]\{order:2\}\s*'
    r'#tabbar \.container>a\[data-go="tv"\]\{order:3\}\s*'
    r'#tabbar \.container>a\[data-go="radio"\]\{order:4\}\s*'
    r'#tabbar \.container>\.more-btn\{order:5;display:flex\}')
ORDER_NEW = ('#tabbar .container>a[data-go="scores"]{order:1}\n'
             '  #tabbar .container>a[data-mj]{order:2}\n'
             '  #tabbar .container>a[data-go="tv"]{order:3}\n'
             '  #tabbar .container>a[data-go="table"]{order:4}\n'
             '  #tabbar .container>a[data-go="radio"]{order:5}\n'
             '  #tabbar .container>.more-btn{order:6;display:flex}')


def patch(t):
    m = NAV_RE.search(t)
    if not m or "data-mj" in m.group(0):
        return t, "skip"
    nav = m.group(0)
    anchors = A_RE.findall(nav)
    scores = next((a for a in anchors if 'data-go="scores"' in a), None)
    tv = next((a for a in anchors if 'data-go="tv"' in a), None)
    if not scores or not tv:
        return t, "nav inattendue"
    prefix = re.search(r'href="([^"]*)programme-tv\.html"', tv).group(1)
    mj = f'<a href="{prefix}matchs-du-jour.html" data-mj data-short="Matchs"><span>{ICON}</span>Matchs du jour</a>'
    rest = [a for a in anchors if a is not scores and a is not tv]
    head = nav[:nav.index(anchors[0])]
    new_nav = head + scores + mj + tv + "".join(rest) + "</div></nav>"
    t = t.replace(nav, new_nav, 1)
    t = ORDER_RE.sub(lambda _: ORDER_NEW, t, count=1)
    return t, "ok"


def main():
    stats = {}
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", ".github", "matchs", "scripts", "clubs", "buteurs")]
        for f in files:
            if not f.endswith(".html") or (root == "." and f == "matchs-du-jour.html"):
                continue
            p = os.path.join(root, f)
            t = open(p, encoding="utf-8").read()
            new, st = patch(t)
            if st == "ok":
                open(p, "w", encoding="utf-8").write(new)
                if new.count("a[data-mj]{order:2}") != 1:
                    st = "ok (ordre mobile NON mis à jour)"
            stats.setdefault(st, []).append(p)
    for k, v in stats.items():
        print(f"{k}: {len(v)}", ("-> " + ", ".join(v[:6])) if k not in ("ok", "skip") or len(v) < 4 else "")


if __name__ == "__main__":
    main()

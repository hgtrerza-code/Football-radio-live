#!/usr/bin/env python3
"""Ajoute le bouton « Installer l'app » (install-app.js) à toutes les pages qui ont le menu du bas.
Usage (racine du dépôt) : python3 add-install-app.py
Sans danger si relancé : une page déjà modifiée est ignorée. Corrige aussi register("sw.js") -> register("/sw.js")."""
import os, re, sys

EARLY = '<script id="flp-ip">window.addEventListener("beforeinstallprompt",function(e){e.preventDefault();window.__flpIP=e;window.dispatchEvent(new Event("flp-ip"))});</script>\n<script src="/install-app.js" defer></script>\n'
D = sys.argv[1] if len(sys.argv) > 1 else "."
n = sw = skipped = 0
for root, dirs, files in os.walk(D):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "clubs", "buteurs", "scripts", ".github")]
    for fn in files:
        if not fn.endswith(".html"):
            continue
        p = os.path.join(root, fn)
        s = open(p, encoding="utf-8").read()
        o = s
        if 'register("sw.js")' in s:
            s = s.replace('register("sw.js")', 'register("/sw.js")')
            sw += 1
        if 'id="tabbar"' in s and 'id="flp-ip"' not in s:
            s = re.sub(r'<style id="install-app">.*?</style>\n?', '', s, flags=re.S)
            s = re.sub(r'<script>window\.addEventListener\("beforeinstallprompt".*?</script>\n?', '', s, flags=re.S)
            s = re.sub(r"<script>\n/\* Installer l'app : bouton.*?</script>\n?", '', s, flags=re.S)
            if s.count("</head>") != 1:
                print("ignorée (</head> introuvable ou multiple) :", p); skipped += 1
                continue
            s = s.replace("</head>", EARLY + "</head>", 1)
            n += 1
        if s != o:
            open(p, "w", encoding="utf-8").write(s)
print(n, "page(s) avec le bouton Installer,", sw, "page(s) avec register('/sw.js') corrigé,", skipped, "ignorée(s).")

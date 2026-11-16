#!/usr/bin/env python3
"""
Met à jour les <lastmod> de sitemap.xml, sitemap-langues-accueil.xml et sitemap-langues-competitions.xml
avec la date du dernier commit Git de chaque page (la date réelle de modification, pas l'heure du checkout).

- ne touche qu'aux balises <lastmod> : le reste du fichier (hreflang, ordre, etc.) reste identique
- jamais de date dans le futur ; page introuvable ou sans historique Git : la date existante est conservée
- dépôt « shallow » (checkout sans historique) : rien n'est modifié (les dates seraient fausses)
Dans GitHub Actions : actions/checkout avec fetch-depth: 0.
"""
import os
import re
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.environ.get("SEO_ROOT", ".")
BASE = "https://www.footlivepro.com"
FILES = ["sitemap.xml", "sitemap-langues-accueil.xml", "sitemap-langues-competitions.xml"]


def git(*args):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def page_file(loc):
    p = loc[len(BASE):] if loc.startswith(BASE) else loc
    if p.endswith("/"):
        p += "index.html"
    return p.lstrip("/")


def main():
    if not git("rev-parse", "--git-dir"):
        print("Pas de dépôt Git : dates inchangées.")
        return 0
    if git("rev-parse", "--is-shallow-repository") == "true":
        print("Dépôt incomplet (shallow) : dates inchangées (utiliser fetch-depth: 0).")
        return 0
    today = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
    cache, total = {}, 0
    for name in FILES:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        txt = open(path, encoding="utf-8").read()

        def fix(m):
            rel = page_file(m[2])
            if rel not in cache:
                d = git("log", "-1", "--format=%cs", "--", rel) if os.path.exists(os.path.join(ROOT, rel)) else ""
                cache[rel] = d if re.fullmatch(r"\d{4}-\d\d-\d\d", d) else ""
            d = min(cache[rel], today) if cache[rel] else m[3]
            return m[1] + d + m[4]

        new = re.sub(r"(<loc>([^<]*)</loc>\s*<lastmod>)([^<]*)(</lastmod>)", fix, txt)
        if new != txt:
            open(path, "w", encoding="utf-8").write(new)
            total += 1
            print("mis à jour :", name)
    print(f"{total} sitemap(s) modifié(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

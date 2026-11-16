#!/usr/bin/env python3
"""
FootLive Pro : génère une page statique par match (vraies URLs .html, indexables).

  matchs/<domicile>-<exterieur>-<id>.html   -> heure, score, buteurs, FAQ, lien vers le suivi en direct (match.html)
  matchs/index.html                         -> tous les matchs : en direct, aujourd'hui, à venir, derniers résultats
  sitemap-matchs.xml                        -> à soumettre dans Google Search Console (déjà listé dans robots.txt)

Matchs retenus : les 11 compétitions de la barre du site + tout match d'un club suivi (liste CLUBS d'index.html).
Fenêtre : 7 jours en arrière, 7 jours en avant. Les pages sortant de la fenêtre sont supprimées (le dépôt ne grossit pas).
Féminines, jeunes, réserves et compétitions israéliennes sont exclues.

Réutilise generate_seo_pages.py (même gabarit, mêmes règles). Aucune dépendance : Python 3.9+.
    python scripts/generate_match_pages.py
"""
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_seo_pages as G  # noqa: E402

BACK, FWD, MAX_PAGES = 7, 7, 400
DIR = "matchs"


# ----------------------------------------------------------------------------- lecture ESPN
def load_events(slug_names):
    """Un appel par compétition ; si ESPN refuse la période (HTTP 400...), elle est coupée en deux."""
    today = datetime.now(G.PARIS).date()
    d0, d1 = today - timedelta(days=BACK), today + timedelta(days=FWD)
    f = lambda d: d.strftime("%Y%m%d")  # noqa: E731

    def rng(slug, a, b, depth=0):
        j = G.fetch_json(f"{G.ESPN}/{slug}/scoreboard?dates={f(a)}-{f(b)}&limit=1000")
        if j is not None:
            return j.get("events", []), True
        if depth >= 2 or (b - a).days < 2:
            return [], False
        mid = a + timedelta(days=(b - a).days // 2)
        e1, o1 = rng(slug, a, mid, depth + 1)
        e2, o2 = rng(slug, mid + timedelta(days=1), b, depth + 1)
        return e1 + e2, o1 and o2

    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(lambda sl: (sl, rng(sl, d0, d1)), list(slug_names)))
    ok = sum(1 for _, (_, good) in res if good)
    return [(sl, ev) for sl, (evs, _) in res for ev in evs], ok, len(res)


def parse_event(ev, slug, lg):
    c = (ev.get("competitions") or [{}])[0]
    cp = c.get("competitors") or []
    h = next((x for x in cp if x.get("homeAway") == "home"), cp[0] if cp else None)
    a = next((x for x in cp if x.get("homeAway") == "away"), cp[1] if len(cp) > 1 else None)
    start = G.parse_dt(ev.get("date"))
    if not h or not a or not start or not ev.get("id"):
        return None
    ht, at = h.get("team") or {}, a.get("team") or {}
    home = ht.get("displayName") or ht.get("name") or ""
    away = at.get("displayName") or at.get("name") or ""
    if not home or not away or G.EXC.search(G.norm(home)) or G.EXC.search(G.norm(away)):
        return None
    st = ev.get("status") or {}
    ty = st.get("type") or {}
    label = (ty.get("name") or "") + " " + (ty.get("description") or "")
    ven = c.get("venue") or {}
    addr = ven.get("address") or {}
    goals = []
    for d in c.get("details") or []:
        if not d.get("scoringPlay"):
            continue
        who = ((d.get("athletesInvolved") or [{}])[0] or {}).get("displayName") or ""
        tid = str((d.get("team") or {}).get("id") or "")
        kind = ((d.get("type") or {}).get("text") or "")
        goals.append(dict(
            minute=(d.get("clock") or {}).get("displayValue") or "", who=who,
            team=home if tid and tid == str(ht.get("id") or "") else (away if tid and tid == str(at.get("id") or "") else ""),
            note="c.s.c." if re.search(r"own", kind, re.I) else ("pen." if re.search(r"penalty", kind, re.I) else "")))
    return dict(
        id=str(ev["id"]), start=start, state=ty.get("state") or "pre",
        off=bool(re.search(r"postponed|cancel|suspend|abandon", label, re.I)),
        cancelled=bool(re.search(r"cancel|abandon", label, re.I)),
        home=home, away=away, hs=h.get("score"), as_=a.get("score"), slug=slug, lg=lg,
        clock=st.get("displayClock") or "", venue=ven.get("fullName") or "",
        city=", ".join(x for x in (addr.get("city"), addr.get("country")) if x), goals=goals)


# ----------------------------------------------------------------------------- pages
def score(m):
    n = lambda v: "0" if v in (None, "") else str(v)  # noqa: E731
    return f"{n(m['hs'])}–{n(m['as_'])}"


def li(m, with_day=False):
    d = m["start"]
    if m["off"]:
        right, cls = "Reporté", ""
    elif m["state"] == "pre":
        right, cls = f"{d:%H:%M}", ""
    else:
        right, cls = score(m), ("live" if m["state"] == "in" else "")
    when = '<span class="live">● EN DIRECT</span>' if m["state"] == "in" else (G.fr_short(d) if with_day else f"{d:%H:%M}")
    return (f'<li><span class="d">{when}</span><span><a href="{G.match_url(m)}">{G.e(m["home"])} – {G.e(m["away"])}</a>'
            f'<span class="l">{G.e(m["lg"])}</span></span><span class="s {cls}">{right}</span></li>')


def match_page(m, clubs, leagues_by_slug, same_day):
    home, away, lg, d = m["home"], m["away"], m["lg"], m["start"]
    path = G.match_url(m)
    lgo = leagues_by_slug.get(m["slug"])
    comp_path = G.COMP_PAGES.get(lgo["key"]) if lgo else None
    comp_url = (G.BASE + f"/{comp_path}.html") if comp_path and os.path.exists(os.path.join(G.ROOT, comp_path + ".html")) else G.BASE + "/"
    day = G.fr_day(d)
    kick = f"{day} à {d:%H:%M} (heure de Paris)"
    sc = score(m)
    if m["off"]:
        status = "Match annulé" if m["cancelled"] else "Match reporté"
        head, box_small, box_main = f"{home} – {away} : match {'annulé' if m['cancelled'] else 'reporté'}", status, f"{home} – {away}"
        box_sub = f"Date initialement prévue : {kick}"
        title = f"{home} – {away} : {status.lower()} ({G.fr_short(d)})"
        desc = f"{home} – {away} ({lg}) : {status.lower()}. Date initialement prévue : {kick}. Suivi des scores sur FootLive Pro."
    elif m["state"] == "pre":
        head, box_small, box_main = f"{home} – {away} : heure du match et suivi en direct", "Coup d’envoi", f"{home} – {away}"
        box_sub = kick
        title = f"{home} – {away} : heure du match et suivi en direct ({G.fr_short(d)})"
        desc = f"{home} – {away} ({lg}) : coup d’envoi {kick}. Score en direct, compositions et statistiques sur FootLive Pro."
    elif m["state"] == "in":
        head, box_small, box_main = f"{home} {sc} {away} : match en direct", "En direct" + (f" · {m['clock']}" if m["clock"] else ""), f"{home} {sc} {away}"
        box_sub = f"{lg} · {day}"
        title = f"{home} {sc} {away} : match en direct ({G.fr_short(d)})"
        desc = f"{home} {sc} {away} en direct ({lg}) : score, buteurs, compositions et statistiques en temps réel sur FootLive Pro."
    else:
        head, box_small, box_main = f"{home} {sc} {away} : résumé, score et buteurs", "Terminé", f"{home} {sc} {away}"
        box_sub = f"{lg} · {day}"
        title = f"{home} {sc} {away} : résumé et buteurs ({G.fr_short(d)})"
        desc = f"{home} {sc} {away} ({lg}, {day}) : score final, buteurs et statistiques du match sur FootLive Pro."

    faqs = [(f"À quelle heure joue {home} – {away} ?",
             (f"{home} – {away} est reporté (date initialement prévue : {kick})." if m["off"]
              else f"{home} – {away} ({lg}) {'a été joué' if m['state'] == 'post' else 'est programmé'} le {kick}."))]
    if not m["off"] and m["state"] in ("in", "post"):
        faqs.append((f"Quel est le score de {home} – {away} ?",
                     f"{'Score actuel' if m['state'] == 'in' else 'Score final'} : {home} {sc} {away}."))
    goals_html = ""
    if m["goals"] and not m["off"]:
        rows = "".join(f'<li><span class="d">{G.e(x["minute"])}</span><span>{G.e(x["who"] or "But")}'
                       + (f' ({G.e(x["note"])})' if x["note"] else "") + (f'<span class="l">{G.e(x["team"])}</span>' if x["team"] else "")
                       + "</span><span></span></li>" for x in m["goals"])
        goals_html = f"<h2>Buteurs</h2><ul class=\"m\">{rows}</ul>"
        faqs.append((f"Qui a marqué lors de {home} – {away} ?",
                     "Buteurs : " + ", ".join(f"{x['who'] or 'but'} {x['minute']}".strip() + (f" ({x['note']})" if x["note"] else "") for x in m["goals"]) + "."))
    faqs.append((f"Où suivre {home} – {away} en direct ?",
                 "Sur FootLive Pro : score en direct, événements du match, compositions, statistiques et commentaires, "
                 "sans inscription, sur la page de suivi du match."))

    info = [("Compétition", lg), ("Date", f"{day} {d.year}"), ("Heure (Paris)", f"{d:%H:%M}")]
    if m["venue"]:
        info.append(("Stade", m["venue"] + (f" ({m['city']})" if m["city"] else "")))
    info_html = ("<h2>Informations sur le match</h2><table><thead><tr><th>Info</th><th>Détail</th></tr></thead><tbody>"
                 + "".join(f"<tr><td>{G.e(a)}</td><td>{G.e(b)}</td></tr>" for a, b in info) + "</tbody></table>")

    chips = []
    for t in (home, away):
        cs = G.club_slug_for(t, clubs)
        if cs:
            chips.append(f'<a href="/clubs/{cs}.html">{G.e(t)} : calendrier et résultats</a>')
    if comp_path and comp_url != G.BASE + "/":
        chips.append(f'<a href="/{comp_path}.html">{G.e(lg)}</a>')
    others = [x for x in same_day if x["id"] != m["id"]][:8]
    body = (f'<p class="crumbs"><a href="/">Accueil</a> › <a href="/matchs/">Matchs</a> › {G.e(home)} – {G.e(away)}</p>'
            f"<h1>{G.e(head)}</h1>"
            f"<p>{G.e(lg)} · {G.e(kick)}. Suivez {G.e(home)} – {G.e(away)} avec FootLive Pro : score, événements du match, compositions et statistiques.</p>"
            f'<div class="next"><small>{G.e(box_small)}</small><b>{G.e(box_main)}</b><span>{G.e(box_sub)}</span></div>'
            f'<a class="cta" href="/match.html?id={m["id"]}&amp;slug={G.e(m["slug"])}">▶ Suivre le match en direct (compos, stats, commentaires)</a>'
            + goals_html + info_html
            + "<h2>Questions fréquentes</h2>" + "".join(f"<h3>{G.e(q)}</h3><p>{G.e(a)}</p>" for q, a in faqs)
            + (f'<h2>Liens utiles</h2><div class="chips">{"".join(chips)}</div>' if chips else "")
            + (f'<h2>Autres matchs ce jour-là</h2><ul class="m">{"".join(li(x) for x in others)}</ul>' if others else ""))

    status_url = ("https://schema.org/EventCancelled" if m["cancelled"] else
                  "https://schema.org/EventPostponed" if m["off"] else "https://schema.org/EventScheduled")
    place = {"@type": "Place", "name": m["venue"] or f"Domicile de {home}"}
    if m["city"]:
        place["address"] = m["city"]
    ld_event = {"@context": "https://schema.org", "@type": "SportsEvent", "name": f"{home} – {away}", "sport": "Soccer",
                "description": desc, "startDate": d.isoformat(), "eventStatus": status_url,
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode", "url": G.BASE + path,
                "image": G.BASE + "/og-image.png", "location": place,
                "organizer": {"@type": "SportsOrganization", "name": lg, "url": comp_url},
                "homeTeam": {"@type": "SportsTeam", "name": home}, "awayTeam": {"@type": "SportsTeam", "name": away}}
    ld = [ld_event, G.breadcrumb([("Accueil", "/"), ("Matchs", "/matchs/"), (f"{home} – {away}", path)]), G.faq_ld(faqs)]
    return G.page(title + " | FootLive Pro", desc, path, body, ld)


def hub_page(matches):
    now = datetime.now(G.PARIS)
    today = now.date()
    live = [m for m in matches if m["state"] == "in"]
    by_day = {}
    for m in sorted(matches, key=lambda x: x["start"]):
        if m["state"] != "post" and m["state"] != "in" and m["start"].date() >= today:
            by_day.setdefault(m["start"].date(), []).append(m)
    past = sorted([m for m in matches if m["state"] == "post" and m["start"] >= now - timedelta(days=3)],
                  key=lambda x: x["start"], reverse=True)
    parts = []
    if live:
        parts.append(f'<h2>En direct</h2><ul class="m">{"".join(li(m) for m in live)}</ul>')
    for day, ms in sorted(by_day.items()):
        lab = "Aujourd’hui" if day == today else ("Demain" if day == today + timedelta(days=1) else G.fr_day(ms[0]["start"]))
        parts.append(f'<h2>{G.e(lab)}</h2><ul class="m">{"".join(li(m) for m in ms)}</ul>')
    if past:
        parts.append(f'<h2>Derniers résultats</h2><ul class="m">{"".join(li(m, True) for m in past)}</ul>')
    body = ('<p class="crumbs"><a href="/">Accueil</a> › Matchs</p><h1>Matchs de football : en direct, aujourd’hui et à venir</h1>'
            "<p>Heure, score et résumé des matchs des grands championnats, des coupes d’Europe et des principaux clubs, mis à jour automatiquement.</p>"
            + ("".join(parts) or "<p>Aucun match à afficher pour le moment.</p>")
            + '<p><a href="/clubs/">Clubs</a> · <a href="/buteurs/">Meilleurs buteurs</a> · <a href="/programme-tv.html">Programme TV</a></p>')
    return G.page("Matchs de football : en direct, aujourd’hui et à venir | FootLive Pro",
                  "Tous les matchs de football : heure, score en direct et résultats des grands championnats et des coupes d’Europe. Gratuit sur FootLive Pro.",
                  "/matchs/", body, [G.breadcrumb([("Accueil", "/"), ("Matchs", "/matchs/")])])


# ----------------------------------------------------------------------------- principal
def main():
    clubs, leagues = G.parse_index()
    slug_names = G.men_slugs(clubs, leagues)
    top = {sl for l in leagues if l["key"] in G.COMP_PAGES for sl in l["slugs"]}
    by_slug = {sl: l for l in leagues for sl in l["slugs"]}
    raw, ok, total = load_events(slug_names)
    print(f"{ok}/{total} compétitions lues")
    seen = {}
    for slug, ev in raw:
        m = parse_event(ev, slug, slug_names[slug])
        if not m or m["id"] in seen:
            continue
        if m["state"] == "pre" and not m["off"] and m["start"] < datetime.now(G.PARIS) - timedelta(hours=4):
            continue  # « à venir » plus de 4 h après le coup d'envoi : statut ESPN non fiable, pas de page
        if slug in top or G.club_slug_for(m["home"], clubs) or G.club_slug_for(m["away"], clubs):
            seen[m["id"]] = m
    matches = sorted(seen.values(), key=lambda x: x["start"])
    if not matches:
        print("Aucun match reçu : abandon, pages existantes conservées.")
        return 0
    if len(matches) > MAX_PAGES:  # garde-fou : on garde ceux les plus proches d'aujourd'hui
        now = datetime.now(G.PARIS)
        matches = sorted(sorted(matches, key=lambda x: abs((x["start"] - now).total_seconds()))[:MAX_PAGES], key=lambda x: x["start"])
    print(len(matches), "matchs retenus")

    written, changed = [], 0
    for m in matches:
        try:
            same_day = [x for x in matches if x["start"].date() == m["start"].date() and x["slug"] == m["slug"]]
            changed += G.write_if_changed(G.match_url(m).lstrip("/"), match_page(m, clubs, by_slug, same_day), written)
        except Exception as ex:  # noqa : une erreur sur un match ne doit pas bloquer les autres
            print("  ! match", m["id"], ex, file=sys.stderr)
    changed += G.write_if_changed(f"{DIR}/index.html", hub_page(matches), written)

    # suppression des pages sorties de la fenêtre (seulement si la lecture ESPN est à peu près complète)
    d = os.path.join(G.ROOT, DIR)
    if total and ok / total >= 0.7:
        keep = {os.path.basename(w) for w in written}
        for f in os.listdir(d):
            if f.endswith(".html") and f not in keep:
                os.remove(os.path.join(d, f))
                print("page de match retirée :", f)
    else:
        print("Lecture ESPN incomplète : aucune page supprimée.")

    today = datetime.now(G.PARIS).strftime("%Y-%m-%d")
    urls = ["/matchs/"] + [f"/{w}" for w in written if w != f"{DIR}/index.html"]
    changed += G.write_sitemap("sitemap-matchs.xml", urls, today)
    print(f"{len(written)} pages de match, {changed} fichiers modifiés")
    return 0


if __name__ == "__main__":
    sys.exit(main())

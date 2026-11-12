#!/usr/bin/env bash
# Corrige le décalage de l'en-tête sur mobile : le bouton « Buts » arrive tard et fait passer
# le bloc « Buts + langue » à la ligne suivante (la page descend de ~48 px).
# On réserve sa largeur dès le départ : l'affichage final reste identique.
# Usage (racine du dépôt) :
#   bash reserver-entete.sh        -> les 7 accueils seulement
#   bash reserver-entete.sh tout   -> toutes les pages qui ont cet en-tête (compétitions, etc.)
# Sans danger si relancé (une page déjà corrigée est ignorée).
width_for() { case "$1" in fr) echo 115;; en|es|nl) echo 123;; it) echo 108;; de) echo 115;; ar) echo 128;; *) echo "";; esac; }
if [ "$1" = "tout" ]; then
  FILES=$(grep -rl 'hdr-capsule' --include='*.html' . | grep -v '^./.git/')
else
  FILES="./index.html ./en/index.html ./es/index.html ./it/index.html ./nl/index.html ./de/index.html ./ar/index.html"
fi
n=0
for f in $FILES; do
  [ -f "$f" ] || continue
  grep -q 'id="hdr-reserve"' "$f" && continue
  grep -q 'hdr-capsule' "$f" || continue
  lang=$(grep -o -m1 '<html[^>]*lang="[a-z][a-z]' "$f" | sed 's/.*lang="//')
  w=$(width_for "$lang"); [ -n "$w" ] || continue
  sed -i "0,/<\/head>/s##<style id=\"hdr-reserve\">@media(max-width:600px){.hdr-capsule .header-actions{min-width:${w}px}}</style></head>#" "$f" && n=$((n+1))
done
echo "$n page(s) modifiée(s)."

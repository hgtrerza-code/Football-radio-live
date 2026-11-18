# Plan trafic FootLive Pro

Diagnostic fait sur le code (284 pages). Je n'ai pas vu Search Console ni les statistiques : les priorités ci-dessous sont à confirmer avec elles.

## Ce qui est déjà bon (ne pas toucher)
Titres, descriptions, canoniques et hreflang sur toutes les pages, JSON-LD, sitemaps cohérents avec les fichiers, 7 langues, PWA, pages clubs et buteurs, aucun titre ni description en double.

## Le problème principal
Le trafic foot vient des requêtes « équipe A – équipe B heure / chaîne / score ». Aucune page du site ne pouvait se classer dessus : `match.html` est en `noindex` et change selon l'URL. Le site ne cible que des requêtes génériques (« scores foot en direct »), dominées par Flashscore, SofaScore, L'Équipe et ESPN, des sites bien plus anciens et plus liés.

## Ce qui a été ajouté dans ce zip
1. **Une page indexable par match** : `/matchs/<equipe-a>-<equipe-b>-<id>.html` (heure dans 6 fuseaux, score qui se rafraîchit en direct, FAQ, schema SportsEvent + FAQPage + fil d'Ariane, liens vers compétition, clubs, radio, programme TV).
2. **Page hub** `/matchs-du-jour.html`, liée depuis l'accueil.
3. **Pages créées 2 jours à l'avance** (J+1, J+2), pour être indexées avant le match.
4. **`sitemap-matchs.xml`** déclaré dans `robots.txt`.
5. **IndexNow** (Bing, Yandex, etc.) : chaque nouvelle page est signalée automatiquement. Fichier clé : `b7e3f1a94c2d4e08a6d95f3c1e7b2a40.txt`.
6. **Maillage interne** : chaque match de l'aperçu de l'accueil pointe vers sa page, et le schema `SportsEvent` de l'accueil utilise l'URL du match.
7. Le workflow `apercu-matchs.yml` régénère tout toutes les 2 h ; les pages de plus de 10 jours sont supprimées.

## À faire par vous (je n'ai pas accès à ces comptes)
### Cette semaine
- **Search Console** : envoyer `sitemap-matchs.xml` ; demander l'indexation de `/matchs-du-jour.html` et de 5 pages match. Vérifier dans « Pages » ce qui est « Détectée, actuellement non indexée » : c'est le vrai indicateur du blocage.
- **Bing Webmaster Tools** : ajouter le site (import depuis Search Console en 1 clic) et envoyer les sitemaps. Bing alimente aussi DuckDuckGo et une partie des assistants IA.
- Publier une fois, puis vérifier dans GitHub Actions que l'étape « Pages indexables par match » passe au vert.

### Contenu (le plus rentable après les pages match)
- **Pages « où voir / à quelle heure » pour les gros matchs** (clasico, derbys, PSG–OM, matchs du Maroc, Ligue des champions) : 150 mots rédigés à la main (enjeu, forme, absents) valent plus que 10 pages automatiques.
- **Langues** : les pages en/es/de/it/nl/ar font 300 à 370 mots contre 1 000 en français. Traduire le bloc de texte de l'accueil et des compétitions dans les langues où vous voulez du trafic (arabe et espagnol d'abord, vu votre audience Botola/Maroc).
- **Pages clubs** : 101 clubs en français uniquement. Ajouter les clubs de Botola Pro et de CAF, très recherchés au Maroc et en Afrique du Nord.

### Hors du site (c'est ce qui manque le plus : l'autorité)
- **Backlinks** : proposer le site comme ressource à des blogs, forums et sites de supporters (Wydad, Raja, PSG, OM…), ajouter le lien sur vos profils, et déclarer le site sur des annuaires sportifs sérieux. Évitez les liens achetés en masse : risque de pénalité.
- **Réseaux** : un compte X/Telegram/WhatsApp Channel publiant chaque jour « les matchs du jour » avec le lien du hub. Les chaînes Telegram et WhatsApp de foot ramènent du trafic direct et régulier.
- **Google Discover** : nécessite des images d'au moins 1200 px et un contenu éditorial régulier (voir `actualites.html`). Les articles originaux courts (analyses, pronostics factuels, stats) y passent mieux que les titres repris de flux.
- **Rétention** : l'installation PWA existe déjà ; ajouter des notifications push (OneSignal gratuit) pour « but » et « début du match » multiplie les retours.

### Performance (Core Web Vitals)
Chaque page HTML pèse 320 à 500 Ko (CSS et JS en ligne). Déplacer le JS commun dans un fichier mis en cache (comme `competition.js`) et compresser `og-image.png` ; mesurer avant/après sur PageSpeed Insights (mobile).

## Résultats à attendre
Les pages match sont indexées en quelques jours à quelques semaines, mais le trafic vient surtout des matchs moins couverts et des requêtes longues. Comptez 2 à 3 mois et la progression des backlinks pour voir un effet net. Suivez : pages indexées (Search Console), impressions sur les requêtes contenant « – » ou « vs », clics.

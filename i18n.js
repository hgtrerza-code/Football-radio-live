/* FootLive Pro — changement de langue (FR, EN, AR, DE, NL, ES)
   À charger tout en haut de <head> : <script src="i18n.js"></script>
   - Le français reste la langue par défaut (rien ne change pour le SEO / les robots).
   - Le choix est mémorisé (localStorage "fl_lang") puis la page se recharge.
   - Traduit l'interface (onglets, boutons, messages, pied de page...) + dates/heures/nombres.
   - Pour traduire un texte de plus : ajouter une ligne [fr, en, ar, de, nl, es] dans D. */
(function () {
  "use strict";
  var LANGS = ["fr", "en", "ar", "de", "nl", "es"];
  var NAMES = { fr: "Français", en: "English", ar: "العربية", de: "Deutsch", nl: "Nederlands", es: "Español" };
  var LOC = { fr: "fr-FR", en: "en-GB", ar: "ar-MA", de: "de-DE", nl: "nl-NL", es: "es-ES" };

  var lang = "fr";
  try { var s = localStorage.getItem("fl_lang"); if (LANGS.indexOf(s) >= 0) lang = s; } catch (e) { }
  var idx = LANGS.indexOf(lang);

  // ---------- Dictionnaire : [fr, en, ar, de, nl, es] ----------
  var D = [
    // Onglets
    ["Scores", "Scores", "المباريات", "Spiele", "Wedstrijden", "Marcadores"],
    ["Radio", "Radio", "الراديو", "Radio", "Radio", "Radio"],
    ["Clubs", "Clubs", "الأندية", "Vereine", "Clubs", "Clubes"],
    ["Classements", "Standings", "الترتيب", "Tabellen", "Standen", "Clasificaciones"],
    ["Classement", "Standings", "الترتيب", "Tabelle", "Stand", "Clasificación"],
    ["Buteurs", "Top scorers", "الهدافون", "Torschützen", "Topscorers", "Goleadores"],
    ["Actus", "News", "الأخبار", "News", "Nieuws", "Noticias"],
    ["Programme TV", "TV schedule", "برنامج التلفزيون", "TV-Programm", "TV-gids", "Programación TV"],
    // Filtres
    ["En direct", "Live", "مباشر", "Live", "Live", "En vivo"],
    ["Aujourd'hui", "Today", "اليوم", "Heute", "Vandaag", "Hoy"],
    ["Aujourd’hui", "Today", "اليوم", "Heute", "Vandaag", "Hoy"],
    ["Résultats", "Results", "النتائج", "Ergebnisse", "Uitslagen", "Resultados"],
    ["À venir", "Upcoming", "القادمة", "Demnächst", "Binnenkort", "Próximos"],
    ["AUJ.", "TODAY", "اليوم", "HEUTE", "VANDAAG", "HOY"],
    ["🌍 Toutes les ligues", "🌍 All leagues", "🌍 كل الدوريات", "🌍 Alle Ligen", "🌍 Alle competities", "🌍 Todas las ligas"],
    ["Toutes les ligues", "All leagues", "كل الدوريات", "Alle Ligen", "Alle competities", "Todas las ligas"],
    ["Toutes les compétitions", "All competitions", "كل المسابقات", "Alle Wettbewerbe", "Alle competities", "Todas las competiciones"],
    ["🔍 Rechercher une équipe...", "🔍 Search a team...", "🔍 ابحث عن فريق...", "🔍 Mannschaft suchen...", "🔍 Zoek een team...", "🔍 Buscar un equipo..."],
    ["Rechercher une radio (nom, ville…)", "Search a radio (name, city…)", "ابحث عن إذاعة (الاسم، المدينة…)", "Radio suchen (Name, Stadt …)", "Zoek een radio (naam, stad…)", "Buscar una radio (nombre, ciudad…)"],
    ["Rechercher un club...", "Search a club...", "ابحث عن نادٍ...", "Verein suchen...", "Zoek een club...", "Buscar un club..."],
    ["Rechercher un club", "Search a club", "ابحث عن نادٍ", "Verein suchen", "Zoek een club", "Buscar un club"],
    // Titres de sections
    ["📅 Calendrier & résultats", "📅 Fixtures & results", "📅 المباريات والنتائج", "📅 Spielplan & Ergebnisse", "📅 Programma & uitslagen", "📅 Calendario y resultados"],
    ["touchez un match pour voir les statistiques détaillées", "tap a match to see detailed stats", "المس مباراة لعرض الإحصائيات التفصيلية", "Spiel antippen für detaillierte Statistiken", "tik op een wedstrijd voor gedetailleerde statistieken", "toca un partido para ver las estadísticas detalladas"],
    ["📻 Foot Radio", "📻 Football Radio", "📻 راديو كرة القدم", "📻 Fußball-Radio", "📻 Voetbalradio", "📻 Radio de fútbol"],
    ["écoutez les radios en direct, classées par type de compétition", "listen to live radio, sorted by competition type", "استمع إلى الإذاعات مباشرة، مصنفة حسب نوع المسابقة", "Radios live hören, nach Wettbewerb sortiert", "luister live naar radio, gesorteerd per competitie", "escucha radios en directo, clasificadas por competición"],
    ["📺 Programme TV", "📺 TV schedule", "📺 برنامج التلفزيون", "📺 TV-Programm", "📺 TV-gids", "📺 Programación TV"],
    ["les matchs importants et la chaîne qui les diffuse", "the key matches and the channel showing them", "أهم المباريات والقناة الناقلة لها", "die wichtigsten Spiele und der übertragende Sender", "de belangrijkste wedstrijden en de zender die ze uitzendt", "los partidos importantes y el canal que los emite"],
    // Chargements / messages vides
    ["Chargement…", "Loading…", "جارٍ التحميل…", "Wird geladen…", "Laden…", "Cargando…"],
    ["Chargement du programme…", "Loading schedule…", "جارٍ تحميل البرنامج…", "Programm wird geladen…", "Programma laden…", "Cargando la programación…"],
    ["Chargement des infos du football…", "Loading football news…", "جارٍ تحميل أخبار كرة القدم…", "Fußball-News werden geladen…", "Voetbalnieuws laden…", "Cargando noticias de fútbol…"],
    ["Chargement du direct…", "Loading live matches…", "جارٍ تحميل المباريات المباشرة…", "Live-Spiele werden geladen…", "Live wedstrijden laden…", "Cargando partidos en directo…"],
    ["Chargement du classement…", "Loading standings…", "جارٍ تحميل الترتيب…", "Tabelle wird geladen…", "Stand laden…", "Cargando la clasificación…"],
    ["Chargement du calendrier…", "Loading fixtures…", "جارٍ تحميل المباريات…", "Spielplan wird geladen…", "Programma laden…", "Cargando el calendario…"],
    ["Chargement des statistiques…", "Loading stats…", "جارٍ تحميل الإحصائيات…", "Statistiken werden geladen…", "Statistieken laden…", "Cargando estadísticas…"],
    ["Aucun résultat récent.", "No recent results.", "لا توجد نتائج حديثة.", "Keine aktuellen Ergebnisse.", "Geen recente uitslagen.", "Sin resultados recientes."],
    ["Aucun match en direct pour le moment.", "No live matches right now.", "لا توجد مباريات مباشرة حاليًا.", "Derzeit keine Live-Spiele.", "Momenteel geen live wedstrijden.", "No hay partidos en directo ahora."],
    ["Aucun match à venir pour le moment.", "No upcoming matches for now.", "لا توجد مباريات قادمة حاليًا.", "Derzeit keine anstehenden Spiele.", "Momenteel geen aankomende wedstrijden.", "No hay próximos partidos por ahora."],
    ["Aucun match pour ces critères.", "No matches for these criteria.", "لا توجد مباريات بهذه المعايير.", "Keine Spiele für diese Kriterien.", "Geen wedstrijden voor deze criteria.", "Ningún partido con estos criterios."],
    ["Aucun club trouvé.", "No club found.", "لم يتم العثور على أي نادٍ.", "Kein Verein gefunden.", "Geen club gevonden.", "Ningún club encontrado."],
    ["Aucun but enregistré pour le moment.", "No goals recorded yet.", "لا توجد أهداف مسجلة حتى الآن.", "Noch keine Tore erfasst.", "Nog geen doelpunten geregistreerd.", "Aún no hay goles registrados."],
    ["Aucun match avec chaîne annoncée ce jour-là.", "No match with an announced channel that day.", "لا توجد مباراة بقناة معلنة في هذا اليوم.", "An diesem Tag kein Spiel mit angekündigtem Sender.", "Geen wedstrijd met aangekondigde zender op die dag.", "Ningún partido con canal anunciado ese día."],
    ["Aucun match annoncé dans les prochains jours", "No matches announced in the coming days", "لا توجد مباريات معلنة في الأيام القادمة", "In den nächsten Tagen sind keine Spiele angekündigt", "Geen wedstrijden aangekondigd de komende dagen", "Ningún partido anunciado en los próximos días"],
    // Statuts
    ["Terminé", "Finished", "انتهت", "Beendet", "Afgelopen", "Finalizado"],
    ["Reporté", "Postponed", "مؤجلة", "Verschoben", "Uitgesteld", "Aplazado"],
    ["Mi-temps", "Half-time", "استراحة", "Halbzeit", "Rust", "Descanso"],
    ["Direct", "Live", "مباشر", "Live", "Live", "Directo"],
    ["Hors ligne", "Offline", "غير متصل", "Offline", "Offline", "Sin conexión"],
    ["Erreur", "Error", "خطأ", "Fehler", "Fout", "Error"],
    ["Prochain match", "Next match", "المباراة القادمة", "Nächstes Spiel", "Volgende wedstrijd", "Próximo partido"],
    ["📡 Hors connexion — affichage des dernières données enregistrées", "📡 Offline — showing the last saved data", "📡 لا يوجد اتصال — عرض آخر البيانات المحفوظة", "📡 Offline — zuletzt gespeicherte Daten werden angezeigt", "📡 Offline — laatst opgeslagen gegevens worden getoond", "📡 Sin conexión — mostrando los últimos datos guardados"],
    ["🔔 Buts : activés", "🔔 Goals: on", "🔔 الأهداف: مفعّلة", "🔔 Tore: an", "🔔 Doelpunten: aan", "🔔 Goles: activados"],
    ["🔕 Buts : désactivés", "🔕 Goals: off", "🔕 الأهداف: معطّلة", "🔕 Tore: aus", "🔕 Doelpunten: uit", "🔕 Goles: desactivados"],
    // Détail d'un match
    ["Compétition", "Competition", "المسابقة", "Wettbewerb", "Competitie", "Competición"],
    ["Statut", "Status", "الحالة", "Status", "Status", "Estado"],
    ["Coup d'envoi", "Kick-off", "ضربة البداية", "Anstoß", "Aftrap", "Saque inicial"],
    ["Capacité", "Capacity", "السعة", "Kapazität", "Capaciteit", "Capacidad"],
    ["👥 Affluence", "👥 Attendance", "👥 الحضور الجماهيري", "👥 Zuschauer", "👥 Opkomst", "👥 Asistencia"],
    ["⚽ Buteurs", "⚽ Scorers", "⚽ الهدافون", "⚽ Torschützen", "⚽ Doelpuntenmakers", "⚽ Goleadores"],
    ["Forme récente", "Recent form", "الأداء الأخير", "Aktuelle Form", "Recente vorm", "Forma reciente"],
    ["Meilleurs joueurs", "Top players", "أفضل اللاعبين", "Beste Spieler", "Beste spelers", "Mejores jugadores"],
    ["Confrontations directes", "Head-to-head", "المواجهات المباشرة", "Direkter Vergleich", "Onderlinge duels", "Enfrentamientos directos"],
    // Pied de page / divers
    ["À propos", "About", "حول الموقع", "Über uns", "Over ons", "Acerca de"],
    ["Mentions légales", "Legal notice", "إشعار قانوني", "Impressum", "Juridische informatie", "Aviso legal"],
    ["Confidentialité", "Privacy", "الخصوصية", "Datenschutz", "Privacy", "Privacidad"],
    ["Contact", "Contact", "اتصل بنا", "Kontakt", "Contact", "Contacto"],
    ["Gérer les cookies", "Manage cookies", "إدارة ملفات تعريف الارتباط", "Cookies verwalten", "Cookies beheren", "Gestionar cookies"],
    ["Publicité", "Advertisement", "إعلان", "Werbung", "Advertentie", "Publicidad"],
    ["Remonter", "Back to top", "إلى الأعلى", "Nach oben", "Naar boven", "Subir"],
    ["Langue", "Language", "اللغة", "Sprache", "Taal", "Idioma"],
    ["Navigation du site", "Site navigation", "التنقل في الموقع", "Seitennavigation", "Sitenavigatie", "Navegación del sitio"],
    ["Meilleures compétitions", "Top competitions", "أفضل المسابقات", "Top-Wettbewerbe", "Topcompetities", "Mejores competiciones"],
    ["Actualités du football mondial", "World football news", "أخبار كرة القدم العالمية", "Weltfußball-News", "Wereldvoetbalnieuws", "Noticias del fútbol mundial"],
    ["Lecteur radio", "Radio player", "مشغل الراديو", "Radio-Player", "Radiospeler", "Reproductor de radio"],
    // Compétitions et pays
    ["Ligue des champions", "Champions League", "دوري أبطال أوروبا", "Champions League", "Champions League", "Liga de Campeones"],
    ["Ligue Europa", "Europa League", "الدوري الأوروبي", "Europa League", "Europa League", "Europa League"],
    ["Angleterre", "England", "إنجلترا", "England", "Engeland", "Inglaterra"],
    ["Espagne", "Spain", "إسبانيا", "Spanien", "Spanje", "España"],
    ["Italie", "Italy", "إيطاليا", "Italien", "Italië", "Italia"],
    ["Allemagne", "Germany", "ألمانيا", "Deutschland", "Duitsland", "Alemania"],
    ["France", "France", "فرنسا", "Frankreich", "Frankrijk", "Francia"],
    ["Portugal", "Portugal", "البرتغال", "Portugal", "Portugal", "Portugal"],
    ["Europe", "Europe", "أوروبا", "Europa", "Europa", "Europa"],
    ["Maroc", "Morocco", "المغرب", "Marokko", "Marokko", "Marruecos"],
    ["Pays-Bas", "Netherlands", "هولندا", "Niederlande", "Nederland", "Países Bajos"],
    ["Belgique", "Belgium", "بلجيكا", "Belgien", "België", "Bélgica"],
    ["Brésil", "Brazil", "البرازيل", "Brasilien", "Brazilië", "Brasil"]
  ];

  // ---------- Dates, heures, nombres : la locale française est remplacée par celle choisie ----------
  if (lang !== "fr") {
    var target = LOC[lang];
    var fix = function (l) {
      if (typeof l === "string" && /^fr(-FR)?$/.test(l)) return target;
      if (Array.isArray(l) && l.length && /^fr(-FR)?$/.test(l[0])) return [target];
      return l;
    };
    ["toLocaleDateString", "toLocaleTimeString", "toLocaleString"].forEach(function (m) {
      var o = Date.prototype[m];
      Date.prototype[m] = function (l, opt) { return o.call(this, fix(l), opt); };
    });
    var nl = Number.prototype.toLocaleString;
    Number.prototype.toLocaleString = function (l, opt) { return nl.call(this, fix(l), opt); };
    if (window.Intl && Intl.DisplayNames) {
      var DN = Intl.DisplayNames;
      Intl.DisplayNames = function (l, opt) { return new DN(fix(l), opt); };
      Intl.DisplayNames.prototype = DN.prototype;
      Intl.DisplayNames.supportedLocalesOf = DN.supportedLocalesOf;
    }
  }

  // ---------- Langue du document + sens d'écriture ----------
  var de = document.documentElement;
  de.setAttribute("lang", lang);
  de.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
  window.FL_LANG = lang;

  // ---------- Traduction du texte affiché ----------
  var map = {};
  if (lang !== "fr") D.forEach(function (r) { if (r[idx] && r[idx] !== r[0]) map[r[0]] = r[idx]; });
  var ATTRS = ["placeholder", "title", "aria-label"];
  var SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, NOSCRIPT: 1 };

  function trText(n) {
    var t = n.nodeValue; if (!t) return;
    var k = t.trim(); if (!k) return;
    var v = map[k]; if (v) n.nodeValue = t.replace(k, v);
  }
  function trAttrs(el) {
    for (var i = 0; i < ATTRS.length; i++) {
      var a = el.getAttribute(ATTRS[i]); if (!a) continue;
      var v = map[a.trim()]; if (v) el.setAttribute(ATTRS[i], v);
    }
  }
  function trTree(root) {
    if (root.nodeType === 3) { if (!root.parentNode || !SKIP[root.parentNode.nodeName]) trText(root); return; }
    if (root.nodeType !== 1 || SKIP[root.nodeName]) return;
    if (root.hasAttribute && (root.hasAttribute("placeholder") || root.hasAttribute("title") || root.hasAttribute("aria-label"))) trAttrs(root);
    var w = document.createTreeWalker(root, 5, {
      acceptNode: function (n) { return n.nodeType === 1 && SKIP[n.nodeName] ? 2 : 1; }
    });
    var n; while ((n = w.nextNode())) { if (n.nodeType === 3) trText(n); else trAttrs(n); }
  }

  // ---------- Sélecteur de langue ----------
  function css() {
    var st = document.createElement("style");
    st.textContent =
      ".lang-sel{background:var(--bg-card,#111827);border:1px solid var(--accent,#22c55e);color:inherit;border-radius:20px;padding:4px 8px;font-size:.75rem;font-weight:700;cursor:pointer;max-width:120px;font-family:inherit}" +
      ".lang-sel option{background:var(--bg-card,#fff);color:var(--text-main,#111)}" +
      "html[dir=rtl] body{text-align:right}" +
      "html[dir=rtl] .tv-n,html[dir=rtl] .m-home,html[dir=rtl] .m-away{unicode-bidi:plaintext}";
    document.head.appendChild(st);
  }
  function mount() {
    if (document.getElementById("lang-select")) return true;
    var host = document.querySelector(".header-actions") || document.querySelector(".header-content");
    if (!host) return false;
    var sel = document.createElement("select");
    sel.id = "lang-select"; sel.className = "lang-sel";
    sel.setAttribute("aria-label", (map["Langue"] || "Langue"));
    sel.title = map["Langue"] || "Langue";
    LANGS.forEach(function (c) {
      var o = document.createElement("option");
      o.value = c; o.textContent = NAMES[c]; if (c === lang) o.selected = true;
      sel.appendChild(o);
    });
    sel.addEventListener("change", function () {
      try { localStorage.setItem("fl_lang", sel.value); } catch (e) { }
      location.reload();
    });
    host.insertBefore(sel, host.firstChild);
    return true;
  }

  function start() {
    css();
    mount();
    if (lang !== "fr") trTree(document.body);
    var pending = new Set(), raf = 0;
    var flush = function () {
      raf = 0;
      mount();
      pending.forEach(function (n) { if (n.isConnected) trTree(n); });
      pending.clear();
    };
    new MutationObserver(function (list) {
      if (lang === "fr") { if (!raf) raf = requestAnimationFrame(function () { raf = 0; mount(); }); return; }
      for (var i = 0; i < list.length; i++) {
        var r = list[i];
        if (r.type === "childList") { for (var j = 0; j < r.addedNodes.length; j++) pending.add(r.addedNodes[j]); }
        else if (r.type === "characterData") pending.add(r.target);
        else if (r.type === "attributes") pending.add(r.target);
      }
      if (!raf) raf = requestAnimationFrame(flush);
    }).observe(document.body, { childList: true, subtree: true, characterData: lang !== "fr", attributes: lang !== "fr", attributeFilter: ATTRS });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();

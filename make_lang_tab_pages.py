#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Génère les pages Radio, Classements et Programme TV dans chaque langue (en, es, it, nl, de, ar) :
   en/radio.html, en/classements.html, en/programme-tv.html, etc.  (18 pages)
Chaque page part de l'accueil traduit de sa langue (<langue>/index.html) : même application, même interface traduite
par i18n.js ; seuls changent le titre, la description, la canonique, les hreflang, le JSON-LD, le texte visible pour
les moteurs de recherche et les liens de la barre d'onglets.
Met aussi à jour, sans rien changer d'autre : les balises hreflang + le sélecteur de langue des 3 pages françaises
(radio.html, classements.html, programme-tv.html) pour qu'elles pointent vers les nouvelles pages, la barre d'onglets
des accueils et pages Sélections traduits, sitemap-langues-onglets.xml et robots.txt.
Usage : python3 make_lang_tab_pages.py [dossier]   (le dossier contient index.html ; par défaut le dossier courant)
Relancer après chaque modification de <langue>/index.html. Le script peut être relancé sans danger."""
import json, re, sys, os

D = sys.argv[1] if len(sys.argv) > 1 else "."
SITE = "https://www.footlivepro.com/"
TODAY = "2026-11-18"
LANGS = ["en", "es", "it", "nl", "de", "ar"]
ALL = ["fr"] + LANGS
FILES = {"radio": "radio.html", "table": "classements.html", "tv": "programme-tv.html"}
LOCALE = {"en": "en_GB", "es": "es_ES", "it": "it_IT", "nl": "nl_NL", "de": "de_DE", "ar": "ar_AR"}

def url(lang, key):
    return SITE + ("" if lang == "fr" else lang + "/") + FILES[key]

# ---------------------------------------------------------------------------------------------------------------
# Textes par langue : pour chaque page -> title, desc, name (fil d'Ariane), faq [(question, réponse)], h2, intro
# ---------------------------------------------------------------------------------------------------------------
T = {
"en": dict(home="Home", lead="More pages:", links=dict(scores="live scores", table="football standings", radio="football radio", tv="TV guide"),
 radio=dict(title="Live football radio: listen to sports radio | FootLive Pro",
  desc="Listen to live football and sports radio (RMC, BBC Radio 5 Live, talkSPORT, Cadena SER, COPE…) by competition. Free on FootLive Pro.",
  name="Football radio",
  faq=[("How can I listen to live football radio?", "Tap a station’s play button: the stream starts right in the page, with no app to install. If a station blocks its stream, the “↗” link opens its official website."),
       ("Does the radio keep playing when I switch tabs?", "Yes. The player stays at the bottom of the screen, so you can follow scores, standings or news while you keep listening to the commentary."),
       ("Is the radio free?", "Yes, listening to radio on FootLive Pro is free.")]),
 table=dict(title="Live football standings: all leagues | FootLive Pro",
  desc="Live football standings: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Champions League and more. Updated automatically on FootLive Pro.",
  name="Standings", h2="Football standings: every league, live",
  intro="FootLive Pro shows the standings of many leagues and competitions: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Liga Portugal, Botola Pro, Champions League, Europa League, Conference League, MLS, Saudi Pro League and more. Pick a competition from the list to see its table, updated automatically.",
  faq=[("How is the table worked out?", "Teams are ranked by points (3 for a win, 1 for a draw), then separated by goal difference and each competition’s own rules. The table also shows matches played, wins, draws, losses, and goals scored and conceded."),
       ("How do I follow my team?", "Tap the star next to a team: it is highlighted in every table.")]),
 tv=dict(title="Football on TV: today’s matches and channels (beIN SPORTS, Arryadia) | FootLive Pro",
  desc="Football TV guide: today’s key matches, kick-off times and the channel showing them (beIN SPORTS, Arryadia, Sport TV). Free on FootLive Pro.",
  name="TV guide", h2="Football TV guide: today’s matches and where to watch",
  intro="The FootLive Pro TV guide lists the day’s key matches with kick-off time, teams, live score and the channel broadcasting the game (beIN SPORTS, Arryadia, Sport TV). Pick a day in the date strip to see upcoming matches.",
  faq=[("Which channel shows the Champions League and the big leagues?", "The guide only covers the 10 competitions in the top bar (Champions League, Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Europa League, Conference League, Liga Portugal, Botola Pro). For each match it lists beIN SPORTS, Arryadia or Sport TV depending on the competition, then every other channel announced by the source (Spain, Italy, France, Europe…), when available. Always check the channel’s schedule on match day."),
       ("What is the beIN SPORTS channel number for a match?", "The exact number (beIN SPORTS 1, 2, 3…) is announced by the broadcaster on match day. It appears in the guide when the source provides it."),
       ("Is the FootLive Pro TV guide free?", "Yes, the TV guide, scores, standings and sports radio are all free.")])),
"es": dict(home="Inicio", lead="Más páginas:", links=dict(scores="resultados en directo", table="clasificaciones de fútbol", radio="radios de fútbol", tv="programación TV"),
 radio=dict(title="Radio de fútbol en directo: escucha radios deportivas | FootLive Pro",
  desc="Escucha radios de fútbol y deportes en directo (RMC, BBC Radio 5 Live, talkSPORT, Cadena SER, COPE…) por competición. Gratis en FootLive Pro.",
  name="Radios de fútbol",
  faq=[("¿Cómo escuchar una radio de fútbol en directo?", "Pulsa el botón de reproducción de una emisora: la señal empieza directamente en la página, sin instalar ninguna aplicación. Si una emisora bloquea su señal, el enlace «↗» abre su web oficial."),
       ("¿La radio sigue sonando si cambio de pestaña?", "Sí. El reproductor se mantiene en la parte inferior de la pantalla: puedes seguir los resultados, las clasificaciones o las noticias mientras sigues escuchando la narración."),
       ("¿Las radios son gratuitas?", "Sí, escuchar las radios en FootLive Pro es gratis.")]),
 table=dict(title="Clasificaciones de fútbol en directo: todas las ligas | FootLive Pro",
  desc="Clasificaciones de fútbol en directo: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Champions League y más. Actualizadas automáticamente en FootLive Pro.",
  name="Clasificaciones", h2="Clasificaciones de fútbol: todas las ligas en directo",
  intro="FootLive Pro muestra la clasificación de muchas ligas y competiciones: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Liga Portugal, Botola Pro, Champions League, Europa League, Conference League, MLS, Saudi Pro League y más. Elige una competición de la lista para ver su tabla, actualizada automáticamente.",
  faq=[("¿Cómo se establece la clasificación?", "Los equipos se ordenan por puntos (3 por victoria, 1 por empate) y después se desempata por la diferencia de goles y las reglas propias de cada competición. La tabla también indica partidos jugados, victorias, empates, derrotas y goles a favor y en contra."),
       ("¿Cómo sigo a mi equipo?", "Pulsa la estrella junto a un equipo: aparece resaltado en todas las clasificaciones.")]),
 tv=dict(title="Fútbol en TV: partidos de hoy y canales (beIN SPORTS, Arryadia) | FootLive Pro",
  desc="Programación de fútbol en TV: los partidos importantes de hoy, la hora y el canal que los emite (beIN SPORTS, Arryadia, Sport TV). Gratis en FootLive Pro.",
  name="Programación TV", h2="Programación TV de fútbol: partidos de hoy y canales que los emiten",
  intro="La programación TV de FootLive Pro enumera los partidos importantes del día con la hora, los equipos, el marcador en directo y el canal que emite el encuentro (beIN SPORTS, Arryadia, Sport TV). Elige un día en la franja de fechas para ver los próximos partidos.",
  faq=[("¿En qué canal ver la Champions League y las grandes ligas?", "La programación solo muestra los partidos de las 10 competiciones de la barra (Champions League, Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Europa League, Conference League, Liga Portugal, Botola Pro). Para cada partido muestra beIN SPORTS, Arryadia o Sport TV según la competición y, después, el resto de canales que anuncia la fuente (España, Italia, Francia, Europa…), cuando están disponibles. Comprueba siempre la parrilla del canal el día del partido."),
       ("¿Cuál es el número del canal beIN SPORTS para un partido?", "El número exacto (beIN SPORTS 1, 2, 3…) lo anuncia el canal el día del partido. Aparece en la programación cuando la fuente lo facilita."),
       ("¿Es gratuita la programación TV de FootLive Pro?", "Sí, la programación TV, los resultados, las clasificaciones y las radios deportivas son gratuitos.")])),
"it": dict(home="Home", lead="Altre pagine:", links=dict(scores="risultati in diretta", table="classifiche di calcio", radio="radio calcio", tv="programma TV"),
 radio=dict(title="Radio calcio in diretta: ascolta le radio sportive | FootLive Pro",
  desc="Ascolta le radio di calcio e sport in diretta (RMC, BBC Radio 5 Live, talkSPORT, Cadena SER, COPE…) per competizione. Gratis su FootLive Pro.",
  name="Radio calcio",
  faq=[("Come ascoltare una radio di calcio in diretta?", "Tocca il pulsante di riproduzione di una radio: lo streaming parte direttamente nella pagina, senza installare alcuna app. Se una radio blocca il proprio flusso, il link «↗» apre il suo sito ufficiale."),
       ("La radio continua se cambio scheda?", "Sì. Il lettore resta visibile in fondo allo schermo: puoi seguire risultati, classifiche o notizie continuando ad ascoltare la radiocronaca."),
       ("Le radio sono gratuite?", "Sì, l’ascolto delle radio su FootLive Pro è gratuito.")]),
 table=dict(title="Classifiche di calcio in diretta: tutti i campionati | FootLive Pro",
  desc="Classifiche di calcio in diretta: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Champions League e altro. Aggiornate automaticamente su FootLive Pro.",
  name="Classifiche", h2="Classifiche di calcio: tutti i campionati in diretta",
  intro="FootLive Pro mostra la classifica di numerosi campionati e competizioni: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Liga Portugal, Botola Pro, Champions League, Europa League, Conference League, MLS, Saudi Pro League e altro. Scegli una competizione dall’elenco per vedere la sua classifica, aggiornata automaticamente.",
  faq=[("Come viene stabilita la classifica?", "Le squadre sono ordinate per punti (3 per una vittoria, 1 per un pareggio), poi per differenza reti e secondo le regole specifiche di ogni competizione. La tabella indica anche partite giocate, vittorie, pareggi, sconfitte, gol fatti e subiti."),
       ("Come seguo la mia squadra?", "Tocca la stella accanto a una squadra: viene evidenziata in tutte le classifiche.")]),
 tv=dict(title="Calcio in TV: partite di oggi e canali (beIN SPORTS, Arryadia) | FootLive Pro",
  desc="Programma TV del calcio: le partite importanti di oggi, l’orario e il canale che le trasmette (beIN SPORTS, Arryadia, Sport TV). Gratis su FootLive Pro.",
  name="Programma TV", h2="Programma TV del calcio: partite di oggi e canali che le trasmettono",
  intro="Il programma TV di FootLive Pro elenca le partite importanti della giornata con orario, squadre, risultato in diretta e canale che trasmette l’incontro (beIN SPORTS, Arryadia, Sport TV). Scegli un giorno nella barra delle date per vedere le prossime partite.",
  faq=[("Su quale canale vedere la Champions League e i grandi campionati?", "Il programma mostra solo le partite delle 10 competizioni della barra (Champions League, Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Europa League, Conference League, Liga Portugal, Botola Pro). Per ogni partita indica beIN SPORTS, Arryadia o Sport TV a seconda della competizione, poi tutti gli altri canali segnalati dalla fonte (Spagna, Italia, Francia, Europa…), quando disponibili. Controlla sempre il palinsesto del canale il giorno della partita."),
       ("Qual è il numero del canale beIN SPORTS per una partita?", "Il numero esatto (beIN SPORTS 1, 2, 3…) viene annunciato dall’emittente il giorno della partita. Compare nel programma quando la fonte lo fornisce."),
       ("Il programma TV di FootLive Pro è gratuito?", "Sì, il programma TV, i risultati, le classifiche e le radio sportive sono gratuiti.")])),
"nl": dict(home="Home", lead="Meer pagina’s:", links=dict(scores="live uitslagen", table="voetbalstanden", radio="voetbalradio", tv="tv-gids"),
 radio=dict(title="Voetbalradio live: luister naar sportradio | FootLive Pro",
  desc="Luister live naar voetbal- en sportradio (RMC, BBC Radio 5 Live, talkSPORT, Cadena SER, COPE…) per competitie. Gratis op FootLive Pro.",
  name="Voetbalradio",
  faq=[("Hoe luister ik live naar voetbalradio?", "Tik op de afspeelknop van een zender: de stream start direct op de pagina, zonder dat je een app hoeft te installeren. Blokkeert een zender zijn stream, dan opent de link “↗” de officiële website."),
       ("Blijft de radio spelen als ik van tabblad wissel?", "Ja. De speler blijft onderaan het scherm staan, zodat je uitslagen, standen of nieuws kunt volgen terwijl je naar de verslaggeving blijft luisteren."),
       ("Is de radio gratis?", "Ja, luisteren naar radio op FootLive Pro is gratis.")]),
 table=dict(title="Voetbalstanden live: alle competities | FootLive Pro",
  desc="Voetbalstanden live: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Champions League en meer. Automatisch bijgewerkt op FootLive Pro.",
  name="Standen", h2="Voetbalstanden: alle competities live",
  intro="FootLive Pro toont de stand van veel competities en toernooien: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Liga Portugal, Botola Pro, Champions League, Europa League, Conference League, MLS, Saudi Pro League en meer. Kies een competitie in de lijst om de stand te zien, automatisch bijgewerkt.",
  faq=[("Hoe wordt de stand bepaald?", "Teams worden gerangschikt op punten (3 voor een zege, 1 voor een gelijkspel), daarna op doelsaldo en de regels van elke competitie. De tabel toont ook gespeelde wedstrijden, winst, gelijkspel, verlies en gemaakte en tegengoals."),
       ("Hoe volg ik mijn team?", "Tik op de ster naast een team: het wordt in alle standen gemarkeerd.")]),
 tv=dict(title="Voetbal op tv: wedstrijden van vandaag en zenders (beIN SPORTS, Arryadia) | FootLive Pro",
  desc="Tv-gids voetbal: de belangrijkste wedstrijden van vandaag, de aanvangstijd en de zender die ze uitzendt (beIN SPORTS, Arryadia, Sport TV). Gratis op FootLive Pro.",
  name="TV-gids", h2="Voetbal tv-gids: wedstrijden van vandaag en zenders",
  intro="De tv-gids van FootLive Pro toont de belangrijkste wedstrijden van de dag met aanvangstijd, teams, live score en de zender die de wedstrijd uitzendt (beIN SPORTS, Arryadia, Sport TV). Kies een dag in de datumbalk om komende wedstrijden te zien.",
  faq=[("Op welke zender kijk ik naar de Champions League en de grote competities?", "De gids toont alleen wedstrijden van de 10 competities in de balk (Champions League, Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Europa League, Conference League, Liga Portugal, Botola Pro). Per wedstrijd staat eerst beIN SPORTS, Arryadia of Sport TV, afhankelijk van de competitie, en daarna alle andere zenders die de bron meldt (Spanje, Italië, Frankrijk, Europa…), wanneer beschikbaar. Controleer op de wedstrijddag altijd het schema van de zender."),
       ("Wat is het zendernummer van beIN SPORTS voor een wedstrijd?", "Het exacte nummer (beIN SPORTS 1, 2, 3…) wordt op de wedstrijddag door de zender bekendgemaakt. Het verschijnt in de gids zodra de bron het levert."),
       ("Is de tv-gids van FootLive Pro gratis?", "Ja, de tv-gids, uitslagen, standen en sportradio zijn gratis.")])),
"de": dict(home="Startseite", lead="Weitere Seiten:", links=dict(scores="Live-Ergebnisse", table="Fußball-Tabellen", radio="Fußball-Radio", tv="TV-Programm"),
 radio=dict(title="Fußball-Radio live: Sportradios hören | FootLive Pro",
  desc="Fußball- und Sportradios live hören (RMC, BBC Radio 5 Live, talkSPORT, Cadena SER, COPE…), sortiert nach Wettbewerb. Kostenlos auf FootLive Pro.",
  name="Fußball-Radio",
  faq=[("Wie höre ich Fußball-Radio live?", "Tippe auf die Wiedergabetaste eines Senders: Der Stream startet direkt auf der Seite, ohne dass du eine App installieren musst. Blockiert ein Sender seinen Stream, öffnet der Link „↗“ die offizielle Website."),
       ("Läuft das Radio weiter, wenn ich den Tab wechsle?", "Ja. Der Player bleibt am unteren Bildschirmrand sichtbar: Du kannst Ergebnisse, Tabellen oder News verfolgen und dabei weiter die Reportage hören."),
       ("Sind die Radios kostenlos?", "Ja, das Radiohören auf FootLive Pro ist kostenlos.")]),
 table=dict(title="Fußball-Tabellen live: alle Ligen | FootLive Pro",
  desc="Fußball-Tabellen live: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Champions League und mehr. Automatisch aktualisiert auf FootLive Pro.",
  name="Tabellen", h2="Fußball-Tabellen: alle Ligen live",
  intro="FootLive Pro zeigt die Tabellen vieler Ligen und Wettbewerbe: Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Liga Portugal, Botola Pro, Champions League, Europa League, Conference League, MLS, Saudi Pro League und mehr. Wähle einen Wettbewerb aus der Liste, um seine automatisch aktualisierte Tabelle zu sehen.",
  faq=[("Wie entsteht die Tabelle?", "Die Teams werden nach Punkten sortiert (3 für einen Sieg, 1 für ein Unentschieden), danach nach Tordifferenz und den Regeln des jeweiligen Wettbewerbs. Die Tabelle zeigt auch Spiele, Siege, Unentschieden, Niederlagen sowie erzielte und kassierte Tore."),
       ("Wie verfolge ich mein Team?", "Tippe auf den Stern neben einem Team: Es wird in allen Tabellen hervorgehoben.")]),
 tv=dict(title="Fußball im TV: Spiele von heute und Sender (beIN SPORTS, Arryadia) | FootLive Pro",
  desc="Fußball-TV-Programm: die wichtigen Spiele des Tages, Anstoßzeit und der übertragende Sender (beIN SPORTS, Arryadia, Sport TV). Kostenlos auf FootLive Pro.",
  name="TV-Programm", h2="Fußball-TV-Programm: Spiele von heute und Sender",
  intro="Das TV-Programm von FootLive Pro listet die wichtigen Spiele des Tages mit Anstoßzeit, Teams, Live-Ergebnis und dem Sender, der die Partie überträgt (beIN SPORTS, Arryadia, Sport TV). Wähle in der Datumsleiste einen Tag, um kommende Spiele zu sehen.",
  faq=[("Auf welchem Sender laufen die Champions League und die großen Ligen?", "Das Programm zeigt nur Spiele der 10 Wettbewerbe in der Leiste (Champions League, Premier League, LaLiga, Serie A, Bundesliga, Ligue 1, Europa League, Conference League, Liga Portugal, Botola Pro). Zu jedem Spiel steht je nach Wettbewerb zuerst beIN SPORTS, Arryadia oder Sport TV, danach alle weiteren von der Quelle gemeldeten Sender (Spanien, Italien, Frankreich, Europa …), sofern verfügbar. Prüfe am Spieltag immer das Programm des Senders."),
       ("Welche Senderplatznummer hat beIN SPORTS bei einem Spiel?", "Die genaue Nummer (beIN SPORTS 1, 2, 3 …) gibt der Sender am Spieltag bekannt. Sie erscheint im Programm, sobald die Quelle sie liefert."),
       ("Ist das TV-Programm von FootLive Pro kostenlos?", "Ja, TV-Programm, Ergebnisse, Tabellen und Sportradios sind kostenlos.")])),
"ar": dict(home="الرئيسية", lead="صفحات أخرى:", links=dict(scores="النتائج المباشرة", table="جداول الترتيب", radio="راديو كرة القدم", tv="برنامج التلفزيون"),
 radio=dict(title="راديو كرة القدم مباشر: استمع إلى الإذاعات الرياضية | FootLive Pro",
  desc="استمع إلى إذاعات كرة القدم والرياضة مباشرة (RMC وBBC Radio 5 Live وtalkSPORT وCadena SER وCOPE…) حسب البطولة. مجاناً على FootLive Pro.",
  name="راديو كرة القدم",
  faq=[("كيف أستمع إلى راديو كرة القدم مباشرة؟", "اضغط على زر التشغيل بجانب الإذاعة: يبدأ البث مباشرة داخل الصفحة دون تثبيت أي تطبيق. وإذا حجبت الإذاعة بثها، يفتح الرابط «↗» موقعها الرسمي."),
       ("هل يستمر الراديو عند تغيير التبويب؟", "نعم. يبقى المشغّل ظاهراً أسفل الشاشة، فيمكنك متابعة النتائج أو الترتيب أو الأخبار مع مواصلة الاستماع إلى التعليق."),
       ("هل الإذاعات مجانية؟", "نعم، الاستماع إلى الإذاعات على FootLive Pro مجاني.")]),
 table=dict(title="جداول ترتيب كرة القدم مباشرة: جميع الدوريات | FootLive Pro",
  desc="جداول ترتيب كرة القدم مباشرة: الدوري الإنجليزي الممتاز والليغا والدوري الإيطالي والبوندسليغا والدوري الفرنسي ودوري أبطال أوروبا وغيرها. تُحدَّث تلقائياً على FootLive Pro.",
  name="جداول الترتيب", h2="جداول ترتيب كرة القدم: جميع الدوريات مباشرة",
  intro="يعرض FootLive Pro ترتيب العديد من الدوريات والبطولات: الدوري الإنجليزي الممتاز، الليغا، الدوري الإيطالي، البوندسليغا، الدوري الفرنسي، الدوري البرتغالي، البطولة المغربية، دوري أبطال أوروبا، الدوري الأوروبي، دوري المؤتمر الأوروبي، الدوري الأمريكي، الدوري السعودي للمحترفين وغيرها. اختر بطولة من القائمة لعرض جدولها المحدَّث تلقائياً.",
  faq=[("كيف يُحدَّد الترتيب؟", "تُرتَّب الفرق حسب النقاط (3 للفوز و1 للتعادل)، ثم بفارق الأهداف والقواعد الخاصة بكل بطولة. ويعرض الجدول أيضاً المباريات الملعوبة وعدد مرات الفوز والتعادل والخسارة والأهداف المسجلة والمستقبلة."),
       ("كيف أتابع فريقي؟", "اضغط على النجمة بجانب الفريق: سيظهر مميَّزاً في جميع الجداول.")]),
 tv=dict(title="كرة القدم على التلفزيون: مباريات اليوم والقنوات (beIN SPORTS وArryadia) | FootLive Pro",
  desc="برنامج كرة القدم على التلفزيون: أهم مباريات اليوم وموعدها والقناة الناقلة (beIN SPORTS وArryadia وSport TV). مجاناً على FootLive Pro.",
  name="برنامج التلفزيون", h2="برنامج كرة القدم على التلفزيون: مباريات اليوم والقنوات الناقلة",
  intro="يعرض برنامج التلفزيون في FootLive Pro أهم مباريات اليوم مع الموعد والفرق والنتيجة المباشرة والقناة الناقلة للمباراة (beIN SPORTS وArryadia وSport TV). اختر يوماً من شريط التواريخ لعرض المباريات القادمة.",
  faq=[("على أي قناة أشاهد دوري الأبطال والدوريات الكبرى؟", "يعرض البرنامج فقط مباريات البطولات العشر الموجودة في الشريط (دوري أبطال أوروبا، الدوري الإنجليزي الممتاز، الليغا، الدوري الإيطالي، البوندسليغا، الدوري الفرنسي، الدوري الأوروبي، دوري المؤتمر، الدوري البرتغالي، البطولة المغربية). وتظهر لكل مباراة قناة beIN SPORTS أو Arryadia أو Sport TV بحسب البطولة، ثم جميع القنوات الأخرى التي يعلنها المصدر (إسبانيا وإيطاليا وفرنسا وأوروبا…) عند توفرها. تحقق دائماً من جدول القناة يوم المباراة."),
       ("ما رقم قناة beIN SPORTS لمباراة ما؟", "تعلن القناة الرقم الدقيق (beIN SPORTS 1 أو 2 أو 3…) يوم المباراة. ويظهر في البرنامج عندما يوفره المصدر."),
       ("هل برنامج التلفزيون في FootLive Pro مجاني؟", "نعم، برنامج التلفزيون والنتائج والترتيب والإذاعات الرياضية كلها مجانية.")])),
}

def rep(t, a, b, n=1):
    assert t.count(a) == n, (a[:90], t.count(a))
    return t.replace(a, b)

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def hreflang_block(key, indent="    "):
    lines = "".join('%s<link rel="alternate" hreflang="%s" href="%s">\n' % (indent, l, url(l, key)) for l in ALL)
    return lines + '%s<link rel="alternate" hreflang="x-default" href="%s">\n' % (indent, url("fr", key))

HREFLANG_RE = re.compile(r'(?:[ \t]*<link rel="alternate" hreflang="[^"]*" href="[^"]*">\n)+')

def switcher(t, key):
    """Le sélecteur de langue reste sur la même page (Radio, Classements ou Programme TV) dans l'autre langue."""
    f = FILES[key]
    return re.sub(r'href="(/(?:en/|es/|it/|nl/|de/|ar/)?)"(\s+hreflang=)', lambda m: 'href="%s%s"%s' % (m.group(1), f, m.group(2)), t)

def static_block(lang, key):
    d = T[lang][key]
    if key == "radio":
        return None
    parts = ['<h2>%s</h2><p>%s</p>' % (esc(d["h2"]), esc(d["intro"]))]
    L = T[lang]["links"]
    rel = {"scores": "./", "table": "classements.html", "radio": "radio.html", "tv": "programme-tv.html"}
    items = ", ".join('<a href="%s" style="color:var(--accent)">%s</a>' % (rel[k], esc(L[k])) for k in ("scores", "table", "radio", "tv") if k != key)
    parts.append('<p>%s %s.</p>' % (esc(T[lang]["lead"]), items))
    for q, a in d["faq"]:
        parts.append('<h3>%s</h3><p>%s</p>' % (esc(q), esc(a)))
    return "".join(parts)

def build(lang, key, src):
    d = T[lang][key]
    u = url(lang, key)
    t = src
    # <html> : page d'onglet
    t = re.sub(r"<html([^>]*)>", lambda m: '<html%s data-start="%s" data-tabpage="1">' % (m.group(1), key), t, 1)
    # SEO
    t = re.sub(r'<meta name="description" content="[^"]*">', lambda m: '<meta name="description" content="%s">' % esc(d["desc"]), t, 1)
    t = re.sub(r'<title>[^<]*</title>', lambda m: '<title>%s</title>' % esc(d["title"]), t, 1)
    t = re.sub(r'<link rel="canonical" href="[^"]*">', '<link rel="canonical" href="%s">' % u, t, 1)
    t = HREFLANG_RE.sub(lambda m: hreflang_block(key), t, 1)
    t = re.sub(r'(<meta property="og:url" content=)"[^"]*"', r'\1"%s"' % u, t, 1)
    t = re.sub(r'(<meta property="og:title" content=)"[^"]*"', lambda m: '%s"%s"' % (m.group(1), esc(d["title"])), t, 1)
    t = re.sub(r'(<meta property="og:description" content=)"[^"]*"', lambda m: '%s"%s"' % (m.group(1), esc(d["desc"])), t, 1)
    t = re.sub(r'(<meta name="twitter:title" content=)"[^"]*"', lambda m: '%s"%s"' % (m.group(1), esc(d["title"])), t, 1)
    t = re.sub(r'(<meta name="twitter:description" content=)"[^"]*"', lambda m: '%s"%s"' % (m.group(1), esc(d["desc"])), t, 1)
    # JSON-LD : WebSite + Organization conservés ; WebPage + fil d'Ariane + FAQ propres à la page ; aperçu des matchs de l'accueil retiré
    t = re.sub(r'<!--APERCU-LD-START-->.*?<!--APERCU-LD-END-->', '', t, 1, flags=re.S)
    t = re.sub(r'<!--APERCU-START-->.*?<!--APERCU-END-->', '', t, 1, flags=re.S)
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', t, re.S)
    base = [g for g in json.loads(m.group(1))["@graph"] if g.get("@type") in ("WebSite", "Organization")]
    home = SITE + lang + "/"
    graph = base + [
        {"@type": "WebPage", "@id": u + "#page", "url": u, "name": d["title"], "description": d["desc"], "inLanguage": lang,
         "isPartOf": {"@id": SITE + "#site"}, "breadcrumb": {"@id": u + "#bc"}},
        {"@type": "BreadcrumbList", "@id": u + "#bc", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": T[lang]["home"], "item": home},
            {"@type": "ListItem", "position": 2, "name": d["name"], "item": u}]},
        {"@type": "FAQPage", "@id": u + "#faq", "inLanguage": lang, "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in d["faq"]]}]
    ld = '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":")) + '</script>'
    t = t[:m.start()] + ld + t[m.end():]
    # navigation : mêmes mécanismes que la page française (adresse de l'onglet dans le dossier de la langue)
    t = rep(t, "const TAB_URL = {};", 'const TAB_URL = { radio: "radio.html", table: "classements.html", tv: "programme-tv.html" };')
    # descriptions affichées quand on change d'onglet : dans la langue de la page (sinon le français revenait dans la balise description)
    i = t.index("const TAB_META"); j = t.index("};", i)
    block = t[i:j]
    for k in FILES:
        block, n = re.subn(r'(\b%s:\s*)"(?:[^"\\]|\\.)*"' % k, lambda mm, k=k: mm.group(1) + json.dumps(T[lang][k]["desc"], ensure_ascii=False), block, 1)
        assert n == 1, ("TAB_META", lang, k)
    t = t[:i] + block + t[j:]
    for k, f in FILES.items():
        t = t.replace('href="../%s" data-go="%s"' % (f, k), 'href="%s" data-go="%s"' % (f, k))
    t = switcher(t, key)
    t = rep(t, "</head>", "<style>html[data-start] #scores-view{display:none}</style>\n</head>")
    if key == "radio":
        t = rep(t, '<div id="radio-view" hidden>', '<div id="radio-view">')   # texte visible dans le HTML pour les robots
    else:
        t = rep(t, "    </main>", '    <section id="static-seo" class="cb-seo" aria-label="%s">%s</section>\n    </main>' % (esc(d["name"]), static_block(lang, key)))
    return t

def update_fr(key):
    """Pages françaises : hreflang et sélecteur de langue vers les nouvelles pages (rien d'autre n'est modifié)."""
    p = os.path.join(D, FILES[key])
    t = open(p, encoding="utf-8").read()
    t2 = HREFLANG_RE.sub(lambda m: hreflang_block(key), t, 1)
    t2 = switcher(t2, key) if 'href="/en/%s"' % FILES[key] not in t2 else t2
    if t2 != t:
        open(p, "w", encoding="utf-8").write(t2)
        print("mis à jour :", FILES[key])

def update_nav(path, lang):
    """Accueil et page Sélections traduits : les liens Radio / Classements / Programme TV de la barre d'onglets pointent vers les pages traduites
    (le clic reste géré sans rechargement par le script de la page ; seuls les liens lus par les moteurs changent)."""
    if not os.path.exists(path):
        return
    t = open(path, encoding="utf-8").read()
    t2 = t
    for k, f in FILES.items():
        t2 = t2.replace('href="../%s" data-go="%s"' % (f, k), 'href="%s" data-go="%s"' % (f, k))
    if t2 != t:
        open(path, "w", encoding="utf-8").write(t2)
        print("barre d'onglets :", os.path.relpath(path, D))

def sitemap():
    p = os.path.join(D, "sitemap-langues-onglets.xml")
    out = ['<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n']
    for key in FILES:
        alt = "".join('    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>\n' % (l, url(l, key)) for l in ALL) + \
              '    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>\n' % url("fr", key)
        for l in ALL:
            out.append("  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n%s  </url>\n" % (url(l, key), TODAY, alt))
    out.append("</urlset>\n")
    open(p, "w", encoding="utf-8").write("".join(out))
    r = os.path.join(D, "robots.txt")
    x = open(r, encoding="utf-8").read()
    line = "Sitemap: %ssitemap-langues-onglets.xml" % SITE
    if line not in x:
        x = x.rstrip("\n") + "\n" + line + "\n"
        open(r, "w", encoding="utf-8").write(x)
        print("robots.txt : sitemap-langues-onglets.xml déclaré")
    print("sitemap-langues-onglets.xml :", len(ALL) * len(FILES), "URL")

def main():
    n = 0
    for lang in LANGS:
        src = open(os.path.join(D, lang, "index.html"), encoding="utf-8").read()
        for key, f in FILES.items():
            t = build(lang, key, src)
            open(os.path.join(D, lang, f), "w", encoding="utf-8").write(t)
            n += 1
        update_nav(os.path.join(D, lang, "index.html"), lang)
        update_nav(os.path.join(D, lang, "selections.html"), lang)
    print(n, "pages générées")
    for key in FILES:
        update_fr(key)
    sitemap()

if __name__ == "__main__":
    main()

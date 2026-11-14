/* FootLive Pro : message discret « Installer l'app ? » en bas de l'écran (mobile).
 * Android / Chrome : le bouton ouvre l'invite d'installation du navigateur. iPhone : petite fenêtre avec les étapes.
 * Affiché au plus une fois par visite, et plus jamais après une installation, un refus (×) ou un clic sur « Compris ».
 * Chargé avec <script src="/install-app.js" defer>, après l'écouteur beforeinstallprompt placé dans le <head>. */
(function () {
  var KEY = "flp_install_done", SEEN = "flp_install_seen", DELAY = 4000, LIFE = 15000;
  function done() { try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; } }
  function mark() { try { localStorage.setItem(KEY, "1"); } catch (e) {} }
  function seen() { try { return sessionStorage.getItem(SEEN) === "1"; } catch (e) { return false; } }
  function setSeen() { try { sessionStorage.setItem(SEEN, "1"); } catch (e) {} }
  var standalone = (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || navigator.standalone === true;
  if (standalone || done() || !document.getElementById("tabbar")) return;

  var T = {
    fr: { q: "Installer l’app ?", go: "Installer", x: "Fermer", t: "Installer sur iPhone", a: "Touchez {s} Partager", b: "Choisissez « Sur l’écran d’accueil »", c: "Touchez Ajouter", ok: "Compris" },
    en: { q: "Install the app?", go: "Install", x: "Close", t: "Install on iPhone", a: "Tap {s} Share", b: "Choose “Add to Home Screen”", c: "Tap Add", ok: "Got it" },
    es: { q: "¿Instalar la app?", go: "Instalar", x: "Cerrar", t: "Instalar en iPhone", a: "Toca {s} Compartir", b: "Elige «Añadir a pantalla de inicio»", c: "Toca Añadir", ok: "Entendido" },
    it: { q: "Installare l’app?", go: "Installa", x: "Chiudi", t: "Installa su iPhone", a: "Tocca {s} Condividi", b: "Scegli «Aggiungi alla schermata Home»", c: "Tocca Aggiungi", ok: "Ho capito" },
    nl: { q: "App installeren?", go: "Installeren", x: "Sluiten", t: "Installeren op iPhone", a: "Tik op {s} Deel", b: "Kies “Zet op beginscherm”", c: "Tik op Voeg toe", ok: "Begrepen" },
    de: { q: "App installieren?", go: "Installieren", x: "Schließen", t: "Auf dem iPhone installieren", a: "Tippe auf {s} Teilen", b: "Wähle „Zum Home-Bildschirm“", c: "Tippe auf Hinzufügen", ok: "Verstanden" },
    ar: { q: "تثبيت التطبيق؟", go: "تثبيت", x: "إغلاق", t: "التثبيت على iPhone", a: "اضغط على {s} مشاركة", b: "اختر «إضافة إلى الشاشة الرئيسية»", c: "اضغط على إضافة", ok: "فهمت" }
  };
  var lang = ((document.documentElement.lang || "fr") + "").slice(0, 2).toLowerCase();
  var L = T[lang] || T.fr;

  var css = document.createElement("style");
  css.id = "install-app-css";
  css.textContent =
    ".inst-toast{display:none}" +
    ".inst-ov{position:fixed;left:0;right:0;top:0;bottom:0;z-index:2000;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;padding:20px}" +
    ".inst-card{background:#0d1524;border:1px solid var(--border);border-radius:18px;padding:18px;width:100%;max-width:340px;color:var(--text-main)}" +
    ".inst-card h3{margin:0 0 12px;font-size:1.05rem}" +
    ".inst-card ol{margin:0 0 16px;padding:0;padding-inline-start:20px;line-height:1.7;font-size:.95rem}" +
    ".inst-card ol svg{width:1.1em;height:1.1em;vertical-align:-.2em}" +
    ".inst-ok{display:block;width:100%;padding:12px;border:0;border-radius:12px;background:var(--accent);color:#06101f;font-weight:700;font-size:1rem;font-family:inherit;cursor:pointer}" +
    "@media (max-width:700px){" +
    ".inst-toast{display:flex;align-items:center;gap:10px;position:fixed;left:10px;right:10px;bottom:calc(var(--tbh,60px) + var(--sab,0px) + 10px);z-index:1500;background:#0d1524;border:1px solid var(--border);border-radius:14px;padding:10px 12px;color:var(--text-main);box-shadow:0 6px 24px rgba(0,0,0,.5);font-size:.9rem;font-weight:700;animation:inst-up .25s ease}" +
    "body.radio-on .inst-toast{bottom:calc(var(--tbh,60px) + 76px + var(--sab,0px) + 10px)}" +
    ".inst-toast span{flex:1}" +
    ".inst-toast .inst-go{border:0;background:none;color:var(--accent);font:inherit;font-weight:700;padding:6px 8px;cursor:pointer}" +
    ".inst-toast .inst-x{border:0;background:none;color:var(--text-muted);font:inherit;font-size:1.3rem;line-height:1;padding:4px 8px;cursor:pointer}" +
    "@keyframes inst-up{from{transform:translateY(10px);opacity:0}}" +
    "}" +
    "@media (prefers-reduced-motion:reduce){.inst-toast{animation:none}}";
  document.head.appendChild(css);

  var SVG = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';
  var toast = null, timer = null;
  function hide() { if (timer) { clearTimeout(timer); timer = null; } if (toast && toast.parentNode) toast.parentNode.removeChild(toast); toast = null; }

  function iosHelp() {
    var share = "<svg " + SVG + '><path d="M12 3v12"/><path d="M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>';
    var ov = document.createElement("div");
    ov.className = "inst-ov";
    ov.innerHTML = '<div class="inst-card" role="dialog" aria-modal="true"><h3>' + L.t + "</h3><ol><li>" + L.a.replace("{s}", share) + "</li><li>" + L.b + "</li><li>" + L.c + '</li></ol><button type="button" class="inst-ok">' + L.ok + "</button></div>";
    function close() { mark(); if (ov.parentNode) ov.parentNode.removeChild(ov); }
    ov.addEventListener("click", function (e) { if (e.target === ov || (e.target.closest && e.target.closest(".inst-ok"))) close(); });
    document.body.appendChild(ov);
  }
  function install(ios) {
    hide();
    if (ios) { iosHelp(); return; }
    var e = window.__flpIP;
    if (!e) return;
    e.prompt();
    e.userChoice.then(function () { mark(); window.__flpIP = null; }, function () { mark(); });
  }
  function show(ios) {
    if (toast || done() || seen()) return;
    setSeen();
    toast = document.createElement("div");
    toast.className = "inst-toast";
    toast.setAttribute("role", "status");
    toast.innerHTML = "<span>" + L.q + '</span><button type="button" class="inst-go" data-a="go">' + L.go + '</button><button type="button" class="inst-x" data-a="x" aria-label="' + L.x + '">×</button>';
    toast.addEventListener("click", function (e) {
      var t = e.target.closest && e.target.closest("[data-a]");
      if (!t) return;
      if (t.getAttribute("data-a") === "go") install(ios);
      else { mark(); hide(); }
    });
    document.body.appendChild(toast);
    timer = setTimeout(hide, LIFE);
  }

  window.addEventListener("appinstalled", function () { mark(); hide(); });
  var ua = navigator.userAgent;
  var ios = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  function later(ok) { setTimeout(function () { if (ok()) show(ios); }, DELAY); }
  if (ios) later(function () { return true; });
  else {
    var armed = false;
    var arm = function () { if (armed || !window.__flpIP) return; armed = true; later(function () { return !!window.__flpIP; }); };
    arm();
    window.addEventListener("flp-ip", arm);
  }
})();

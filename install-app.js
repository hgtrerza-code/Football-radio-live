/* FootLive Pro : bouton « Installer l'app » dans le menu du bas (mobile).
 * Affiché une seule fois : il disparaît après une installation, un refus ou un clic sur « Compris ».
 * Android / Chrome : invite d'installation du navigateur. iPhone : petite fenêtre avec les étapes.
 * Chargé avec <script src="/install-app.js" defer>, après l'écouteur beforeinstallprompt placé dans le <head>. */
(function () {
  var KEY = "flp_install_done";
  function done() { try { return localStorage.getItem(KEY) === "1"; } catch (e) { return false; } }
  function mark() { try { localStorage.setItem(KEY, "1"); } catch (e) {} }
  var standalone = (window.matchMedia && matchMedia("(display-mode: standalone)").matches) || navigator.standalone === true;
  if (standalone || done()) return;
  var bar = document.getElementById("tabbar"), box = bar && bar.querySelector(".container");
  if (!box) return;

  var T = {
    fr: ["Installer", "Installer FootLive Pro", "Installer sur iPhone", "Touchez {s} Partager", "Choisissez « Sur l’écran d’accueil »", "Touchez Ajouter", "Compris"],
    en: ["Install", "Install FootLive Pro", "Install on iPhone", "Tap {s} Share", "Choose “Add to Home Screen”", "Tap Add", "Got it"],
    es: ["Instalar", "Instalar FootLive Pro", "Instalar en iPhone", "Toca {s} Compartir", "Elige «Añadir a pantalla de inicio»", "Toca Añadir", "Entendido"],
    it: ["Installa", "Installa FootLive Pro", "Installa su iPhone", "Tocca {s} Condividi", "Scegli «Aggiungi alla schermata Home»", "Tocca Aggiungi", "Ho capito"],
    nl: ["App", "FootLive Pro installeren", "Installeren op iPhone", "Tik op {s} Deel", "Kies “Zet op beginscherm”", "Tik op Voeg toe", "Begrepen"],
    de: ["App", "FootLive Pro installieren", "Auf dem iPhone installieren", "Tippe auf {s} Teilen", "Wähle „Zum Home-Bildschirm“", "Tippe auf Hinzufügen", "Verstanden"],
    ar: ["تثبيت", "تثبيت FootLive Pro", "التثبيت على iPhone", "اضغط على {s} مشاركة", "اختر «إضافة إلى الشاشة الرئيسية»", "اضغط على إضافة", "فهمت"]
  };
  var lang = ((document.documentElement.lang || "fr") + "").slice(0, 2).toLowerCase();
  var L = T[lang] || T.fr;

  var css = document.createElement("style");
  css.id = "install-app-css";
  css.textContent =
    "#tabbar .inst-btn{display:none}" +
    ".inst-ov{position:fixed;left:0;right:0;top:0;bottom:0;z-index:2000;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;padding:20px}" +
    ".inst-card{background:#0d1524;border:1px solid var(--border);border-radius:18px;padding:18px;width:100%;max-width:340px;color:var(--text-main)}" +
    ".inst-card h3{margin:0 0 12px;font-size:1.05rem}" +
    ".inst-card ol{margin:0 0 16px;padding:0;padding-inline-start:20px;line-height:1.7;font-size:.95rem}" +
    ".inst-card ol svg{width:1.1em;height:1.1em;vertical-align:-.2em}" +
    ".inst-ok{display:block;width:100%;padding:12px;border:0;border-radius:12px;background:var(--accent);color:#06101f;font-weight:700;font-size:1rem;font-family:inherit;cursor:pointer}" +
    "@media (max-width:700px){" +
    "#tabbar .container>.inst-btn{order:5;display:flex;flex-direction:column;align-items:center;justify-content:flex-start;gap:4px;height:var(--tbh);padding:10px 0 0;box-sizing:border-box;font-size:0;border:0;border-radius:0;background:none;color:var(--accent);cursor:pointer;position:relative;font-family:inherit;font-weight:700}" +
    "#tabbar .container>.inst-btn::after{content:attr(data-short);font-size:.64rem;line-height:12px;height:12px;flex:0 0 12px;font-weight:700;white-space:nowrap}" +
    "#tabbar .container>.inst-btn>span{width:26px;height:26px;flex:0 0 26px;display:flex;align-items:center;justify-content:center;font-size:0}" +
    "#tabbar .container>.inst-btn>span svg{width:24px;height:24px}" +
    "#tabbar .container>.more-btn{order:6}" +
    "}";
  document.head.appendChild(css);

  var SVG = 'xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"';
  var btn = null;
  function remove() { if (btn && btn.parentNode) btn.parentNode.removeChild(btn); btn = null; }
  function make(onclick) {
    if (btn) return;
    btn = document.createElement("button");
    btn.type = "button";
    btn.className = "inst-btn";
    btn.setAttribute("data-short", L[0]);
    btn.setAttribute("aria-label", L[1]);
    btn.innerHTML = "<span><svg " + SVG + '><path d="M12 4v11"/><path d="M7 11l5 5 5-5"/><path d="M5 20h14"/></svg></span>';
    btn.addEventListener("click", onclick);
    box.appendChild(btn);
  }
  function iosHelp() {
    var share = "<svg " + SVG + '><path d="M12 3v12"/><path d="M8 7l4-4 4 4"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/></svg>';
    var ov = document.createElement("div");
    ov.className = "inst-ov";
    ov.innerHTML = '<div class="inst-card" role="dialog" aria-modal="true"><h3>' + L[2] + "</h3><ol><li>" + L[3].replace("{s}", share) + "</li><li>" + L[4] + "</li><li>" + L[5] + '</li></ol><button type="button" class="inst-ok">' + L[6] + "</button></div>";
    function close() { mark(); remove(); if (ov.parentNode) ov.parentNode.removeChild(ov); }
    ov.addEventListener("click", function (e) { if (e.target === ov || (e.target.closest && e.target.closest(".inst-ok"))) close(); });
    document.body.appendChild(ov);
  }
  function android() {
    if (!window.__flpIP) return;
    make(function () {
      var e = window.__flpIP;
      if (!e) return;
      e.prompt();
      e.userChoice.then(function () { mark(); remove(); window.__flpIP = null; }, function () { mark(); remove(); });
    });
  }

  window.addEventListener("appinstalled", function () { mark(); remove(); });
  var ua = navigator.userAgent;
  var ios = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  if (ios) make(iosHelp);
  else { android(); window.addEventListener("flp-ip", android); }
})();

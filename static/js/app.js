/* Abfuhrkalender Lübeck – kleines, abhängigkeitsarmes Frontend-Skript.
   Theme-Umschaltung, Copy-to-Clipboard, Toasts. HTMX/Alpine übernehmen den Rest. */

(function () {
  "use strict";

  // ----- Theme -------------------------------------------------------------
  // Die initiale Zuweisung passiert inline im <head> (kein Flackern);
  // hier nur der Umschalter + Persistenz.
  function currentTheme() {
    return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
  }

  window.akToggleTheme = function () {
    var next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("ak-theme", next); } catch (e) { /* privat modus */ }
  };

  // ----- Toasts ------------------------------------------------------------
  window.akToast = function (message, icon) {
    var region = document.querySelector(".ak-toast-region");
    if (!region) {
      region = document.createElement("div");
      region.className = "ak-toast-region";
      region.setAttribute("role", "status");
      region.setAttribute("aria-live", "polite");
      document.body.appendChild(region);
    }
    var toast = document.createElement("div");
    toast.className = "ak-toast";
    toast.innerHTML = '<i class="fa-solid ' + (icon || "fa-check") + '"></i><span></span>';
    toast.querySelector("span").textContent = message;
    region.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 3500);
  };

  // ----- Copy to clipboard ---------------------------------------------------
  window.akCopy = function (text, message) {
    function done() { window.akToast(message || "In die Zwischenablage kopiert"); }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done);
    } else {
      var area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      try { document.execCommand("copy"); done(); } finally { area.remove(); }
    }
  };
})();

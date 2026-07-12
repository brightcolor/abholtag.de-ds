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

  // ----- Autocomplete (Startseite) ------------------------------------------
  // Vanilla statt Alpine: die strikte CSP (ohne unsafe-eval) bleibt erhalten.
  function initSearchForm() {
    var form = document.querySelector("[data-search-form]");
    if (!form) return;
    var input = form.querySelector("#strasse");
    var hidden = form.querySelector("#street_id");
    var submit = form.querySelector("[data-search-submit]");
    var box = form.querySelector("#vorschlaege");

    function update() { submit.disabled = !hidden.value; }
    update();

    input.addEventListener("input", function () {
      hidden.value = "";
      update();
    });
    document.addEventListener("click", function (event) {
      var pick = event.target.closest("[data-street-id]");
      if (pick && form.contains(pick)) {
        hidden.value = pick.dataset.streetId;
        input.value = pick.dataset.streetName;
        box.innerHTML = "";
        update();
        var house = form.querySelector("#hausnr");
        if (house) house.focus();  // spürbares Feedback nach der Auswahl
        return;
      }
      if (!form.contains(event.target)) box.innerHTML = "";
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") box.innerHTML = "";
    });
  }

  // ----- Collapse (Jahresübersicht) -----------------------------------------
  window.akToggle = function (id, button) {
    var panel = document.getElementById(id);
    var hidden = panel.hasAttribute("hidden");
    if (hidden) { panel.removeAttribute("hidden"); } else { panel.setAttribute("hidden", ""); }
    button.setAttribute("aria-expanded", String(hidden));
    var label = button.querySelector("span");
    if (label) label.textContent = hidden ? "Einklappen" : "Alle anzeigen";
  };

  // ----- Tabs (Abo-Anleitungen) ----------------------------------------------
  function initTabs() {
    document.querySelectorAll("[data-tabs]").forEach(function (root) {
      var tabs = root.querySelectorAll("[data-tab]");
      var panels = root.querySelectorAll("[data-panel]");
      tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
          tabs.forEach(function (other) {
            other.classList.toggle("active", other === tab);
            other.setAttribute("aria-selected", String(other === tab));
          });
          panels.forEach(function (panel) {
            if (panel.dataset.panel === tab.dataset.tab) {
              panel.removeAttribute("hidden");
            } else {
              panel.setAttribute("hidden", "");
            }
          });
        });
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { initSearchForm(); initTabs(); });
  } else {
    initSearchForm(); initTabs();
  }

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

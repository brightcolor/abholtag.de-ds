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

  // ----- Typewriter: Abfallarten in der Überschrift ---------------------------
  // Segmente: Farbwort in Tonnenfarbe, "Tonne"/"Sack" in Standard-Textfarbe.
  // Gelb bekommt einen schwarzen Hintergrund, der beim Tippen mitwächst.
  var WASTE_ITEMS = [
    [{ t: "der " }, { t: "Gelbe", c: "ak-c-yellow" }, { t: " Sack" }],
    [{ t: "die " }, { t: "Blaue", c: "ak-c-blue" }, { t: " Tonne" }],
    [{ t: "der Restmüll" }],
    [{ t: "die " }, { t: "Graue", c: "ak-c-gray" }, { t: " Tonne" }],
    [{ t: "die " }, { t: "Bio", c: "ak-c-green" }, { t: "-Tonne" }],
    [{ t: "der " }, { t: "Bio", c: "ak-c-green" }, { t: "müll" }],
    [{ t: "die " }, { t: "Braune", c: "ak-c-brown" }, { t: " Tonne" }],
    [{ t: "die " }, { t: "Gelbe", c: "ak-c-yellow" }, { t: " Tonne" }],
  ];

  function reducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function renderSegments(host, item, count, withCaret) {
    host.textContent = "";
    var remaining = count;
    for (var i = 0; i < item.length && remaining > 0; i++) {
      var take = Math.min(item[i].t.length, remaining);
      var node;
      if (item[i].c) {
        node = document.createElement("span");
        node.className = item[i].c;
        node.textContent = item[i].t.slice(0, take);
      } else {
        node = document.createTextNode(item[i].t.slice(0, take));
      }
      host.appendChild(node);
      remaining -= take;
    }
    if (withCaret) {
      var caret = document.createElement("span");
      caret.className = "ak-tw-caret";
      host.appendChild(caret);
    }
  }

  function itemLength(item) {
    return item.reduce(function (sum, seg) { return sum + seg.t.length; }, 0);
  }

  function initWasteTypewriter() {
    var host = document.getElementById("wt-typewriter");
    if (!host) return;
    if (reducedMotion()) {
      renderSegments(host, WASTE_ITEMS[0], itemLength(WASTE_ITEMS[0]), false);
      return;
    }
    var index = 0, count = 0, deleting = false;
    function tick() {
      var item = WASTE_ITEMS[index];
      var total = itemLength(item);
      if (!deleting) {
        count++;
        renderSegments(host, item, count, true);
        if (count >= total) {
          deleting = true;
          setTimeout(tick, 1800);
          return;
        }
        setTimeout(tick, 65 + Math.random() * 55);
      } else {
        count--;
        renderSegments(host, item, count, true);
        if (count <= 0) {
          deleting = false;
          index = (index + 1) % WASTE_ITEMS.length;
          setTimeout(tick, 350);
          return;
        }
        setTimeout(tick, 32);
      }
    }
    tick();
  }

  // ----- Typewriter: Straßennamen im Suchfeld-Placeholder ---------------------
  // Läuft, bis das Feld fokussiert wird oder Eingabe erfolgt.
  function initStreetTypewriter() {
    var input = document.getElementById("strasse");
    if (!input) return;
    var names;
    try { names = JSON.parse(input.dataset.demoStreets || "[]"); } catch (e) { names = []; }
    if (!names.length || reducedMotion()) return;

    var defaultPlaceholder = input.getAttribute("placeholder") || "";
    var stopped = false;

    function stop() {
      if (stopped) return;
      stopped = true;
      input.setAttribute("placeholder", defaultPlaceholder);
    }
    input.addEventListener("focus", stop, { once: true });
    input.addEventListener("input", stop, { once: true });

    var index = Math.floor(Math.random() * names.length);
    var count = 0, deleting = false;
    function tick() {
      if (stopped) return;
      if (document.activeElement === input || input.value) { stop(); return; }
      var name = names[index];
      if (!deleting) {
        count++;
        input.setAttribute("placeholder", name.slice(0, count));
        if (count >= name.length) {
          deleting = true;
          setTimeout(tick, 1500);
          return;
        }
        setTimeout(tick, 70 + Math.random() * 60);
      } else {
        count--;
        input.setAttribute("placeholder", count ? name.slice(0, count) : "");
        if (count <= 0) {
          deleting = false;
          index = (index + 1) % names.length;
          setTimeout(tick, 400);
          return;
        }
        setTimeout(tick, 35);
      }
    }
    setTimeout(tick, 900);
  }

  function initAll() {
    initSearchForm();
    initTabs();
    initWasteTypewriter();
    initStreetTypewriter();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAll);
  } else {
    initAll();
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

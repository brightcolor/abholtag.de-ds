# Designsystem (Phase 2)

Ziel: ein bürgerfreundliches, modernes Produktgefühl (Referenzniveau sender.report),
konsistent über öffentliche Seiten und Verwaltung (§2/§3).

## Aufbau

- **Design Tokens** in `static/css/tokens.css`: alle Farben, Abstände, Radien, Schatten,
  Schriftgrößen als CSS Custom Properties (`--ak-*`). Keine hart kodierten Farben in
  Komponenten.
- **Komponenten** in `static/css/app.css`: `ak-card`, `ak-stat`, `ak-badge-*`, `ak-alert-*`,
  `ak-btn-*`, `ak-steps`, `ak-date-list`/`ak-date-box`, `ak-next-date`, `ak-chip`,
  `ak-feed-box`, `ak-tabs`, `ak-suggestions` (Autocomplete), `ak-skeleton`, `ak-toast`,
  `ak-empty-state`, Fokus-Stile, Druck-Styles.
- **Icons**: ausschließlich Font Awesome 6 Free (lokal eingebunden, keine CDN).
- **Schrift**: System-Stack (schnell, keine Drittanbieter-Fonts, §36).

## Farbwelt

Petrol/Teal (`--ak-brand`, Hanse/Wasser) als Markenfarbe, Gelb (`--ak-accent`) für den
Gelben Sack; Statusfarben (Erfolg/Warnung/Fehler/Info) je Theme abgestimmt.

## Light-/Darkmode (§3.4)

- Umschalter in der Top-Navigation; Auswahl in `localStorage`, sonst `prefers-color-scheme`.
- Inline-Skript im `<head>` setzt `data-theme` **vor** dem ersten Paint → kein Flackern.
- Dark-Werte als `[data-theme="dark"]`-Overrides derselben Tokens; `color-scheme` gesetzt
  (native Formularelemente). Diagramme (Chart.js) lesen die Theme-Klasse.
- Druckansicht ist immer hell (`@media print`).

## Layouts

- **Öffentlich** (`templates/base.html`): schlanke Sticky-Top-Navigation, Inhalt in Cards,
  keine Sidebar, Suche als dominante Hauptaktion, 3-Schritte-Erklärung, Statistik-Karten,
  Footer mit Rechtlichem und Haftungshinweis (§3.2, §9).
- **Verwaltung**: Jazzmin (AdminLTE 3) mit vollständigem App-Layout: Sidebar nach
  Fachbereichen sortiert, Topbar-Links zu Statistik/Moderation/Systemstatus, Icons je
  Modell, Feinschliff über `static/css/admin-custom.css` (§3.3). Eigene Seiten
  (Statistik-Dashboard, Moderationsqueue, Systemstatus) erweitern `admin/base_site.html`
  und nutzen AdminLTE-Widgets (small-box, info-box, cards).

## Barrierefreiheit (§35)

Semantisches HTML, Skip-Link, sichtbarer Fokus (`:focus-visible`), ausreichende Kontraste in
beiden Themes, Labels und `aria-*` an Suche/Tabs/Toasts, Termin-Infos nie nur über Farbe,
Diagramm mit Datentabelle als Alternative, `prefers-reduced-motion` respektiert,
Formularfehler in Textform.

## JavaScript-Grundsatz

Serverseitiges Rendering + HTMX für die Suche; kleine Interaktionen (Theme, Copy, Tabs,
Collapse, Autocomplete-Auswahl) in ~150 Zeilen Vanilla-JS (`static/js/app.js`).
Bewusst **kein Alpine.js**: dessen Expression-Evaluation erfordert `unsafe-eval` in der
CSP – die strikte CSP hat Vorrang (§34).

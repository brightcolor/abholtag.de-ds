# Changelog

Alle nennenswerten Änderungen dieses Projekts. Format angelehnt an
[Keep a Changelog](https://keepachangelog.com/de/), Versionierung nach SemVer.

## [0.6.0] - 2026-07-13

### Hinzugefügt
- **Hausnummern-Abgleich gegen den offiziellen BMS-Bestand** (44.690 Nummern):
  - Eingegebene Hausnummern werden bei der Auflösung validiert; unbekannte
    Nummern (z. B. Beethovenstr. 12 – existiert nicht) erhalten eine
    freundliche Fehlseite mit den nächstliegenden vorhandenen Nummern als
    Klick-Vorschläge und einem Melden-Link.
  - Bereichseinträge („21-31", gemeinsame Müllplätze) decken enthaltene
    Nummern paritätsbewusst ab und sind auch als exakter Text auflösbar.
  - **Hausnummern-Autovervollständigung**: Nach der Straßenwahl lädt das
    Nummernfeld die offiziellen Hausnummern als native Vorschlagsliste
    (neuer Endpunkt /suche/hausnummern/).
  - Bestands-Adressen mit laut Verzeichnis unbekannter Nummer zeigen einen
    Hinweis auf der Terminseite (Feed-URLs bleiben stabil).
  - Straßen ohne BMS-Daten werden wie bisher ohne Validierung aufgelöst.

## [0.5.2] - 2026-07-13

### Geändert
- **Termin-Markierungen in Tonnenfarbe**: Die Badges der kommenden Termine
  (und der Abo-Vorschau) tragen jetzt Farbpunkt, Rahmen und Hintergrund-Tönung
  in der Farbe der jeweiligen Tonne/des Sacks (`--wt` aus WasteType.color,
  color-mix). Der Text bleibt in Standardfarbe, damit auch dunkle Tonnenfarben
  (Restabfall-Grau) im Darkmode lesbar sind.
- Darkmode per Kontrast-Audit verifiziert (alle geprüften Elemente ≥ 6,4:1).

## [0.5.1] - 2026-07-13

### Behoben
- **Kennzahl „unterstützte Straßen"** zählt jetzt nur noch tatsächlich
  auflösbare Straßen (aktiv + mindestens eine aktive Tourenzuordnung) statt
  aller aktiven Stammdatensätze; BMS-Sondereinträge ohne Termine (gemeinsame
  Müllplätze, Herreninsel-Wege) zählen nicht mehr mit. Weiteres
  PDF-Artefakt („Zum") deaktiviert.

## [0.5.0] - 2026-07-13

### Hinzugefügt
- **Mehrfachauswahl der Abfallarten**: Auf der Startseite ersetzt eine
  Chip-Auswahl (alle standardmäßig aktiv) das Einzel-Dropdown; die Terminseite
  hat umschaltbare Filter-Chips je Abfallart. Die Auswahl wandert als
  `?arten=slug1,slug2` durch Terminliste, Jahresübersicht, Abo-Seite,
  ICS-Download und den kombinierten Feed (`all.ics?arten=…`); die API
  akzeptiert `waste_type` jetzt auch als Kommaliste. Einzel-Feeds und der
  Legacy-Parameter `abfallart` funktionieren unverändert.

## [0.4.0] - 2026-07-13

### Hinzugefügt
- **Live-Fallback mit Cache (BMS)**: Ruft eine Adresse eine Straße auf, der
  für Restabfall/Bioabfall/Papier noch die Zuordnung fehlt, wird der
  BMS-ICS-Feed einmalig live geholt und dauerhaft ins Zonenmodell übernommen
  (identisches Terminmuster → bestehende Zone, sonst neue). Tagesdrossel je
  Straße + Disk-Cache verhindern unnötige Anfragen an insert-it.de;
  Upstream-Ausfälle beeinträchtigen den Seitenaufbau nicht. Ergänzt nur in
  bereits veröffentlichte Jahrespläne (Review-Prinzip bleibt gewahrt).

### Geändert
- **Typewriter läuft immer**: Der statische prefers-reduced-motion-Fallback
  entfiel als Produktentscheidung (unter Windows ist die Einstellung oft
  systemweit aktiv, wodurch der Effekt „verschwand"). Screenreader erhalten
  weiterhin den statischen sr-only-Text.

## [0.3.0] - 2026-07-13

### Hinzugefügt
- **Restabfall, Bioabfall und Papier (PPK) sind live** – in Terminansicht,
  Jahresübersicht, Druckansicht und allen ICS-Feeds (`all.ics` sowie je
  Abfallart, z. B. `/calendar/address/<id>/restabfall.ics`).
- Neues Command `import_bms_schedules --year <jahr>`: ruft den BMS-ICS-Feed
  für eine Location je Straße ab (≤4 parallel, Disk-Cache, Retries), clustert
  identische Terminmuster je Abfallart zu Abfuhrbezirken (2026: Restabfall 48,
  Bioabfall 33, Papier 48 Zonen) und erzeugt Zuordnungen + Jahrespläne mit dem
  gewohnten Review-/Publish-Gate. Re-Runs bauen die abgeleiteten
  BMS-Zuordnungen neu auf; manuelle Korrekturen bleiben erhalten.
- Kreuzvalidierung: gespeicherte Termine sind 1:1 identisch mit dem
  EBL-Quell-ICS (stichprobenverifiziert).

### Hinweis
- Je Straße wird eine Location gesampelt; sollte eine Straße hausnummern-
  abhängig auf mehrere Touren aufgeteilt sein, gilt das Muster der Probe.
  Der Direktlink zum offiziellen EBL-Kalender dient als Gegencheck.

## [0.2.0] - 2026-07-12

### Hinzugefügt
- **BMS-Adressstamm (EBL-Online-Abfallkalender)**: neues Management-Command
  `import_bms_addresses` importiert 2.594 Straßen (bmsStreetId) und 45.054
  Hausnummern (bmsLocationId) aus `data/bms/*.json` oder live per `--scrape`
  (User-Agent, max. 4 parallel, Retries, 404-Sonderfall Geniner Ufer).
  Neues Modell `HouseNumber`, `Street.bms_street_id`; geteilte Location-IDs
  werden unterstützt. 1.705 PDF-Straßen automatisch verknüpft.
- **Abfallarten vorbereitet**: Restabfall, Bioabfall, Papier (PPK) als inaktive
  WasteTypes angelegt; der BMS-ICS-Endpunkt (`Main/Calender`) liefert deren
  Termine je Adresse und ist in docs/ANALYSE.md dokumentiert (Zonen-Clustering
  als nächster Schritt).
- **Terminseite**: Direktlink zum offiziellen EBL-Kalender der aufgelösten
  Adresse (bmsStreetId + bmsLocationId), sofern die Hausnummer im
  BMS-Datenbestand existiert.

### Behoben
- 9 Artefakt-Straßen aus dem PDF-Import (verschmolzene Doppelnamen,
  Bereichsfragmente) deaktiviert und zur Prüfung markiert.

## [0.1.3] - 2026-07-12

### Hinzugefügt
- **Typewriter-Startseite**: Die Überschrift heißt jetzt korrekt
  "Wann wird … abgeholt?" und tippt rotierend die Abfallarten (Gelber Sack,
  Blaue/Graue/Braune/Gelbe Tonne, Restmüll, Bio-Tonne, Biomüll). Das Farbwort
  erscheint in der Tonnenfarbe, "Tonne"/"Sack" in Standardfarbe; Gelb erhält
  einen schwarzen, beim Tippen mitwachsenden Hintergrund (Lesbarkeit).
- **Suchfeld-Typewriter**: Zufällige echte Straßennamen werden als Platzhalter
  getippt und gelöscht, bis das Feld fokussiert wird oder Eingabe erfolgt.
- Beide Effekte respektieren prefers-reduced-motion (statischer Fallback) und
  sind für Screenreader ausgeblendet (statischer sr-only-Text).

## [0.1.2] - 2026-07-12

### Behoben
- **Sperrschrift-Straßennamen**: ~1.300 Zeilen der PDF-Straßenliste sind gesperrt
  gedruckt ("K a h l h o r s t s t r .") und wurden bisher fehlerhaft übernommen.
  Der Parser rekonstruiert sie jetzt zuverlässig (Kollaps + Wortgrenzen an
  Großbuchstaben/Ziffern, zusammengesetzte Präpositionen wie "An der",
  Fragment-Zusammenführung); B/G-Doppelbezirke in Sperrschrift-Zeilen (99 statt
  30 Innenstadt-Straßen) werden korrekt erkannt. Straßenstamm muss einmalig neu
  geseedet werden (docs/BETRIEB.md).
- Fehlende FontAwesome-TTF-Webfonts vendoriert (collectstatic/Manifest-Storage
  schlug im Docker-Build fehl).

## [0.1.1] – 2026-07-12

### Hinzugefügt
- Eigenständiges Repository `abholtag.de-claude` mit bereinigter Struktur
  (nur Root-Layout: `manage.py`, `Dockerfile`, `docker-compose.yml` im Stamm).
- CI baut und veröffentlicht Docker-Images nach
  `ghcr.io/brightcolor/abholtag.de-claude` (latest auf main, SemVer bei Tags,
  GHA-Layer-Cache).

### Behoben
- Autocomplete: Nach Auswahl eines Straßenvorschlags springt der Fokus in das
  Hausnummernfeld (deutlicheres Feedback); Asset-Versionierung `?v=2` verhindert,
  dass Browser ein veraltetes `app.js` aus dem Cache verwenden.

## [0.1.0] – 2026-07-12

Erste lauffähige Version der Root-Layout-Variante (`config/` + `apps/`).

### Hinzugefügt
- **Parser** für den offiziellen Gelber-Sack-Plan: Straßenliste per Textlayout
  (pdfplumber), Jahreskalender per OCR (RapidOCR) mit Geometrie-Clustering,
  Zellen-Zweitpass und Komponentenanalyse für den Buchstaben „I“; verifiziert
  gegen die Ausgabe 2026 (260 Termine, 1.738 Straßeneinträge, 10 Bezirke).
- **Stammdaten/Jahresdaten-Trennung** mit Herkunfts-Kennzeichnung, Review-Gates,
  Straßen-Diff statt Überschreiben, Statusmodelle für Jahrespläne und Vorschläge.
- **Öffentliche Oberfläche**: tolerante Adresssuche (HTMX-Autocomplete),
  Terminansicht (nächster Termin, kommende 10, Jahresübersicht, Druck),
  Kalender-Abo-Seite mit Anleitungen für Apple/Google/Android/Outlook/Thunderbird;
  Light-/Darkmode ohne Flackern, WCAG-orientiert, strikte CSP ohne unsafe-eval.
- **iCalendar-Feeds** (RFC 5545): stabile UIDs, SEQUENCE-Bump bei Änderungen,
  STATUS:CANCELLED für entfallene Termine, ETag/If-None-Match/304, optionale
  Erinnerung, stabile URLs über Jahreswechsel.
- **Verwaltung**: Jazzmin/AdminLTE-Admin für alle Modelle, Moderationsqueue,
  Systemstatusseite, internes Statistik-Dashboard (Chart + Tabellen + CSV).
- **Analytics** datenschutzfreundlich: 13 Ereignistypen, täglich rotierender
  Session-Hash ohne IP-Speicherung, Aggregation + Rohdaten-Purge, dokumentierte
  Abo-Schätzung.
- **Community-Fundament**: Fehlermeldungen mit Vorgangsnummer und Statusseite,
  strukturierte Korrekturvorschläge mit Bestätigungen, konfigurierbare
  Quorum-Regeln (Standard: deaktiviert), Fallback-Erfassung mit Beleg-Upload.
- **Öffentliche API** `/api/v1/` mit OpenAPI-Spezifikation, Pagination,
  Rate-Limits und einheitlichen Fehlerobjekten.
- **Betrieb**: 13 Management-Commands, /health-Endpunkte, Docker/Compose mit
  Bind Mounts, nginx-/Cron-/Backup-Vorlagen, GitHub-Actions-CI,
  43 Tests (Parser gegen archiviertes PDF, ohne Netzzugriff).

### Bekannte Punkte
- Das amtliche PDF 2026 enthält für Bezirk C im Mai keinen Termin (Druckfehler
  im Quelldokument); der Import meldet dies als Warnung (docs/ANALYSE.md).
- 21 Straßen mit Hausnummernbereichen stehen bewusst auf „in Prüfung“ und
  benötigen eine einmalige manuelle Freigabe im Admin.
- Parallel existiert im Repo eine zweite Implementierung unter `src/` mit
  eigenem manage.py/Dockerfile; Konsolidierung steht aus (docs/ROADMAP.md).

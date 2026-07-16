# Changelog

Alle nennenswerten Änderungen dieses Projekts. Format angelehnt an
[Keep a Changelog](https://keepachangelog.com/de/), Versionierung nach SemVer.

## [0.14.1] - 2026-07-16

### Geändert
- Seite „Datenquelle & Nutzung": Formulierung zur Nutzungserlaubnis
  richtiggestellt – es besteht (noch) kein Kontakt/keine Abstimmung mit der
  EBL. Ehrlich: eine ausdrückliche Erlaubnis liegt bislang nicht vor, wir
  streben sie an und würden einer Anpassung/Einstellung auf Wunsch der EBL
  selbstverständlich nachkommen.

## [0.14.0] - 2026-07-16

### Hinzugefügt
- **Seite „Datenquelle & Nutzung"** (`/datenquelle/`, im Footer verlinkt): legt
  transparent offen, dass alle Termine aus dem offiziellen Abfuhrplan der
  Entsorgungsbetriebe Lübeck (EBL) stammen (mit Link zum Quell-PDF und zu
  entsorgung.luebeck.de), erklärt die maschinelle Aufbereitung, den
  unabhängigen/gemeinnützigen/werbefreien Charakter, den Haftungsausschluss
  („ohne Gewähr“, verbindlich sind die EBL-Pläne) und den Stand zur
  Nutzungserlaubnis/Datenlizenz.

## [0.13.0] - 2026-07-14

### Hinzugefügt
- **Status-Abruf per Vorgangsnummer**: Neue Seite `/melden/status/` mit Eingabefeld – Bürger:innen können mit
  ihrer Vorgangsnummer jederzeit den Bearbeitungsstand ihrer Meldung abrufen (vorher nur über den Direktlink
  der Bestätigungsseite erreichbar). Verlinkt von der Melde-Seite und der Bestätigungs-/Statusseite,
  rate-limitiert, Eingabe unabhängig von Groß-/Kleinschreibung.

### Geändert
- **2FA im Admin ist jetzt opt-in statt harter Pflicht**: Bei aktiviertem `ADMIN_OTP_REQUIRED` müssen nur noch
  Admins mit **eingerichtetem** TOTP-Gerät den zweiten Faktor bestätigen; Konten ohne Gerät melden sich weiter
  mit Passwort an und können 2FA später hinzufügen. Behebt das Aussperren/Henne-Ei-Problem
  (`SoftOTPAdminSite`).

## [0.12.0] - 2026-07-14

### Hinzugefügt
- **Menschenlesbare API-Dokumentation unter `/api/`** (Footer-Link „API“ zeigt
  jetzt dorthin statt auf die rohe `openapi.json`). Erklärt Basis-URL,
  Schnellstart (Straße → Adresse auflösen → Termine), alle Endpunkte und
  Beispiele in curl, JavaScript und Python – mit einer echten Beispiel-Adresse.
- **CORS für die öffentliche API**: read-only JSON-Endpunkte senden
  `Access-Control-Allow-Origin: *` (inkl. OPTIONS-Preflight), sodass die
  Offenen Daten auch direkt aus dem Browser nutzbar sind.

## [0.11.5] - 2026-07-14

### Geändert
- Adress-Terminseite: doppelte Bezirks-Badges entfernt. Da die Tourbuchstaben
  je Abfallart vergeben werden, lag dieselbe Adresse oft mehrfach in „Bezirk A“
  – angezeigt werden jetzt nur die eindeutigen Bezirke (z. B. „A“ und „J“).

## [0.11.4] - 2026-07-14

### Behoben
- Performance: Die Straßen-Landingpage (`/strasse/<slug>/`, die von Crawlern
  am häufigsten besuchte Seite) erzeugte pro Aufruf ~100 DB-Queries, weil die
  Jahres-Ermittlung `schedule_year` nicht mit `select_related` lud (N+1).
  Jetzt ~9 Queries (~6× schneller). Wichtig für viele gleichzeitige Anfragen
  auf kleiner Hardware.

## [0.11.3] - 2026-07-14

### Geändert
- Abo-Seite, Google-Kalender: ehrliche, zuverlässige Anleitung. Die
  Google-Kalender-App auf dem Handy kann abonnierte Kalender bauartbedingt
  nicht selbst hinzufügen (meldet „hinzugefügt“, zeigt sie aber nicht an –
  bekannte Google-Einschränkung). Der Google-Tab führt jetzt zuerst die zwei
  Wege, die wirklich funktionieren: einmalig am Computer per URL einrichten
  (synct dann aufs Handy) oder die App ICSx⁵ auf Android. Der ICS-Feed selbst
  ist unverändert korrekt (200, text/calendar, ohne Redirect, für Bots abrufbar).

## [0.11.2] - 2026-07-14

### Behoben
- EBL-Import auf PostgreSQL: Sehr lange, aber gültige Hausnummernlisten
  (z. B. Beckergrube, Königstraße mit >100 Zeichen) sprengten die
  `raw_range`-Spalte (varchar(100)). Feld auf 255 erweitert (Migration
  0005) und defensiv gekappt; ein einzelner Ausreißer bricht den Import
  nicht mehr ab. (SQLite ignoriert das Limit, PostgreSQL erzwingt es.)

## [0.11.1] - 2026-07-13

### Behoben
- EBL-Import: Beim Umstieg von den BMS-Cluster-Zonen auf die amtlichen
  Tourbuchstaben werden „neue Bezirke" und „alte Bezirke ohne Termine"
  nicht mehr als Warnung gemeldet – das ist der erwartete Schema-Wechsel.
  Ein sauberer `--publish`-Lauf meldet dadurch korrekt „abgeschlossen".

## [0.11.0] - 2026-07-13

### Hinzugefügt
- **Offizieller EBL-Abfuhrplan als Primärquelle für alle vier Abfallarten**
  (Restabfall, Bioabfall, Papier, Gelber Sack):
  - Neuer, vollständig textbasierter Parser `luebeck_ebl` (kein OCR nötig)
    liest Kalender und Straßenverzeichnis aus dem EBL-„Wegweiser"-PDF.
  - **Hausnummern-genaue Zuordnung:** Straßen mit nach Hausnummer geteilten
    Touren (z. B. Kahlhorststraße 1–16 → F, 17–Ende → D) lösen jetzt korrekt
    auf – die größte Schwäche der bisherigen BMS-Stichprobe ist behoben.
    `parse_house_ranges()` zerlegt 542 von 548 Bereichen automatisch; die 6
    Sonderfälle werden zur Prüfung markiert statt geraten.
  - Amtliche Tourbuchstaben (A–J bzw. A–T) als stabile Zonencodes; der frühere
    BMS-Cluster-Code (R##/B##/P##) wird beim Umstieg abgelöst.
  - Selbstvalidierender Kalenderparser (Wochentagsabgleich je Monatsspalte,
    Vergleich beider Kalenderkopien) – robust auch für den Folgejahres-Plan.
  - Ergänzt den im Veolia-PDF fehlenden 13.-Mai-Termin (Bezirk C).
  - Neues Kommando `import_ebl` (mit `--publish`), Anbindung an
    `fetch_waste_source` für die jährliche Automatik, Doku in
    [docs/EBL-IMPORT.md](docs/EBL-IMPORT.md).

## [0.10.1] - 2026-07-13

### Behoben
- Straßenseiten liefern keine leeren Hüllen mehr: Straßen ohne aktive
  Tourenzuordnung antworten mit 404 (Soft-404-Vermeidung), Seiten mit
  ausschließlich hausnummernabhängigen Zuordnungen stehen auf noindex.

## [0.10.0] - 2026-07-13

### Hinzugefügt
- **SEO-Ausbau (On-Page + Off-Page-Anbindung):**
  - Straßen-Landingpages `/strasse/<slug>/` für alle unterstützten Straßen
    (nächste Termine je Abfallart, Bezirk, Hausnummern-Hinweis, Abo-CTA,
    BreadcrumbList-Schema); neues Slug-Feld am Straßenmodell.
  - Straßenverzeichnis `/strassen/` von A bis Z mit Suche – Crawl-Pfad und
    Ziel der Schema.org-SearchAction.
  - SEO-Head in allen Seiten: Title-/Description-Blöcke, Canonical, Open
    Graph + Twitter Card, theme-color, OG-Bild (1200×630).
  - Startseite: sichtbare FAQ-Sektion + FAQPage-Schema, SEO-Textblock,
    WebSite/SearchAction-JSON-LD.
  - `sitemap.xml` (statische Seiten + alle Straßenseiten) und `robots.txt`;
    personalisierte Adress-, Abo- und Druckseiten auf `noindex`.
  - IndexNow-Integration: Schlüssel-Route `/<key>.txt` und Management-Command
    `indexnow_submit` (Bing/Yandex/Seznam/Naver); Search-Console-Verifizierung
    per `GOOGLE_SITE_VERIFICATION`-Umgebungsvariable.
  - Neues Dokument [docs/SEO.md](docs/SEO.md) mit Off-Page-Playbook.

## [0.9.1] - 2026-07-13

### Geändert
- Abo-Seite: Die Google-Anleitung erklärt den entscheidenden Android-Schritt –
  neue URL-Abos blendet die Google-Kalender-App zunächst aus, bis in den
  App-Einstellungen die Synchronisierung für den Kalender aktiviert wird.
  Android-Nutzer sehen den Hinweis zusätzlich direkt unter dem Abo-Button.

## [0.9.0] - 2026-07-13

### Geändert
- **Admin-UI-Neuaufbau nach Screenshot-Review** (Kontraste + Verständlichkeit):
  - Durchgängig helles Theme: das dark_mode_theme erzeugte einen unlesbaren
    Mischzustand (dunkle Karten auf hellem Layout) und entfiel.
  - Flatlys kontrastschwaches Grün (#18bc9c) vollständig durch die
    Teal-Markenpalette ersetzt (Links, Buttons, Tabellenköpfe, Pagination,
    Brand-Header); KPI-Zahlen und Pills in dunkler Textfarbe.
  - Dashboard: ruhige, einheitliche weiße KPI-Karten mit farbigen
    Icon-Kacheln statt vierfarbiger small-boxes; sanfte Warnleiste;
    klare Kopfzeile (Titel + Untertitel links, Pill-Aktionen rechts).
  - **Deutsche Feldnamen** überall in Listen/Filtern (Abfallart, Status,
    Quelldokument, Jahresplan, Bezirk, Herkunft, Straße, …).
  - **Farbige Status-Badges** in den Änderungslisten (Jahrespläne,
    Importläufe, Meldungen, Vorschläge, Tourenzuordnungen) statt nacktem Text.

## [0.8.0] - 2026-07-13

### Hinzugefügt
- **Neues Admin-Dashboard** als /admin/-Startseite: Zustands-KPIs
  (Termine/Jahrespläne, Straßen, offene Vorgänge, Systemstatus mit
  Warn-Banner), Schnellzugriffe, „Bereiche – was finde ich wo?" mit
  Erklärkarten zu allen sieben Admin-Bereichen sowie „zuletzt passiert"
  (Importläufe, Fehlermeldungen).

### Geändert
- **Admin-UI-Überarbeitung (AdminLTE-Polish)**: kuratierte Seitenleiste in
  fachlicher Reihenfolge (Rohdaten-/Zwischentabellen ausgeblendet, über
  Dashboard/Statistik erreichbar), Marken-Farbwelt (Petrol/Gelb), runde
  Karten/Buttons, Sticky-Tabellenköpfe, gestylte Login-Seite, Logo,
  Related-Modals und Tab-Formulare; eigene Seiten (Statistik, Moderation,
  Systemstatus) tragen jetzt die vollständige Admin-Navigation.
- **Abo-Seite**: Auf dem Smartphone erscheint nur noch der zur Plattform
  passende Button (Apple bzw. Google); am Desktop weiterhin beide.

### Behoben
- LOGIN_REDIRECT_URL gesetzt (Login ohne next-Parameter lief auf 404).

## [0.7.2] - 2026-07-13

### Geändert
- Abo-Seite: Google-Anleitung erklärt jetzt, dass URL-Abos bei Google immer
  als eigener Kalender erscheinen (Ziel-Kalender nur beim einmaligen Import
  über „Importieren & Exportieren" wählbar) und dass die erste
  Synchronisation bei Google dauern kann.

## [0.7.1] - 2026-07-13

### Behoben
- **Google Kalender blieb leer**: Googles Kalender-Crawler normalisiert
  webcal:// zu http:// und scheitert dort am HTTPS-Redirect. Der
  Google-Button übergibt jetzt die https-URL direkt (cid), und die
  /calendar/-Feeds werden zusätzlich über http ohne Redirect ausgeliefert
  (nginx-Ausnahme; alle übrigen Seiten leiten weiter auf HTTPS um).

## [0.7.0] - 2026-07-13

### Hinzugefügt
- **Ein-Klick-Kalender-Abo fürs Smartphone**: Die Abo-Seite bietet
  "Zum Kalender hinzufügen" (webcal, iPhone/iPad/Mac) und "Zu Google Kalender
  hinzufügen" (cid-Link, Android/Google) als direkte Buttons; die Plattform
  wird erkannt, der passende Button hervorgehoben und die zugehörige
  Anleitung vorgewählt.

## [0.6.1] - 2026-07-13

### Behoben
- **Docker-Image**: rapidocr installiert das GUI-`opencv-python` als Dependency,
  dessen fehlende libxcb im Slim-Image den OCR-Import (und nach Uninstall das
  geteilte cv2-Paket) zerbrach – das Image behält jetzt nur
  `opencv-python-headless` (sauber neu installiert).

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

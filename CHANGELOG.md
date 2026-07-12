# Changelog

Alle nennenswerten Änderungen dieses Projekts. Format angelehnt an
[Keep a Changelog](https://keepachangelog.com/de/), Versionierung nach SemVer.

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

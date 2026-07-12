# Roadmap / Umsetzungsstand

## Umgesetzt (v0.1.0, Root-Layout-Variante)

- **Phase 1 Analyse** – PDF-Struktur, Kalender-/Buchstabenlogik, Parserrisiken (docs/ANALYSE.md)
- **Phase 2 UX/Design** – Token-Designsystem, öffentliches Layout, Jazzmin-Admin, Light/Dark
- **Phase 3 Architektur** – 16 Module, Datenmodell, Rollen, Statusmodelle, Prioritäten
- **Phase 4 Parser** – Text-Straßenparser + OCR-Kalenderparser inkl. Zellen-Zweitpass,
  gegen die echte Ausgabe 2026 verifiziert (260 Termine, 1.738 Straßen)
- **Phase 5 Kern** – Stammdaten, tolerante Adresssuche (HTMX), Terminansicht, RFC-5545-Feeds
  mit stabilen UIDs/ETag/304, Abo-Seite mit Anleitungen, Druckansicht
- **Phase 6 Administration (Basis)** – Jazzmin-CRUD für alle Modelle, Importläufe mit
  Issues/Diff, Systemstatusseite, Audit-Log per Signals
- **Phase 7 Statistik** – Ereigniserfassung, Aggregation + Purge, internes Dashboard mit
  Chart/Tabellen/Filtern/CSV
- **Phase 8 Bürgerfunktionen (Basis)** – Fehlermeldung mit Vorgangsnummer/Statusseite,
  Korrekturvorschläge + Bestätigungen (API/Web), Moderationsqueue
- **Phase 9 Community (Fundament)** – Quorum-Regeln + Auswertung, Fallback-Erfassung mit
  Beleg-Upload (Feature-Flags, standardmäßig aus)
- **Phase 10 Betrieb** – fetch-Command mit Archivierung, Health-Endpunkte, Docker/Compose,
  Cron-Beispiele, Backup, CI, Doku

## Nächste Schritte (priorisiert)

1. **Layout-Entscheidung**: Root-Variante vs. paralleler src/-Baum konsolidieren (siehe README-Hinweis im Repo-Verlauf)
2. Visuelle Diff-Ansicht für Straßen-Diffs im Admin (aktuell JSON + Command)
3. Vorschlags-Detailseite öffentlich (Bestätigen-Button aus der Terminansicht heraus)
4. Benutzerkonten-Selbstverwaltung (Registrierung, eigene Meldungen einsehen)
5. Zweite Abfallart (Blaue Tonne) inkl. zweitem Parser als Architektur-Beweis
6. Konflikt-Dashboard (konkurrierende Werte nebeneinander, §26-Visualisierung)
7. XLSX-/PDF-Export der Statistik, /metrics (Prometheus)
8. E-Mail-Bestätigung für Melder (Opt-in), i18n-Vorbereitung

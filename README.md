# abholtag.de – Abfuhrkalender Lübeck

Öffentliche Open-Source-Webanwendung für Abfuhrtermine in der Hansestadt Lübeck:
Adresse suchen, Termine prüfen, Kalender dauerhaft abonnieren – mit automatischem
Import des offiziellen Abfuhrplans (PDF), Bürger-Fehlermeldungen und moderierter
Datenpflege.

**Erste Abfallart:** Gelber Sack (Ausgabe 2026 vollständig importiert und verifiziert).
Weitere Abfallarten (Papier, Restmüll, Bio, …) sind architektonisch vorbereitet.

## Funktionen

- 🔍 **Tolerante Adresssuche** – „Straße/Strasse/Str./St.“, Umlaute, Hausnummern
  mit Zusätzen, gerade/ungerade Bereiche, Ortsteile
- 📅 **Terminansicht** – nächster Termin mit Countdown, kommende Abholungen,
  Jahresübersicht, Druckansicht
- 🔗 **iCalendar-Feeds (RFC 5545)** – stabile URLs über Jahreswechsel, stabile UIDs,
  Änderungen per SEQUENCE/CANCELLED, ETag/304, kompatibel mit Apple/Google/
  Outlook/Thunderbird; Anleitunge­n auf der Abo-Seite
- 🤖 **Automatischer PDF-Import** – täglicher Abruf, Archivierung, OCR-Parser für
  den Kalenderteil, Validierung mit Review-Gate (nichts geht ungeprüft live)
- 🧑‍🤝‍🧑 **Bürgerbeteiligung** – Fehlermeldungen mit Vorgangsnummer, strukturierte
  Korrekturvorschläge, konfigurierbares Quorum, Community-Fallback-Erfassung
- 📊 **Interne Statistik** – datenschutzfreundlich (keine IPs, rotierende Hashes,
  Aggregation + Löschfristen), AdminLTE-Dashboard
- 🌗 Light-/Darkmode, WCAG-orientiert, strikte CSP, keine externen Dienste
- 🔎 **SEO** – Straßen-Landingpages (`/strasse/<slug>/`) und A–Z-Verzeichnis
  (`/strassen/`), Sitemap/robots, Open Graph, JSON-LD (WebSite/SearchAction,
  FAQPage, BreadcrumbList), IndexNow-Anbindung

## Schnellstart (Entwicklung)

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt      # Linux/macOS: .venv/bin/pip
python manage.py migrate
python manage.py import_waste_schedule --waste-type gelber-sack \
    --file data/samples/abfuhrplan-gelber-sack-2026.pdf
python manage.py publish_waste_schedule --waste-type gelber-sack --year 2026 --force
python manage.py createsuperuser
python manage.py runserver
```

Das `--force` ist beim Beispielplan 2026 nötig, weil das amtliche Quell-PDF einen
dokumentierten Druckfehler enthält (fehlender Termin Bezirk C im Mai) – der Import
meldet das korrekt als Warnung. Details: [docs/ANALYSE.md](docs/ANALYSE.md).

Tests & Lint:

```bash
python -m pytest -c pyproject.toml
ruff check apps config
```

## Produktion (Docker)

Die CI baut bei jedem Push auf `main` und bei Release-Tags (`vX.Y.Z`) ein Image nach
**`ghcr.io/brightcolor/abholtag.de-claude`**.

```bash
cp .env.example .env    # ausfüllen (Secret, Hosts, DB-Passwort, Betreiberangaben)
docker compose up -d    # zieht das GHCR-Image; lokal bauen: docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

Reverse Proxy: [deploy/nginx.conf](deploy/nginx.conf) ·
Cron/systemd statt Compose-cron: [deploy/cron.example](deploy/cron.example) ·
Backup: [deploy/backup.sh](deploy/backup.sh)

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [docs/ANALYSE.md](docs/ANALYSE.md) | PDF-Struktur, OCR-Strategie, Parserrisiken, Befunde |
| [docs/ARCHITEKTUR.md](docs/ARCHITEKTUR.md) | Module, Datenmodell, Rollen, Statusmodelle, Konfliktregeln |
| [docs/DESIGNSYSTEM.md](docs/DESIGNSYSTEM.md) | Tokens, Komponenten, Light/Dark, Barrierefreiheit |
| [docs/IMPORT-UND-FALLBACK.md](docs/IMPORT-UND-FALLBACK.md) | Import-Pipeline, Diff, Community-Fallback |
| [docs/ANALYTICS-DATENSCHUTZ.md](docs/ANALYTICS-DATENSCHUTZ.md) | Ereignisse, Pseudonymisierung, Löschkonzept |
| [docs/MODERATION-QUORUM.md](docs/MODERATION-QUORUM.md) | Moderationshandbuch, Quorum-Regeln |
| [docs/BETRIEB.md](docs/BETRIEB.md) | Deployment, Backup/Restore, Monitoring, Admin-Handbuch |
| [docs/SEO.md](docs/SEO.md) | On-Page-Maßnahmen, IndexNow, Search-Console, Off-Page-Playbook |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Umsetzungsstand und nächste Schritte |
| [docs/openapi.json](docs/openapi.json) | API-Spezifikation (auch unter `/api/v1/openapi.json`) |

## Rechtliches

Unabhängiges Bürgerprojekt, keine Seite der Hansestadt Lübeck oder der
Entsorgungsbetriebe. Alle Angaben ohne Gewähr; verbindlich sind die offiziellen
Veröffentlichungen. Lizenz: [MIT](LICENSE).

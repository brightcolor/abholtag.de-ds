# Betriebshandbuch (Deployment, Backup, Monitoring) – Root-Layout-Variante

## Schnellstart (Entwicklung)

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
set DJANGO_SETTINGS_MODULE=config.settings.dev
.venv/Scripts/python -m django migrate
.venv/Scripts/python -m django import_waste_schedule --waste-type gelber-sack \
    --file data/samples/abfuhrplan-gelber-sack-2026.pdf
.venv/Scripts/python -m django publish_waste_schedule --waste-type gelber-sack --year 2026 --force
.venv/Scripts/python -m django createsuperuser
.venv/Scripts/python -m django runserver
```

(`--force` beim Beispielplan 2026 wegen der dokumentierten Bezirk-C-Lücke im Quell-PDF,
siehe docs/ANALYSE.md.)

## Produktion (Docker Compose)

Dateien: `deploy/Dockerfile.root`, `deploy/docker-compose.root.yml` (Bind Mounts unter
`./docker-data/`), `.env` nach `deploy/env.root.example`. Reverse Proxy: `deploy/nginx.conf`.

```bash
cp deploy/env.root.example .env   # ausfüllen!
docker compose -f deploy/docker-compose.root.yml up -d --build
docker compose -f deploy/docker-compose.root.yml exec web python manage_prod.py migrate
docker compose -f deploy/docker-compose.root.yml exec web python manage_prod.py createsuperuser
```

Periodik: Compose-Service `cron` (alle 6 h fetch/aggregate/purge/quorums) oder
`deploy/cron.example` für System-Cron/systemd-Timer.

## Sicherheit (§34)

HSTS/SSL-Redirect (prod.py), CSP ohne `unsafe-eval`, Referrer-/Permissions-Policy,
Secure/HttpOnly-Cookies, Rate-Limits, Honeypots, Upload-Prüfung.
**2FA:** TOTP-Gerät unter `/admin/otp_totp/totpdevice/` anlegen (QR-Code), danach
`ADMIN_OTP_REQUIRED=true` setzen → /admin verlangt OTP.

## Monitoring (§37)

- `/health` (Gesamtstatus, 503 bei degraded), `/health/live`, `/health/ready`
- Admin-Statusseite `/intern/status/`: DB, Speicherplatz, Quellen-Freshness (überfällige
  Abrufe), fehlende Jahrespläne (ab Oktober auch Folgejahr), Moderations-Backlog,
  letzte Dokumente/Importläufe.
- Empfehlung: externen Uptime-Check auf `/health` legen; `ADMIN_EMAILS` setzen, damit neue
  Planversionen, Quorum-Erfolge und Meldungen zugestellt werden.

## Backup & Wiederherstellung (§38)

`deploy/backup.sh`: täglicher PostgreSQL-Dump + `docker-data/media` (Original-PDFs,
Belege) + `.env`; Aufbewahrung 30 Tage, extern replizieren.

Wiederherstellung: Compose auf neuem Host starten → `gunzip -c db-….sql.gz |
docker compose exec -T db psql -U abfuhrkalender abfuhrkalender` → Media-Tar nach
`docker-data/media` entpacken. Einzelne Datensätze: Audit-Log enthält Vorher/Nachher-
Snapshots; Jahresplan-Rollback über `withdraw_waste_schedule` bzw. Re-Import eines
archivierten `SourceDocument` (`import_waste_schedule --document-id …`).
Export/Weitergabe: `export_schedule --format json|csv`.

## Administrationshandbuch (Kurzfassung)

- **Neues Jahr:** Cron archiviert das PDF automatisch → Importlauf prüfen
  (`/intern/moderation/` bzw. Admin → Importe) → Warnungen bewerten → veröffentlichen.
- **Straßenänderungen:** Diff im Importlauf ansehen, Änderungen gezielt in
  Adressen → Straßen/Tourenzuordnungen übernehmen (auditiert, rückverfolgbar).
- **Pending-Zuordnungen:** Nach Erstimport die 21 Bereichs-Zuordnungen (raw_range) prüfen
  und auf `aktiv` stellen, damit die betroffenen Straßen auflösbar werden.
- **Kurzfristige Terminänderung:** Termin im Admin bearbeiten (Hinweis setzen oder
  `Entfällt` + Ersatztermin anlegen) – SEQUENCE erhöht sich automatisch, Feeds
  aktualisieren sich bei Clients innerhalb ihres Poll-Intervalls.

# Architektur

Modularer Django-Monolith (kein Microservice-Zuschnitt, §4). Diese Dokumentation beschreibt
die **Root-Layout-Variante** (`config/` + `apps/` im Projektstamm, Start über `manage_prod.py`
bzw. `python -m django`).

## Module (§5)

| App | Verantwortung |
|---|---|
| `core` | Basismodelle (TimeStamped, Origin/Herkunft), Normalisierung, Security-Header, Rate-Limiting, pseudonyme Sitzungs-Hashes |
| `accounts` | Custom User, Rollen (Gruppen), Vertrauensprofile |
| `waste_types` | Abfallarten inkl. ICS-Texten, Farben, Icons (§8) |
| `addresses` | Städte, Ortsteile, Straßen, Aliasse, Tourenzuordnungen, stabile `AddressKey`s |
| `schedules` | Bezirke/Touren, Jahrespläne (Statusmodell §31), Termine, öffentliche Views |
| `data_sources` | Quellen (PDF-URL/manuell/Community/API), archivierte Originaldokumente |
| `imports` | Parser-Registry, Validierung, Diff, Importläufe, Management-Commands |
| `calendars` | RFC-5545-Generator, Feeds mit ETag/304, Abo-Seite |
| `analytics` | Ereignisse, Aggregate, internes Dashboard (§17–19) |
| `reports` | Export-Helfer (CSV) |
| `community` | Fehlermeldungen, Korrekturvorschläge, Votes, Quorum-Regeln, Fallback-Erfassung (§20–24) |
| `moderation` | Queue-Oberfläche, Kommentare (§27) |
| `notifications` | Admin-Benachrichtigungen (mail_admins) |
| `audit` | Änderungsprotokoll per Signals, ChangeSets, `audit_context` (§25) |
| `public_api` | versionierte JSON-API `/api/v1/` (§33) |
| `system_status` | /health-Endpunkte, Statusseiten (§37) |

Parser sind von Views/Models entkoppelt: `imports/parsers/` liefert reine `ParsedPlan`-
Datenobjekte; `imports/services.py` wendet sie mit Review-Gates auf die DB an.

## Datenmodell – Kernbeziehungen (§30)

```
WasteType 1─n CollectionZone 1─n CollectionDate n─1 ScheduleYear n─1 SourceDocument n─1 DataSource
                    │
Street 1─n StreetAssignment (house_from/to, Parität, raw_range, Status, Herkunft)
  │ 1─n StreetAlias      n─1 District n─1 City
  └ 1─n AddressKey (public_id, stabil über Jahre → Feed-URLs, §12)
ErrorReport / CorrectionProposal (1─n ProposalVote) / CommunityContribution / QuorumRule
AuditLog (n─1 ChangeSet) · AnalyticsEvent / AnalyticsAggregate · UserTrustProfile
```

**Stammdaten vs. Jahresdaten (§6/§7):** Straßen/Zuordnungen werden beim Erstimport angelegt
und danach nie automatisch überschrieben (Diff + manuelle Übernahme, §16). Jahrespläne
ersetzen bei Re-Import nur Termine mit Herkunft `official_import`; manuelle Korrekturen
bleiben erhalten.

## Herkunft & Konfliktpriorität (§23/§26)

Jeder Termin/jede Zuordnung trägt `origin`:
`official_import · admin · moderator · citizen · quorum · external_api · manual_import`.

Standardpriorität bei Konflikten (im Admin sichtbar, nicht stillschweigend):
1. administrativ bestätigte manuelle Korrektur (`admin`/`moderator`)
2. offiziell importierte Daten (`official_import`)
3. Quorum-bestätigte Bürgerdaten (`quorum`)
4. ungeprüfte Bürgerhinweise (nur gekennzeichnet sichtbar, nie in Feeds)

Technisch: Re-Importe löschen nur `official_import`-Termine; ein von Hand angelegter oder
korrigierter Termin desselben Datums bleibt bestehen und gewinnt.

## Rollen (§29)

Gruppen werden per Datenmigration angelegt: **Administrator** (Superuser),
**Datenmanager** (Stammdaten/Pläne/Importe), **Moderator** (Meldungen/Vorschläge),
**Analyst** (nur Statistik lesen, keine Kontaktdaten), **Auditor** (nur Audit lesen).
2FA für /admin über django-otp, erzwingbar per `ADMIN_OTP_REQUIRED`.

## Statusmodelle (§31)

- `ScheduleYear`: discovered → downloaded → parsing → (parse_failed) → parsed →
  (validation_failed) → needs_review → approved → **published** → superseded/withdrawn/archived
- `CorrectionProposal`: draft → submitted → (duplicate) → awaiting_confirmation →
  quorum_reached → under_review → accepted/partially_accepted/rejected → published;
  jederzeit withdrawn/superseded.

## Technologie

Python 3.11 · Django 5.2 LTS · PostgreSQL (SQLite im Dev) · Django-Templates + HTMX +
minimales Vanilla-JS (CSP ohne `unsafe-eval`!) · AdminLTE 3 (Jazzmin) im Adminbereich,
eigenes Token-basiertes Designsystem öffentlich · pdfplumber/pypdfium2 + RapidOCR (pip-only)
· Whitenoise · Gunicorn · Docker Compose (Bind Mounts) · Cron statt Celery (§4).

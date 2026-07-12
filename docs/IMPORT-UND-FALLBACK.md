# Import-Pipeline und Fallback-Strategie (§14–§16, §24)

## Automatischer Abruf

`python manage_prod.py fetch_waste_source [--import]` (Cron, täglich):

1. GET mit `If-None-Match`/`If-Modified-Since` auf die bekannte PDF-URL.
2. Prüfung: HTTP-Status, Content-Type, Größe (Limit 50 MB), SHA-256 gegen letzte Version.
3. Neue Version → Originaldatei **archivieren** (`SourceDocument`, Bind-Mount `media/`),
   Vorgängerversion als `superseded` markieren, Admin-Mail.
4. Mit `--import`: Parserlauf inkl. Validierung; Ergebnis ist **nie automatisch öffentlich**.

## Importlauf (`run_import`)

```
SourceDocument → Parser (Registry, austauschbar) → ParsedPlan
   → validate_plan (§32: Jahr plausibel, Termine im Jahr, Bezirke, Vorjahresvergleich)
   → Fehler   ⇒ ImportRun: validation_failed (nichts geschrieben)
   → Straßen:  DB leer ⇒ Seed | sonst ⇒ nur Diff (streets_added/removed/changed)
   → Termine:  ScheduleYear (parsed | needs_review), nur origin=official ersetzt
   → Warnungen/Diff ⇒ needs_review, sonst completed
```

Veröffentlichung ausschließlich bewusst: `publish_waste_schedule --waste-type … --year …`
(`--force` nötig bei offenen Warnungen) oder im Admin. `withdraw_waste_schedule` zieht
zurück; Kalender-Feeds enthalten dann keine Termine des Plans mehr (Clients räumen über
UID/SEQUENCE auf).

## Straßenlisten-Diff (§16)

`compare_street_assignments --file … [--json]` bzw. Importlauf-Diff im Admin: neue,
entfernte, geänderte Zuordnungen inkl. Zusammenfassung. Übernahme einzeln über die
Stammdatenpflege (Straßen/Zuordnungen im Admin, auditiert) – niemals automatisch.

## Jahreswechsel (Normalfall)

Nur Termine ändern sich: neuer `ScheduleYear` + `CollectionDate`s; Straßen, Zuordnungen und
`AddressKey`s (und damit **alle Feed-URLs**) bleiben unverändert. Nach Veröffentlichung
erscheinen die neuen Termine automatisch in bestehenden Abonnements.

## Fallback-Kaskade, wenn das PDF nicht mehr maschinenlesbar ist (§24)

1. **Parser-Anpassung** – Layout-Änderungen werden als `parse_failed`/`validation_failed`
   samt Diagnose gemeldet; neuer Parser wird unter neuem `parser_key` registriert.
2. **Manueller Import** – `import_waste_schedule --file plan.pdf` mit lokal beschaffter
   Datei; alternativ CSV/JSON-Pflege über den Admin (Termine-Massenbearbeitung).
3. **Community-Erfassung** – `COMMUNITY_MODE_ENABLED=true` schaltet `/melden/community/`
   frei: strukturierte Erfassung (Abfallart, Jahr, Datum, Tour, Straße, Beleg-Upload),
   standardmäßig moderiert; Quorum-Regeln pro Änderungstyp konfigurierbar (§22).

## Management-Commands (§41)

`fetch_waste_source · import_waste_schedule · validate_waste_schedule ·
compare_schedule_years · publish_waste_schedule · withdraw_waste_schedule ·
import_street_assignments · compare_street_assignments · export_schedule ·
aggregate_analytics · purge_old_analytics · evaluate_quorums ·
expire_unverified_contributions`

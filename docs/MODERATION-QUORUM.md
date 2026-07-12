# Moderations- und Quorumskonzept (§20–§27) – zugleich Moderationshandbuch

## Eingangskanäle

1. **Fehlermeldung** (`/melden/`, anonym möglich): Kategorie, Beschreibung, optional Quelle
   und E-Mail; Honeypot + Mindest-Ausfüllzeit + Rate-Limit gegen Bots. Ergebnis:
   Vorgangsnummer + öffentliche Statusseite (`/melden/status/<token>/`).
2. **Korrekturvorschlag** (strukturiert, API `/api/v1/corrections`): Zielobjekt, alter Wert,
   neuer Wert (JSON), Begründung, Quelle; bestätigbar per `/api/v1/proposals/{id}/confirm`
   bzw. Formular-POST.
3. **Community-Erfassung** (nur bei aktiviertem Fallback-Modus, §24).

## Moderationsablauf (`/intern/moderation/`)

Queue mit offenen Fehlermeldungen, Vorschlägen (inkl. Bestätigungs-/Gegenstimmenzähler),
Community-Beiträgen sowie Importläufen/Jahresplänen mit Prüfbedarf. Bearbeitung im Admin:
Status setzen (in Prüfung/gelöst/abgelehnt/Duplikat), öffentliche Antwort (erscheint auf
der Statusseite), interne Kommentare (`ModerationComment`), Umsetzung der Änderung in den
Stammdaten/Terminen (auditiert, Herkunft `moderator`).

## Veröffentlichungsstufen (§23)

1. ungeprüfte Meldung → nur intern
2. öffentlicher Bürgerhinweis → sichtbar, klar als ungeprüft markiert (nie in Feeds)
3. Quorum-bestätigt → als gemeinschaftlich bestätigt gekennzeichnet
4. moderierte Korrektur → regulär in Web, API und Kalender-Feeds
5. automatisch veröffentlichte Community-Korrektur → **nur** bei
   `COMMUNITY_MODE_ENABLED=true` **und** `COMMUNITY_AUTO_PUBLISH=true` **und** Regel-Flag

## Quorum (§22, standardmäßig deaktiviert)

`QuorumRule` je Änderungstyp, optional je Abfallart:

- `min_confirmations` – unabhängige Bestätigungen (Dedupe über Konto bzw. Session-Hash)
- `max_objection_ratio` – Gegenstimmen-Anteil, ab dem das Quorum scheitert
- `requires_source` – Quellenangabe Pflicht
- `window_days` – Zeitfenster, in dem Bestätigungen zählen
- `auto_publish` – nur wirksam im Community-Modus

Empfohlene Startwerte: Hinweis 3 · Terminabweichung 5 · geänderte Straßenzuordnung 10 + Quelle.
Auswertung durch `evaluate_quorums` (Cron): erreichte Quoren → Status `quorum_reached` +
Admin-Benachrichtigung; die tatsächliche Datenänderung bleibt ein moderierter Schritt,
solange auto_publish aus ist. Offizieller Neuimport setzt betroffene offene Vorschläge auf
`superseded`.

## Missbrauchsschutz (§34)

Ein Vote pro Vorgang und Session-Hash (täglich rotierend), Rate-Limits pro Endpunkt,
Honeypot/Zeitprüfung in Formularen, Upload-Validierung (Typ/Größe), `UserTrustProfile`
für wiederkehrende Beitragende.

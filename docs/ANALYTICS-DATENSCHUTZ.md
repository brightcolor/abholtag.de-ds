# Analytics- und Datenschutzkonzept (§17–§19)

## Grundsätze

Keine externen Tracker, keine Cookies für Statistik, keine IP-Speicherung, keine Profile,
keine Weitergabe. Statistiken sind ausschließlich im geschützten Bereich sichtbar
(`/intern/statistik/`, Rolle Analyst+). Öffentlich gibt es nur grobe Bestandszahlen
(Straßen-/Terminanzahl, Datenstand).

## Ereignisse (§17.1)

`page_view, street_search, street_search_no_result, address_resolved, schedule_view,
calendar_subscription_page_view, calendar_feed_requested, calendar_downloaded,
error_report_opened, error_report_submitted, correction_submitted, proposal_confirmed,
community_entry_submitted`

Metadaten: Zeitstempel, Ortsteil-/Straßen-/Adressschlüssel-Referenz, Abfallart, Jahr,
Geräteklasse, Browserfamilie, Kalender-Client, Referrer-Domain (gekürzt), Ergebnisstatus,
Suchbegriff (nur bei ergebnislosen Suchen, max. 100 Zeichen).

## Pseudonymisierung

`session_hash = sha256(SECRET_KEY + Kalendertag + IP + User-Agent)[:32]`
– die IP wird **nicht gespeichert**; der Salt rotiert täglich, eine Verkettung über
Tagesgrenzen ist konstruktionsbedingt unmöglich. Derselbe Hash begrenzt Mehrfach-Votes
(§22) und anonyme Meldungsfluten.

## Aufbewahrung & Löschkonzept

| Datenart | Frist | Mechanismus |
|---|---|---|
| Roh-Ereignisse | `ANALYTICS_RAW_RETENTION_DAYS` (Std. 90 Tage) | `purge_old_analytics` (Cron) |
| Tagesaggregate (`AnalyticsAggregate`) | unbegrenzt (rein zählend) | `aggregate_analytics` |
| Reporter-E-Mail (freiwillig) | bis Vorgangsabschluss + Löschung auf Wunsch | Admin |
| Community-Belege (Uploads) | bis Prüfung; verfallene Beiträge | `expire_unverified_contributions` |
| Original-PDFs | dauerhaft (Nachvollziehbarkeit der Datenherkunft) | Archiv |

## Geschätzte aktive Abonnements (dokumentierte Methode, §19)

Ein Feed-**Abruf** ist kein Abo. Gezählt werden `(AddressKey, Kalender-Client)`-Paare mit
Feed-Abrufen an **mindestens zwei verschiedenen Tagen innerhalb von 21 Tagen** –
wiederkehrendes Client-Polling unterscheidet sich so von Einmal-Downloads
(`calendar_downloaded` wird separat erfasst). Die Zahl ist als Schätzung gekennzeichnet.

## Dashboard (§18)

Übersichtskarten (heute/Woche/Monat, Auflösungen, ergebnislose Suchen, Feed-Abrufe,
geschätzte Abos, offene Meldungen/Vorschläge/Beiträge), Zeitverlaufs-Chart mit
Tabellen-Alternative (a11y), Top-Ortsteile/-Straßen, ergebnislose Suchbegriffe,
Kalender-Clients; Filter für Zeitraum/Ereignis/Gerät; CSV-Export.

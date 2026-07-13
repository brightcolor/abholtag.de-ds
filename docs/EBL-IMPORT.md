# EBL-Abfuhrplan – Import aller Abfallarten

Seit v0.11.0 ist der offizielle **EBL-„Wegweiser"** (`abfuhrplan-ebl-web.pdf`)
die maßgebliche Quelle für **alle vier Abfallarten**: Restabfall, Bioabfall,
Papier (Kommunale Lübecker Altpapiertonne) und Gelber Sack.

## Warum dieser Plan

Anders als das Veolia-„Gelber-Sack"-PDF (Rasterbild → OCR) und die
BMS-Online-Abfrage (eine Stichprobe je Straße) ist der EBL-Plan **vollständig
textbasiert** und listet pro Straße die amtlichen Tourbuchstaben **inklusive
Hausnummernbereichen**. Damit löst er die größte Schwäche der bisherigen
Quellen: In Straßen, deren Touren nach Hausnummer geteilt sind
(z. B. Kahlhorststraße 1–16 → Tour F, 17–Ende → Tour D), lösen wir jetzt
korrekt auf.

## Aufbau des PDFs

* **Kalenderdoppelseite** (zweimal, eine zum Herausnehmen): 12 Monatsspalten,
  eine Zeile je Tag. Jeder Abfuhrtag trägt **drei Tourbuchstaben**:

  | Spalte | Buchstaben | Abfallart |
  |--------|-----------|-----------|
  | 1 | A–J | Restmüll **und** Biotonne (gleiche Tour, gleicher Tag) |
  | 2 | A–T | Kommunale Lübecker Altpapiertonne (4-wöchentlich) |
  | 3 | A–J | Gelber Sack (Veolia) |

  Samstage sind Ersatztermine (Feiertagsverschiebungen, bereits eingearbeitet).

* **Straßenverzeichnis** (~1300 Zeilen, drei Layout-Spalten je Seite):
  Straßenname, optionale Hausnummernbereiche, dann die drei Tourbuchstaben.
  Altstadtstraßen können geteilte Codes tragen („G/Q" = beide Touren, also
  wöchentliche Abfuhr).

## Robustheit (Jahreswechsel)

Der Parser (`apps/imports/parsers/luebeck_ebl.py`) ist so gebaut, dass er auch
den Plan des Folgejahres ohne Anpassung korrekt liest:

* **Nichts** hängt an Seitenzahlen, Monatsnamen oder einer fest verdrahteten
  Jahreszahl. Kalender- und Verzeichnisseiten werden am Inhalt erkannt, das
  Jahr aus „1. Januar bis 31. Dezember JJJJ" gelesen.
* **Selbstvalidierung:** Jede erkannte Monatsspalte wird gegen den echten
  Kalender geprüft (Wochentag jeder Tagesnummer muss stimmen). Eine falsch
  erkannte Spalte kann nie stillschweigend durchrutschen – sie erzeugt einen
  blockierenden Fehler.
* **Buchstaben-Slots** werden je Monatsspalte aus den Dreier-Zellen kalibriert,
  damit auch einzelne Ersatztermin-Buchstaben (Samstage) der richtigen
  Abfallart zugeordnet werden.
* **Zwei Kalenderkopien** werden verglichen; Widersprüche blockieren.
* **Zonencodes** sind die amtlichen Tourbuchstaben (A–J bzw. A–T) und damit
  über Jahre stabil – ein neuer Jahrgang aktualisiert dieselben Zonen.

Die Hausnummernbereiche werden mit `parse_house_ranges()` (in
`apps/core/text.py`) in `von/bis/Seite` zerlegt. Genau die Fälle, die sich
nicht eindeutig parsen lassen (~6 von ~550), werden **nicht geraten**, sondern
als `PENDING`-Zuordnung mit Originaltext zur manuellen Prüfung angelegt (§10).

## Betrieb

Einmaliger Import / Umstieg von den BMS-Daten:

```bash
# lokal testen (ohne Veröffentlichung)
python manage.py import_ebl --path data/samples/abfuhrplan-ebl-2026.pdf

# direkt veröffentlichen (Umstieg auf dem Server)
python manage.py import_ebl --path <pfad-zur-pdf> --publish
```

Ohne `--publish` landen die Jahrespläne im Status „Prüfung erforderlich" und
werden mit `publish_waste_schedule --waste-type <slug> --year <jahr>` (für jede
Abfallart) freigegeben.

**Jährliche Automatik:** Eine `DataSource` vom Typ `pdf_url` mit
`parser_key="luebeck_ebl"` und der EBL-PDF-URL wird von
`fetch_waste_source --import` täglich geprüft. Eine neue Version wird
archiviert und automatisch (gestaffelt, zur Prüfung) importiert – der
Menschen-Review vor Veröffentlichung bleibt erhalten.

## Verhältnis zu den anderen Quellen

* **Veolia-OCR-PDF (Gelber Sack):** bleibt als unabhängige Kreuzprüfung
  erhalten; der EBL-Plan stimmt damit überein und ergänzt den im Veolia-PDF
  fehlenden 13.-Mai-Termin (Bezirk C).
* **BMS/insert-it (Live):** bleibt als Selbstheilungs-Fallback und für die
  Hausnummern-Referenzdaten, ist aber nicht mehr die primäre Terminquelle.

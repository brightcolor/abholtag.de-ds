# Phase 1 – Analyse des offiziellen Abfuhrplans (Gelber Sack, Ausgabe 2026)

Quelle: `https://entsorgung.luebeck.de/files/Abfuhrplan/abfuhrplan-gelber-sack-luebeck.pdf`
(archivierte Referenzkopie: `data/samples/abfuhrplan-gelber-sack-2026.pdf`, SHA-256 wird beim
Import gespeichert).

## Dokumentaufbau

Das PDF hat 2 Seiten im A2-Querformat:

| Bereich | Seite | Technische Form | Parser-Strategie |
|---|---|---|---|
| Infotexte, Ausgabestellen | 1 | eingebetteter Text | Jahreserkennung (Regex `20\d{2}`, häufigster Treffer) |
| **Jahreskalender** | 1 | **Rasterbild** (2246×1142 px, eingebettet) | OCR (RapidOCR, pip-only) + Geometrie |
| **Straßenliste** | 2 | echter Text mit Positionsdaten | pdfplumber `extract_words` |

## Kalenderstruktur

- 12 Monatsspalten × 31 Tageszeilen; je Spalte Unterspalten **Datum** (Tag + Wochentag) und
  **Bezirk** (Tourenbuchstabe A–J).
- Rhythmus: **14-täglich**, eine Woche A–E (Mo–Fr), Folgewoche F–J.
- Feiertagsverschiebungen sind eingearbeitet und teils gelb markiert
  (z. B. 2026: `2 Fr I` nach Neujahr, `19 Sa A` vor Weihnachten).
- Bezirk I hat 2026 **27 Termine** (Jahresanfang und -ende fallen auf Donnerstage) – die
  Validierung darf 26 nicht hart voraussetzen.

### OCR-Erkenntnisse (Parser-Risiken)

1. **Monatsnamen** (rot auf gelb) werden vom OCR-Detektor unzuverlässig erkannt →
   Monatsspalten werden stattdessen aus dem Clustering der Tagesnummern-x-Positionen
   abgeleitet (12 Cluster, Raster ≈183 px).
2. Zeilen sind äquidistant → Least-Squares-Fit `y = a·Tag + b` statt Einzelerkennung.
3. Der Buchstabe **„I“** wird vom Detektor systematisch übersehen → Zweitpass: leere
   Rasterzellen werden zugeschnitten, per Recognition-only-OCR und zusätzlich per
   Komponentenanalyse (schmaler, hoher, randfreier Strich) klassifiziert.
4. OCR-Verwechsler im Bezirksfenster: `1/l/| → I`, `0 → D` (nur dort angewendet).
5. Im Quellbild sind einzelne Tageszahlen als `#` gerendert (August) – unkritisch, da der
   Tag aus der Zeilengeometrie folgt.

### Echter Datenfehler im amtlichen PDF 2026

Die Zelle **13. Mai (Mi)** enthält keinen Bezirksbuchstaben, sondern einen umgebrochenen
Hinweistext („Himmel-“). Dadurch fehlt für **Bezirk C** der Termin zwischen 29.04. und
28.05. (Lücke von 29 Tagen). Der Parser **rät nicht**, sondern meldet eine
`zone_rhythm`-Warnung; der Importlauf erhält den Status *Prüfung erforderlich* (§32).
Behebung: manueller Termin durch Datenmanager (Herkunft „Administrator“) oder
Bürgerbestätigung.

## Straßenliste

- ~1.740 Einträge in „Straße | Bezirk“-Spaltenpaaren (8 Spaltenpaare pro Blockhälfte).
- Besonderheiten, die der Parser behandelt:
  - **Sperrschrift** einzelner Einträge (`K a h l h o r s t s t r .`) → `x_tolerance=6`;
  - Abschnittsmarker `- A -` und Kopfzeilen werden gefiltert;
  - Ortsteile in Klammern (`(Krummesse)`) → District;
  - **Doppelbezirke** `B/G` (Innenstadt, 30 Straßen) → zwei Zuordnungen, Termin-Union;
  - **Hausnummernbereiche** (`Kahlhorststr. 1-15/16`, `Ratzeburger Allee 23a-75/34-96`, 21
    Einträge): Die Notation ist nicht eindeutig dokumentiert → Zuordnungen werden als
    `PENDING` gespeichert und im Admin geprüft, statt geraten (§10). Die Rohangabe bleibt
    in `raw_range` erhalten.

## Ergebnis des Parser-Prototyps (Phase 4)

Gegen die Ausgabe 2026: **Jahr erkannt, 1.738 Straßeneinträge, 260 Kalendertermine**,
alle Bezirke vollständig (A–H, J: 26; I: 27; C: 25 mit dokumentierter Quell-Lücke),
14-Tage-Rhythmus inkl. aller Feiertagsverschiebungen verifiziert.

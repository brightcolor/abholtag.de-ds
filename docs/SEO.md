# SEO-Konzept abholtag.de

Stand: Juli 2026. Ziel: Sichtbarkeit für Suchanfragen wie „Müllabfuhr Lübeck",
„Gelber Sack Lübeck Termine", „Abfuhrkalender Lübeck" und den Long-Tail
„Müllabfuhr <Straßenname> Lübeck".

## On-Page (implementiert)

- **Straßen-Landingpages** `/strasse/<slug>/` – eine indexierbare Seite pro
  unterstützter Straße (~1800 Stück) mit nächsten Terminen je Abfallart,
  Jahresangabe im Title, BreadcrumbList-Schema und CTA zur Adresssuche.
- **Straßenverzeichnis** `/strassen/` – A–Z-Index als Crawl-Pfad zu allen
  Landingpages; `?q=`-Suche ist Ziel der Schema.org-SearchAction.
- **Meta-Fundament** in `templates/base.html`: Title-/Description-Blöcke pro
  Seite, Canonical-URLs, Open Graph + Twitter Card, `theme-color`,
  OG-Bild (`static/og-image.png`, 1200×630).
- **Strukturierte Daten** (JSON-LD): WebSite + SearchAction und FAQPage auf
  der Startseite, BreadcrumbList auf Straßenseiten und im Verzeichnis.
- **FAQ- und Textsektion** auf der Startseite (sichtbarer Content, identisch
  zum FAQPage-Schema – Pflicht laut Google-Richtlinien).
- **Indexsteuerung**: `robots.txt` (sperrt /admin/, /intern/, /a/, /melden/,
  /suche/, /api/), `noindex` auf personalisierten Adress-/Abo-/Druckseiten,
  `sitemap.xml` (statische Seiten + alle Straßen).

## Off-Page / Aktivierung

### Sofort (technisch vorbereitet)

1. **IndexNow** (Bing, Yandex, Seznam, Naver):
   - Schlüssel erzeugen: `openssl rand -hex 16`
   - Auf dem Server in `/opt/abholtag.de/.env` setzen: `INDEXNOW_KEY=<key>`
   - Einreichen: `docker compose exec -T web python manage.py indexnow_submit`
   - Der Schlüssel wird automatisch unter `https://abholtag.de/<key>.txt` ausgeliefert.
2. **Google Search Console**:
   - Property `https://abholtag.de` anlegen (Domain- oder URL-Präfix).
   - Bei Meta-Tag-Verifizierung: Token in `.env` als
     `GOOGLE_SITE_VERIFICATION=<token>` setzen, Container neu starten.
   - Sitemap einreichen: `https://abholtag.de/sitemap.xml`.
3. **Bing Webmaster Tools**: Import aus der Search Console möglich (ein Klick).

### Backlinks & lokale Sichtbarkeit (manuell)

- GitHub-Repo: Homepage-Feld auf https://abholtag.de gesetzt, Topics pflegen
  (`luebeck`, `abfallkalender`, `ical`, `open-data`) – Follow-Link + Discoverability.
- Lübeck-Verzeichnisse/Foren: luebeck.de-Bürgerservice-Hinweise, Stadtteilgruppen
  (Facebook/Nebenan.de), lokale Subreddits – als nützliches kostenloses Tool
  vorstellen, nicht als Werbung.
- Open-Data-/Civic-Tech-Kataloge: Code for Germany / OK Lab Lübeck,
  bund.dev-Umfeld, awesome-Listen für iCal/Abfall-Tools.
- Presse lokal: HL-live.de, Lübecker Nachrichten (Digital-Ressort) – Aufhänger:
  „Open-Source-Abfuhrkalender mit Kalender-Abo für alle Lübecker Straßen".
- Wikipedia/Stadtwiki nur, wo Relevanzkriterien es hergeben (kein Spam).

## Monitoring

- Search Console: Indexabdeckung der `/strasse/`-Seiten beobachten
  (Soft-404-Quote, Duplicate-Cluster).
- Interne Statistik (`/intern/statistik/`): `schedule_view`-Events werden auch
  auf Straßenseiten gezählt.
- Nach jedem Jahresplan-Import lohnt ein erneuter `indexnow_submit`-Lauf
  (Titles/Inhalte ändern sich mit dem neuen Jahr).

## Leitplanken

- Keine Doorway-Patterns: Jede Straßenseite zeigt echte, straßenspezifische
  Termine (Bezirke/Zonen unterscheiden sich real zwischen Straßen).
- FAQ-Inhalte müssen sichtbar und identisch zum Schema bleiben.
- Keine externen Skripte/Tracker – Core Web Vitals bleiben der Vorteil.

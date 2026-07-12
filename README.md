# Abfuhrkalender Lübeck

Open-Source-Webanwendung für Abfuhrtermine in der Hansestadt Lübeck.

## Features

- 🔍 Adress- und Straßensuche mit Autovervollständigung
- 🗑️ Anzeige kommender Abfuhrtermine (Gelber Sack und weitere)
- 📅 iCalendar-Abonnement-Feeds (RFC 5545)
- 📊 Datenschutzfreundliche Nutzungsstatistiken
- 📝 Bürger-Fehlermeldungen und Korrekturvorschläge
- 👥 Quorum-basierte Community-Datenpflege
- ⚙️ Vollständige administrative Kontrolle
- 🌙 Light- und Darkmode
- ♿ Barrierefrei (WCAG 2.2 AA)

## Technologie

- **Backend:** Python, Django 5.x, Gunicorn
- **Frontend:** AdminLTE 4, Bootstrap 5, HTMX, Alpine.js
- **Datenbank:** PostgreSQL 16
- **Infrastruktur:** Docker, Docker Compose, nginx

## Schnellstart

```bash
cp .env.example .env
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_data
```

## Lizenz

MIT
# Blue Quants

Real-time market movement intelligence prototype built with Django.

Blue Quants focuses on one question:

> Why did this stock move?

The app presents a terminal-style dashboard with movement attribution, driver timelines, confidence scoring, sentiment decomposition, historical event similarity, and sector propagation views.

## Developer

Developed by Cytric.

- GitHub: https://github.com/cytric-74
- LinkedIn: https://linkedin.com/in/roh28j

## Current Stack

- Django
- Python
- HTML templates
- CSS
- SQLite

## Run Locally

The included virtual environment points to a machine-specific Python path. If it does not activate correctly, use system Python with the packaged site dependencies:

```powershell
$env:PYTHONPATH="C:\Users\try\Desktop\stock-market-analysis\virtualenv\Lib\site-packages"
python manage.py runserver 127.0.0.1:8000
```

Open:

```text
http://127.0.0.1:8000/
```

## Main Routes

- `/` - market intelligence dashboard
- `/search/` - why-moved analysis input
- `/ticker/` - markets monitor
- `/predict/NVDA/30/` - stock movement analysis

## Notes

This version uses deterministic prototype data so the interface loads quickly and does not depend on live market APIs during development.

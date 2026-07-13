FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# rapidocr zieht das GUI-opencv als Dependency mit; im Slim-Image fehlt dessen
# libxcb und das geteilte cv2-Paket zerbricht -> nur headless behalten.
RUN pip install --no-cache-dir -r requirements.txt     && pip uninstall -y opencv-python     && pip install --no-cache-dir --force-reinstall --no-deps opencv-python-headless==4.11.0.86

COPY . .

RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput --settings=config.settings.prod

RUN useradd --create-home appuser \
    && mkdir -p /app/media \
    && chown -R appuser:appuser /app/media
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live')"

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

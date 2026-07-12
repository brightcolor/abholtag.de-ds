"""Fetching and archiving of official source files (§14)."""

import hashlib
import logging

import requests
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import DataSource, DocumentStatus, SourceDocument

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024


class FetchResult:
    def __init__(self, source: DataSource):
        self.source = source
        self.new_document: SourceDocument | None = None
        self.unchanged = False
        self.error = ""


def fetch_source(source: DataSource, force: bool = False) -> FetchResult:
    """Check the source URL and archive a new version when one appears."""
    result = FetchResult(source)
    headers = {"User-Agent": "abfuhrkalender-luebeck/1.0 (Open-Source-Projekt)"}
    if source.last_etag and not force:
        headers["If-None-Match"] = source.last_etag
    if source.last_modified_header and not force:
        headers["If-Modified-Since"] = source.last_modified_header

    source.last_checked_at = timezone.now()
    try:
        response = requests.get(source.url, headers=headers, timeout=60)
    except requests.RequestException as exc:
        source.last_status = f"Fehler: {exc.__class__.__name__}"
        source.save(update_fields=["last_checked_at", "last_status"])
        result.error = str(exc)
        return result

    if response.status_code == 304:
        source.last_status = "304 – unverändert"
        source.save(update_fields=["last_checked_at", "last_status"])
        result.unchanged = True
        return result

    if response.status_code != 200:
        source.last_status = f"HTTP {response.status_code}"
        source.save(update_fields=["last_checked_at", "last_status"])
        result.error = f"HTTP {response.status_code}"
        return result

    content = response.content[: MAX_DOWNLOAD_BYTES + 1]
    if len(content) > MAX_DOWNLOAD_BYTES:
        source.last_status = "Datei zu groß"
        source.save(update_fields=["last_checked_at", "last_status"])
        result.error = "Datei überschreitet das Größenlimit."
        return result

    sha256 = hashlib.sha256(content).hexdigest()
    if sha256 == source.last_sha256 and not force:
        source.last_status = "200 – Prüfsumme unverändert"
        source.save(update_fields=["last_checked_at", "last_status"])
        result.unchanged = True
        return result

    existing = SourceDocument.objects.filter(sha256=sha256).first()
    if existing:
        source.last_sha256 = sha256
        source.last_status = "200 – Dokument bereits archiviert"
        source.save(update_fields=["last_checked_at", "last_status", "last_sha256"])
        result.unchanged = True
        return result

    # Archive the new version, mark previous ones as superseded.
    SourceDocument.objects.filter(data_source=source, status=DocumentStatus.ACTIVE).update(
        status=DocumentStatus.SUPERSEDED
    )
    document = SourceDocument(
        data_source=source,
        sha256=sha256,
        size_bytes=len(content),
        content_type=response.headers.get("Content-Type", ""),
        etag=response.headers.get("ETag", ""),
        last_modified_header=response.headers.get("Last-Modified", ""),
        fetched_at=timezone.now(),
    )
    filename = f"{source.waste_type.slug}-{timezone.now():%Y%m%d-%H%M%S}.pdf"
    document.file.save(filename, ContentFile(content), save=False)
    document.save()

    source.last_etag = document.etag
    source.last_modified_header = document.last_modified_header
    source.last_sha256 = sha256
    source.last_status = "200 – neue Version archiviert"
    source.save()

    logger.info("Neue Quelldatei archiviert: %s (%s Bytes)", filename, len(content))
    result.new_document = document
    return result


def archive_local_file(path: str, source: DataSource) -> SourceDocument:
    """Archive a locally provided file (manual import / tests)."""
    with open(path, "rb") as handle:
        content = handle.read()
    sha256 = hashlib.sha256(content).hexdigest()
    existing = SourceDocument.objects.filter(sha256=sha256).first()
    if existing:
        return existing
    document = SourceDocument(
        data_source=source,
        sha256=sha256,
        size_bytes=len(content),
        content_type="application/pdf",
        fetched_at=timezone.now(),
    )
    filename = f"{source.waste_type.slug}-manuell-{timezone.now():%Y%m%d-%H%M%S}.pdf"
    document.file.save(filename, ContentFile(content), save=False)
    document.save()
    return document

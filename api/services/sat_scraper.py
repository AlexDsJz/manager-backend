import io
import csv
import json
import logging
import time
import unicodedata
import zipfile
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import chardet
import requests
from bs4 import BeautifulSoup
from django.db import connection
from django.utils import timezone

from api.models.sat.import_batch import SATImportBatch

logger = logging.getLogger(__name__)

SAT_BASE_URL = "http://omawww.sat.gob.mx"
SAT_PAGE_URL = (
    "http://omawww.sat.gob.mx/cifras_sat/Paginas/DatosAbiertos/contribuyentes_publicados.html"
)
DOWNLOAD_TIMEOUT = 120

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9",
}

COLUMN_MAP = {
    'rfc': 'rfc',
    'nombre': 'name',
    'razon social': 'name',
    'denominacion o razon social': 'name',
    'tipo de persona': 'person_type',
    'tipo persona': 'person_type',
    'supuesto': 'assumption',
    'numero de credito': 'credit_number',
    'num credito': 'credit_number',
    'monto del credito': 'amount',
    'monto': 'amount',
    'entidad federativa': 'state',
    'entidad': 'state',
}


_DOWNLOAD_EXTENSIONS = ('.zip', '.csv', '.txt')
_CANCEL_KEYWORDS = ('cancelado', 'cancel', 'baja', 'lista69', 'lista_69', 'listcompleta69', 'l_69')


def _find_download_url(page_url: str) -> str:
    response = requests.get(page_url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'lxml')
    all_links = [(tag.get_text(strip=True), tag['href']) for tag in soup.find_all('a', href=True)]

    logger.debug("Links found on %s: %s", page_url, all_links)

    def resolve(href: str) -> str:
        return href if href.startswith('http') else urljoin(SAT_BASE_URL, href)

    # Pass 1: link text mentions cancelado/cancela (original logic)
    for text, href in all_links:
        if 'cancelado' in text.lower() or 'cancela' in text.lower():
            return resolve(href)

    # Pass 2: href contains a cancel-related keyword AND has a download extension
    for _, href in all_links:
        href_lower = href.lower()
        if any(kw in href_lower for kw in _CANCEL_KEYWORDS) and any(href_lower.endswith(ext) for ext in _DOWNLOAD_EXTENSIONS):
            return resolve(href)

    # Pass 3: any downloadable file whose href contains a cancel-related keyword (no extension filter)
    for _, href in all_links:
        href_lower = href.lower()
        if any(kw in href_lower for kw in _CANCEL_KEYWORDS):
            return resolve(href)

    # Pass 4: any downloadable file on the same SAT domain (last resort)
    for _, href in all_links:
        href_lower = href.lower()
        if any(href_lower.endswith(ext) for ext in _DOWNLOAD_EXTENSIONS):
            full = resolve(href)
            if 'sat.gob.mx' in full:
                return full

    logger.error(
        "Could not find a download link on %s. All links found:\n%s",
        page_url,
        "\n".join(f"  [{text!r}] -> {href}" for text, href in all_links),
    )
    raise ValueError(f"No download link for 'Cancelados' found on {page_url}")


def _download(url: str) -> bytes:
    logger.info("Downloading from %s", url)
    chunks = []
    with requests.get(url, headers=REQUEST_HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                chunks.append(chunk)
    data = b''.join(chunks)
    logger.info("Downloaded %.2f MB", len(data) / (1024 * 1024))
    return data


def _get_csv_bytes(data: bytes) -> bytes:
    if data[:4] == b'PK\x03\x04':
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                if name.lower().endswith(('.csv', '.txt')):
                    logger.info("Extracting '%s' from ZIP", name)
                    return zf.read(name)
        raise ValueError("No CSV or TXT file found inside the ZIP.")
    return data


def _safe_decimal(value: str):
    cleaned = value.strip().replace(',', '')
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _normalize_col(s: str) -> str:
    """Lowercase + strip accents so 'Razón Social' matches 'razon social'."""
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _pg_escape(s: str) -> str:
    """Escape a string value for PostgreSQL text COPY format."""
    return s.replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n').replace('\r', '\\r')


def _bulk_insert(csv_bytes: bytes, batch: SATImportBatch) -> int:
    encoding = chardet.detect(csv_bytes[:10_000]).get('encoding') or 'utf-8'
    text = csv_bytes.decode(encoding, errors='replace')

    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=',|\t;')
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)

    buf = io.StringIO()
    total = 0

    for row in reader:
        if not any(v and v.strip() for v in row.values() if v is not None):
            continue

        mapped = {}
        extra = {}
        for col, val in row.items():
            if col is None:
                continue
            field = COLUMN_MAP.get(_normalize_col(col.strip()))
            if field:
                mapped[field] = (val or '').strip()
            else:
                extra[col] = val

        amount = _safe_decimal(mapped.get('amount', ''))

        buf.write('\t'.join([
            _pg_escape(str(batch.pk)),
            _pg_escape(mapped.get('rfc', '')),
            _pg_escape(mapped.get('name', '')),
            _pg_escape(mapped.get('person_type', '')),
            _pg_escape(mapped.get('assumption', '')),
            _pg_escape(mapped.get('credit_number', '')),
            '\\N' if amount is None else str(amount),
            _pg_escape(mapped.get('state', '')),
            _pg_escape(json.dumps(extra, ensure_ascii=False)),
        ]) + '\n')
        total += 1

    logger.info("Parsed %d rows, starting COPY", total)
    buf.seek(0)

    with connection.cursor() as cursor:
        cursor.copy_expert(
            "COPY sat_canceled_taxpayers "
            "(batch_id, rfc, name, person_type, assumption, credit_number, amount, state, extra_data) "
            "FROM STDIN",
            buf,
        )

    return total


def run_import(batch: SATImportBatch) -> None:
    start = time.perf_counter()
    batch.status = SATImportBatch.Status.RUNNING
    batch.save(update_fields=['status'])

    try:
        url = _find_download_url(batch.source_url)
        raw = _download(url)
        csv_bytes = _get_csv_bytes(raw)
        total = _bulk_insert(csv_bytes, batch)

        elapsed = time.perf_counter() - start
        batch.status = SATImportBatch.Status.SUCCESS
        batch.finished_at = timezone.now()
        batch.records_imported = total
        batch.execution_seconds = round(elapsed, 3)
        batch.save(update_fields=['status', 'finished_at', 'records_imported', 'execution_seconds'])

        logger.info("Import #%d done: %d records in %.2fs", batch.pk, total, elapsed)

    except Exception as exc:
        elapsed = time.perf_counter() - start
        logger.exception("Import #%d failed: %s", batch.pk, exc)
        batch.status = SATImportBatch.Status.FAILED
        batch.finished_at = timezone.now()
        batch.execution_seconds = round(elapsed, 3)
        batch.error_message = str(exc)
        batch.save(update_fields=['status', 'finished_at', 'execution_seconds', 'error_message'])
        raise

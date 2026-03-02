import io
import csv
import logging
import time
import zipfile
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

import chardet
import requests
from bs4 import BeautifulSoup
from django.utils import timezone

from api.models.sat.import_batch import SATImportBatch
from api.models.sat.canceled_taxpayer import CanceledTaxpayer

logger = logging.getLogger(__name__)

SAT_BASE_URL = "http://omawww.sat.gob.mx"
SAT_PAGE_URL = (
    "http://omawww.sat.gob.mx/cifras_sat/paginas/datos/vinculo.html"
    "?page=ListCompleta69.html"
)
BULK_BATCH_SIZE = 1000
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


def _find_download_url(page_url: str) -> str:
    response = requests.get(page_url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'lxml')

    for tag in soup.find_all('a', href=True):
        if 'cancelado' in tag.get_text(strip=True).lower():
            href = tag['href']
            return href if href.startswith('http') else urljoin(SAT_BASE_URL, href)

    for tag in soup.find_all('a', href=True):
        href = tag['href'].lower()
        if 'cancel' in href and any(href.endswith(ext) for ext in ('.zip', '.csv', '.txt')):
            full = tag['href']
            return full if full.startswith('http') else urljoin(SAT_BASE_URL, full)

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


def _bulk_insert(csv_bytes: bytes, batch: SATImportBatch) -> int:
    encoding = chardet.detect(csv_bytes[:10_000]).get('encoding') or 'utf-8'
    text = csv_bytes.decode(encoding, errors='replace')

    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=',|\t;')
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    records = []
    total = 0

    for row in reader:
        if not any(v.strip() for v in row.values()):
            continue

        mapped = {}
        extra = {}
        for col, val in row.items():
            field = COLUMN_MAP.get(col.strip().lower())
            if field:
                mapped[field] = val.strip()
            else:
                extra[col] = val

        records.append(CanceledTaxpayer(
            batch=batch,
            rfc=mapped.get('rfc', ''),
            name=mapped.get('name', ''),
            person_type=mapped.get('person_type', ''),
            assumption=mapped.get('assumption', ''),
            credit_number=mapped.get('credit_number', ''),
            amount=_safe_decimal(mapped.get('amount', '')),
            state=mapped.get('state', ''),
            extra_data=extra,
        ))

        if len(records) >= BULK_BATCH_SIZE:
            CanceledTaxpayer.objects.bulk_create(records, ignore_conflicts=True)
            total += len(records)
            records = []
            logger.debug("Inserted batch, total so far: %d", total)

    if records:
        CanceledTaxpayer.objects.bulk_create(records, ignore_conflicts=True)
        total += len(records)

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

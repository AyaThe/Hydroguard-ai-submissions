"""HTTP helper with timeouts, retries, response checks, and retrieval manifests."""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import HTTP_RETRIES, HTTP_RETRY_BACKOFF_SECONDS, HTTP_TIMEOUT_SECONDS, USER_AGENT

LOGGER = logging.getLogger(__name__)


class HttpError(RuntimeError):
    """Raised when an HTTP download cannot be completed safely."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def manifest_path(destination: Path) -> Path:
    return destination.with_name(destination.name + ".manifest.json")


def load_manifest(destination: Path) -> dict[str, Any] | None:
    path = manifest_path(destination)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(destination: Path, payload: dict[str, Any]) -> None:
    path = manifest_path(destination)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_is_fresh(destination: Path) -> bool:
    if not destination.exists() or destination.stat().st_size == 0:
        return False
    return manifest_path(destination).exists()


def request_bytes(
    url: str,
    *,
    params: dict[str, str] | None = None,
    timeout: int = HTTP_TIMEOUT_SECONDS,
    expected_status: int = 200,
    min_bytes: int = 32,
) -> tuple[bytes, str, int]:
    if params:
        query = urllib.parse.urlencode(params)
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{query}"

    last_error: Exception | None = None
    for attempt in range(1, HTTP_RETRIES + 1):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = int(response.status)
                content_type = response.headers.get("Content-Type", "")
                body = response.read()
            if status != expected_status:
                raise HttpError(f"Unexpected HTTP {status} for {url}")
            if len(body) < min_bytes:
                raise HttpError(f"Response too small ({len(body)} bytes) for {url}")
            return body, content_type, status
        except (urllib.error.URLError, TimeoutError, HttpError) as exc:
            last_error = exc
            LOGGER.warning("Attempt %s/%s failed for %s: %s", attempt, HTTP_RETRIES, url, exc)
            if attempt < HTTP_RETRIES:
                time.sleep(HTTP_RETRY_BACKOFF_SECONDS * attempt)

    raise HttpError(f"Failed to download {url}: {last_error}") from last_error


def download_file(
    url: str,
    destination: Path,
    *,
    params: dict[str, str] | None = None,
    source_name: str,
    expected_content_substrings: tuple[str, ...] = (),
    skip_if_cached: bool = True,
    binary: bool = False,
) -> Path:
    """Download a URL to destination. Existing raw files are never overwritten."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if skip_if_cached and cache_is_fresh(destination):
        LOGGER.info("Cache hit: %s", destination)
        return destination
    if destination.exists():
        LOGGER.info("Raw file already exists, not overwriting: %s", destination)
        return destination

    body: bytes | None = None
    content_type = ""
    status = 0
    last_error: Exception | None = None
    for attempt in range(1, HTTP_RETRIES + 1):
        body, content_type, status = request_bytes(url, params=params)
        if expected_content_substrings:
            haystack = (
                content_type.lower()
                + " "
                + body[:8192].decode("utf-8", errors="replace").lower()
            )
            if not any(token.lower() in haystack for token in expected_content_substrings):
                last_error = HttpError(
                    f"Unexpected content type {content_type!r} for {url}; "
                    f"expected one of {expected_content_substrings}"
                )
                LOGGER.warning(
                    "Attempt %s/%s: unexpected body for %s (%s bytes)",
                    attempt,
                    HTTP_RETRIES,
                    destination.name,
                    len(body),
                )
                if attempt < HTTP_RETRIES:
                    time.sleep(HTTP_RETRY_BACKOFF_SECONDS * attempt)
                    continue
                raise last_error
        last_error = None
        break
    if body is None:
        raise HttpError(f"Failed to download {url}: {last_error}")

    tmp_path = destination.with_suffix(destination.suffix + ".partial")
    tmp_path.write_bytes(body)
    tmp_path.replace(destination)

    write_manifest(
        destination,
        {
            "source_name": source_name,
            "source_url": url if not params else f"{url}?{urllib.parse.urlencode(params)}",
            "retrieved_at_utc": utc_now_iso(),
            "http_status": status,
            "content_type": content_type,
            "bytes": len(body),
            "sha256": file_sha256(destination),
            "binary": binary,
        },
    )
    LOGGER.info("Saved %s (%s bytes) from %s", destination.name, len(body), source_name)
    return destination

import logging
import re
import unicodedata
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from . import config

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10
HEADERS = {"User-Agent": "FIAP-TechChallenge5-SDR-ETL/1.0 (educational POC; no contact configured)"}
MAX_PROSE_PARAGRAPHS = 3
MAX_DOCUMENT_CHARS = 4000
MAX_METADATA_VALUE_CHARS = 200

_region_index_cache: dict[str, str] | None = None


def _strip_reference_markers(soup_fragment) -> None:
    for sup in soup_fragment.select("sup.reference"):
        sup.decompose()


def _fetch_region_index() -> dict[str, str]:
    response = requests.get(config.WIKIPEDIA_REGION_URL, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    index: dict[str, str] = {}
    for link in soup.select("#mw-content-text a[href*='/wiki/']"):
        href = link.get("href", "")
        tail = href.split("/wiki/")[-1]
        if not tail or ":" in tail:
            continue
        text = link.get_text(strip=True)
        if not text:
            continue
        index[text] = href if href.startswith("http") else "https://pt.wikipedia.org" + href

    return index


def resolve_city_url(city: str) -> str:
    global _region_index_cache
    if _region_index_cache is None:
        _region_index_cache = _fetch_region_index()

    url = _region_index_cache.get(city)
    if url:
        return url

    slug = quote(city.replace(" ", "_"))
    return f"https://pt.wikipedia.org/wiki/{slug}"


def _slugify_label(label: str) -> str:
    normalized = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "_", normalized).strip("_").lower()


def scrape_city_geo(city: str) -> dict:
    url = resolve_city_url(city)
    logger.info("Scraping Wikipedia geo data for %s (%s)", city, url)
    response = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    _strip_reference_markers(soup)

    infobox: dict[str, str] = {}
    table = soup.select_one("table.infobox")
    if table:
        for row in table.select("tr"):
            header, value = row.find("th"), row.find("td")
            if header is None or value is None:
                continue
            label, text = header.get_text(" ", strip=True), value.get_text(" ", strip=True)
            if label and text:
                infobox[label] = text

    paragraphs = []
    for p in soup.select("#mw-content-text p"):
        text = p.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)
        if len(paragraphs) >= MAX_PROSE_PARAGRAPHS:
            break

    document = f"{city}: {' '.join(paragraphs)}".strip()[:MAX_DOCUMENT_CHARS]

    metadata = {"city": city, "wikipedia_url": url}
    for label, value in infobox.items():
        key = _slugify_label(label)
        if key:
            metadata[key] = value[:MAX_METADATA_VALUE_CHARS]

    return {"document": document, "metadata": metadata}

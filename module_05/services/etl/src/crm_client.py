import logging

import requests

from . import config

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 5
PAGE_LIMIT = 100


class CrmUnavailableError(Exception):
    pass


def fetch_available_listings() -> list[dict]:
    listings: list[dict] = []
    offset = 0
    while True:
        try:
            response = requests.get(
                f"{config.CRM_INTERNAL_URL}/properties",
                params={"status": "available", "offset": offset, "limit": PAGE_LIMIT},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CrmUnavailableError(str(exc)) from exc

        page = response.json()
        listings.extend(page)
        if len(page) < PAGE_LIMIT:
            break
        offset += PAGE_LIMIT

    logger.info("Fetched %d available listing(s) from CRM", len(listings))
    return listings

import requests

import config

TIMEOUT_SECONDS = 5


class CrmUnavailableError(Exception):
    pass


def list_properties(**filters) -> list[dict]:
    try:
        response = requests.get(
            f"{config.CRM_INTERNAL_URL}/properties",
            params={k: v for k, v in filters.items() if v is not None},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise CrmUnavailableError(str(exc)) from exc


def get_property(listing_id: int) -> dict | None:
    try:
        response = requests.get(
            f"{config.CRM_INTERNAL_URL}/properties/{listing_id}",
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise CrmUnavailableError(str(exc)) from exc


def photo_url(relative_path: str) -> str:
    return f"{config.CRM_PUBLIC_URL}/static/photos/{relative_path}"

import itertools
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generate_listings import generate_listings  # noqa: E402

from src import config  # noqa: E402
from src.database import connection_scope  # noqa: E402

SEED_LEADS = [
    ("Marina Souza", "marina.souza@example.com"),
    ("Rafael Lima", "rafael.lima@example.com"),
    ("Beatriz Alves", "beatriz.alves@example.com"),
    ("Thiago Ramos", "thiago.ramos@example.com"),
    ("Camila Ferreira", "camila.ferreira@example.com"),
    ("Lucas Martins", "lucas.martins@example.com"),
    ("Juliana Rocha", "juliana.rocha@example.com"),
]
SEED_CHANNELS = ["website", "website", "telegram"]
SEED_HOURS = [9, 10, 11, 14, 15, 16, 17]


def _pick_visit_targets(listings: list[dict]) -> tuple[list[tuple[int, dict]], list[tuple[int, dict]]]:
    numbered = list(enumerate(listings, start=1))
    closed = [(listing_id, listing) for listing_id, listing in numbered if listing["status"] != "available"]

    open_ads = []
    for listing_type in ("sale", "rent"):
        for listing_id, listing in numbered:
            if listing["status"] == "available" and listing["listing_type"] == listing_type:
                open_ads.append((listing_id, listing))
                break

    return closed, open_ads


def _insert_visit(conn, listing_id: int, when: datetime, lead: tuple[str, str], channel: str) -> None:
    lead_name, lead_contact = lead
    when_iso = when.isoformat()
    conn.execute(
        """
        INSERT INTO visits (
            property_id, conversation_id, lead_name, lead_contact, channel,
            requested_datetime, confirmed_datetime, broker_name, broker_contact,
            status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
        """,
        (
            listing_id,
            f"seed-{listing_id}",
            lead_name,
            lead_contact,
            channel,
            when_iso,
            when_iso,
            config.BROKER_NAME,
            config.BROKER_CONTACT,
            datetime.now().isoformat(),
        ),
    )


def _seed_visits(conn, listings: list[dict]) -> int:
    closed, open_ads = _pick_visit_targets(listings)
    leads = itertools.cycle(SEED_LEADS)
    channels = itertools.cycle(SEED_CHANNELS)
    hours = itertools.cycle(SEED_HOURS)
    now = datetime.now()

    for days_ago, (listing_id, _listing) in zip(range(3, 3 + 2 * len(closed), 2), closed):
        when = (now - timedelta(days=days_ago)).replace(hour=next(hours), minute=0, second=0, microsecond=0)
        _insert_visit(conn, listing_id, when, next(leads), next(channels))

    for days_ahead, (listing_id, _listing) in zip(range(4, 4 + 5 * len(open_ads), 5), open_ads):
        when = (now + timedelta(days=days_ahead)).replace(hour=next(hours), minute=0, second=0, microsecond=0)
        _insert_visit(conn, listing_id, when, next(leads), next(channels))

    return len(closed) + len(open_ads)


def _copy_photos(listing_id: int, source_paths: list[Path]) -> list[str]:
    dest_dir = config.STATIC_PHOTOS_DIR / str(listing_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    relative_paths = []
    for index, source_path in enumerate(source_paths):
        dest_path = dest_dir / f"{index}{source_path.suffix}"
        shutil.copyfile(source_path, dest_path)
        relative_paths.append(f"{listing_id}/{dest_path.name}")
    return relative_paths


def seed() -> None:
    listings = generate_listings()

    shutil.rmtree(config.STATIC_PHOTOS_DIR, ignore_errors=True)
    config.STATIC_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

    with connection_scope() as conn:
        conn.execute("DELETE FROM visits")
        conn.execute("DELETE FROM listing_photos")
        conn.execute("DELETE FROM listings")
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('listings', 'listing_photos', 'visits')")
        for listing_id, listing in enumerate(listings, start=1):
            conn.execute(
                """
                INSERT INTO listings (
                    id, listing_type, city, neighborhood, property_type, price, rooms,
                    area_sqm, lease_duration_months, available_from, description,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing_id,
                    listing["listing_type"],
                    listing["city"],
                    listing["neighborhood"],
                    listing["property_type"],
                    listing["price"],
                    listing["rooms"],
                    listing["area_sqm"],
                    listing["lease_duration_months"],
                    listing["available_from"],
                    listing["description"],
                    listing["status"],
                    listing["created_at"],
                    listing["updated_at"],
                ),
            )
            relative_paths = _copy_photos(listing_id, listing["photo_paths"])
            for order_index, relative_path in enumerate(relative_paths):
                conn.execute(
                    "INSERT INTO listing_photos (listing_id, file_path, sort_order) VALUES (?, ?, ?)",
                    (listing_id, relative_path, order_index),
                )

        visit_count = _seed_visits(conn, listings)

    print(f"Seeded {len(listings)} listings and {visit_count} visits.")


if __name__ == "__main__":
    seed()

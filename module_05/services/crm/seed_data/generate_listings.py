import json
import random
from datetime import datetime, timedelta
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent / "raw"

CITIES = {
    "São José dos Campos": "urban",
    "Taubaté": "urban",
    "Guaratinguetá": "urban",
    "Pindamonhangaba": "urban",
    "Jacareí": "urban",
    "Caçapava": "urban",
    "Lorena": "urban",
    "Cruzeiro": "urban",
    "Campos do Jordão": "mountain",
    "Cunha": "mountain",
    "São Bento do Sapucaí": "mountain",
    "Monteiro Lobato": "mountain",
    "São Luiz do Paraitinga": "mountain",
    "Ubatuba": "coastal",
    "Caraguatatuba": "coastal",
    "São Sebastião": "coastal",
    "Ilhabela": "coastal",
}

NEIGHBORHOODS_BY_ARCHETYPE = {
    "urban": ["Centro", "Jardim Europa", "Vila Nova"],
    "mountain": ["Centro", "Alto da Serra", "Recanto Verde"],
    "coastal": ["Centro", "Praia Grande", "Enseada"],
}

PROPERTY_TYPES = ["apartment", "house"]

PRICE_RANGE_BY_TYPE_AND_ARCHETYPE = {
    ("apartment", "urban"): (220_000, 550_000),
    ("apartment", "mountain"): (280_000, 650_000),
    ("apartment", "coastal"): (300_000, 750_000),
    ("house", "urban"): (350_000, 800_000),
    ("house", "mountain"): (450_000, 1_100_000),
    ("house", "coastal"): (500_000, 1_300_000),
}

MONTHLY_RENT_RATIO = 0.006
LISTINGS_PER_CITY = 4
MAX_PHOTOS_PER_LISTING = 3

random.seed(42)


def _load_descriptions(category: str) -> list[str]:
    path = RAW_DIR / "descriptions" / f"{category}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_photo_paths(category: str) -> list[Path]:
    photo_dir = RAW_DIR / "photos" / category
    return sorted(photo_dir.glob("*"))


def generate_listings() -> list[dict]:
    listings = []
    now = datetime.now().isoformat()

    for city, archetype in CITIES.items():
        neighborhood_by_property_type = {
            property_type: random.choice(NEIGHBORHOODS_BY_ARCHETYPE[archetype])
            for property_type in PROPERTY_TYPES
        }

        for i in range(LISTINGS_PER_CITY):
            property_type = PROPERTY_TYPES[i % len(PROPERTY_TYPES)]
            listing_type = "sale" if (i // len(PROPERTY_TYPES)) % 2 == 0 else "rent"
            category = f"{property_type}_{archetype}"

            neighborhood = neighborhood_by_property_type[property_type]
            rooms = random.randint(1, 4)
            area_sqm = round(30 + rooms * random.uniform(15, 25), 1)

            low, high = PRICE_RANGE_BY_TYPE_AND_ARCHETYPE[(property_type, archetype)]
            sale_price = round(random.uniform(low, high), -3)
            price = sale_price if listing_type == "sale" else round(sale_price * MONTHLY_RENT_RATIO, -1)

            status = "available"
            roll = random.random()
            if listing_type == "sale" and roll < 0.1:
                status = "sold"
            elif listing_type == "rent" and roll < 0.1:
                status = "rented"

            lease_duration_months = random.choice([12, 24, 36]) if listing_type == "rent" else None
            available_from = (
                (datetime.now() + timedelta(days=random.randint(0, 60))).date().isoformat()
                if listing_type == "rent"
                else None
            )

            description = random.choice(_load_descriptions(category))
            photo_paths = _load_photo_paths(category)
            sample_size = min(MAX_PHOTOS_PER_LISTING, len(photo_paths))
            chosen_photos = random.sample(photo_paths, sample_size) if photo_paths else []

            listings.append(
                {
                    "listing_type": listing_type,
                    "city": city,
                    "neighborhood": neighborhood,
                    "property_type": property_type,
                    "price": price,
                    "rooms": rooms,
                    "area_sqm": area_sqm,
                    "lease_duration_months": lease_duration_months,
                    "available_from": available_from,
                    "description": description,
                    "status": status,
                    "created_at": now,
                    "updated_at": now,
                    "photo_paths": chosen_photos,
                }
            )

    return listings

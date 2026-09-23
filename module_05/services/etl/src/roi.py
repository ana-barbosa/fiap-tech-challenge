from collections import defaultdict


def segment_key(city: str, neighborhood: str, property_type: str) -> str:
    return f"{city}|{neighborhood}|{property_type}"


def compute_roi_segments(listings: list[dict], segment_keys: set[str] | None = None) -> dict[str, dict | None]:
    sale_prices: dict[str, list[float]] = defaultdict(list)
    rent_prices: dict[str, list[float]] = defaultdict(list)
    labels: dict[str, tuple[str, str, str]] = {}

    for listing in listings:
        key = segment_key(listing["city"], listing["neighborhood"], listing["property_type"])
        labels[key] = (listing["city"], listing["neighborhood"], listing["property_type"])
        if listing["listing_type"] == "sale":
            sale_prices[key].append(listing["price"])
        elif listing["listing_type"] == "rent":
            rent_prices[key].append(listing["price"])

    keys = segment_keys if segment_keys is not None else set(sale_prices) | set(rent_prices)

    results: dict[str, dict | None] = {}
    for key in keys:
        sales, rents = sale_prices.get(key, []), rent_prices.get(key, [])
        if not sales or not rents:
            results[key] = None
            continue

        avg_sale = sum(sales) / len(sales)
        avg_annual_rent = (sum(rents) / len(rents)) * 12
        city, neighborhood, property_type = labels[key]
        results[key] = {
            "city": city,
            "neighborhood": neighborhood,
            "property_type": property_type,
            "gross_yield": avg_annual_rent / avg_sale,
            "sale_sample_size": len(sales),
            "rent_sample_size": len(rents),
        }

    return results

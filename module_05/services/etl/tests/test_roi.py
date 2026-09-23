from src import roi


def _listing(city, neighborhood, property_type, listing_type, price):
    return {
        "city": city,
        "neighborhood": neighborhood,
        "property_type": property_type,
        "listing_type": listing_type,
        "price": price,
    }


def test_computes_yield_for_paired_segment():
    listings = [
        _listing("Ubatuba", "Centro", "house", "sale", 500_000),
        _listing("Ubatuba", "Centro", "house", "rent", 2_500),
    ]
    result = roi.compute_roi_segments(listings)
    key = roi.segment_key("Ubatuba", "Centro", "house")
    assert result[key]["gross_yield"] == (2_500 * 12) / 500_000
    assert result[key]["sale_sample_size"] == 1
    assert result[key]["rent_sample_size"] == 1


def test_averages_across_multiple_listings_per_side():
    listings = [
        _listing("Ubatuba", "Centro", "house", "sale", 400_000),
        _listing("Ubatuba", "Centro", "house", "sale", 600_000),
        _listing("Ubatuba", "Centro", "house", "rent", 2_000),
        _listing("Ubatuba", "Centro", "house", "rent", 3_000),
    ]
    result = roi.compute_roi_segments(listings)
    key = roi.segment_key("Ubatuba", "Centro", "house")
    assert result[key]["gross_yield"] == (2_500 * 12) / 500_000
    assert result[key]["sale_sample_size"] == 2
    assert result[key]["rent_sample_size"] == 2


def test_segment_without_both_sides_is_none():
    listings = [_listing("Ubatuba", "Centro", "house", "sale", 500_000)]
    result = roi.compute_roi_segments(listings)
    key = roi.segment_key("Ubatuba", "Centro", "house")
    assert result[key] is None


def test_segment_keys_filter_restricts_output():
    listings = [
        _listing("Ubatuba", "Centro", "house", "sale", 500_000),
        _listing("Ubatuba", "Centro", "house", "rent", 2_500),
        _listing("Taubaté", "Centro", "apartment", "sale", 300_000),
        _listing("Taubaté", "Centro", "apartment", "rent", 1_800),
    ]
    only_key = roi.segment_key("Ubatuba", "Centro", "house")
    result = roi.compute_roi_segments(listings, segment_keys={only_key})
    assert set(result) == {only_key}


def test_unrequested_segment_with_no_matching_listings_is_none():
    key = roi.segment_key("Nowhere", "Centro", "house")
    result = roi.compute_roi_segments([], segment_keys={key})
    assert result[key] is None

CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_type TEXT NOT NULL CHECK (listing_type IN ('sale', 'rent')),
    city TEXT NOT NULL,
    neighborhood TEXT NOT NULL,
    property_type TEXT NOT NULL,
    price REAL NOT NULL,
    rooms INTEGER NOT NULL,
    area_sqm REAL NOT NULL,
    lease_duration_months INTEGER,
    available_from TEXT,
    description TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('available', 'sold', 'rented')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS listing_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    file_path TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_listings_filters ON listings (status, listing_type, city, property_type);
CREATE INDEX IF NOT EXISTS idx_listing_photos_listing_id ON listing_photos (listing_id);

CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES listings(id),
    conversation_id TEXT NOT NULL,
    lead_name TEXT NOT NULL,
    lead_contact TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'website',
    requested_datetime TEXT NOT NULL,
    confirmed_datetime TEXT NOT NULL,
    broker_name TEXT NOT NULL,
    broker_contact TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_visits_conversation_id ON visits (conversation_id);
CREATE INDEX IF NOT EXISTS idx_visits_property_id ON visits (property_id);

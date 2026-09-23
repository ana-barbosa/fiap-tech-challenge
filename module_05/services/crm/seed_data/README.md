# Seed data

`raw/photos/` and `raw/descriptions/` are currently placeholder content (generated locally, not scraped from real listings). They exist so the CRM can be seeded and the system run end-to-end today.

To swap in real content: replace the files in each `raw/photos/{property_type}_{archetype}/` folder with real photos, and the entries in each `raw/descriptions/{property_type}_{archetype}.json` with real description text, keeping the same folder/file naming convention. `generate_listings.py` reads from these pools; it doesn't care whether the content is real or placeholder.

`generate_listings.py` and `seed_crm.py` still author every listing's price, rooms, city, status and lease terms themselves — the raw pool only supplies photos and description text.

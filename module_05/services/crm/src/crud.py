import sqlite3
from datetime import datetime
from typing import Optional

from .models import ListingCreate, ListingUpdate, VisitCreate

ALLOWED_SORT_FIELDS = {"price", "created_at", "rooms", "area_sqm"}


def _now_iso() -> str:
    return datetime.now().isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def get_photos(conn: sqlite3.Connection, listing_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT file_path FROM listing_photos WHERE listing_id = ? ORDER BY sort_order",
        (listing_id,),
    ).fetchall()
    return [row["file_path"] for row in rows]


def list_listings(
    conn: sqlite3.Connection,
    *,
    listing_type: Optional[str] = None,
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    rooms: Optional[int] = None,
    status: str = "available",
    sort_by: str = "created_at",
    order: str = "desc",
    offset: int = 0,
    limit: int = 12,
) -> list[dict]:
    if sort_by not in ALLOWED_SORT_FIELDS:
        sort_by = "created_at"
    order = "asc" if order == "asc" else "desc"

    clauses = ["status = ?"]
    params: list = [status]

    if listing_type:
        clauses.append("listing_type = ?")
        params.append(listing_type)
    if city:
        clauses.append("city = ?")
        params.append(city)
    if property_type:
        clauses.append("property_type = ?")
        params.append(property_type)
    if min_price is not None:
        clauses.append("price >= ?")
        params.append(min_price)
    if max_price is not None:
        clauses.append("price <= ?")
        params.append(max_price)
    if rooms is not None:
        clauses.append("rooms >= ?")
        params.append(rooms)

    where = " AND ".join(clauses)
    query = f"SELECT * FROM listings WHERE {where} ORDER BY {sort_by} {order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    listings = [_row_to_dict(row) for row in rows]
    for listing in listings:
        listing["photos"] = get_photos(conn, listing["id"])
    return listings


def get_listing(conn: sqlite3.Connection, listing_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM listings WHERE id = ?", (listing_id,)).fetchone()
    if row is None:
        return None
    listing = _row_to_dict(row)
    listing["photos"] = get_photos(conn, listing_id)
    return listing


def create_listing(conn: sqlite3.Connection, data: ListingCreate) -> int:
    now = _now_iso()
    cursor = conn.execute(
        """
        INSERT INTO listings (
            listing_type, city, neighborhood, property_type, price, rooms,
            area_sqm, lease_duration_months, available_from, description,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.listing_type,
            data.city,
            data.neighborhood,
            data.property_type,
            data.price,
            data.rooms,
            data.area_sqm,
            data.lease_duration_months,
            data.available_from,
            data.description,
            data.status,
            now,
            now,
        ),
    )
    listing_id = cursor.lastrowid
    for order_index, file_path in enumerate(data.photos):
        conn.execute(
            "INSERT INTO listing_photos (listing_id, file_path, sort_order) VALUES (?, ?, ?)",
            (listing_id, file_path, order_index),
        )
    return listing_id


def update_listing(conn: sqlite3.Connection, listing_id: int, data: ListingUpdate) -> bool:
    fields = data.model_dump(exclude_unset=True)
    if get_listing(conn, listing_id) is None:
        return False
    if not fields:
        return True
    fields["updated_at"] = _now_iso()
    assignments = ", ".join(f"{key} = ?" for key in fields)
    params = list(fields.values()) + [listing_id]
    conn.execute(f"UPDATE listings SET {assignments} WHERE id = ?", params)
    return True


def create_visit(
    conn: sqlite3.Connection,
    data: VisitCreate,
    *,
    broker_name: str,
    broker_contact: str,
    confirmed_datetime: datetime,
) -> dict:
    cursor = conn.execute(
        """
        INSERT INTO visits (
            property_id, conversation_id, lead_name, lead_contact, channel,
            requested_datetime, confirmed_datetime, broker_name, broker_contact,
            status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', ?)
        """,
        (
            data.property_id,
            data.conversation_id,
            data.lead_name,
            data.lead_contact,
            data.channel,
            data.requested_datetime.isoformat(),
            confirmed_datetime.isoformat(),
            broker_name,
            broker_contact,
            _now_iso(),
        ),
    )
    row = conn.execute("SELECT * FROM visits WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_dict(row)


def list_visits(
    conn: sqlite3.Connection,
    *,
    conversation_id: Optional[str] = None,
    property_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[dict]:
    clauses = []
    params: list = []

    if conversation_id:
        clauses.append("conversation_id = ?")
        params.append(conversation_id)
    if property_id is not None:
        clauses.append("property_id = ?")
        params.append(property_id)
    if status:
        clauses.append("status = ?")
        params.append(status)

    query = "SELECT * FROM visits"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()
    return [_row_to_dict(row) for row in rows]

import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config, crud
from .database import connection_scope
from .models import ListingCreate, ListingOut, ListingUpdate, VisitCreate, VisitOut


class _HealthCheckLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(_HealthCheckLogFilter())

app = FastAPI(title="Dummy Real Estate CRM")

config.STATIC_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/photos", StaticFiles(directory=config.STATIC_PHOTOS_DIR), name="photos")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get("/health")
def health() -> dict:
    with connection_scope() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.get("/properties", response_model=list[ListingOut])
def list_properties(
    listing_type: Optional[str] = None,
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    rooms: Optional[int] = None,
    status: str = "available",
    sort_by: str = "created_at",
    order: str = "desc",
    offset: int = Query(0, ge=0),
    limit: int = Query(12, ge=1, le=100),
):
    with connection_scope() as conn:
        return crud.list_listings(
            conn,
            listing_type=listing_type,
            city=city,
            property_type=property_type,
            min_price=min_price,
            max_price=max_price,
            rooms=rooms,
            status=status,
            sort_by=sort_by,
            order=order,
            offset=offset,
            limit=limit,
        )


@app.get("/properties/{listing_id}", response_model=ListingOut)
def get_property(listing_id: int):
    with connection_scope() as conn:
        listing = crud.get_listing(conn, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return listing


@app.post("/properties", response_model=ListingOut, status_code=201)
def create_property(data: ListingCreate):
    with connection_scope() as conn:
        listing_id = crud.create_listing(conn, data)
        listing = crud.get_listing(conn, listing_id)
    return listing


@app.patch("/properties/{listing_id}", response_model=ListingOut)
def update_property(listing_id: int, data: ListingUpdate):
    with connection_scope() as conn:
        updated = crud.update_listing(conn, listing_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Property not found")
        listing = crud.get_listing(conn, listing_id)
    return listing


@app.post("/visits", response_model=VisitOut, status_code=201)
def create_visit(data: VisitCreate):
    if data.requested_datetime <= datetime.now():
        raise HTTPException(status_code=422, detail="requested_datetime must be in the future")

    with connection_scope() as conn:
        listing = crud.get_listing(conn, data.property_id)

        if listing is None:
            raise HTTPException(status_code=404, detail="Property not found")
        if listing["status"] != "available":
            raise HTTPException(status_code=409, detail="Property is not available for visits")

        visit = crud.create_visit(
            conn,
            data,
            broker_name=config.BROKER_NAME,
            broker_contact=config.BROKER_CONTACT,
            confirmed_datetime=data.requested_datetime,
        )

    return visit


@app.get("/visits", response_model=list[VisitOut])
def get_visits(
    conversation_id: Optional[str] = None,
    property_id: Optional[int] = None,
    status: Optional[str] = None,
):
    with connection_scope() as conn:
        return crud.list_visits(conn, conversation_id=conversation_id, property_id=property_id, status=status)

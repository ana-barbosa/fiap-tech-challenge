from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ListingType = Literal["sale", "rent"]
ListingStatus = Literal["available", "sold", "rented"]


class ListingOut(BaseModel):
    id: int
    listing_type: ListingType
    city: str
    neighborhood: str
    property_type: str
    price: float
    rooms: int
    area_sqm: float
    lease_duration_months: Optional[int] = None
    available_from: Optional[str] = None
    description: str
    status: ListingStatus
    created_at: str
    updated_at: str
    photos: list[str] = Field(default_factory=list)


class ListingCreate(BaseModel):
    listing_type: ListingType
    city: str
    neighborhood: str
    property_type: str
    price: float
    rooms: int
    area_sqm: float
    lease_duration_months: Optional[int] = None
    available_from: Optional[str] = None
    description: str
    status: ListingStatus = "available"
    photos: list[str] = Field(default_factory=list)


class ListingUpdate(BaseModel):
    price: Optional[float] = None
    status: Optional[ListingStatus] = None


class VisitCreate(BaseModel):
    property_id: int
    conversation_id: str = Field(min_length=1)
    lead_name: str = Field(min_length=1)
    lead_contact: str = Field(min_length=1)
    requested_datetime: datetime
    channel: str = "website"


class VisitOut(BaseModel):
    id: int
    property_id: int
    conversation_id: str
    lead_name: str
    lead_contact: str
    broker_name: str
    broker_contact: str
    confirmed_datetime: datetime
    status: Literal["confirmed"] = "confirmed"

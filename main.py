import os
from datetime import datetime, date, timedelta
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import db, create_document, get_documents

app = FastAPI(title="Boat Renting API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Models for API requests
# -----------------------------
class QuoteRequest(BaseModel):
    boat_id: str
    start_date: date
    end_date: date
    guests: int = Field(ge=1)
    extras: Dict[str, bool] = {}


class BookingRequest(BaseModel):
    boat_id: str
    start_date: date
    end_date: date
    guests: int = Field(ge=1)
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    extras: Dict[str, bool] = {}
    notes: Optional[str] = None


# -----------------------------
# Utility functions
# -----------------------------
EXTRA_PRICING = {
    "skipper": {"type": "per_day", "amount": 150.0},
    "fuel": {"type": "per_day", "amount": 80.0},
    "snorkel": {"type": "per_person_per_day", "amount": 20.0},
}


def date_range_days(start: date, end: date) -> int:
    days = (end - start).days
    if days < 1:
        raise HTTPException(status_code=400, detail="End date must be after start date by at least 1 day")
    return days


def get_boat_or_404(boat_id: str) -> dict:
    from bson import ObjectId

    try:
        oid = ObjectId(boat_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid boat_id")

    boat = db["boat"].find_one({"_id": oid})
    if not boat:
        raise HTTPException(status_code=404, detail="Boat not found")
    return boat


def compute_quote(boat: dict, start: date, end: date, guests: int, extras: Dict[str, bool]):
    days = date_range_days(start, end)

    base_daily = float(boat.get("base_price_per_day", 0))
    cleaning_fee = float(boat.get("cleaning_fee", 0.0))
    tax_rate = float(boat.get("tax_rate", 0.0))

    breakdown = {
        "nights": days,
        "base": round(base_daily * days, 2),
        "extras": {},
        "cleaning_fee": round(cleaning_fee, 2),
        "tax": 0.0,
        "total": 0.0,
        "currency": "USD",
        "transparent": True,
        "notes": "Prices include all fees and taxes. No hidden fees.",
    }

    extras_total = 0.0
    for key, enabled in (extras or {}).items():
        if not enabled:
            continue
        rule = EXTRA_PRICING.get(key)
        if not rule:
            continue
        if rule["type"] == "per_day":
            cost = rule["amount"] * days
        elif rule["type"] == "per_person_per_day":
            cost = rule["amount"] * guests * days
        else:
            cost = 0.0
        breakdown["extras"][key] = round(cost, 2)
        extras_total += cost

    subtotal = breakdown["base"] + extras_total + breakdown["cleaning_fee"]
    breakdown["tax"] = round(subtotal * tax_rate, 2)
    breakdown["total"] = round(subtotal + breakdown["tax"], 2)

    return breakdown


# -----------------------------
# Seed data on first run
# -----------------------------
@app.on_event("startup")
def seed_boats():
    try:
        if db is None:
            return
        count = db["boat"].count_documents({})
        if count == 0:
            sample_boats = [
                {
                    "name": "Aqua Breeze 32",
                    "type": "sailboat",
                    "capacity": 6,
                    "base_price_per_day": 420.0,
                    "location": "Marina Grande",
                    "images": [
                        "https://images.unsplash.com/photo-1505852679233-d9fd70aff56d?q=80&w=1600&auto=format&fit=crop",
                    ],
                    "description": "Elegant cruiser perfect for day sails and weekend getaways.",
                    "features": ["GPS", "Bluetooth Audio", "Bimini", "Fresh water shower"],
                    "tax_rate": 0.08,
                    "cleaning_fee": 35.0,
                },
                {
                    "name": "Sunset Whisper 45",
                    "type": "yacht",
                    "capacity": 10,
                    "base_price_per_day": 850.0,
                    "location": "Harbor Cove",
                    "images": [
                        "https://images.unsplash.com/photo-1502877338535-766e1452684a?q=80&w=1600&auto=format&fit=crop",
                    ],
                    "description": "Spacious comfort with refined finishes for premium charters.",
                    "features": ["Skylounge", "Air Conditioning", "Kitchenette", "Skipper ready"],
                    "tax_rate": 0.1,
                    "cleaning_fee": 60.0,
                },
                {
                    "name": "Sandline 24",
                    "type": "speedboat",
                    "capacity": 4,
                    "base_price_per_day": 260.0,
                    "location": "Pier 7",
                    "images": [
                        "https://images.unsplash.com/photo-1504367087812-9f34b82a0f05?q=80&w=1600&auto=format&fit=crop",
                    ],
                    "description": "Sporty and nimble for quick coastal hops and snorkeling.",
                    "features": ["Life vests", "Cooler", "Sun awning"],
                    "tax_rate": 0.07,
                    "cleaning_fee": 25.0,
                },
            ]
            db["boat"].insert_many(sample_boats)
    except Exception:
        # seeding is best-effort
        pass


# -----------------------------
# Basic endpoints
# -----------------------------
@app.get("/")
def root():
    return {"message": "Boat Renting API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# -----------------------------
# Boats
# -----------------------------
@app.get("/api/boats")
def list_boats():
    docs = get_documents("boat") if db is not None else []
    # convert ObjectId to str
    def to_public(doc):
        doc["id"] = str(doc.pop("_id"))
        return doc
    return [to_public(d) for d in docs]


@app.post("/api/boats")
def create_boat(boat: Dict):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    boat_id = create_document("boat", boat)
    return {"id": boat_id}


# -----------------------------
# Pricing / Quote
# -----------------------------
@app.post("/api/quote")
def quote(req: QuoteRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    boat = get_boat_or_404(req.boat_id)
    breakdown = compute_quote(boat, req.start_date, req.end_date, req.guests, req.extras)
    breakdown["boat_id"] = req.boat_id
    return breakdown


# -----------------------------
# Bookings
# -----------------------------
@app.post("/api/bookings")
def create_booking(req: BookingRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    boat = get_boat_or_404(req.boat_id)
    pricing = compute_quote(boat, req.start_date, req.end_date, req.guests, req.extras)

    booking_doc = {
        "boat_id": req.boat_id,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "guests": req.guests,
        "customer_name": req.customer_name,
        "customer_email": req.customer_email,
        "customer_phone": req.customer_phone,
        "extras": req.extras,
        "notes": req.notes,
        "pricing": pricing,
        "status": "requested",
        "created_at": datetime.utcnow().isoformat(),
    }

    booking_id = create_document("booking", booking_doc)
    return {"id": booking_id, "status": "requested", "pricing": pricing}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Boat rental platform schemas

class Boat(BaseModel):
    name: str = Field(..., description="Boat name")
    type: str = Field(..., description="Boat type, e.g., sailboat, yacht, speedboat")
    capacity: int = Field(..., ge=1, description="Max passengers")
    base_price_per_day: float = Field(..., ge=0, description="Base daily price in USD")
    location: str = Field(..., description="Harbor/Marina location")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    description: Optional[str] = Field(None, description="Boat description")
    features: List[str] = Field(default_factory=list, description="Key features")
    tax_rate: float = Field(0.07, ge=0, le=0.3, description="Applied tax rate")
    cleaning_fee: float = Field(0.0, ge=0, description="Optional one-time cleaning fee (visible)")

class Booking(BaseModel):
    boat_id: str = Field(..., description="ID of the boat")
    start_date: date = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (YYYY-MM-DD)")
    guests: int = Field(..., ge=1, description="Number of guests")
    customer_name: str = Field(..., description="Customer full name")
    customer_email: str = Field(..., description="Customer email")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    extras: Dict[str, bool] = Field(default_factory=dict, description="Selected extras (e.g., skipper, snorkel)")
    notes: Optional[str] = Field(None, description="Special requests")

# Add your own schemas here:
# --------------------------------------------------

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!

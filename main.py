import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Product as ProductSchema

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProductOut(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    price: float
    category: str
    in_stock: bool = True
    image: Optional[str] = None
    rating: Optional[float] = None


SAMPLE_PRODUCTS = [
    {
        "title": "Wireless Noise Cancelling Headphones",
        "description": "Over-ear Bluetooth headphones with 30h battery and ANC.",
        "price": 129.99,
        "category": "Electronics",
        "in_stock": True,
        "image": "https://images.unsplash.com/photo-1518443885661-7a08f0f64f32?q=80&w=1200&auto=format&fit=crop",
        "rating": 4.6,
    },
    {
        "title": "Stainless Steel Water Bottle",
        "description": "Insulated 32oz bottle keeps drinks cold for 24h.",
        "price": 24.95,
        "category": "Home",
        "in_stock": True,
        "image": "https://images.unsplash.com/photo-1517705008128-361805f42e86?q=80&w=1200&auto=format&fit=crop",
        "rating": 4.4,
    },
    {
        "title": "Ergonomic Office Chair",
        "description": "Adjustable lumbar support, breathable mesh back.",
        "price": 199.0,
        "category": "Furniture",
        "in_stock": True,
        "image": "https://images.unsplash.com/photo-1582582429416-cfecfc0a0bdf?q=80&w=1200&auto=format&fit=crop",
        "rating": 4.3,
    },
    {
        "title": "4K UHD Smart TV 55\"",
        "description": "Ultra HD, HDR, built-in streaming apps.",
        "price": 429.0,
        "category": "Electronics",
        "in_stock": True,
        "image": "https://images.unsplash.com/photo-1587300003388-59208cc962cb?q=80&w=1200&auto=format&fit=crop",
        "rating": 4.5,
    },
    {
        "title": "Non-Stick Cookware Set (10 pcs)",
        "description": "Durable, PFOA-free non-stick with glass lids.",
        "price": 89.99,
        "category": "Kitchen",
        "in_stock": True,
        "image": "https://images.unsplash.com/photo-1544025162-d76694265947?q=80&w=1200&auto=format&fit=crop",
        "rating": 4.2,
    },
    {
        "title": "Running Shoes",
        "description": "Lightweight, breathable, everyday trainers.",
        "price": 59.99,
        "category": "Fashion",
        "in_stock": True,
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1200&auto=format&fit=crop",
        "rating": 4.1,
    },
]


@app.get("/")
def read_root():
    return {"message": "Ecommerce backend running"}


@app.get("/api/products")
def list_products(category: Optional[str] = None, q: Optional[str] = None):
    """Return products from DB if available, otherwise sample data."""
    items: List[dict] = []
    try:
        docs = get_documents("product")
        for d in docs:
            d["id"] = str(d.get("_id"))
            items.append(d)
    except Exception:
        items = SAMPLE_PRODUCTS.copy()

    if category:
        items = [p for p in items if p.get("category", "").lower() == category.lower()]
    if q:
        ql = q.lower()
        items = [p for p in items if ql in p.get("title", "").lower() or ql in (p.get("description") or "").lower()]

    return {"items": items, "count": len(items)}


@app.get("/api/categories")
def list_categories():
    try:
        docs = get_documents("product")
        cats = sorted({d.get("category", "Misc") for d in docs})
        if not cats:
            raise Exception("empty")
        return {"items": cats}
    except Exception:
        return {"items": sorted({p["category"] for p in SAMPLE_PRODUCTS})}


@app.post("/api/seed")
def seed_products():
    """Seed database with sample products (idempotent-ish)."""
    if db is None:
        raise HTTPException(status_code=503, detail="Database not configured")
    existing = list(db["product"].find({}, {"title": 1}))
    existing_titles = {e.get("title") for e in existing}
    inserted = 0
    for p in SAMPLE_PRODUCTS:
        if p["title"] not in existing_titles:
            create_document("product", ProductSchema(**p))
            inserted += 1
    return {"inserted": inserted}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

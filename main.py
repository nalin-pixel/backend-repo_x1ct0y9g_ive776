import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Sneaker

app = FastAPI(title="Sneaker Store API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SneakerCreate(Sneaker):
    pass

class SneakerOut(BaseModel):
    id: str
    name: str
    brand: str
    price: float
    description: Optional[str] = None
    images: List[str] = []
    colors: List[str] = []
    sizes: List[float] = []
    category: str = "sneakers"
    in_stock: bool = True
    featured: bool = False
    rating: float = 4.5

    class Config:
        from_attributes = True


def serialize_doc(doc: dict) -> dict:
    doc["id"] = str(doc.get("_id"))
    doc.pop("_id", None)
    return doc

@app.get("/")
def read_root():
    return {"message": "Sneaker Store API running"}

@app.get("/test")
def test_database():
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
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
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

    return response

# Seed sample sneakers if empty
@app.post("/seed")
def seed_sneakers():
    try:
        count = db["sneaker"].count_documents({}) if db else 0
        if count > 0:
            return {"message": "Already seeded", "count": count}
        samples = [
            {
                "name": "Air Zoom Infinity",
                "brand": "Nike",
                "price": 149.99,
                "description": "Responsive cushioning for everyday runs.",
                "images": [
                    "https://images.unsplash.com/photo-1542293787938-c9e299b88054?q=80&w=1400&auto=format&fit=crop"
                ],
                "colors": ["black", "white", "volt"],
                "sizes": [7, 8, 9, 10, 11, 12],
                "featured": True,
                "rating": 4.7,
            },
            {
                "name": "Ultraboost 22",
                "brand": "Adidas",
                "price": 180.0,
                "description": "Energy return with a sock-like fit.",
                "images": [
                    "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?q=80&w=1400&auto=format&fit=crop"
                ],
                "colors": ["core black", "cloud white"],
                "sizes": [6, 7, 8, 9, 10, 11],
                "featured": True,
                "rating": 4.6,
            },
            {
                "name": "Classic Leather",
                "brand": "Reebok",
                "price": 75.0,
                "description": "A timeless streetwear staple.",
                "images": [
                    "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1400&auto=format&fit=crop"
                ],
                "colors": ["white"],
                "sizes": [5, 6, 7, 8, 9, 10],
                "featured": False,
                "rating": 4.4,
            },
        ]
        for s in samples:
            create_document("sneaker", s)
        return {"message": "Seeded", "count": len(samples)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sneakers", response_model=List[SneakerOut])
def list_sneakers(
    q: Optional[str] = Query(None, description="Search term for name or brand"),
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    featured: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100)
):
    try:
        filter_q = {}
        if q:
            filter_q["$or"] = [
                {"name": {"$regex": q, "$options": "i"}},
                {"brand": {"$regex": q, "$options": "i"}},
            ]
        if brand:
            filter_q["brand"] = {"$regex": f"^{brand}$", "$options": "i"}
        if min_price is not None or max_price is not None:
            price_filter = {}
            if min_price is not None:
                price_filter["$gte"] = min_price
            if max_price is not None:
                price_filter["$lte"] = max_price
            filter_q["price"] = price_filter
        if featured is not None:
            filter_q["featured"] = featured

        docs = get_documents("sneaker", filter_q, limit)
        return [SneakerOut(**serialize_doc(d)) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sneakers/{sneaker_id}", response_model=SneakerOut)
def get_sneaker(sneaker_id: str):
    try:
        if not ObjectId.is_valid(sneaker_id):
            raise HTTPException(status_code=400, detail="Invalid ID")
        doc = db["sneaker"].find_one({"_id": ObjectId(sneaker_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Sneaker not found")
        return SneakerOut(**serialize_doc(doc))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

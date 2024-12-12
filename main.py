from fastapi import FastAPI, HTTPException
from typing import List, Dict
from pymongo import MongoClient
from rapidfuzz import fuzz
import pandas as pd
from bson import ObjectId
import logging
from pydantic import BaseModel
import math

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# MongoDB Connection
MONGO_URI = "mongodb+srv://Avnish:Avnish1245@cluster0.jedujxw.mongodb.net/"
try:
    client = MongoClient(MONGO_URI)
    db = client.get_database("test")
    collection = db["products"]
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise HTTPException(status_code=500, detail="Database connection failed")

# Utility functions

def convert_objectid(obj):
    """Recursively converts ObjectId to string in MongoDB documents."""
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectid(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    else:
        return obj

def normalize_specifications(specs):
    """Normalizes specifications by converting keys and values to lowercase strings."""
    if isinstance(specs, dict):
        return {k.lower(): str(v).lower() for k, v in specs.items()}
    else:
        return {}

def sanitize_data(data):
    """Recursively sanitize data to ensure JSON compatibility."""
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, float):
        return data if math.isfinite(data) else None
    return data

# Load and preprocess data
data = list(collection.find({}))
data = [convert_objectid(doc) for doc in data] 
df = pd.DataFrame(data)
df["specifications"] = df["specifications"].apply(normalize_specifications)

# Pydantic model for input validation
class ProductSearchRequest(BaseModel):
    name: str
    type: str
    specifications: Dict[str, str]

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Product Matching API!",
        "usage": {
            "endpoint": "/match",
            "method": "POST",
            "input": {
                "name": "Product name (string)",
                "type": "Product type (string)",
                "specifications": "Desired specifications (dict)"
            },
            "example": {
                "request": {
                    "name": "HP 15",
                    "type": "laptop",
                    "specifications": {"brand": "HP", "color": "Black", "memory": "8GB"}
                },
                "response": "Matched products with match scores."
            }
        },
        "note": "Errors return a 500 status with details."
    }

# Matching logic
@app.post("/match", status_code=200)
def match_products(request: ProductSearchRequest):
    try:
        logger.info(f"Received match request: {request.dict()}")

        # Normalize user specifications
        user_specs = {k.lower(): str(v).lower() for k, v in request.specifications.items()}

        # Function to calculate match score
        def calculate_match_score(product_specs, user_specs):
            scores = [
                fuzz.ratio(str(product_specs.get(k, "")).lower(), v)
                for k, v in user_specs.items()
            ]
            return sum(scores) / len(scores) if scores else 0

        # Calculate match scores
        df["match_score"] = df["specifications"].apply(lambda specs: calculate_match_score(specs, user_specs))
        matched_products = df[df["match_score"] > 0].nlargest(5, "match_score").copy()

        # Convert matched products to JSON-compliant format and sanitize
        matched_products = matched_products.drop(columns=["_id"], errors="ignore")
        sanitized_products = sanitize_data(matched_products.to_dict(orient="records"))

        return {
            "input": request.dict(),
            "matched_products": sanitized_products
        }

    except KeyError as e:
        logger.error(f"KeyError: {e}")
        raise HTTPException(status_code=400, detail=f"Missing field in request: {e}")

    except Exception as e:
        logger.error(f"Error during product matching: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while matching products.")

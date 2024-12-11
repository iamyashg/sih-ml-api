from fastapi import FastAPI, HTTPException, Query
from typing import List
from pymongo import MongoClient
from rapidfuzz import fuzz
import pandas as pd
from bson import ObjectId
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

MONGO_URI = "mongodb+srv://Avnish:Avnish1245@cluster0.jedujxw.mongodb.net/"
client = MongoClient(MONGO_URI)
db = client.get_database("test")
collection = db["products"]

# MongoDB conversion functions
def convert_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectid(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    else:
        return obj

data = list(collection.find({}))
data = [convert_objectid(doc) for doc in data]

df = pd.DataFrame(data)

def normalize_specifications(specs):
    if isinstance(specs, dict):
        return {k.lower(): str(v).lower() for k, v in specs.items()}
    else:
        return {}

df["specifications"] = df["specifications"].apply(normalize_specifications)

# FastAPI route to find similar products
@app.get("/")
def read_root():
    return {"message": "Welcome to the Product Specification Matching API!"}

@app.get("/match", status_code=200)
def match_products(
    input: List[str] = Query(..., description="A list of key-value pairs representing desired specifications"),
    top_n: int = Query(5, ge=1, description="Number of top matches to return (default is 5, must be at least 1)")
):
    try:
        # Parse the user specifications from query parameters
        user_specs = {}
        for item in input:
            if ":" in item:
                key, value = item.split(":", 1)
                user_specs[key.strip().lower()] = value.strip().lower()

        # Matching logic to find similar products
        def calculate_match_score(product_specs, user_specs):
            scores = [
                fuzz.ratio(str(product_specs.get(k, "")).lower(), str(v).lower())
                for k, v in user_specs.items()
            ]
            return sum(scores) / len(scores) if scores else 0

        df["match_score"] = df["specifications"].apply(lambda specs: calculate_match_score(specs, user_specs))
        matched_products = df[df["match_score"] > 0].nlargest(top_n, "match_score").copy()

        # Return the matched products in a user-friendly format
        return {"input": input, "parsed_specs": user_specs, "matched_products": matched_products.to_dict(orient="records")}

    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred")

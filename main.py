from fastapi import FastAPI, HTTPException, Query
from typing import List
from pymongo import MongoClient
from rapidfuzz import fuzz
import pandas as pd
from bson import ObjectId
import logging
from pydantic import BaseModel

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


# Pydantic model for input validation
class ProductSearchRequest(BaseModel):
    name: str
    type: str
    specifications: dict


# FastAPI route to find similar products
@app.get("/")
def read_root():
    return {
        "message": "Welcome to the Product Specification Matching API! Here’s how to use the API:",
        "instructions": [
            "1. **GET /match**: This endpoint allows you to search for products based on your desired specifications.",
            "2. **JSON Input**:",
            "   - `name`: Name of the product (string).",
            "   - `type`: Type of the product (string).",
            "   - `specifications`: A dictionary of key-value pairs representing desired product specifications.",
            "     - Example: {\"brand\": \"Samsung\", \"color\": \"Black\", \"memory\": \"16GB\"}",
            "3. **Response**: The API will return the matched products along with their specifications and match scores.",
            "4. Example Usage:",
            "   - Request: `{\"name\": \"HP 15\", \"type\": \"laptop\", \"specifications\": {\"brand\": \"HP\", \"color\": \"Black\", \"memory\": \"8GB\"}}`",
            "   - Response: A list of products that match the given specifications, with their match scores.",
            "5. **Error Handling**: If there’s an issue with your request, you will receive an error message with a 500 status code."
        ]
    }


@app.get("/match", status_code=200)
def match_products(request: ProductSearchRequest):
    try:
        # Parse the user specifications from query parameters
        user_specs = {k.lower(): str(v).lower() for k, v in request.specifications.items()}


        # Matching logic to find similar products
        def calculate_match_score(product_specs, user_specs):
            scores = [
                fuzz.ratio(str(product_specs.get(k, "")).lower(), v)
                for k, v in user_specs.items()
            ]
            return sum(scores) / len(scores) if scores else 0

        df["match_score"] = df["specifications"].apply(lambda specs: calculate_match_score(specs, user_specs))
        matched_products = df[df["match_score"] > 0].nlargest(5, "match_score").copy()

        # Return the matched products in a user-friendly format
        return {
            "input": request.dict(),
            "matched_products": matched_products.to_dict(orient="records")
        }

    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred")

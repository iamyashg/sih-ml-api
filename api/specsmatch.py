from pymongo import MongoClient
from rapidfuzz import fuzz
import pandas as pd
from bson import ObjectId

# MongoDB connection string
MONGO_URI = "mongodb+srv://Avnish:Avnish1245@cluster0.jedujxw.mongodb.net/"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client.get_database("test")  # Replace with your database name
collection = db["products"]  # Replace with your collection name

# Function to convert ObjectId to string
def convert_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_objectid(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    else:
        return obj

# Fetch data from MongoDB and convert ObjectId to string
data = list(collection.find({}))
data = [convert_objectid(doc) for doc in data]

# Convert MongoDB data into a DataFrame
df = pd.DataFrame(data)

# Ensure specifications are flattened and normalized
def normalize_specifications(specs):
    if isinstance(specs, dict):
        return {k.lower(): str(v).lower() for k, v in specs.items()}
    else:
        return {}

# Normalize the specifications in the DataFrame
df["specifications"] = df["specifications"].apply(normalize_specifications)

# Function to find similar products based on user specifications
def find_similar_products(user_specs, top_n=5):
    def calculate_match_score(product_specs, user_specs):
        # Use rapidfuzz for partial matching
        scores = [
            fuzz.ratio(str(product_specs.get(k, "")).lower(), str(v).lower())
            for k, v in user_specs.items()
        ]
        return sum(scores) / len(scores) if scores else 0

    # Calculate match scores for all products
    df["match_score"] = df["specifications"].apply(lambda specs: calculate_match_score(specs, user_specs))

    # Filter and sort products by match score
    matched_products = df[df["match_score"] > 0].nlargest(top_n, "match_score").copy()

    # Return all columns of the matched products
    return matched_products

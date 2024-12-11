from fastapi import FastAPI, HTTPException, Query
from typing import List
from specsmatch import find_similar_products
import logging
import uvicorn

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
def read_root():
    """
    Root endpoint to confirm API is running and provide usage instructions.
    """
    return {
        "message": "Welcome to the Product Specification Matching API!",
        "usage": "To find similar products, use the '/match' endpoint with the following query parameters:",
        "parameters": {
            "input": "A list of key-value pairs representing the desired specifications (e.g., 'RAM:4GB').",
            "top_n": "Optional: Number of top matches to return (default is 5)."
        },
        "example": "/match?input=RAM:4GB&input=Storage:128GB&top_n=3"
    }

@app.get("/match", status_code=200)
def match_products(
    input: List[str] = Query(..., description="A list of key-value pairs representing desired specifications"),
    top_n: int = Query(5, ge=1, description="Number of top matches to return (default is 5, must be at least 1)"),
):
    """
    API endpoint to find similar products based on user input specifications.
    """
    try:
        logger.info(f"Received query: input={input}, top_n={top_n}")

        # Check if input is empty
        if not input:
            raise ValueError("Input cannot be empty. Please provide product specifications.")

        # Combine all key-value inputs into a single dictionary
        user_specs = {}
        for item in input:
            if ":" in item:
                key, value = item.split(":", 1)
                user_specs[key.strip().lower()] = value.strip().lower()
            else:
                raise ValueError(f"Invalid input format: '{item}'. Use 'key:value' format.")

        logger.info(f"Parsed input into specifications: {user_specs}")

        # Call the function to find similar products
        result = find_similar_products(user_specs, top_n)

        # Ensure result is a valid pandas DataFrame or has a 'to_dict' method
        if not hasattr(result, 'to_dict'):
            raise TypeError("The result must be a pandas DataFrame or have a 'to_dict' method.")

        products = result.to_dict(orient="records")

        return {
            "input": input,
            "parsed_specs": user_specs,
            "matched_products": products,
        }

    except ValueError as ve:
        logger.error(f"Value error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except TypeError as te:
        logger.error(f"Type error: {te}")
        raise HTTPException(status_code=500, detail=str(te))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)

import requests
import os

def get_food_nutrition_info(query, data_type=None):
    base_url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "query": query,
        "api_key": os.getenv('USDA_API_KEY'),
        "pageSize": 1,  # Limit to one result
    }
    if data_type:
        params["dataType"] = data_type

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        result = response.json()
        # Check if results are available
        foods = result.get("foods", [])
        if foods:
            food = foods[0]
            # Ensure the returned food matches the query exactly
            if food.get("description", "").lower() == query.lower():
                return food
            else:
                raise ValueError(f"No exact match found for query: {query}")
        else:
            raise ValueError(f"No food found for query: {query}")
    else:
        raise Exception(f"API request failed with status code {response.status_code}")
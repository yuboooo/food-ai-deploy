import os
import json

def save_results_to_file(results):
    output_dir = "./"
    os.makedirs(output_dir, exist_ok=True)  # Ensure the directory exists
    file_path = os.path.join(output_dir, f"nutrition.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)
    print(f"Results saved to {file_path}")


def load_results_from_file():
    file_path = "./nutrition.json"
    with open(file_path, "r", encoding="utf-8") as f:
        results = json.load(f)
    return results

all_nutrition = load_results_from_file()

def filter_nutrition_data(all_nutrition):
    nutrient_filter = [1005, 1003, 1008, 1004]
    # all_nutrition = load_results_from_file()
    result = []
    result.append({
        "description": all_nutrition["description"]
    })
    for nutrient in all_nutrition["foodNutrients"]:
        if nutrient["nutrientId"] in nutrient_filter:
            result[0][nutrient["nutrientName"]] = f"{nutrient['value']} {nutrient['unitName']}"
    return result

# print(filter_nutrition_data(all_nutrition))
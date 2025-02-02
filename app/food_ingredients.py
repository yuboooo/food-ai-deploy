from preprocess import vector_db
from usda_api import get_food_nutrition_info
from postprocess import filter_nutrition_data



if __name__ == "__main__":

    filtered_db_path = "../data/food_db/food_descriptions.csv"
    vector_db_path = "../data/food_db/vector_db"
    db = vector_db(filtered_db_path, vector_db_path)
    retriever = db.as_retriever(search_type="similarity", search_kwargs={'k': 1})

    ingredients = ["Salmon (raw)", "White rice", "Pineapple", "Cucumber", "Seaweed (wakame)", "Sesame seeds"]

    api_querys = []
    for ingredient in ingredients:
        text_query = ingredient
        similar_doc = retriever.invoke(text_query)
        api_query = similar_doc[0].page_content if similar_doc else None
        api_querys.append(api_query)
    print("API Querys:", api_querys)


    filtered_nutrition_info = []

    for api_query in api_querys:
        nutrition_info = get_food_nutrition_info(api_query)
        filtered_nutrition_info.extend(filter_nutrition_data(nutrition_info))
    print(filtered_nutrition_info)


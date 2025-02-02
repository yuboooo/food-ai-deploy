# __import__('pysqlite3')
# import sys
# import pysqlite3
# sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import json
import pandas as pd
import base64
from pathlib import Path
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from uuid import uuid4
import streamlit as st
import boto3
import streamlit as st
from PIL import Image
import io
from datetime import datetime
import uuid

load_dotenv()
openai_api_key = st.secrets["general"]["OPENAI_API_KEY"]

def encode_image(file) -> str:
    """
    Takes a file-like object and returns the base64 encoded image.
    """
    try:
        file.seek(0)  # Ensure you're at the start of the file
        return base64.b64encode(file.read()).decode('utf-8')
    except Exception as e:
        raise ValueError(f"Error encoding image: {str(e)}")

def encode_image_path(image_path: str) -> str:
    """
    Take the path of image file and return the base64 encoded image.
    """
    if not Path(image_path).is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        raise ValueError(f"Error encoding image: {str(e)}")
    

def upload_image(file):

    bucket_name = "food-ai-images"

    s3 = boto3.client(
        's3',
        aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"]
    )

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    original_filename = file.name
    extension = original_filename.split('.')[-1]
    filename = f"image_{timestamp}_{unique_id}.{extension}"

    s3.put_object(
        Bucket=bucket_name,
        Key=filename,
        Body=file.getvalue(),
        ContentType=file.type if file.type else 'application/octet-stream'
    )
    
def filter_food_description_from_USDA_DB(database_url: str):
    """
    Take the USDA database URL and filter the food description from the database.
    """
    with open(database_url, 'r') as file:
        data = json.load(file)
    
    food_descriptions = [item['description'] for item in data['SRLegacyFoods']]
    food_descriptions_df = pd.DataFrame(food_descriptions, columns=['Description'])
    output_path = "../data/food_db/food_descriptions.csv"
    if not Path(output_path).is_file():
        food_descriptions_df.to_csv(output_path, index=False, quoting=1)
        print(f"Processed food descriptions saved to {output_path}")
    else:
        'File already exists'

def vector_db(filtered_db_path: str, vector_db_path: str):
    """
    Take the filtered database and vectorize the food descriptions.
    Each line in the file will be one vector.
    """
    openai_embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", api_key=openai_api_key)
    if not Path(vector_db_path).is_dir():
        data = pd.read_csv(filtered_db_path)
        text_data = data['Description'].tolist()
        db = Chroma.from_texts(text_data, openai_embeddings, persist_directory=vector_db_path)
    else:
        db = Chroma(persist_directory=vector_db_path, embedding_function=openai_embeddings)
    return db

def vector_db_json(filtered_db_path: str, vector_db_path: str):
    """
    Vectorize a JSON file with descriptions and metadata, storing them in a Chroma vector database.

    Args:
        filtered_db_path (str): Path to the input JSON file.
        vector_db_path (str): Directory path where the vector database will be stored.
    """
    # Load JSON data
    with open(filtered_db_path, 'r') as file:
        json_data = json.load(file)

    # Initialize embeddings and vector store
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    vector_store = Chroma(
        collection_name="food_items_collection",
        embedding_function=embeddings,
        persist_directory=vector_db_path
    )

    # Prepare documents and add them to the vector store
    documents = []
    ids = []
    for item in json_data:
        # Extract description and metadata
        description = item.get("description", "")
        metadata = {k: v for k, v in item.items() if k != "description"}
        
        # Create a Document
        doc = Document(
            page_content=description,
            metadata=metadata,
            id=str(uuid4())  # Generate a unique ID for the document
        )
        documents.append(doc)
        ids.append(doc.id)

    # Add documents to the vector store
    vector_store.add_documents(documents=documents, ids=ids)


    print(f"Vector database created and saved at: {vector_db_path}")
def filter_nutrition_data(food_data):
    """
    Filters the food data to only include the desired nutrient information.
    """
    # Nutrient IDs to keep
    nutrient_filter = [1005, 1003, 1008, 1004]
    result = {
        "description": food_data["description"]
    }
    
    # Extract and filter nutrients
    for nutrient in food_data["foodNutrients"]:
        if nutrient["nutrient"]["id"] in nutrient_filter:
            nutrient_name = nutrient["nutrient"]["name"]
            nutrient_value = nutrient["amount"]
            nutrient_unit = nutrient["nutrient"]["unitName"]
            result[nutrient_name] = f"{nutrient_value} {nutrient_unit}"
    
    return result

def process_food_db(input_file, output_file):
    """
    Processes the entire food database, filters relevant nutrient information,
    and saves it to a new file.
    """
    # Load the input JSON file
    with open(input_file, 'r') as file:
        food_db = json.load(file)

    # Process each food item
    processed_data = []
    for food_item in food_db["SRLegacyFoods"]:
        filtered_data = filter_nutrition_data(food_item)
        processed_data.append(filtered_data)

    # Save the processed data to the output JSON file
    with open(output_file, 'w') as file:
        json.dump(processed_data, file, indent=4)

# # File paths
# input_file = "../../backend/data/food_db/fooddb.json"  # Replace with your input file path
# output_file = "./filtered_fooddb.json"  # Replace with your desired output file path

# # Process the data
# process_food_db(input_file, output_file)

# Vectorize json file
# filtered_db_path = "../data/food_db/filtered_fooddb.json"
# vector_db_path = "../data/food_db/vector_db_json"
# db = vector_db_json(filtered_db_path, vector_db_path)


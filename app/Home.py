__import__('pysqlite3')
import sys
import pysqlite3
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from preprocess import encode_image
from agents import agent1_food_image_caption, agent2_nutrition_augmentation, agent3_parse_nutrition, agent4_create_summary
import chromadb
import chromadb.config
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
import streamlit as st
import boto3
from PIL import Image
import os
import pandas as pd
from preprocess import upload_image
import streamlit as st
import streamlit_authenticator as stauth

from streamlit_google_auth import Authenticate
from mongodb import MongoDB
import datetime

from user import show_user_profile



authenticator = Authenticate(
    secret_credentials_path='./.streamlit/google_credentials.json',
    cookie_name='my_cookie_name',
    cookie_key='this_is_secret',
    redirect_uri='http://localhost:5173',
)

authenticator.check_authentification()

# Display user profile in sidebar
show_user_profile(authenticator)

OPENAI_API_KEY = st.secrets["general"]["OPENAI_API_KEY"]
# def get_db_json():
#     return Chroma(
#         collection_name="food_items_collection",
#         embedding_function=OpenAIEmbeddings(model="text-embedding-3-large"),
#         persist_directory="../data/food_db/vector_db_json"
#     )

def download_s3_bucket(bucket_name, local_dir):
    # Create an S3 client
    s3 = boto3.client(
        's3',
        aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"]
    )

    paginator = s3.get_paginator('list_objects_v2')
    operation_parameters = {'Bucket': bucket_name}
    
    for page in paginator.paginate(**operation_parameters):
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                local_file_path = os.path.join(local_dir, key)

                # Create local directory structure if it doesn't exist
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

                # Download the file
                print(f"Downloading {key} to {local_file_path}")
                s3.download_file(bucket_name, key, local_file_path)

def initialize_db():
    """Initialize database connection if not already in session state"""
    if 'vector_db' not in st.session_state:
        with st.spinner("Loading database..."):
            # Define S3 and local paths
            bucket_name = "food-ai-db" 
            local_dir = "../data/food_db_cloud/" 

            # Call the function
            download_s3_bucket(bucket_name, local_dir)

            db_path = os.path.join(local_dir, "vector_db_json")

            # Load the Chroma database
            st.session_state.vector_db = Chroma(
                collection_name="food_items_collection",
                embedding_function=OpenAIEmbeddings(model="text-embedding-3-large", api_key=st.secrets["general"]["OPENAI_API_KEY"]),
                persist_directory=db_path
            )
    return st.session_state.vector_db

def save_analysis_to_db(email, image_data, ingredients, nutrition_info, nutrition_df, augmented_info):
    """
    Save the food analysis results to MongoDB
    """
    try:
        with MongoDB() as mongo:
            analysis_data = {
                "date": datetime.datetime.utcnow(),
                "image": image_data,
                "ingredients": ingredients,
                "nutrition_info": nutrition_info,
                "nutrition_df": nutrition_df.to_dict() if nutrition_df is not None else {},
                "augmented_info": augmented_info
            }
            
            # Update user document, adding new analysis to food_history
            result = mongo.users.update_one(
                {"email": email},
                {
                    "$setOnInsert": {
                        "email": email,
                        "created_at": datetime.datetime.utcnow()
                    },
                    "$push": {
                        "food_history": analysis_data
                    }
                },
                upsert=True
            )
            
            return True, "Analysis saved successfully!"
            
    except Exception as e:
        st.error(f"Error saving to database: {str(e)}")
        return False, str(e)

@st.cache_data
def get_source_information():
    return """
    The nutritional facts displayed above are sourced from the **USDA SRLegacy Database**. 
    Our system identifies the most similar food descriptions in the database based on the ingredients we identified. 
    While we strive to make the matches as accurate as possible, they might not always perfectly reflect the exact nutrition of your specific ingredient.
    We are working to improve our data and algorithms in future versions.

    Below are the matched descriptions from the USDA SRLegacy Database for your reference:
    """

if __name__ == "__main__":

    # Streamlit app
    st.title("🍎 Food AI")

    # Initialize empty sidebar
    st.sidebar.empty()

    st.markdown("Analyze your food and get detailed nutritional insights! 🎉")
    st.header("📸 Upload a Food Image")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "png", "jpeg"])

    if uploaded_file is None:
        st.info("Please upload a JPG, PNG, or JPEG image of your food to get started!")
    else:
        # Clear session state if a new image is uploaded
        current_file_name = getattr(uploaded_file, 'name', None)
        if 'last_uploaded_file' not in st.session_state or st.session_state.last_uploaded_file != current_file_name:
            if 'current_analysis' in st.session_state:
                del st.session_state.current_analysis
            st.session_state.last_uploaded_file = current_file_name

        # Initialize analysis if not already done
        if 'current_analysis' not in st.session_state:
            st.session_state.current_analysis = {}
            
            image = Image.open(uploaded_file)
            upload_image(uploaded_file)
            st.image(image, caption="Uploaded Food Image", use_container_width=True)

            # Encode image and extract ingredients
            with st.spinner("Processing image to extract food ingredients..."):
                encoded_image = encode_image(uploaded_file)
                ingredients = agent1_food_image_caption(encoded_image)

            if ingredients[0] == 'False':
                st.error("Sorry, we couldn't identify the food in the image. Please try again with a clearer image.")
                st.stop()

            # Store all analysis results in session state
            st.session_state.current_analysis = {
                'ingredients': ingredients,
                'encoded_image': encoded_image,
                'uploaded_file': uploaded_file
            }

        # Now we can safely access the ingredients
        ingredients = st.session_state.current_analysis['ingredients']
        
        st.subheader("🍴 Extracted Food Ingredients")
        st.write(ingredients)

        # Continue with nutrition info processing using stored ingredients
        with st.spinner("Fetching nutrition information for ingredients..."):
            if 'nutrition_info' not in st.session_state.current_analysis:
                db = initialize_db()
                nutrition_info = {}
                display_info = {}
                for ingredient in ingredients:
                    similar_doc = db.similarity_search(ingredient, k=1)
                    food_description = similar_doc[0].page_content if similar_doc else None
                    metadata = similar_doc[0].metadata
                    display_info[ingredient] = metadata
                    nutrition_info[food_description] = metadata
                
                st.session_state.current_analysis['nutrition_info'] = nutrition_info
                st.session_state.current_analysis['display_info'] = display_info

        # Use stored nutrition info for display
        display_info = st.session_state.current_analysis['display_info']
        nutrition_info = st.session_state.current_analysis['nutrition_info']

        # Prepare a cleaner table
        st.subheader("🍽️ Nutrition Facts for Each Ingredient (per 100g)")

        # Convert nutrition info to a DataFrame for better display
        nutrition_df = pd.DataFrame.from_dict(display_info, orient='index').reset_index()
        nutrition_df.columns = ["Ingredient", "Carbohydrate (g)", "Energy (kcal)", "Protein (g)", "Fat (g)"]

        # Customize the DataFrame for a better display
        nutrition_df["Carbohydrate (g)"] = nutrition_df["Carbohydrate (g)"].apply(lambda x: x.split()[0])
        nutrition_df["Protein (g)"] = nutrition_df["Protein (g)"].apply(lambda x: x.split()[0])
        nutrition_df["Fat (g)"] = nutrition_df["Fat (g)"].apply(lambda x: x.split()[0])
        nutrition_df["Energy (kcal)"] = nutrition_df["Energy (kcal)"].apply(lambda x: x.split()[0])

        # Display as a pretty table in Streamlit
        st.table(nutrition_df)


        # # Augmented nutrition data
        # st.write("Generating augmented nutrition information...")
        # nutrition_augmentation = agent2_nutrition_augmentation(encoded_image, nutrition_info)
        # st.subheader("Augmented Nutrition Information")
        # st.write(nutrition_augmentation)


        # Augmented Nutrition Data
        st.subheader("🌟 Augmented Nutrition Information")
        st.markdown("""
        Here, we enhance the basic nutrition facts with additional insights, 
        combining data and analysis to provide you with a richer understanding of your food choices.
        """)

        # Generate augmented nutrition information only if not already generated
        if 'nutrition_augmentation' not in st.session_state.current_analysis:
            with st.spinner("Generating augmented nutrition information..."):
                nutrition_augmentation = agent2_nutrition_augmentation(
                    st.session_state.current_analysis['encoded_image'], 
                    nutrition_info, 
                    ingredients
                )
                st.session_state.current_analysis['nutrition_augmentation'] = nutrition_augmentation

        # Display the stored augmented information
        st.markdown(f"""{st.session_state.current_analysis['nutrition_augmentation']}""")




        # Add explanation and citation only if not already in session state
        st.subheader("📚 Source Information")
        st.markdown(get_source_information())

        with st.expander("View USDA Food Central Data Sources"):
            if 'matched_descriptions' not in st.session_state.current_analysis:
                st.session_state.current_analysis['matched_descriptions'] = nutrition_info
            
            for ingredient, description in st.session_state.current_analysis['matched_descriptions'].items():
                st.write(f"- **{ingredient}**:  {description}.")

        # Save Analysis section
        if st.session_state.get('connected', False):
            email = st.session_state['user_info'].get('email')
            
            # Add a save button
            if st.button("Save Analysis"):
                try:
                    # Use stored file for saving
                    uploaded_file = st.session_state.current_analysis['uploaded_file']
                    uploaded_file.seek(0)
                    image_data = uploaded_file.read()
                    
                    nutrition_augmentation = st.session_state.current_analysis['nutrition_augmentation']
                    final_nutrition_info = agent3_parse_nutrition(nutrition_augmentation)
                    text_summary = agent4_create_summary(nutrition_augmentation)
                    
                    # Create MongoDB instance and save
                    mongo = MongoDB()
                    mongo.save_analysis(
                        email=email,
                        image_data=image_data,
                        ingredients=st.session_state.current_analysis['ingredients'],
                        final_nutrition_info=final_nutrition_info,
                        text_summary=text_summary
                    )
                    
                    st.success("Analysis saved successfully!")
                    
                except Exception as e:
                    st.error(f"Error saving to database: {str(e)}")
        else:
            st.warning("Please log in to save your analysis.")

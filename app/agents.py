import os
from openai import OpenAI
from dotenv import load_dotenv
import streamlit as st
import json

load_dotenv()
api_key = st.secrets["general"]["OPENAI_API_KEY"]

def agent1_food_image_caption(encoded_image: str) -> str:
    """
    Take the food image (base64 encoded) and prompt (which ask to describe the food component in the image) and return the caption.
    """
    client = OpenAI(api_key=api_key)


    prompt = "List the major ingredients you can visually identify in the food item shown, separated by commas. Each ingredient should be described in simple terms (e.g., raw salmon, white rice). Do not include the dish name, preparation methods, quantities, or any additional commentary. Avoid using brackets, quotes, or special formatting. Example output format: raw salmon, white rice, cucumber, sesame seeds. Note: If the image is unclear or the food is unidentifiable, your response should be a simple string 'False'."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                    ]
                }
            ],
            max_tokens=100
        )

        ingredients_str = response.choices[0].message.content.strip()
        ingredients = [item.strip() for item in ingredients_str.split(',')]
        return ingredients
    except Exception as e:
        raise Exception(f"Error during API call: {str(e)}")


def agent2_nutrition_augmentation(encoded_image: str, nutrition_info: dict, ingredients: list) -> str:
    """
    Take the nutrition information and augment it with additional details.
    """
    # Step 1: Initialize the OpenAI client
    client = OpenAI(api_key=api_key)
    # Step 2: Prompt


    # prompt = "The above nutrition facts, it describe the ingredient's nutrition per 100g. Can you then estimate the total nutrition info for the food in the provided image, based on the nutrition facts i provided to you, and also your own knowledge from your database, if you identified this food from your database, you can also directly use the information their. Simply return the nutrition info in a nice readable str format, make it concise, and easy to read. If you need to use scratch pad, you can use the scratch pad below to do your calculation. But keep the output clean(dont explicitly show our provided nutrition facts in response), especially provide a Summary Section in the end"

    # prompt = f"{nutrition_info} \n\n{prompt}"
    


    # prompt = f"""
    #             You are a nutrition researcher who can analyze the nutrition information for food in the provided image.
    #             Please first identify the food in the image.
    #             And search through your nutrition and food database to help yourself understand the nutrition details of the food.
    #             We also provided you with the nutrition facts for each of the {ingredients} in the food. For each of the ingredients,
    #             we find the most similar nutrition facts on USDA Food Database, here is the detailed nutrition information for your reference: {nutrition_info}.
    #             They are based on the nutrition facts per 100g.
    #             Thus you need to based on the food image, estimate the weight of each ingredient in the food.
    #             Then, I want you to based on the nutrition knowledge you searched in your own database, the weight of each ingredient you esitimated, and the provided nutrition facts, to estimate the total nutrition info for the food in the provided image. Note, if you think the provided nutrition facts are irelevant, for example it mentioned the ingredients that are not in the food, you can ignore them, and use your own knowledge to estimate the nutrition info.

    #             Note: Everything related to calculation, use plain text format, be super concise, NO SPECIAL FORMAT, USE PLAIN TEXT ONLY.

    #             Your response will directly display to end users, so be friendly and professional, you want the user understand your analysis easily. 
    #             Provide your response in markdown format, the title size will be similar to h3. Here are some sections you can include in your response:
    #             Overview: 
    #                 - The estimated weight for each ingredient in the food.
    #             Nutrition Estimation:
    #                 - For each ingredient, provide a simple calculation estimation walkthrough, display in plain text format, be really concise, including energy, protein, fat, and carbohydrate. (Dont need to be using exact number, just give a rough estimation, and only display unit in the end, it would be great if you can provide a range of the estimation, +/- 10% is fine, and no need to be accurate on the digit)
    #             Summary:
    #                 - List the total nutrition info for the food in the image, including energy, protein, fat, and carbohydrate.

    #         """
    
    prompt = f"""
            Role and Context
            You are a nutrition researcher specialized in analyzing food components and nutritional content. Your task is to analyze food items from images and provide detailed nutritional assessments.
            Input Analysis

            Examine the provided food image
            Here is the ingredients we identified in the image: {ingredients}
            Reference the provided USDA Food Database nutrition facts per 100g for each ingredient: {nutrition_info}

            Analysis Requirements

            Weight Estimation

            Estimate the approximate weight of each visible ingredient
            Consider typical serving sizes and proportions
            Account for cooking methods that may affect weight


            Nutritional Calculation

            Use provided USDA data when relevant, dont over over estimate the nutrition info, if the USDA data is inaccurate, and dont over rely on the USDA data. 
            Apply your nutrition knowledge for any ingredients without provided data
            Consider cooking methods that might affect nutritional content
            Provide calculations based on estimated weights

            Note: If provided nutrition facts are irrelevant or inaccurate for the visible food item, rely on your nutrition knowledge database for more accurate estimations, do not over estimate the nutrition info.



            Output Format
            Please structure your response in markdown format with the following sections:
            Overview

            Identify the food item
            List each ingredient with its estimated weight
            Note any assumptions made in weight estimation in italics

            Nutrition Estimation

            For each ingredient:

            Show only final estimated values (no calculation steps)
            Include: energy, protein, fat, and carbohydrates
            Present as a range (±10%)
            List units at the end
            Example: "Bread (50-60g): Energy 140-160 kcal, Protein 4-5g, Fat 2-3g, Carbs 28-32g"

            Summary

            Present total values with ±10% range for:

            Energy (kcal)
            Protein (g)
            Fat (g)
            Carbohydrates (g)

            In a nice Table format

            Before return the final result, refer back to your nutrition knowledge database for more accurate estimations if the provided nutrition facts seem irrelevant or inaccurate for the visible food item, revise the nutrition information accordingly.



            Style Guidelines

            Use professional but accessible language
            Keep calculations concise and easy to follow
            Avoid special formatting in calculation sections
            Present ranges rather than precise numbers
            Write in a friendly, informative tone
            The title of each section should be similar to h3 size

            Note: If provided nutrition facts seem irrelevant or inaccurate for the visible food item, rely on your nutrition knowledge database for more accurate estimations, do not over estimate the nutrition info.

            """

    # Step 3: Return the augmented nutrition information
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                    ]
                }
            ],
            max_tokens=1000
        )

        augmented_nutrition_info = response.choices[0].message.content.strip()
        return augmented_nutrition_info
    except Exception as e:
        raise Exception(f"Error during API call: {str(e)}")

def agent3_parse_nutrition(agent2_response: str) -> list:
    """
    Parse the nutrition summary table from agent2's response and return it as a structured list.
    """
    client = OpenAI(api_key=api_key)
    
    prompt = """
    Extract the numerical ranges from the Summary section's nutrition table and convert them to a JSON format.
    
    Example input text:
    Summary
    Nutrient	Total Estimated Values (±10%)
    Energy	493 - 611 kcal
    Protein	32 - 39g
    Fat	25 - 32g
    Carbohydrates	31 - 42g

    Expected output format:
    {
        "data": [
            {"nutrient": "energy", "min": 493, "max": 611},
            {"nutrient": "protein", "min": 32, "max": 39},
            {"nutrient": "fat", "min": 25, "max": 32},
            {"nutrient": "carbs", "min": 31, "max": 42}
        ]
    }

    Important:
    - Extract only the numerical values
    - Remove all units (kcal, g)
    - Return a valid JSON object with the exact structure shown above
    - Convert all numbers to floats
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nText to parse:\n{agent2_response}"
                }
            ],
            max_tokens=300,
            response_format={ "type": "json_object" }
        )
        
        # Print raw response for debugging
        print("\nRaw GPT Response:")
        print(response.choices[0].message.content.strip())
        
        # Parse the JSON response
        parsed_response = json.loads(response.choices[0].message.content.strip())
        nutrition_list = parsed_response.get('data', [])
        
        print("\nAgent3 Output:")
        print(json.dumps(nutrition_list, indent=2))
        
        return nutrition_list
        
    except Exception as e:
        raise Exception(f"Error parsing nutrition information: {str(e)}")

def agent4_create_summary(agent2_response: str) -> str:
    """
    Create a concise, informative summary of the nutritional analysis from agent2's response.
    Returns a brief, professional summary focusing on key nutritional aspects.
    """
    client = OpenAI(api_key=api_key)
    
    prompt = """
    As a professional nutritionist, create a brief, informative summary of this meal's nutritional analysis.
    
    Guidelines:
    1. Start with a one-sentence overview of the dish and its main components
    2. Highlight the key macronutrient distribution (protein, carbs, fat ratio)
    3. Mention any notable nutritional characteristics (e.g., protein-rich, balanced meal, etc.)
    4. Keep the tone professional but conversational
    5. Be concise - aim for 3-4 sentences total
    
    Format the response in plain text without special formatting or bullet points.
    Focus on facts rather than recommendations.
    
    Example style:
    "This sushi roll combines salmon and rice for a balanced meal providing 400-450 calories. The macronutrient distribution is well-balanced with 40% carbs, 30% protein, and 30% healthy fats. This meal offers a good source of omega-3 fatty acids and complete protein."
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt}\n\nNutritional analysis to summarize:\n{agent2_response}"
                }
            ],
            max_tokens=200
        )
        
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        raise Exception(f"Error creating nutritional summary: {str(e)}")
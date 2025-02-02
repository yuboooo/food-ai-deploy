import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
from streamlit_calendar import calendar
from mongodb import MongoDB
import json
from user import show_user_profile
from utils.session_manager import get_authenticator



authenticator = get_authenticator()

def show_profile():
    st.title("Nutrition Profile Dashboard")
    show_user_profile(authenticator)

    def load_user_nutrition_history():
        try:
            mongo = MongoDB()
            # Force a new MongoDB connection each time
            mongo.client.server_info()  # Test connection
            user_data = mongo.users.find_one({"email": st.session_state['user_info'].get('email')})
            food_history = user_data.get('food_history', []) if user_data else []
            
            # Add debug info
            # st.write(f"Loading data at: {datetime.now()}")
            # st.write(f"Number of food history entries: {len(food_history)}")
            
            # Process food history into daily totals
            daily_totals = {}
            for entry in food_history:
                date = entry['date']
                if isinstance(date, datetime):
                    date_key = date.date()
                else:
                    date_key = datetime.fromisoformat(date).date()
                
                nutrition_info = entry.get('final_nutrition_info', [])
                if not daily_totals.get(date_key):
                    daily_totals[date_key] = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}
                
                # Handle both list and dict formats of nutrition_info
                if isinstance(nutrition_info, list):
                    for item in nutrition_info:
                        nutrient = item.get('nutrient')
                        # Use average of min and max values
                        value = (float(str(item.get('min', 0)).replace(',', '')) + 
                                float(str(item.get('max', 0)).replace(',', ''))) / 2
                        if nutrient == 'energy':
                            daily_totals[date_key]['calories'] += value
                        elif nutrient in ['protein', 'carbs', 'fat']:
                            daily_totals[date_key][nutrient] += value
                elif isinstance(nutrition_info, dict):
                    daily_totals[date_key]['calories'] += float(str(nutrition_info.get('energy', 0)).replace(',', ''))
                    daily_totals[date_key]['protein'] += float(str(nutrition_info.get('protein', 0)).replace(',', ''))
                    daily_totals[date_key]['carbs'] += float(str(nutrition_info.get('carbs', 0)).replace(',', ''))
                    daily_totals[date_key]['fat'] += float(str(nutrition_info.get('fat', 0)).replace(',', ''))
            
            # Convert to DataFrame
            df_data = {
                'date': list(daily_totals.keys()),
                'calories': [totals['calories'] for totals in daily_totals.values()],
                'protein': [totals['protein'] for totals in daily_totals.values()],
                'carbs': [totals['carbs'] for totals in daily_totals.values()],
                'fat': [totals['fat'] for totals in daily_totals.values()]
            }
            df = pd.DataFrame(df_data)
            df = df.sort_values('date')
            return df
        except Exception as e:
            st.error(f"Error loading nutrition history: {str(e)}")
            return pd.DataFrame(columns=['date', 'calories', 'protein', 'carbs', 'fat'])

    # Load user data
    user_data = load_user_nutrition_history()

    # Create dashboard layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Calorie intake over time
        st.subheader("Calorie Intake Timeline")
        fig_calories = px.line(user_data, x='date', y='calories',
                             title='Daily Calorie Intake')
        st.plotly_chart(fig_calories)

        st.markdown("")
        st.markdown("")
        # Macronutrient distribution
        st.subheader("Macronutrient Distribution")
        fig_macros = go.Figure()
        for macro in ['protein', 'carbs', 'fat']:
            fig_macros.add_trace(go.Scatter(x=user_data['date'], 
                                          y=user_data[macro],
                                          name=macro.capitalize()))
        st.plotly_chart(fig_macros)

    with col2:
        # Summary statistics
        st.subheader("Weekly Summary")
        # Get last 7 non-empty entries instead of last 7 days
        recent_data = user_data[user_data['calories'] > 0].tail(7)
        
        # Add debug info
        # st.write(f"Number of recent entries: {len(recent_data)}")
        # st.write("Recent data:")
        # st.write(recent_data)
        
        if len(recent_data) > 0:
            avg_calories = recent_data['calories'].mean()
            avg_protein = recent_data['protein'].mean()
            avg_carbs = recent_data['carbs'].mean()
            avg_fat = recent_data['fat'].mean()
        else:
            avg_calories = avg_protein = avg_carbs = avg_fat = 0

        st.metric("Avg. Daily Calories", f"{avg_calories:.0f} kcal")
        st.metric("Avg. Daily Protein", f"{avg_protein:.1f}g")
        st.metric("Avg. Daily Carbs", f"{avg_carbs:.1f}g")
        st.metric("Avg. Daily Fat", f"{avg_fat:.1f}g")
        # Add a separator line
        st.markdown("")
        st.markdown("")
        st.markdown("")
        
        st.markdown("")
        st.markdown("")
        st.markdown("")
        
        # Progress towards goals
        st.subheader("Goals Progress")
        # These should be customizable by user
        calorie_goal = 2000
        protein_goal = 80
        carbs_goal = 250
        fat_goal = 65

        progress_calories = avg_calories / calorie_goal
        st.progress(min(progress_calories, 1.0), "Calories")
        
        progress_protein = avg_protein / protein_goal
        st.progress(min(progress_protein, 1.0), "Protein")
        
        progress_carbs = avg_carbs / carbs_goal
        st.progress(min(progress_carbs, 1.0), "Carbs")
        
        progress_fat = avg_fat / fat_goal
        st.progress(min(progress_fat, 1.0), "Fat")

    # Add a separator
    st.markdown("---")
    
    # Calendar Section
    st.subheader("Food History Calendar")
    
    # Simple calendar styling
    st.markdown("""
        <style>
        .fc {
            background-color: white;
            padding: 20px;
            border-radius: 10px;
        }
        .fc-event {
            border-radius: 5px !important;
            padding: 2px 5px !important;
        }
        .fc-day-today {
            background-color: #e8f5e9 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    try:
        mongo = MongoDB()
        user_data = mongo.users.find_one({"email": st.session_state['user_info'].get('email')})
        food_history = user_data.get('food_history', []) if user_data else []
        
        # Group meals by date
        meals_by_date = {}
        for entry in food_history:
            date_str = entry['date'].isoformat() if isinstance(entry['date'], datetime) else entry['date']
            date_key = date_str.split('T')[0]
            if date_key not in meals_by_date:
                meals_by_date[date_key] = []
            meals_by_date[date_key].append(entry)
        
        # Create individual events for each meal
        calendar_events = []
        for date, meals in meals_by_date.items():
            # Sort meals by datetime
            meals.sort(key=lambda x: x['date'] if isinstance(x['date'], datetime) else x['date'])
            
            # Create an event for each meal
            for i, meal in enumerate(meals, 1):
                meal_time = meal['date']
                if isinstance(meal_time, datetime):
                    start_time = meal_time.isoformat()
                else:
                    start_time = date
                
                event = {
                    'title': f"Meal {i}",
                    'start': start_time,
                    'id': f"{date}-meal-{i}",
                    'backgroundColor': '#4CAF50',
                    'borderColor': '#4CAF50',
                    'textColor': '#ffffff',
                }
                calendar_events.append(event)
        
        # Calendar configuration
        calendar_options = {
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "dayGridMonth,timeGridDay",
            },
            "initialView": "dayGridMonth",
            "selectable": True,
            "dayMaxEvents": True,
            "editable": True,
            "events": calendar_events,
            "height": 650,
        }
        
        # Display calendar
        calendar_state = calendar(events=calendar_events, options=calendar_options)
        
        # Show food details when a meal is selected
        if calendar_state and 'eventClick' in calendar_state:
            event_id = calendar_state['eventClick']['event']['id']
            date = event_id.split('-meal-')[0]
            meal_index = int(event_id.split('-meal-')[1]) - 1
            
            selected_meals = meals_by_date.get(date, [])
            if selected_meals and meal_index < len(selected_meals):
                selected_meal = selected_meals[meal_index]
                # Add the date as a main title
                meal_date = datetime.fromisoformat(date) if isinstance(date, str) else date
                st.markdown(f"# 📅 {meal_date.strftime('%B %d, %Y')}")
                
                # Create dropdown for meal selection
                meal_options = [f"Meal {i+1}" for i in range(len(selected_meals))]
                selected_meal_index = st.selectbox(
                    "Select meal to view details",
                    range(len(meal_options)),
                    format_func=lambda x: meal_options[x],
                    index=meal_index
                )
                
                # Display details for the selected meal
                selected_meal = selected_meals[selected_meal_index]
                st.markdown(f"### 🍽️ {meal_options[selected_meal_index]} Details")
                display_meal_details(selected_meal)

    except Exception as e:
        st.error(f"Error loading food history: {str(e)}")

def display_meal_details(entry):
    """Helper function to display detailed meal information"""
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("##### 📋 Ingredients")
        ingredients_list = "• " + "\n• ".join(entry['ingredients'])
        st.markdown(ingredients_list)
        
        st.markdown("##### 📝 Summary")
        st.markdown(f"_{entry['text_summary']}_")
    
    with col2:
        st.markdown("##### 📊 Detailed Nutrition")
        nutrition_info = entry.get('final_nutrition_info', [])
        
        # Define nutrient display names and units
        nutrient_display = {
            "energy": ("Calories", "kcal"),
            "protein": ("Protein", "g"),
            "carbs": ("Carbohydrates", "g"),
            "fat": ("Fat", "g")
        }
        
        # Check if nutrition_info is a list
        if isinstance(nutrition_info, list):
            # Display each nutrient's range
            for item in nutrition_info:
                if isinstance(item, dict):  # Verify item is a dictionary
                    nutrient = item.get('nutrient', '')
                    if nutrient in nutrient_display:
                        display_name, unit = nutrient_display[nutrient]
                        min_val = float(str(item.get('min', 0)).replace(',', ''))
                        max_val = float(str(item.get('max', 0)).replace(',', ''))
                        st.markdown(
                            f"**{display_name}:** {min_val:.1f} - {max_val:.1f} {unit}"
                        )
        elif isinstance(nutrition_info, dict):
            # Handle case where nutrition_info is a dictionary
            for nutrient, value in nutrition_info.items():
                if nutrient in nutrient_display:
                    display_name, unit = nutrient_display[nutrient]
                    try:
                        # Convert value to float, handling string values
                        value = float(str(value).replace(',', ''))
                        st.markdown(f"**{display_name}:** {value:.1f} {unit}")
                    except (ValueError, TypeError):
                        # If conversion fails, display the raw value
                        st.markdown(f"**{display_name}:** {value} {unit}")
        
        # Add time information if available
        if isinstance(entry['date'], datetime):
            st.markdown("##### 🕒 Time")
            st.markdown(entry['date'].strftime("%I:%M %p"))

if __name__ == "__main__":
    show_profile()
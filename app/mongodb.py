# mongodb.py
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import streamlit as st
from datetime import datetime, timedelta
import base64
import secrets

class MongoDB:
    def __init__(self):
        # Only create a new connection if one doesn't exist in session state
        if 'mongodb_client' not in st.session_state:
            try:
                # Get connection string from streamlit secrets
                mongodb_uri = st.secrets["mongodb"]["MONGODB_URI"]
                
                # Connection with timeout and proper options
                st.session_state.mongodb_client = MongoClient(
                    mongodb_uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=None,
                    connect=True
                )
                
                # Test the connection
                st.session_state.mongodb_client.server_info()
                print("MongoDB connection successful")
                
            except Exception as e:
                print(f"Error connecting to MongoDB: {e}")
                raise Exception("Failed to connect to MongoDB")
        
        self.client = st.session_state.mongodb_client
        self.db = self.client.food_ai_db
        self.users = self.db.users

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Don't close the connection here anymore since we're reusing it
        pass

    def save_analysis(self, email, image_data, ingredients, final_nutrition_info, text_summary):
        """Save food analysis with image, ingredients, nutrition info, and summary"""
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        analysis_entry = {
            "date": datetime.now(),
            "image": image_base64,
            "ingredients": ingredients,
            "final_nutrition_info": final_nutrition_info,
            "text_summary": text_summary
        }
        
        self.users.update_one(
            {"email": email},
            {"$push": {"food_history": analysis_entry}},
            upsert=True
        )

    def get_user_history(self, email):
        """Get all food analysis history for a user"""
        user = self.users.find_one({"email": email})
        if user and "food_history" in user:
            return user["food_history"]
        return []

    def create_or_get_user(self, google_user):
        """Create a new user or get existing user after Google authentication"""
        try:
            user = self.users.find_one({"email": google_user["email"]})
            
            if not user:
                # Generate a session token
                session_token = secrets.token_urlsafe(32)
                user_data = {
                    "email": google_user["email"],
                    "name": google_user["name"],
                    "picture": google_user.get("picture", ""),
                    "created_at": datetime.now(),
                    "food_history": [],
                    "friend_list": [],
                    "session_token": session_token,
                    "session_expiry": datetime.now() + timedelta(days=30)
                }
                self.users.insert_one(user_data)
                return user_data
            
            # Update existing user's session
            session_token = secrets.token_urlsafe(32)
            self.users.update_one(
                {"email": google_user["email"]},
                {
                    "$set": {
                        "session_token": session_token,
                        "session_expiry": datetime.now() + timedelta(days=30)
                    }
                }
            )
            user["session_token"] = session_token
            return user
            
        except Exception as e:
            raise ConnectionFailure(f"Failed to create or get user: {e}")

    def verify_session(self, session_token):
        """Verify if a session token is valid and return the user"""
        if not session_token:
            return None
            
        user = self.users.find_one({
            "session_token": session_token,
            "session_expiry": {"$gt": datetime.now()}
        })
        return user

    def invalidate_session(self, email):
        """Invalidate a user's session"""
        self.users.update_one(
            {"email": email},
            {
                "$unset": {
                    "session_token": "",
                    "session_expiry": ""
                }
            }
        )

    # --- New Friend Ecosystem Methods ---
    def send_friend_request(self, sender_email, target_email):
        """
        Send a friend request from sender_email to target_email.
        The target user's friend_list will receive an entry with status 0 (pending).
        """
        target_user = self.users.find_one({"email": target_email})
        if not target_user:
            return {"status": "error", "message": "Target user not found"}

        # Check if there is already an entry for this sender in the target's friend_list.
        existing_entry = self.users.find_one({
            "email": target_email,
            "friend_list": {"$elemMatch": {"email": sender_email}}
        })
        if existing_entry:
            for entry in existing_entry.get("friend_list", []):
                if entry["email"] == sender_email:
                    if entry["status"] == 0:
                        return {"status": "info", "message": "Friend request already pending"}
                    elif entry["status"] == 1:
                        return {"status": "info", "message": "You are already friends"}
                    elif entry["status"] == -1:
                        return {"status": "info", "message": "Friend request was previously declined"}
        
        self.users.update_one(
            {"email": target_email},
            {"$push": {"friend_list": {"email": sender_email, "status": 0}}}
        )
        return {"status": "success", "message": "Friend request sent"}

    def get_pending_friend_requests(self, email):
        """
        Retrieve all pending friend requests (status 0) for a user.
        Returns a list of sender emails.
        """
        user = self.users.find_one({"email": email})
        pending = []
        if user and "friend_list" in user:
            for entry in user["friend_list"]:
                if isinstance(entry, dict):
                    if entry.get("status") == 0:
                        pending.append(entry.get("email"))
                elif isinstance(entry, str):
                    # Legacy entries stored as strings are skipped or handled as needed.
                    pass
        return pending

    def approve_friend_request(self, user_email, requester_email):
        """
        Approve a pending friend request.
        Update the current user's friend_list entry for requester_email to status 1.
        Also, update the requester's document to reflect a confirmed friendship.
        """
        # Update current user's friend_list entry for requester to confirmed (1)
        self.users.update_one(
            {"email": user_email, "friend_list.email": requester_email, "friend_list.status": 0},
            {"$set": {"friend_list.$.status": 1}}
        )
        # Update the requester's friend_list: If an entry exists, set to 1; otherwise, add a confirmed entry.
        requester_doc = self.users.find_one({"email": requester_email})
        if requester_doc:
            exists = False
            for entry in requester_doc.get("friend_list", []):
                if isinstance(entry, dict) and entry["email"] == user_email:
                    exists = True
                    if entry["status"] != 1:
                        self.users.update_one(
                            {"email": requester_email, "friend_list.email": user_email},
                            {"$set": {"friend_list.$.status": 1}}
                        )
            if not exists:
                self.users.update_one(
                    {"email": requester_email},
                    {"$push": {"friend_list": {"email": user_email, "status": 1}}}
                )
        return {"status": "success", "message": "Friend request approved"}

    def decline_friend_request(self, user_email, requester_email):
        """
        Decline a pending friend request.
        Update the current user's friend_list entry for requester_email to status -1.
        """
        self.users.update_one(
            {"email": user_email, "friend_list.email": requester_email, "friend_list.status": 0},
            {"$set": {"friend_list.$.status": -1}}
        )
        return {"status": "success", "message": "Friend request declined"}

    def delete_friend(self, user_email, friend_email):
        """
        Delete a confirmed friend relationship. This removes the friend entry from both users' friend_list.
        Only entries with status 1 (confirmed) will be removed.
        """
        result1 = self.users.update_one(
            {"email": user_email},
            {"$pull": {"friend_list": {"email": friend_email, "status": 1}}}
        )
        result2 = self.users.update_one(
            {"email": friend_email},
            {"$pull": {"friend_list": {"email": user_email, "status": 1}}}
        )
        if result1.modified_count > 0 or result2.modified_count > 0:
            return {"status": "success", "message": "Friend deleted successfully"}
        else:
            return {"status": "info", "message": "Friend not found in friend list"}

    def get_friend_list(self, email):
        """
        Retrieve the confirmed friend list for a given user.
        Only entries with status 1 (if a dict) or legacy string entries are considered confirmed friends.
        """
        user = self.users.find_one({"email": email})
        if user and "friend_list" in user:
            confirmed = []
            for entry in user["friend_list"]:
                if isinstance(entry, dict):
                    if entry.get("status") == 1:
                        confirmed.append(entry.get("email"))
                elif isinstance(entry, str):
                    confirmed.append(entry)
            return confirmed
        return []

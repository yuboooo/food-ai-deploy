import streamlit as st
from mongodb import MongoDB
from utils.session_manager import require_auth
from utils.session_manager import get_authenticator
from user import show_user_profile
authenticator = get_authenticator()

st.title("Leaderboard 🏆")

# Require authentication for this page
require_auth()

# authenticator.check_authentification()

# # Display user profile in sidebar
# show_user_profile(authenticator)

# User is authenticated at this point
user = st.session_state["user"]
user_email = user["email"]

# Fetch user and friends' food history data
with MongoDB() as mongo:
    # Get the current user's food history count
    user_history = mongo.get_user_history(user_email)
    user_food_count = len(user_history)

    # Get the user's friends' list
    user_data = mongo.create_or_get_user({"email": user_email, "name": user["name"], "picture": user.get("picture", "")})
    friend_list = user_data.get("friend_list", [])

    # Get all friends' food history count
    friends_data = []
    for friend in friend_list:
        friend_email = friend["email"]
        friend_history = mongo.get_user_history(friend_email)
        friend_user = mongo.create_or_get_user({"email": friend_email, "name": "Unknown", "picture": ""})  # Ensure we get their name & pic
        friends_data.append({
            "name": friend_user.get("name", "Unknown"),
            "email": friend_email,
            "picture": friend_user.get("picture", ""),
            "food_history_size": len(friend_history)
        })
    pending_requests = mongo.get_pending_friend_requests(user_email)


# ---- Right Section (Friend Management) ----
# st.header("👥 Friends")

# Initialize session states for popups
if "show_add_friend" not in st.session_state:
    st.session_state.show_add_friend = False
if "show_pending_requests" not in st.session_state:
    st.session_state.show_pending_requests = False
if "show_confirmed_friends" not in st.session_state:
    st.session_state.show_confirmed_friends = False
if "active_popup" not in st.session_state:
    st.session_state.active_popup = None  # Track which popup is open

# ---- Friend Management Buttons ----
col1, col2, col3 = st.columns([3, 3, 3])

def close_other_popups(open_popup):
    """Closes all other popups when opening a new one"""
    if st.session_state.active_popup != open_popup:
        st.session_state.active_popup = open_popup
        st.rerun()  # Ensure UI updates

with col1:
    if st.button("➕ Add Friend"):
        close_other_popups("add_friend")

# Only show Pending Requests button if there are pending requests
if pending_requests:
    with col2:
        if st.button(f"⏳ Pending Requests ({len(pending_requests)})"):
            close_other_popups("pending_requests")

with col3:
    if st.button("✅ Confirmed Friends"):
        close_other_popups("confirmed_friends")

# ---- Mini Popups ----
if st.session_state.active_popup == "add_friend":
    with st.sidebar:
        st.markdown("### ➕ Add a Friend")
        new_friend_email = st.text_input("Enter friend's email:", key="add_friend_email")
        if st.button("Send Friend Request", key="send_request"):
            if new_friend_email:
                with MongoDB() as mongo:
                    result = mongo.send_friend_request(user_email, new_friend_email)
                    st.success(result["message"])
                    st.session_state.active_popup = None  # Close modal
                    st.rerun()
            else:
                st.warning("Please enter a valid email.")
        if st.button("Close"):
            st.session_state.active_popup = None
            st.rerun()

if st.session_state.active_popup == "pending_requests":
    with st.sidebar:
        st.markdown("### ⏳ Pending Friend Requests")
        with MongoDB() as mongo:
            pending_requests = mongo.get_pending_friend_requests(user_email)

        if pending_requests:
            for requester in pending_requests:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"Friend request from: {requester}")
                with col2:
                    if st.button("Approve", key=f"approve_{requester}"):
                        with MongoDB() as mongo:
                            result = mongo.approve_friend_request(user_email, requester)
                            st.success(result["message"])
                            st.session_state.active_popup = None  # Close modal
                            st.rerun()
                with col3:
                    if st.button("Decline", key=f"decline_{requester}"):
                        with MongoDB() as mongo:
                            result = mongo.decline_friend_request(user_email, requester)
                            st.info(result["message"])
                            st.session_state.active_popup = None  # Close modal
                            st.rerun()
        else:
            st.info("No pending requests.")
        
        if st.button("Close"):
            st.session_state.active_popup = None
            st.rerun()

if st.session_state.active_popup == "confirmed_friends":
    with st.sidebar:
        st.markdown("### Confirmed Friends")
        with MongoDB() as mongo:
            confirmed_friends = mongo.get_friend_list(user_email)

        if confirmed_friends:
            for friend in confirmed_friends:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(friend)
                with col2:
                    if st.button("🗑️ Remove", key=f"delete_{friend}"):
                        with MongoDB() as mongo:
                            result = mongo.delete_friend(user_email, friend)
                            st.success(result["message"])
                            st.session_state.active_popup = None  # Close modal
                            st.rerun()
        else:
            st.info("No confirmed friends yet.")

        if st.button("Close"):
            st.session_state.active_popup = None
            st.rerun()

# Leaderboard

# Combine user and friends into one leaderboard list
leaderboard = [
    {"name": user["name"], "email": user_email, "picture": user.get("picture", ""), "food_history_size": user_food_count}
] + friends_data

# Sort by food history size (descending)
leaderboard = sorted(leaderboard, key=lambda x: x["food_history_size"], reverse=True)

# Leaderboard Display in Table Format
st.header("Rankings")

# Emoji medals for top 3 players
medals = ["🏆", "🥈", "🥉"]

# Display leaderboard
for idx, entry in enumerate(leaderboard):
    col1, col2, col3, col4 = st.columns([1, 1, 2, 1])

    # Medal for top 3 players
    with col1:
        if idx < 3:
            st.write(medals[idx])
        else:
            st.write(f"#{idx + 1}")

    # Profile picture
    with col2:
        if entry["picture"]:
            st.image(entry["picture"], width=50)

    # Name & Email
    with col3:
        st.subheader(entry["name"])
        st.write(f"📧 {entry['email']}")

    # Food History Count
    with col4:
        st.write(f"🍔 {entry['food_history_size']}")

st.info("Leaderboard ranks users based on the number of food history records.")


import streamlit as st
import pandas as pd
import hashlib
import requests
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime

# -------------------- INITIAL SETUP --------------------
st.set_page_config(page_title="Waste-to-Wealth", page_icon="♻", layout="wide")

# ✅ Initialize session state
for key, default in {
    "logged_in": False,
    "username": None,
    "role": None,
    "location": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ✅ MongoDB Connection (replace with your MongoDB Atlas URI if needed)
client = MongoClient("mongodb://localhost:27017/")
db = client["waste_to_wealth"]
users = db["users"]
waste = db["waste_items"]

# -------------------- HELPER FUNCTIONS --------------------
def make_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_hash(password, hashed):
    return make_hash(password) == hashed

# ✅ Auto detect user location (IP-based)
def get_location():
    try:
        res = requests.get("https://ipinfo.io/json").json()
        return res.get("city", "Unknown") + ", " + res.get("region", "Unknown")
    except:
        return "Unknown Location"

# ✅ Cached waste data retrieval for performance
@st.cache_data(ttl=60)
def get_all_waste():
    return list(waste.find())

def refresh_waste_cache():
    get_all_waste.clear()

# -------------------- LOGIN SYSTEM --------------------
st.title("♻ Waste-to-Wealth Marketplace")

if not st.session_state.logged_in:
    menu = ["Login", "Register"]
    choice = st.sidebar.selectbox("Menu", menu)

    if choice == "Register":
        st.subheader("Create Account")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["Generator", "Recycler", "Admin"])
        if st.button("Register"):
            if users.find_one({"username": username}):
                st.warning("Username already exists.")
            else:
                hashed = make_hash(password)
                users.insert_one({
                    "username": username,
                    "password": hashed,
                    "role": role,
                    "created_at": datetime.now()
                })
                st.success("Account created successfully!")

    elif choice == "Login":
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = users.find_one({"username": username})
            if user and verify_hash(password, user["password"]):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = user["role"]
                st.session_state.location = get_location()
                st.success(f"Welcome {username} ({user['role']})")
                st.rerun()
            else:
                st.error("Invalid username or password")

else:
    # -------------------- LOGGED-IN DASHBOARD --------------------
    st.sidebar.success(f"Logged in as {st.session_state.username}")
    if st.sidebar.button("Logout"):
        for k in ["logged_in", "username", "role", "location"]:
            st.session_state[k] = None if k != "logged_in" else False
        st.cache_data.clear()
        st.experimental_rerun()

    role = st.session_state.role
    username = st.session_state.username

    # -------------------- GENERATOR --------------------
    if role == "Generator":
        st.header("Generator Dashboard 🏭")
        st.info(f"Your Location: {st.session_state.location}")

        with st.form("waste_form"):
            waste_type = st.selectbox("Waste Type", ["Plastic", "Glass", "Wood", "Metal", "Organic"])
            quantity = st.number_input("Quantity (kg)", min_value=0.1, step=0.1)
            pickup_time = st.text_input("Pickup Time", placeholder="e.g. 2025-10-05 18:00")
            submitted = st.form_submit_button("➕ Add Waste")

            if submitted:
                waste.insert_one({
                    "username": username,
                    "waste_type": waste_type,
                    "quantity": quantity,
                    "pickup_time": pickup_time,
                    "location": st.session_state.location,
                    "status": "Pending",
                    "accepted_by": None,
                    "created_at": datetime.now()
                })
                refresh_waste_cache()
                st.success("✅ Waste added successfully!")

        st.subheader("Your Waste Submissions")
        data = pd.DataFrame([w for w in get_all_waste() if w["username"] == username])
        if not data.empty:
            st.dataframe(data[["waste_type", "quantity", "pickup_time", "status", "accepted_by"]])
        else:
            st.info("No waste items submitted yet.")

    # -------------------- RECYCLER --------------------
    elif role == "Recycler":
        st.header("Recycler Dashboard 🔁")
        all_waste = [w for w in get_all_waste() if w["status"] == "Pending"]

        if all_waste:
            for w_item in all_waste:
                with st.expander(f"{w_item['waste_type']} - {w_item['quantity']}kg @ {w_item['location']}"):
                    st.write(f"Pickup: {w_item['pickup_time']}")
                    if st.button(f"Accept Waste ({w_item['_id']})", key=str(w_item["_id"])):
                        waste.update_one({"_id": w_item["_id"]}, {"$set": {"status": "Accepted", "accepted_by": username}})
                        refresh_waste_cache()
                        st.success(f"✅ You accepted waste from {w_item['username']}")
                        st.rerun()
        else:
            st.info("No pending waste available to accept.")

        accepted = [w for w in get_all_waste() if w.get("accepted_by") == username]
        if accepted:
            st.subheader("Accepted Waste Items")
            st.dataframe(pd.DataFrame(accepted)[["waste_type", "quantity", "username", "pickup_time"]])

    # -------------------- ADMIN --------------------
    elif role == "Admin":
        st.header("Admin Dashboard 📊")

        data = pd.DataFrame(get_all_waste())
        if not data.empty:
            type_summary = data.groupby("waste_type")["quantity"].sum().reset_index()
            recycler_summary = data[data["accepted_by"].notnull()].groupby("accepted_by")["quantity"].sum().reset_index()

            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(px.pie(type_summary, names="waste_type", values="quantity",
                                       title="Waste Distribution by Type"))
            with col2:
                if not recycler_summary.empty:
                    st.plotly_chart(px.bar(recycler_summary, x="accepted_by", y="quantity",
                                           title="Waste Collected by Recycler", color="accepted_by"))
                else:
                    st.info("No accepted waste yet.")

            st.subheader("All Waste Records")
            st.dataframe(data[["username", "waste_type", "quantity", "pickup_time", "status", "accepted_by"]])
        else:
            st.info("No waste records found yet.")

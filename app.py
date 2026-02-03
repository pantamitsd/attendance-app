import streamlit as st
import pandas as pd
import pytz
from datetime import datetime, UTC
import math
from supabase.client import create_client

# ================= SUPABASE =================
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ================= CONFIG =================
IST = pytz.timezone("Asia/Kolkata")

USERS = {
    "ajad": {"password": "1234"},
    "jitender": {"password": "1234"},
    "ramniwas": {"password": "1234"},
    "amit": {"password": "1234"},
    "rahul": {"password": "1234"},
    "himanshu": {"password": "1234"},
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= HELPERS =================
def now_ist():
    return datetime.now(UTC).astimezone(IST)

def get_allowed_warehouse_ids(user):
    res = (
        supabase.table("user_warehouses")
        .select("warehouse_id")
        .eq("user_name", user)
        .execute()
    )
    return [r["warehouse_id"] for r in (res.data or []) if r["warehouse_id"]]

def get_first_warehouse(warehouse_ids):
    if not warehouse_ids:
        return None

    res = (
        supabase.table("warehouses")
        .select("id, name")
        .eq("id", warehouse_ids[0])
        .execute()
    )
    return res.data[0] if res.data else None

def upload_photo(photo, user):
    filename = f"{user}/{datetime.now(UTC).timestamp()}.jpg"
    supabase.storage.from_("attendance-photos").upload(
        filename,
        photo.getvalue(),
        {"content-type": photo.type}
    )
    return filename

def save_row(row):
    supabase.table("attendance").insert(row).execute()

# ================= GPS SCRIPT =================
st.markdown("""
<script>
function getLocation(){
  navigator.geolocation.getCurrentPosition(
    function(pos){
      const p = new URLSearchParams(window.location.search);
      p.set("lat", pos.coords.latitude);
      p.set("lon", pos.coords.longitude);
      window.location.search = p.toString();
    },
    function(){ alert("Location denied"); }
  );
}
</script>
""", unsafe_allow_html=True)

# ================= SESSION =================
if "logged" not in st.session_state:
    st.session_state.logged = False
    st.session_state.user = None
    st.session_state.admin = False

st.title("📍 SWISS MILITARY ATTENDANCE SYSTEM")

# ================= LOGIN =================
if not st.session_state.logged:
    u_raw = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        u = u_raw.strip().lower()

        if u == ADMIN_USER and p == ADMIN_PASSWORD:
            st.session_state.logged = True
            st.session_state.admin = True
            st.rerun()

        if u in USERS and USERS[u]["password"] == p:
            st.session_state.logged = True
            st.session_state.user = u
            st.rerun()

        st.error("Invalid credentials")

# ================= USER PANEL =================
if st.session_state.logged and not st.session_state.admin:
    user = st.session_state.user
    today = now_ist().date()

    st.subheader(f"👤 Welcome {user}")
    st.markdown('<button onclick="getLocation()">📍 Get My Location</button>', unsafe_allow_html=True)

    params = dict(st.query_params)
    if "lat" not in params or "lon" not in params:
        st.warning("📍 Get location first")
        st.stop()

    lat = float(params["lat"])
    lon = float(params["lon"])
    st.write("GPS Captured:", lat, lon)

    warehouse_ids = get_allowed_warehouse_ids(user)
    if not warehouse_ids:
        st.error("❌ Aap kisi warehouse ke liye allowed nahi ho")
        st.stop()

    wh = get_first_warehouse(warehouse_ids)
    if not wh:
        st.error("❌ Warehouse not found")
        st.stop()

    st.success(f"🏭 Assigned Warehouse: {wh['name']}")

    photo = st.camera_input("📸 Attendance Photo (Compulsory)")

    if st.button("✅ PUNCH IN"):
        if not photo:
            st.warning("📸 Photo compulsory")
            st.stop()

        save_row({
            "date": today.isoformat(),
            "name": user,
            "punch_type": "IN",
            "time": now_ist().strftime("%H:%M:%S"),
            "lat": lat,
            "lon": lon,
            "warehouse_id": wh["id"],
            "warehouse_name": wh["name"],
            "photo": upload_photo(photo, user),
        })

        st.success("✅ Punch IN successful (GPS check disabled)")

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

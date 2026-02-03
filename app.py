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
ALLOWED_DISTANCE = 500  # meters
IST = pytz.timezone("Asia/Kolkata")

# 👇 USER TYPES ADDED
USERS = {
    "ajad": {"password": "1234", "type": "warehouse"},
    "jitender": {"password": "1234", "type": "warehouse"},
    "ramniwas": {"password": "1234", "type": "warehouse"},

    # FIELD USERS
    "amit": {"password": "1234", "type": "field"},
    "rahul": {"password": "1234", "type": "field"},
    "himanshu": {"password": "1234", "type": "field"},
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= HELPERS =================
def now_ist():
    return datetime.now(UTC).astimezone(IST)

def distance_in_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def get_allowed_warehouse_ids(user):
    res = (
        supabase.table("user_warehouses")
        .select("warehouse_id")
        .eq("user_name", user)
        .execute()
    )
    return [r["warehouse_id"] for r in (res.data or []) if r["warehouse_id"]]

def get_nearest_warehouse(lat, lon, warehouse_ids):
    nearest = None
    min_dist = float("inf")

    for wid in warehouse_ids:
        res = (
            supabase.table("warehouses")
            .select("id, name, lat, lon")
            .eq("id", wid)
            .execute()
        )
        if not res.data:
            continue

        wh = res.data[0]
        if wh["lat"] is None or wh["lon"] is None:
            continue

        dist = distance_in_meters(lat, lon, float(wh["lat"]), float(wh["lon"]))

        if dist < min_dist:
            min_dist = dist
            nearest = {
                "id": wh["id"],
                "name": wh["name"],
                "distance": dist
            }
    return nearest

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
    user_type = USERS[user]["type"]
    today = now_ist().date()

    st.subheader(f"👤 Welcome {user}")
    st.markdown('<button onclick="getLocation()">📍 Get My Location</button>', unsafe_allow_html=True)

    params = dict(st.query_params)
    if "lat" not in params or "lon" not in params:
        st.warning("📍 Get location first")
        st.stop()

    lat = float(params["lat"])
    lon = float(params["lon"])
    st.write("GPS:", lat, lon)

    # 👇 FIELD USERS KO OPTION
    if user_type == "field":
        location_mode = st.radio(
            "📍 Select Location Type",
            ["Existing Location", "New Location"]
        )
    else:
        location_mode = "Existing Location"

    photo = st.camera_input("📸 Attendance Photo (Compulsory)")

    # ================= EXISTING LOCATION =================
    if location_mode == "Existing Location":

        warehouse_ids = get_allowed_warehouse_ids(user)
        if not warehouse_ids:
            st.error("❌ Aap kisi warehouse ke liye allowed nahi ho")
            st.stop()

        nearest_wh = get_nearest_warehouse(lat, lon, warehouse_ids)
        if not nearest_wh or nearest_wh["distance"] > ALLOWED_DISTANCE:
            st.error("❌ Aap allowed warehouse ke paas nahi ho")
            st.stop()

        st.success(f"🏭 Warehouse Detected: {nearest_wh['name']}")

        if st.button("✅ PUNCH IN"):
            if not photo:
                st.warning("📸 Photo required")
                st.stop()

            save_row({
                "date": today.isoformat(),
                "name": user,
                "punch_type": "IN",
                "time": now_ist().strftime("%H:%M:%S"),
                "lat": lat,
                "lon": lon,
                "warehouse_id": nearest_wh["id"],
                "warehouse_name": nearest_wh["name"],
                "photo": upload_photo(photo, user),
            })

            st.success("Punch IN successful")

    # ================= NEW LOCATION =================
    if location_mode == "New Location":

        st.markdown("### 🆕 Add New Location")

        loc_name = st.text_input("Location Name")
        remark = st.text_area("Reason / Remark")

        if st.button("📍 ADD LOCATION & PUNCH IN"):
            if not loc_name.strip() or not remark.strip():
                st.warning("Location name & remark required")
                st.stop()

            if not photo:
                st.warning("Photo compulsory")
                st.stop()

            loc = supabase.table("warehouses").insert({
                "name": loc_name.upper(),
                "lat": lat,
                "lon": lon,
                "type": "FIELD",
                "created_by": user
            }).execute()

            loc_id = loc.data[0]["id"]

            save_row({
                "date": today.isoformat(),
                "name": user,
                "punch_type": "IN",
                "time": now_ist().strftime("%H:%M:%S"),
                "lat": lat,
                "lon": lon,
                "warehouse_id": loc_id,
                "warehouse_name": loc_name.upper(),
                "photo": upload_photo(photo, user),
            })

            supabase.table("attendance_remarks").insert({
                "user_name": user,
                "date": today.isoformat(),
                "time": now_ist().strftime("%H:%M:%S"),
                "remark": remark.upper()
            }).execute()

            st.success("✅ New location added & Punch IN done")

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

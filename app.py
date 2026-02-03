import streamlit as st
import pytz
from datetime import datetime, UTC
from supabase.client import create_client

# ================= SUPABASE =================
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ================= CONFIG =================
IST = pytz.timezone("Asia/Kolkata")

USERS = {
    "amit": {"password": "1234"},
    "rahul": {"password": "1234"},
    "himanshu": {"password": "1234"},
}

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

# ================= HELPERS =================
def now_ist():
    return datetime.now(UTC).astimezone(IST)

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

# ================= AUTO GPS (NO BUTTON) =================
st.markdown("""
<script>
if (!window.location.search.includes("lat")) {
  navigator.geolocation.getCurrentPosition(
    function(pos){
      const p = new URLSearchParams(window.location.search);
      p.set("lat", pos.coords.latitude);
      p.set("lon", pos.coords.longitude);
      window.location.search = p.toString();
    },
    function(){
      console.log("Location denied");
    }
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

    params = dict(st.query_params)
    if "lat" not in params or "lon" not in params:
        st.info("📡 Fetching location automatically...")
        st.stop()

    lat = float(params["lat"])
    lon = float(params["lon"])

    st.caption(f"📍 Location captured: {lat}, {lon}")

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
            "warehouse_id": None,
            "warehouse_name": None,
            "photo": upload_photo(photo, user),
        })

        st.success("✅ Punch IN successful")

# ================= LOGOUT =================
if st.session_state.logged:
    if st.button("Logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

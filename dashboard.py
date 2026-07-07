import streamlit as st
import sqlite3
import pandas as pd
import os
import time
import base64
import cv2
from ultralytics import YOLO
import easyocr
import numpy as np
from datetime import datetime
import plotly.express as px

# 1. PAGE SETUP
st.set_page_config(
    page_title="Automatic Recognition of Vehicle Number Plate",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🖥️ LOCAL IMAGE TO BASE64 HELPER FUNCTION
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# 🎯 DATABASE SETUP (SQLITE)
DB_FILE = "anpr_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_logs (
            id TEXT PRIMARY KEY,
            daily_serial INTEGER,
            vehicle_number TEXT,
            log_date TEXT,
            time_in TEXT,
            time_out TEXT,
            duration_minutes REAL,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

# ડેટાબેઝ ઇનિશિયલાઈઝ કરો
init_db()

# 🎯 માસ્ટર CSS
bg_img_name = "bg.png"
if os.path.exists(bg_img_name):
    bin_str = get_base64_of_bin_file(bg_img_name)
    bg_css = f"""
        <style>
        [data-testid="stAppViewContainer"], 
        .stAppViewContainer, 
        .stApp, 
        [data-testid="stMainViewWithSidebar"] {{
            background-image: linear-gradient(rgba(15, 23, 42, 0.85), rgba(15, 23, 42, 0.92)), 
                              url("data:image/png;base64,{bin_str}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
            background-color: transparent !important;
        }}
        .stMainView, .stAppViewMain, [data-testid="stCanvas"] {{
            background: transparent !important;
            background-color: transparent !important;
        }}
        [data-testid="stHeader"] {{
            background: transparent !important;
            background-color: transparent !important;
        }}
        </style>
    """
else:
    bg_css = """
        <style>
        [data-testid="stAppViewContainer"] { background-color: #0f172a !important; }
        </style>
    """

st.markdown(bg_css, unsafe_allow_html=True)
# 🚫 FINAL TRICK TO REMOVE FLOATING AVATAR AND CROWN LOGO
hide_st_elements = """
    <style>
    /* નીચે દેખાતી આખી ફ્લોટિંગ પટ્ટી (ફોટો અને મુગટ બંને) ગાયબ કરવા માટે */
    div[data-testid="stStatusWidget"],
    div[class*="stActionButton"],
    footer,
    .stDeployButton,
    div[data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* સાઇડમાંથી પણ કોઈ એલિમેન્ટ પોપઅપ ન થાય એના માટે */
    div[class*="viewerBadge"] {
        display: none !important;
    }
    </style>
"""
st.markdown(hide_st_elements, unsafe_allow_html=True)

# 🔐 LOGIN SYSTEM PARAMETERS IN SESSION STATE
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "lock_until" not in st.session_state:
    st.session_state.lock_until = 0.0
if "show_forgot" not in st.session_state:
    st.session_state.show_forgot = False

ADMIN_USER = "admin"
ADMIN_PASS = "akshaya123"
SECURITY_CODE = "9999"

if not st.session_state.logged_in:
    current_time = time.time()
    if current_time < st.session_state.lock_until:
        remaining_lock = int(st.session_state.lock_until - current_time)
        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.error(f"🚨 Too many wrong attempts! System is locked. Please wait {remaining_lock} seconds...")
        time.sleep(1)
        st.rerun()

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        logo_path = r"C:\Users\Admin\Desktop\Social_ANPR_Project\logo.jpeg"
        logo_html = ""
        if os.path.exists(logo_path):
            logo_base64 = get_base64_of_bin_file(logo_path)
            logo_html = f"<img src='data:image/jpeg;base64,{logo_base64}' width='100%' style='max-width:130px; margin-bottom:15px; border-radius:10px; filter: drop-shadow(0px 4px 12px rgba(0,0,0,0.3));'><br>"
        
        # st.markdown(f"""
        #     <div style='background: linear-gradient(135deg, #1e1b4b 0%, #431407 100%); padding: 35px; border-radius: 15px; border: 1px solid #f97316; box-shadow: 0 4px 25px rgba(249, 115, 22, 0.25); text-align: center;'>
        #         {logo_html}
        #         <h2 style='color: white; margin: 0; font-family: "Segoe UI", sans-serif; font-size: 26px; font-weight: 600;">ARVNP Control Panel</h2>
        #         <p style='color: #fdba74; margin-top: 8px; font-size: 14px; margin-bottom: 0;">Please enter your administrative credentials</p>
        #     </div>
        # """, unsafe_allow_html=True)

        st.markdown(f"""<div style='background: linear-gradient(135deg, #1e1b4b 0%, #431407 100%); padding: 35px; border-radius: 15px; border: 1px solid #f97316; box-shadow: 0 4px 25px rgba(249, 115, 22, 0.25); text-align: center;'>{logo_html}<h2 style='color: white; margin: 0; font-family: "Segoe UI", sans-serif; font-size: 26px; font-weight: 600;'>ARVNP Control Panel</h2><p style='color: #fdba74; margin-top: 8px; font-size: 14px; margin-bottom: 0;'>Please enter your administrative credentials</p></div>""", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        
        st.markdown("<br>", unsafe_allow_html=True)
        login_btn = st.button("Login to Dashboard", use_container_width=True)
        
        if login_btn:
            if username == ADMIN_USER and password == ADMIN_PASS:
                st.session_state.logged_in = True
                st.session_state.attempts = 0
                st.success("Successfully logged in!")
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.attempts += 1
                remaining_attempts = max(0, 3 - st.session_state.attempts)
                if st.session_state.attempts >= 3:
                    st.session_state.lock_until = time.time() + 10.0
                    st.session_state.attempts = 0
                    st.error("🚨 3 Wrong attempts reached! System locked for 10 seconds.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Invalid Username or Password. {remaining_attempts} attempts remaining.")

        st.markdown("---")
        if st.button("Forgot Password?", type="secondary", use_container_width=True):
            st.session_state.show_forgot = not st.session_state.show_forgot

        if st.session_state.show_forgot:
            st.markdown("<br>", unsafe_allow_html=True)
            input_code = st.text_input("🔑 Enter Master Security Code to recover password:", type="password", placeholder="Enter 4-digit code")
            if input_code:
                if input_code == SECURITY_CODE:
                    st.markdown(f"""
                        <div style='background-color: #064e3b; padding: 15px; border-radius: 10px; border-left: 4px solid #10b981; margin-top: 10px; text-align: center;'>
                            <p style='margin: 0 0 5px 0; font-size: 13px; color: #a7f3d0;'>✅ <b>Verification Successful:</b> Administrative credentials listed below</p>
                            <p style='margin: 0; color: white; font-size: 14px;'>Username: <code style='color: #34d399; background-color: #022c22; padding: 2px 6px; border-radius: 4px;'>{ADMIN_USER}</code></p>
                            <p style='margin: 4px 0 0 0; color: white; font-size: 14px;'>Password: <code style='color: #34d399; background-color: #022c22; padding: 2px 6px; border-radius: 4px;'>{ADMIN_PASS}</code></p>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("❌ Incorrect Security Code! Access Denied.")
    st.stop()


# ==========================================
# DASHBOARD CODE
# ==========================================

@st.cache_resource
def load_models():
    model = YOLO('yolov8n.pt') 
    reader = easyocr.Reader(['en'], gpu=False) 
    return model, reader

model, reader = load_models()

# SIDEBAR DESIGN
st.sidebar.markdown("""
    <div style='text-align: center; padding-bottom: 10px;'>
        <img src='https://cdn-icons-png.flaticon.com/512/3001/3001764.png' width='90' style='filter: drop-shadow(0px 4px 8px rgba(0,242,254,0.5));'>
        <h2 style='color: white; font-family: "Segoe UI"; margin-top: 10px;'>Admin Panel</h2>
    </div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📷 Camera Control")
run_camera = st.sidebar.checkbox("Turn ON ANPR Camera")

st.sidebar.subheader("🛠️ Quick Filters")
status_filter = st.sidebar.selectbox("Show Vehicles:", ["All Logged", "Currently IN", "Already OUT"])

# 📅 DATE-WISE CATEGORY FILTER
st.sidebar.subheader("📅 Date Wise Sorting")
selected_date = st.sidebar.date_input("Select Date for Logs:", datetime.now().date())
formatted_search_date = selected_date.strftime("%Y-%m-%d")

st.sidebar.markdown("---")

# 💡 DASHBOARD NOTICE ADDED TO SIDEBAR
st.sidebar.markdown("""
    <div style='background-color: #1e293b; padding: 15px; border-radius: 10px; border-left: 4px solid #3b82f6; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.2);'>
        <p style='margin: 0; font-size: 13px; color: white; font-family: "Segoe UI", sans-serif; line-height: 1.5;'>
            💡 <b>DASHBOARD NOTICE:</b><br>
            The system auto-refreshes every 15s when the camera is inactive to sync data logs.
        </p>
    </div>
""", unsafe_allow_html=True)

if not run_camera:
    st.sidebar.markdown("""
        <div style='background-color: #2d1a1a; padding: 15px; border-radius: 10px; border-left: 4px solid #ef4444; margin-bottom: 15px;'>
            <p style='margin: 0; font-size: 13px; color: #fca5a5; font-family: "Segoe UI", sans-serif; line-height: 1.4;'>
                ⚠️ <b>SYSTEM OFFLINE:</b><br>Please enable the <b>"Turn ON ANPR Camera"</b> checkbox above to start live scanning.
            </p>
        </div>
    """, unsafe_allow_html=True)

if st.sidebar.button("Logout From Session", type="primary", use_container_width=True):
    st.session_state.logged_in = False
    st.rerun()

# MAIN DASHBOARD DESIGN
st.markdown("""
    <div style='background: linear-gradient(135deg, #1e1b4b 0%, #431407 100%); padding:25px; border-radius:15px; border: 1px solid #f97316; box-shadow: 0 4px 25px rgba(249, 115, 22, 0.25); margin-bottom:25px;'>
        <h1 style='color: white; margin:0; font-family: "Segoe UI", sans-serif; font-weight: 700; letter-spacing: 0.5px;'>Automatic Recognition of Vehicle Number Plate</h1>
    </div>
""", unsafe_allow_html=True)

# 🗂️ TABS CREATION
tab1, tab2 = st.tabs(["🎥 Live Tracking & Logs", "📊 Traffic Analytics Dashboard"])

# ----------------- TAB 1: LIVE TRACKING -----------------
with tab1:
    if run_camera:
        st.markdown("<h3 style='color: white;'>🎥 Live ANPR Scanner</h3>", unsafe_allow_html=True)
        cam_col, stats_col = st.columns([2.5, 1])
        
        with cam_col:
            frame_placeholder = st.empty()
            detected_text_placeholder = st.empty()
            
        with stats_col:
            stats_placeholder = st.empty()
        
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        frame_count = 0
        last_detected_plate = ""
        last_save_time = 0
        
        while run_camera:
            ret, frame = cap.read()
            if not ret:
                st.error("Failed to grab frame from camera.")
                break

            frame_count += 1

            # SQLite માંથી આજના લાઈવ કાઉન્ટ મેળવો
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vehicle_logs WHERE log_date = ? AND status = 'IN'", (formatted_search_date,))
            live_in = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM vehicle_logs WHERE log_date = ? AND status = 'OUT'", (formatted_search_date,))
            live_out = cursor.fetchone()[0]
            conn.close()

            stats_placeholder.markdown("""
                <div style='background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #3b82f6; text-align: center;'>
                    <h4 style='color: #93c5fd; margin: 0 0 15px 0;'>⚡ Live Camera Counter ({2})</h4>
                    <div style='margin-bottom: 10px;'>
                        <span style='color: #4ade80; font-size: 16px; font-weight: bold;'>🟢 Vehicles IN:</span>
                        <span style='color: white; font-size: 24px; font-weight: bold; margin-left: 10px;'>{0}</span>
                    </div>
                    <div>
                        <span style='color: #f87171; font-size: 16px; font-weight: bold;'>🔴 Vehicles OUT:</span>
                        <span style='color: white; font-size: 24px; font-weight: bold; margin-left: 10px;'>{1}</span>
                    </div>
                </div>
            """.format(live_in, live_out, formatted_search_date), unsafe_allow_html=True)

            if frame_count % 5 == 0:
                results = model(frame, verbose=False)
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cropped_plate = frame[y1:y2, x1:x2]
                        
                        if cropped_plate.size > 0:
                            ocr_result = reader.readtext(cropped_plate, paragraph=False)
                            if ocr_result:
                                plate_text = ocr_result[0][1].strip().upper().replace(" ", "")
                                
                                if len(plate_text) >= 5 and "TOTAL" not in plate_text:
                                    detected_text_placeholder.success(f"🚗 Detected Plate: **{plate_text}**")
                                    current_sec = time.time()
                                    
                                    if plate_text != last_detected_plate or (current_sec - last_save_time > 8):
                                        last_detected_plate = plate_text
                                        last_save_time = current_sec
                                        
                                        now = datetime.now()
                                        today_str = now.strftime("%Y-%m-%d")
                                        
                                        conn = sqlite3.connect(DB_FILE)
                                        cursor = conn.cursor()
                                        
                                        # ચેક કરો કે આ વ્હીકલ ઓલરેડી 'IN' છે કે નહીં
                                        cursor.execute("SELECT id, time_in FROM vehicle_logs WHERE vehicle_number = ? AND status = 'IN' LIMIT 1", (plate_text,))
                                        existing_vehicle = cursor.fetchone()
                                        
                                        if existing_vehicle:
                                            # જો ઓલરેડી IN હોય, તો એને OUT કરો
                                            doc_id = existing_vehicle[0]
                                            time_in_str = f"{today_str} {existing_vehicle[1]}"
                                            time_in_dt = datetime.strptime(time_in_str, "%Y-%m-%d %H:%M:%S")
                                            duration = round((now - time_in_dt).total_seconds() / 60.0, 2)
                                            
                                            cursor.execute("""
                                                UPDATE vehicle_logs 
                                                SET time_out = ?, duration_minutes = ?, status = 'OUT' 
                                                WHERE id = ?
                                            """, (now.strftime("%H:%M:%S"), duration, doc_id))
                                            st.toast(f"🔴 Vehicle OUT: {plate_text}")
                                        else:
                                            # જો નવું વ્હીકલ હોય, તો એને IN કરો
                                            cursor.execute("SELECT COUNT(*) FROM vehicle_logs WHERE log_date = ?", (today_str,))
                                            next_id_count = cursor.fetchone()[0] + 1
                                            unique_doc_id = f"{today_str}_{next_id_count}"
                                            
                                            cursor.execute("""
                                                INSERT INTO vehicle_logs (id, daily_serial, vehicle_number, log_date, time_in, time_out, duration_minutes, status)
                                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                            """, (unique_doc_id, next_id_count, plate_text, today_str, now.strftime("%H:%M:%S"), "-", 0.0, "IN"))
                                            st.toast(f"🟢 Vehicle IN: {plate_text}")
                                        
                                        conn.commit()
                                        conn.close()
                                        
                                        time.sleep(1)
                                        st.rerun()
                        
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            time.sleep(0.01)
            
        cap.release()

    # ડેટાબેઝમાંથી ડિસ્પ્લે માટે ડેટા લાવો
    conn = sqlite3.connect(DB_FILE)
    df_db = pd.read_sql_query("SELECT * FROM vehicle_logs WHERE log_date = ?", conn, params=(formatted_search_date,))
    conn.close()

    if not df_db.empty:
        total_in = len(df_db[df_db['status'] == 'IN'])
        total_out = len(df_db[df_db['status'] == 'OUT'])

        # LOG ID FORMATTING
        df_db['daily_serial'] = df_db['daily_serial'].astype(int)
        df_db = df_db.sort_values(by='daily_serial', ascending=False)
        df_db['Log ID'] = df_db['daily_serial'].apply(lambda x: f"Log #{x}")

        df_disp = df_db[['Log ID', 'vehicle_number', 'log_date', 'time_in', 'time_out', 'duration_minutes', 'status']].copy()
        df_disp.columns = ['Log ID', 'Vehicle Number', 'Date', 'Time In', 'Time Out', 'Duration (Min)', 'Status']
        
        if status_filter == "Currently IN":
            df_disp = df_disp[df_disp['Status'] == 'IN']
        elif status_filter == "Already OUT":
            df_disp = df_disp[df_disp['Status'] == 'OUT']

        # METRIC CARDS
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""<div style='background: #0f172a; padding:22px; border-radius:14px; text-align:center; border: 1px solid #10b981;'><p style='color:#a1a1aa; font-size:13px; margin:0;'>🟢 CURRENTLY IN ({formatted_search_date})</p><h1 style='color:#10b981; margin:8px 0 0 0; font-size:46px;'>{total_in}</h1></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div style='background: #0f172a; padding:22px; border-radius:14px; text-align:center; border: 1px solid #ef4444;'><p style='color:#a1a1aa; font-size:13px; margin:0;'>🔴 TOTAL OUT ({formatted_search_date})</p><h1 style='color:#ef4444; margin:8px 0 0 0; font-size:46px;'>{total_out}</h1></div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div style='background: #0f172a; padding:22px; border-radius:14px; text-align:center; border: 1px solid #f97316;'><p style='color:#a1a1aa; font-size:13px; margin:0;'>TOTAL DAY LOGS</p><h1 style='color:#f97316; margin:8px 0 0 0; font-size:46px;'>{len(df_db)}</h1></div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='color: white; font-family: \"Segoe UI\";'>📋 Live Vehicle Track Management Table ({formatted_search_date})</h3>", unsafe_allow_html=True)
        
        def highlight_status(val):
            if val == 'IN':
                return 'background-color: #064e3b; color: #34d399; font-weight: bold;'
            elif val == 'OUT':
                return 'background-color: #3b0764; color: #d8b4fe; font-weight: bold;'
            return ''

        st.dataframe(df_disp.style.map(highlight_status, subset=['Status']).format({'Duration (Min)': '{:.2f}'}), width="stretch", hide_index=True)
    else:
        st.info(f"No vehicle log entries found for date: {formatted_search_date}")

# ----------------- TAB 2: TRAFFIC ANALYTICS -----------------
with tab2:
    st.markdown(f"<h2 style='color: white;'>📊 Traffic Peak Hours Analytics ({formatted_search_date})</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>This section visualization displays live statistics of peak vehicle traffic hours based on selected calendar date logs.</p>", unsafe_allow_html=True)
    
    conn = sqlite3.connect(DB_FILE)
    df_ana = pd.read_sql_query("SELECT * FROM vehicle_logs WHERE log_date = ?", conn, params=(formatted_search_date,))
    conn.close()

    if not df_ana.empty:
        df_ana['Hour'] = df_ana['time_in'].apply(lambda x: x.split(':')[0] if ':' in str(x) else '00')
        hourly_counts = df_ana.groupby('Hour').size().reset_index(name='Vehicle Count')
        hourly_counts = hourly_counts.sort_values(by='Hour')
        
        def format_hour(h_str):
            try:
                h = int(h_str)
                if h == 0: return "12 AM"
                elif h < 12: return f"{h} AM"
                elif h == 12: return "12 PM"
                else: return f"{h-12} PM"
            except: return h_str
                
        hourly_counts['Time Slot'] = hourly_counts['Hour'].apply(format_hour)

        fig = px.bar(
            hourly_counts, 
            x='Time Slot', 
            y='Vehicle Count',
            text='Vehicle Count',
            labels={'Vehicle Count': 'Number of Vehicles', 'Time Slot': 'Time Slot (Hourly)'},
            title=f"Hourly Vehicle Traffic Distribution on {formatted_search_date}"
        )
        
        fig.update_traces(marker_color='#f97316', marker_line_color='#ffedd5', marker_line_width=1, opacity=0.9, textposition='outside')
        fig.update_layout(
            plot_bgcolor='rgba(15, 23, 42, 0.5)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            title_font_size=20,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#334155'),
            margin=dict(l=40, r=40, t=60, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        try:
            max_row = hourly_counts.loc[hourly_counts['Vehicle Count'].idxmax()]
            st.markdown(f"""
                <div style='background-color: #1e293b; padding: 20px; border-radius: 12px; border-left: 5px solid #f97316; margin-top: 20px;'>
                    <h4 style='margin: 0 0 8px 0; color: #fdba74;'>💡 Peak Hour Insight:</h4>
                    <p style='margin: 0; color: white; font-size: 15px;'>
                        According to system intelligence, the maximum vehicle traffic density on <b>{formatted_search_date}</b> was recorded around <b>{max_row['Time Slot']}</b> with a total of <b>{max_row['Vehicle Count']} vehicles</b> processed.
                    </p>
                </div>
            """, unsafe_allow_html=True)
        except:
            pass
    else:
        st.info(f"Insufficient data logs available for {formatted_search_date} to generate analytics.")

if not run_camera:
    time.sleep(15)
    st.rerun()

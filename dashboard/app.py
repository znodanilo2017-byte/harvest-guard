import streamlit as st
import pandas as pd
import boto3
import json
import plotly.express as px
from io import BytesIO

# --- CONFIG ---
BUCKET_NAME = "harvest-guard-lviv-2025"  # <--- YOUR AGRI BUCKET NAME
st.set_page_config(page_title="Harvest-Guard Monitor", layout="wide")

# --- AUTHENTICATION ---
try:
    # Check if we are on Streamlit Cloud (where secrets exist)
    if "aws" in st.secrets:
        s3 = boto3.client('s3',
                          aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
                          aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
                          region_name=st.secrets["aws"]["aws_default_region"])
    else:
        # Fallback (rare case where secrets file exists but empty)
        s3 = boto3.client('s3')
except FileNotFoundError:
    # We are running locally on your laptop -> Use ~/.aws/credentials
    s3 = boto3.client('s3')

@st.cache_data(ttl=30) # Refresh every 30s
def load_data():
    """Reads the last 100 JSON files from S3"""
    
    # 1. List files
    response = s3.list_objects_v2(Bucket=BUCKET_NAME)
    if 'Contents' not in response:
        return pd.DataFrame()
    
    # 2. Take last 100 files (Sorted by time)
    files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)[:100]
    
    data_list = []
    
    # 3. Download & Parse JSON
    for file in files:
        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=file['Key'])
            content = obj['Body'].read().decode('utf-8')
            json_data = json.loads(content)
            
            # Flatten the data for Pandas
            row = {
                "timestamp": json_data['timestamp'],
                "device_id": json_data['device_id'],
                "temperature": json_data['metrics']['temperature'],
                "moisture": json_data['metrics']['moisture']
            }
            data_list.append(row)
        except Exception as e:
            continue
            
    if not data_list:
        return pd.DataFrame()
        
    # 4. Convert to DataFrame
    df = pd.DataFrame(data_list)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp')
    return df

# --- UI LAYOUT ---
st.title("🚜 Harvest-Guard: Field Monitor")
st.markdown("**Location:** Lviv, Ukraine (Sensor Node 01)")

if st.button("Refresh Sensor Data"):
    st.cache_data.clear()

df = load_data()

if not df.empty:
    # Get latest values
    latest = df.iloc[-1]
    
    # --- KPI METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    
    # Temperature Logic
    temp_color = "normal"
    if latest['temperature'] < 0: temp_color = "inverse" # Frost!
    col1.metric("Air Temperature", f"{latest['temperature']}°C", delta_color=temp_color)
    
    # Moisture Logic
    moist_val = float(latest['moisture'])
    col2.metric("Soil Moisture", f"{moist_val*100:.1f}%")
    
    # Status Logic
    status = "✅ HEALTHY"
    if latest['temperature'] < 0: status = "❄️ FROST WARNING"
    if moist_val < 0.20: status = "🌵 DROUGHT RISK"
    col3.metric("System Status", status)
    
    col4.metric("Last Update", latest['timestamp'].strftime('%H:%M:%S'))

    # --- LOGIC: "SMART IRRIGATION RECOMMENDATION" ---
    # The Business Logic: 
    # If Soil is DRY (< 30%) AND No Rain is coming (< 50%) -> WATER NOW
    # If Soil is DRY (< 30%) BUT Rain IS coming (> 50%) -> WAIT FOR RAIN (Save Money)
    
    latest_moist = float(latest['moisture'])
    latest_rain_prob = float(latest['rain_prob']) if 'rain_prob' in latest else 0
    
    recommendation = "✅ ALL GOOD"
    rec_color = "off"
    
    if latest_moist < 0.30:
        if latest_rain_prob > 50:
            recommendation = "☁️ WAIT FOR RAIN" # Smart decision
            rec_color = "normal"
        else:
            recommendation = "💧 START IRRIGATION" # Critical action
            rec_color = "inverse"
            
    # Add a new metric row
    st.divider()
    st.subheader("🤖 AI Agronomist Recommendation")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rain Probability", f"{latest_rain_prob}%")
    c2.metric("Action Required", recommendation, delta_color=rec_color)

    # --- CHARTS ---
    st.subheader("Real-Time Conditions (Last 100 Readings)")
    
    # Temperature Chart
    fig_temp = px.line(df, x='timestamp', y='temperature', title='Temperature Trend (°C)', markers=True)
    fig_temp.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Freezing Point")
    st.plotly_chart(fig_temp, use_container_width=True)
    
    # Moisture Chart
    fig_moist = px.line(df, x='timestamp', y='moisture', title='Soil Moisture Content (0.0 - 1.0)', markers=True)
    fig_moist.add_hline(y=0.20, line_dash="dash", line_color="orange", annotation_text="Drought Threshold")
    st.plotly_chart(fig_moist, use_container_width=True)

    # Raw Data
    with st.expander("View Raw Sensor Logs"):
        st.dataframe(df.sort_values(by='timestamp', ascending=False))

else:
    st.info("Waiting for sensor data to arrive in S3...")
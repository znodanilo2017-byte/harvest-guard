import streamlit as st
import pandas as pd
import boto3
import json
import plotly.express as px
from io import BytesIO

# --- CONFIG ---
BUCKET_NAME = "harvest-guard-lviv-2025"  # <--- Перевірте, чи назва правильна
st.set_page_config(page_title="Harvest-Guard Monitor", layout="wide")

# --- AUTHENTICATION ---
try:
    if "aws" in st.secrets:
        s3 = boto3.client('s3',
                          aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
                          aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
                          region_name=st.secrets["aws"]["aws_default_region"])
    else:
        s3 = boto3.client('s3')
except FileNotFoundError:
    s3 = boto3.client('s3')

@st.cache_data(ttl=10) # Оновлюємо кожні 10 сек
def load_data():
    """Reads ONLY the new real sensor data from S3 (Prefix: sensor_real_)"""
    
    # 1. Фільтруємо файли: беремо тільки ті, що створила Ламбда
    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="sensor_real_")
    
    if 'Contents' not in response:
        return pd.DataFrame()
    
    # 2. Сортуємо і беремо останні 100 файлів
    files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)[:100]
    
    data_list = []
    
    # 3. Скачуємо та розбираємо JSON
    for file in files:
        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=file['Key'])
            content = obj['Body'].read().decode('utf-8')
            json_data = json.loads(content)
            
            row = {
                "timestamp": json_data['timestamp'],
                "device_id": json_data.get('device_id', 'Unknown'),
                "temperature": json_data['metrics'].get('temperature', 0),
                "moisture": json_data['metrics'].get('moisture', 0)
            }
            data_list.append(row)
        except Exception:
            continue
            
    if not data_list:
        return pd.DataFrame()
        
    df = pd.DataFrame(data_list)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp')
    return df

# --- UI LAYOUT ---
st.title("🚜 Harvest-Guard: Field Monitor")
st.markdown("**Location:** Lviv, Ukraine (Real IoT Sensor Node)")

if st.button("Refresh Sensor Data"):
    st.cache_data.clear()

# --- ОСЬ ЦЕЙ РЯДОК ВИПАВ МИНУЛОГО РАЗУ ---
df = load_data()
# ------------------------------------------

if not df.empty:
    # Get latest values
    latest = df.iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Temperature (поки 0, бо немає термометра)
    col1.metric("Air Temperature", f"{latest['temperature']}°C")
    
    # Moisture Logic
    moist_val = float(latest['moisture'])
    col2.metric("Soil Moisture", f"{moist_val}%")
    
    # Status Logic
    status = "✅ HEALTHY"
    if moist_val < 20: status = "🌵 DROUGHT RISK"
    col3.metric("System Status", status)
    
    # Time
    col4.metric("Last Update", latest['timestamp'].strftime('%H:%M:%S'))

    # --- CHARTS ---
    st.subheader("Real-Time Conditions")
    
    fig_moist = px.line(df, x='timestamp', y='moisture', title='Real Soil Moisture (%)', markers=True)
    fig_moist.add_hline(y=20, line_dash="dash", line_color="orange", annotation_text="Drought Threshold")
    st.plotly_chart(fig_moist, use_container_width=True)

    with st.expander("View Raw Sensor Logs"):
        st.dataframe(df.sort_values(by='timestamp', ascending=False))

else:
    st.warning("Waiting for REAL sensor data (sensor_real_*) to appear in S3...")
    st.info("Tip: Make sure your ESP32 is plugged in and sending data.")
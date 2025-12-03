import requests
import json
import time
import datetime
import boto3
import os

# --- CONFIG ---
# Lviv Coordinates
LAT = 49.83
LON = 24.02
API_URL = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current=temperature_2m,soil_moisture_0_to_1cm,precipitation_probability"
DEVICE_ID = "SENSOR-LVIV-01"

# AWS & Telegram Config
BUCKET_NAME = "harvest-guard-lviv-2025"  # <--- NEW BUCKET NAME
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") #<--- Set in your environment
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID") #<--- Set in your environment

# Safety Check: Crash if keys are missing (so you know you forgot them)
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("❌ Error: Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables.")

# Thresholds
FROST_WARNING = 3.0      # Alert if temp < 3°C
DROUGHT_WARNING = 0.20   # Alert if moisture < 20% (0.20)

s3_client = boto3.client('s3')

def send_alert(metric_name, value, icon):
    """Sends Telegram alert"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    message = (
        f"🚨 <b>HARVEST GUARD ALERT</b> 🚨\n\n"
        f"{icon} <b>{metric_name} Critical: {value}</b>\n"
        f"📍 Location: Lviv Field 1\n"
        f"🕒 Time: {datetime.datetime.now().strftime('%H:%M:%S')}"
    )
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send alert: {e}")

def upload_to_s3(payload):
    """Saves raw JSON to S3 (No Parquet needed for simple JSON logs)"""
    try:
        # File name: sensor_data_20251202_120000.json
        filename = f"sensor_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        s3_client.put_object(
            Bucket=BUCKET_NAME, 
            Key=filename, 
            Body=json.dumps(payload),
            ContentType='application/json'
        )
        print(f"✅ Uploaded to S3: {filename}")
    except Exception as e:
        print(f"❌ S3 Upload Failed: {e}")

def fetch_sensor_data():
    try:
        response = requests.get(API_URL)
        data = response.json()
        current = data['current']
        
        payload = {
            "device_id": DEVICE_ID,
            "timestamp": datetime.datetime.now().isoformat(),
            "metrics": {
                "temperature": current['temperature_2m'],
                "moisture": current['soil_moisture_0_to_1cm'],
                "rain_prob": current['precipitation_probability'] # <--- NEW
            }
        }
        return payload
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

if __name__ == "__main__":
    print(f"🚜 Harvest-Guard Sensor {DEVICE_ID} started...")
    
    while True:
        data = fetch_sensor_data()
        
        if data:
            temp = data['metrics']['temperature']
            moist = data['metrics']['moisture']
            
            print(f"📡 Readings: Temp={temp}°C | Moisture={moist}")
            
            # 1. Upload to Cloud
            upload_to_s3(data)
            
            # 2. Check Alerts
            if temp < FROST_WARNING:
                send_alert("Low Temperature", f"{temp}°C", "❄️")
            
            if moist < DROUGHT_WARNING:
                send_alert("Low Moisture", f"{moist}", "🌵")
            
        time.sleep(60)
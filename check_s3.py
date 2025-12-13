import boto3
import os

# Спробуй знайти змінні оточення або хардкод (якщо локально)
s3 = boto3.client('s3') 
BUCKET_NAME = "harvest-guard-lviv-2025" # <--- ПЕРЕВІР НАЗВУ БАКЕТА!

print(f"🕵️‍♂️ Checking bucket: {BUCKET_NAME}")

# 1. Шукаємо нові файли (Real)
response_real = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="sensor_real_")
if 'Contents' in response_real:
    count = len(response_real['Contents'])
    latest = response_real['Contents'][-1]['Key']
    print(f"✅ FOUND {count} REAL FILES!")
    print(f"   Latest: {latest}")
else:
    print("❌ NO 'sensor_real_' FILES FOUND. Lambda is not writing.")

# 2. Шукаємо старі файли (Simulation)
response_old = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix="sensor_data_")
if 'Contents' in response_old:
    print(f"⚠️  Found {len(response_old['Contents'])} old simulation files (Dec 3).")
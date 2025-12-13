import json
import boto3
import datetime
import os

BUCKET_NAME = os.environ.get('BUCKET_NAME')
s3 = boto3.client('s3')

def lambda_handler(event, context):
    try:
        # ДІАГНОСТИКА: Друкуємо в логи те, що прийшло
        print("📥 RAW EVENT:", json.dumps(event))

        # РОЗУМНИЙ ПАРСИНГ:
        # 1. Якщо це запит через URL (має 'body'), розпаковуємо його
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body'] # Іноді AWS вже розпаковує JSON
        # 2. Якщо це прямий тест або інший формат
        else:
            body = event

        # Перевіряємо, чи є дані
        if not body:
            return {'statusCode': 400, 'body': 'Empty payload'}

        # --- ДАЛІ ВСЕ ЯК РАНІШЕ ---
        timestamp = datetime.datetime.now().isoformat()
        
        payload = {
            "device_id": body.get('device_id', 'UNKNOWN'),
            "timestamp": timestamp,
            "metrics": {
                "temperature": body.get('temperature', 0),
                "moisture": body.get('moisture', 0)
            }
        }
        
        filename = f"sensor_real_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=filename,
            Body=json.dumps(payload),
            ContentType='application/json'
        )
        
        print(f"✅ Saved: {filename}")
        
        return {
            'statusCode': 200,
            'body': json.dumps('✅ Data Saved to S3')
        }
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }
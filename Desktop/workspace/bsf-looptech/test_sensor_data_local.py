"""
Test script to create sample sensor data locally.
"""

import json
import random
from datetime import datetime, timedelta

# Output file
OUTPUT_FILE = "frontend/public/sample_sensor_data.json"

# Farm ID
FARM_ID = "112"

# Device types and IDs
DEVICES = [
    {"type": "temperature", "id": "temp001", "location": "area1"},
    {"type": "humidity", "id": "hum001", "location": "area1"},
    {"type": "temperature", "id": "temp002", "location": "area2"},
    {"type": "humidity", "id": "hum002", "location": "area2"},
    {"type": "pressure", "id": "press001", "location": "area1"},
]

# Generate random sensor readings
def generate_reading(device_type, device_id, location, timestamp):
    if device_type == "temperature":
        value = round(random.uniform(20.0, 30.0), 1)  # 20.0 to 30.0 °C
        unit = "°C"
        measurement_type = "temperature"
    elif device_type == "humidity":
        value = round(random.uniform(40.0, 80.0), 1)  # 40.0 to 80.0 %RH
        unit = "%RH"
        measurement_type = "humidity"
    elif device_type == "pressure":
        value = round(random.uniform(990.0, 1010.0), 1)  # 990.0 to 1010.0 hPa
        unit = "hPa"
        measurement_type = "pressure"
    else:
        value = 0.0
        unit = ""
        measurement_type = ""
    
    return {
        "id": f"{device_id}_{timestamp.strftime('%Y%m%d%H%M%S')}",
        "farm_id": FARM_ID,
        "device_id": device_id,
        "device_type": device_type,
        "measurement_type": measurement_type,
        "value": value,
        "unit": unit,
        "location": location,
        "timestamp": timestamp.isoformat()
    }

# Create sample data for the last 24 hours
def create_sample_data():
    # Start time: 24 hours ago
    start_time = datetime.now() - timedelta(hours=24)
    
    # All readings
    all_readings = []
    
    # Create readings every 30 minutes
    for i in range(48):  # 48 x 30 minutes = 24 hours
        current_time = start_time + timedelta(minutes=30 * i)
        print(f"Creating readings for {current_time}")
        
        # Create readings for each device
        for device in DEVICES:
            reading = generate_reading(device["type"], device["id"], device["location"], current_time)
            all_readings.append(reading)
            print(f"Created reading for {device['id']}: {reading['value']} {reading['unit']}")
    
    # Save to JSON file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_readings, f, indent=2)
    
    print(f"Saved {len(all_readings)} readings to {OUTPUT_FILE}")

if __name__ == "__main__":
    print("Creating sample sensor data...")
    create_sample_data()
    print("Done!")

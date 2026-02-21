#!/usr/bin/env python3
"""
Historical Sensor Data Generator for BSF-LoopTech
Generates realistic sensor data from April 2024 to November 2024

Devices: 20feet-1 to 20feet-5 (type: m5stick)
Data interval: Every 10 seconds

Weather data based on Toyama Fushiki 2024 observations:
- Temperature: Indoor 27.5-28.2°C with 6 AM dip toward external temp
- Humidity: 65% min at 7 AM, rises to 85% after watering, gradual decline
- Pressure: Based on actual meteorological data
- Ammonia: Spikes every 2.5 weeks
"""

import os
import sys
import uuid
import math
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WriteOptions

# ==================== Configuration ====================

# Database settings
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "bsf_user")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "bsf_password")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "bsf_system")

INFLUXDB_URL = os.environ.get("INFLUXDB_URL") or "http://localhost:8086"
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN") or "bsf-secret-token-for-production"
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG") or "bsf_org"
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET") or "bsf_data"

# Data generation settings
FARM_ID = "farm001"
DEVICE_IDS = ["20feet-1", "20feet-2", "20feet-3", "20feet-4", "20feet-5"]
DEVICE_TYPE = "m5stick"
DATA_INTERVAL_SECONDS = 10

# Time range: April 1, 2024 to November 2, 2024
START_DATE = datetime(2024, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime(2024, 11, 2, 23, 59, 59, tzinfo=timezone.utc)

# ==================== Toyama Fushiki Weather Data 2024 ====================

MONTHLY_WEATHER = {
    4: {"avg_temp": 13.6, "max_temp": 17.9, "min_temp": 3.3, "pressure": 1015.2},
    5: {"avg_temp": 17.1, "max_temp": 21.9, "min_temp": 7.1, "pressure": 1013.9},
    6: {"avg_temp": 22.4, "max_temp": 26.7, "min_temp": 13.3, "pressure": 1009.3},
    7: {"avg_temp": 27.1, "max_temp": 31.4, "min_temp": 21.0, "pressure": 1009.2},
    8: {"avg_temp": 28.3, "max_temp": 32.0, "min_temp": 23.1, "pressure": 1007.9},
    9: {"avg_temp": 26.1, "max_temp": 29.8, "min_temp": 18.0, "pressure": 1013.2},
    10: {"avg_temp": 19.2, "max_temp": 23.1, "min_temp": 9.0, "pressure": 1018.8},
    11: {"avg_temp": 12.1, "max_temp": 15.9, "min_temp": 3.8, "pressure": 1019.8},
}

# ==================== Sensor Value Generators ====================

def get_external_temperature(timestamp: datetime) -> float:
    """Get external temperature based on Toyama Fushiki weather data."""
    month = timestamp.month
    hour = timestamp.hour
    weather = MONTHLY_WEATHER[month]

    # Daily temperature cycle: coldest at 5-6 AM, warmest at 14-15 PM
    # Use sine wave approximation
    hour_offset = (hour - 5) % 24  # 5 AM is the coldest
    daily_factor = math.sin((hour_offset / 24) * math.pi)

    temp_range = weather["max_temp"] - weather["min_temp"]
    temp = weather["min_temp"] + (temp_range * daily_factor)

    # Add daily variation noise
    temp += random.uniform(-1.5, 1.5)

    return temp


def get_temperature(timestamp: datetime, device_idx: int, external_temp: float) -> float:
    """
    Generate indoor temperature (27.5-28.2°C).
    At 6 AM, temperature dips toward external temp and recovers in ~1 hour.
    """
    hour = timestamp.hour
    minute = timestamp.minute

    # Base indoor temperature
    base_temp = 27.85  # Center of 27.5-28.2 range

    # Add device-specific offset (each sensor slightly different)
    device_offset = (device_idx - 2) * 0.05  # Range: -0.1 to +0.1

    # Daily cycle: slightly cooler at night, warmer during day
    daily_cycle = 0.15 * math.sin((hour - 6) / 24 * 2 * math.pi)

    # 6 AM dip effect (influence from external temperature)
    dip_effect = 0.0
    if 5 <= hour <= 7:
        # Calculate time from 6:00 AM in minutes
        minutes_from_6am = (hour - 6) * 60 + minute
        if hour == 5:
            minutes_from_6am = minute - 60  # Negative before 6 AM

        # External influence is strongest at 6:00, fades over ~60 minutes
        if -30 <= minutes_from_6am <= 60:
            # How much external temp differs from indoor
            temp_diff = base_temp - external_temp

            # Peak influence at 6:00 AM (gaussian-like)
            influence = math.exp(-((minutes_from_6am) ** 2) / (2 * 15 ** 2))

            # Max influence: up to 30% of temp difference
            dip_effect = -temp_diff * 0.3 * influence

    # Random noise
    noise = random.uniform(-0.1, 0.1)

    # Calculate final temperature
    temp = base_temp + device_offset + daily_cycle + dip_effect + noise

    # Clamp to realistic range
    return max(27.2, min(28.4, temp))


def get_humidity(timestamp: datetime, device_idx: int) -> float:
    """
    Generate humidity:
    - 65% minimum at 7 AM
    - Rises to 85% after watering (~30 min)
    - Gradual decline throughout the day
    """
    hour = timestamp.hour
    minute = timestamp.minute

    # Base humidity cycle
    if hour < 7:
        # Gradual decline from night to morning minimum
        humidity = 72 - (7 - hour) * 1.0
    elif 7 <= hour < 8:
        # 7 AM is minimum (65%), then watering starts
        if minute < 30:
            # Minimum period
            humidity = 65 + minute * 0.2  # Slow rise as watering starts
        else:
            # Watering effect - rapid rise
            humidity = 71 + (minute - 30) * 0.46  # Rise to ~85 by 8 AM
    elif 8 <= hour < 10:
        # Peak humidity after watering
        humidity = 85 - (hour - 8) * 3 - minute * 0.05
    elif 10 <= hour < 18:
        # Gradual decline during day
        humidity = 79 - (hour - 10) * 1.5 - minute * 0.025
    else:
        # Evening/night: stable around 70-72%
        humidity = 70 + random.uniform(0, 2)

    # Device-specific variation
    device_offset = (device_idx - 2) * 0.8  # Range: -1.6 to +1.6

    # Random noise
    noise = random.uniform(-1.5, 1.5)

    humidity = humidity + device_offset + noise

    # Clamp to realistic range
    return max(60, min(90, humidity))


def get_pressure(timestamp: datetime) -> float:
    """Get atmospheric pressure based on Toyama Fushiki weather data."""
    month = timestamp.month
    base_pressure = MONTHLY_WEATHER[month]["pressure"]

    # Add daily variation (pressure typically higher in morning)
    hour = timestamp.hour
    daily_var = 1.5 * math.sin((hour - 10) / 24 * 2 * math.pi)

    # Add random weather variation
    weather_var = random.uniform(-3, 3)

    return base_pressure + daily_var + weather_var


def get_ammonia(timestamp: datetime, device_idx: int) -> float:
    """
    Generate ammonia (NH3) levels:
    - Baseline: 5-15 ppm
    - Spikes every 2.5 weeks (peak around 50-80 ppm)
    """
    # Calculate days since start
    days_since_start = (timestamp - START_DATE).days

    # 2.5 weeks = 17.5 days
    cycle_position = (days_since_start % 17.5) / 17.5

    # Spike occurs at the beginning of each cycle (days 0-3)
    if cycle_position < 0.17:  # First ~3 days of cycle
        # Spike intensity varies
        spike_phase = cycle_position / 0.17
        if spike_phase < 0.3:
            # Rising
            spike_value = 15 + spike_phase / 0.3 * 50  # Rise to ~65
        elif spike_phase < 0.5:
            # Peak
            spike_value = 65 + random.uniform(-10, 15)
        else:
            # Falling
            spike_value = 65 - (spike_phase - 0.5) / 0.5 * 50

        base = spike_value
    else:
        # Normal baseline
        base = random.uniform(5, 15)

    # Add hourly variation (slightly higher during day due to activity)
    hour = timestamp.hour
    hourly_var = 2 * math.sin((hour - 6) / 24 * 2 * math.pi)

    # Device variation
    device_offset = (device_idx - 2) * 1.5

    # Random noise
    noise = random.uniform(-2, 2)

    nh3 = base + hourly_var + device_offset + noise

    return max(2, min(100, nh3))


def get_h2s(timestamp: datetime, device_idx: int) -> float:
    """
    Generate H2S levels:
    - Baseline: 0.5-3 ppm (lower than ammonia)
    - Correlates somewhat with ammonia spikes
    """
    # Get ammonia level for correlation
    nh3 = get_ammonia(timestamp, device_idx)

    # H2S is typically 5-10% of NH3 levels
    h2s_base = nh3 * 0.08 + random.uniform(0.3, 1.0)

    # Device variation
    device_offset = (device_idx - 2) * 0.2

    return max(0.1, min(15, h2s_base + device_offset))


# ==================== Database Operations ====================

def create_devices():
    """Create 5 sensor devices in PostgreSQL."""
    print("Creating devices in PostgreSQL...")

    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB
    )

    cursor = conn.cursor()

    # Check if devices already exist
    cursor.execute(
        "SELECT device_id FROM sensor_devices WHERE device_id = ANY(%s)",
        (DEVICE_IDS,)
    )
    existing = {row[0] for row in cursor.fetchall()}

    devices_created = 0
    for i, device_id in enumerate(DEVICE_IDS):
        if device_id in existing:
            print(f"  Device {device_id} already exists, skipping")
            continue

        # Generate position (spread across 20-foot container)
        # Container approx 6m x 2.4m x 2.4m
        x_pos = 1.0 + i * 1.0  # 1m to 5m along length
        y_pos = 1.2  # Center of width
        z_pos = 0.5 + (i % 2) * 0.5  # Alternate heights

        cursor.execute("""
            INSERT INTO sensor_devices
            (id, device_id, device_type, name, description, farm_id,
             location, position_x, position_y, position_z, status, is_online, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            str(uuid.uuid4()),
            device_id,
            DEVICE_TYPE,
            f"BSF Sensor {device_id}",
            f"M5StickC environmental sensor in 20-foot container, position {i+1}",
            FARM_ID,
            "20feet-container",
            x_pos,
            y_pos,
            z_pos,
            "active",
            True,
            datetime.now(timezone.utc),
            datetime.now(timezone.utc)
        ))
        devices_created += 1
        print(f"  Created device: {device_id}")

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Created {devices_created} new devices")
    return devices_created


def write_batch_line_protocol(lines: List[str], max_retries: int = 3) -> bool:
    """Write batch of line protocol data using HTTP API directly."""
    import urllib.request
    import urllib.error

    data = "\n".join(lines).encode('utf-8')
    url = f"{INFLUXDB_URL}/api/v2/write?org={INFLUXDB_ORG}&bucket={INFLUXDB_BUCKET}&precision=ns"

    headers = {
        "Authorization": f"Token {INFLUXDB_TOKEN}",
        "Content-Type": "text/plain; charset=utf-8",
    }

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.status == 204
        except urllib.error.HTTPError as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(1 * (attempt + 1))
            else:
                print(f"Failed to write batch after {max_retries} attempts: {e}")
                return False
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                time.sleep(1 * (attempt + 1))
            else:
                print(f"Error writing batch: {e}")
                return False
    return False


def generate_and_write_sensor_data():
    """Generate and write historical sensor data to InfluxDB using line protocol."""
    print("\nGenerating data and writing to InfluxDB...")
    print(f"Time range: {START_DATE} to {END_DATE}")
    print(f"Data interval: {DATA_INTERVAL_SECONDS} seconds")

    # Calculate total points
    total_seconds = int((END_DATE - START_DATE).total_seconds())
    points_per_device = total_seconds // DATA_INTERVAL_SECONDS
    total_points = points_per_device * len(DEVICE_IDS)

    print(f"Total data points to generate: {total_points:,}")
    print(f"Points per device: {points_per_device:,}")

    # Batch configuration
    BATCH_SIZE = 10000  # Lines per batch
    lines_buffer = []
    points_written = 0
    batches_written = 0
    last_progress = -1

    print("\nGenerating and writing data...")

    current_time = START_DATE
    while current_time <= END_DATE:
        external_temp = get_external_temperature(current_time)
        timestamp_ns = int(current_time.timestamp() * 1_000_000_000)

        for device_idx, device_id in enumerate(DEVICE_IDS):
            # Generate sensor values
            temperature = get_temperature(current_time, device_idx, external_temp)
            humidity = get_humidity(current_time, device_idx)
            pressure = get_pressure(current_time)
            nh3 = get_ammonia(current_time, device_idx)
            h2s = get_h2s(current_time, device_idx)

            # Create line protocol string
            # Format: measurement,tags fields timestamp
            line = (
                f"sensor_data,farm_id={FARM_ID},device_id={device_id},device_type={DEVICE_TYPE} "
                f"temperature={temperature:.2f},humidity={humidity:.2f},pressure={pressure:.2f},"
                f"nh3={nh3:.2f},h2s={h2s:.2f} {timestamp_ns}"
            )
            lines_buffer.append(line)
            points_written += 1

            # Write batch when buffer is full
            if len(lines_buffer) >= BATCH_SIZE:
                if write_batch_line_protocol(lines_buffer):
                    batches_written += 1
                else:
                    print(f"Warning: Failed to write batch {batches_written + 1}")
                lines_buffer = []

        # Progress update every 1%
        progress = int((points_written / total_points) * 100)
        if progress > last_progress:
            print(f"  Progress: {progress}% ({points_written:,} / {total_points:,} points, {batches_written} batches)")
            last_progress = progress

        current_time += timedelta(seconds=DATA_INTERVAL_SECONDS)

    # Write remaining data
    if lines_buffer:
        if write_batch_line_protocol(lines_buffer):
            batches_written += 1
        else:
            print(f"Warning: Failed to write final batch")

    print(f"\nCompleted! Total points written: {points_written:,}")
    print(f"Total batches: {batches_written}")
    return points_written


def verify_data():
    """Verify data was written correctly."""
    print("\nVerifying data in InfluxDB...")

    client = InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG
    )

    query_api = client.query_api()

    # Count records per device
    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: 2024-04-01T00:00:00Z, stop: 2024-11-03T00:00:00Z)
        |> filter(fn: (r) => r._measurement == "sensor_data")
        |> filter(fn: (r) => r._field == "temperature")
        |> group(columns: ["device_id"])
        |> count()
    '''

    result = query_api.query(query)

    print("Records per device:")
    for table in result:
        for record in table.records:
            print(f"  {record.values.get('device_id')}: {record.get_value():,} records")

    # Sample data check
    print("\nSample data (first device, most recent):")
    sample_query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
        |> range(start: 2024-04-01T00:00:00Z, stop: 2024-11-03T00:00:00Z)
        |> filter(fn: (r) => r._measurement == "sensor_data")
        |> filter(fn: (r) => r.device_id == "20feet-1")
        |> last()
    '''

    result = query_api.query(sample_query)
    for table in result:
        for record in table.records:
            print(f"  {record.get_field()}: {record.get_value()}")

    client.close()


def main():
    """Main function to generate historical data."""
    print("=" * 60)
    print("BSF-LoopTech Historical Data Generator")
    print("=" * 60)
    print(f"\nTime range: {START_DATE.date()} to {END_DATE.date()}")
    print(f"Devices: {', '.join(DEVICE_IDS)}")
    print(f"Device type: {DEVICE_TYPE}")
    print()

    # Create devices
    create_devices()

    # Generate and write sensor data
    generate_and_write_sensor_data()

    # Verify data
    verify_data()

    print("\n" + "=" * 60)
    print("Data generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

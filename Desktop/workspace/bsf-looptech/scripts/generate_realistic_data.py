#!/usr/bin/env python3
"""
Realistic BSF Sensor Data Generator

Generates sensor data based on Toyama Fushiki weather patterns.
Period: 2024-04-01 to 2025-12-02 16:00
Interval: 10 seconds

Conditions:
- Temperature: 28°C ± 2°C (range: 26-30°C)
- Humidity: 80-90%
- NH3: 25ppm when temp≥28.3°C AND humidity≥90% for 3+ hours
       Otherwise: 2-week cycle with 3-day peak at 10ppm, gradual decline to 2ppm
- H2S: Only when NH3 is at maximum
- Pressure: Based on Toyama Fushiki weather data
- Data distribution: Device 3 < Device 5 < Device 4 = Device 2 = Device 1
"""

import os
import sys
import math
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/data_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS, WriteOptions

# ==================== Configuration ====================

INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "bsf-secret-token-for-production")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "bsf_org")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "bsf_data")

FARM_ID = "farm001"
DEVICE_IDS = ["20feet-1", "20feet-2", "20feet-3", "20feet-4", "20feet-5"]
DEVICE_TYPE = "m5stick"
DATA_INTERVAL_SECONDS = 10

# Data distribution: Device 3 < Device 5 < Device 4 = Device 2 = Device 1
# Skip rates: higher = less data
# Device 1, 2, 4 (indices 0, 1, 3): 0% skip (all data)
# Device 5 (index 4): 30% skip
# Device 3 (index 2): 60% skip
DEVICE_SKIP_RATES = {
    0: 0.0,   # Device 1: 100% data
    1: 0.0,   # Device 2: 100% data
    2: 0.6,   # Device 3: 40% data (60% skip)
    3: 0.0,   # Device 4: 100% data
    4: 0.3,   # Device 5: 70% data (30% skip)
}

# Time range
START_DATE = datetime(2024, 4, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime(2025, 12, 2, 16, 0, 0, tzinfo=timezone.utc)

# Batch settings for efficient writing
BATCH_SIZE = 50000  # Points per batch
WRITE_INTERVAL_HOURS = 6  # Write data every N hours worth

# ==================== Toyama Fushiki Weather Data ====================

# Monthly average pressure (hPa) based on Toyama Fushiki observations
MONTHLY_PRESSURE = {
    1: 1020.5, 2: 1018.3, 3: 1015.8, 4: 1015.2, 5: 1013.9, 6: 1009.3,
    7: 1009.2, 8: 1007.9, 9: 1013.2, 10: 1018.8, 11: 1019.8, 12: 1020.2
}

# Daily pressure variation amplitude (hPa)
PRESSURE_DAILY_AMPLITUDE = 2.5

# ==================== Sensor Value Generators ====================

class SensorDataGenerator:
    def __init__(self):
        self.high_temp_humidity_start = None
        self.nh3_cycle_day = 0  # Day within 14-day cycle
        self.nh3_peak_active = False
        self.last_day = None

    def get_temperature(self, timestamp: datetime, device_idx: int) -> float:
        """
        Generate indoor temperature (28°C ± 2°C).
        Uses daily variation pattern based on Toyama Fushiki.
        Range: 26-30°C
        """
        hour = timestamp.hour
        minute = timestamp.minute
        second = timestamp.second

        # Base indoor temperature
        base_temp = 28.0

        # Daily variation: slightly cooler at night (around 6 AM), warmer in afternoon (around 14:00)
        hour_decimal = hour + minute / 60 + second / 3600
        # Coldest at 6 AM, warmest at 14:00
        daily_offset = 1.5 * math.sin((hour_decimal - 6) / 24 * 2 * math.pi)

        # Random noise for ±2°C variation
        noise = random.gauss(0, 0.5)

        temp = base_temp + daily_offset + noise

        # Clamp to 26-30°C range
        temp = max(26.0, min(30.0, temp))

        return round(temp, 2)

    def get_humidity(self, timestamp: datetime, device_idx: int, temp: float) -> float:
        """
        Generate humidity in 80-90% range.
        """
        hour = timestamp.hour

        # Base humidity varies with time of day
        # Higher in early morning, lower in afternoon
        hour_decimal = hour + timestamp.minute / 60
        base_humidity = 85.0 + 3 * math.sin((hour_decimal - 2) / 24 * 2 * math.pi)

        # Random noise
        noise = random.gauss(0, 1.5)
        humidity = base_humidity + noise

        # Clamp to 80-90% range
        humidity = max(80.0, min(90.0, humidity))

        return round(humidity, 1)

    def get_nh3(self, timestamp: datetime, temp: float, humidity: float) -> float:
        """
        Generate NH3 values:
        - 25ppm when temp≥28.3°C AND humidity≥90% for 3+ hours
        - Otherwise: 2-week cycle with 3-day peak at 10ppm, gradual decline to 2ppm
        """
        # Check high temp + high humidity condition
        is_high_condition = temp >= 28.3 and humidity >= 90

        if is_high_condition:
            if self.high_temp_humidity_start is None:
                self.high_temp_humidity_start = timestamp

            # Check if 3+ hours have passed
            duration = (timestamp - self.high_temp_humidity_start).total_seconds() / 3600
            if duration >= 3:
                # High NH3 due to environmental conditions
                return round(25 + random.gauss(0, 1), 1)
        else:
            self.high_temp_humidity_start = None

        # 2-week (14-day) cycle logic
        current_day = timestamp.date()
        if self.last_day != current_day:
            self.last_day = current_day
            self.nh3_cycle_day = (self.nh3_cycle_day + 1) % 14

        # Days 0-2: Peak period (rise to 10ppm)
        # Days 3-13: Gradual decline to 2ppm
        if self.nh3_cycle_day < 3:
            # Peak period: around 10ppm
            nh3 = 8 + (self.nh3_cycle_day + 1) * 0.7 + random.gauss(0, 0.5)
        else:
            # Decline period: exponential decay from 10 to 2
            days_since_peak = self.nh3_cycle_day - 2
            # Decay from 10 to 2 over 11 days
            decay_factor = math.exp(-days_since_peak * 0.15)
            nh3 = 2 + 8 * decay_factor + random.gauss(0, 0.3)

        return round(max(1.5, min(12, nh3)), 1)

    def get_h2s(self, nh3: float) -> float:
        """
        Generate H2S values - only appears when NH3 is at its worst.
        """
        if nh3 >= 20:
            # H2S appears when NH3 is very high
            h2s = 0.5 + (nh3 - 20) * 0.1 + random.gauss(0, 0.1)
            return round(max(0.1, min(2, h2s)), 2)
        elif nh3 >= 8:
            # Trace amounts
            h2s = 0.05 + random.gauss(0, 0.02)
            return round(max(0, min(0.2, h2s)), 2)
        else:
            # Negligible
            return round(max(0, random.gauss(0.01, 0.01)), 3)

    def get_pressure(self, timestamp: datetime) -> float:
        """
        Generate pressure based on Toyama Fushiki monthly averages with daily variation.
        """
        month = timestamp.month
        hour = timestamp.hour

        # Base pressure from monthly average
        base_pressure = MONTHLY_PRESSURE[month]

        # Daily variation (pressure tends to be higher in morning, lower in afternoon)
        hour_decimal = hour + timestamp.minute / 60
        daily_variation = PRESSURE_DAILY_AMPLITUDE * math.cos((hour_decimal - 10) / 24 * 2 * math.pi)

        # Random weather variation
        weather_noise = random.gauss(0, 1.5)

        pressure = base_pressure + daily_variation + weather_noise

        return round(pressure, 1)


def generate_data():
    """Main data generation function."""
    logger.info("=" * 60)
    logger.info("Starting BSF Realistic Data Generation")
    logger.info(f"Period: {START_DATE} to {END_DATE}")
    logger.info(f"Interval: {DATA_INTERVAL_SECONDS} seconds")
    logger.info("=" * 60)

    # Connect to InfluxDB
    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=WriteOptions(
        batch_size=5000,
        flush_interval=10000,
        jitter_interval=2000,
        retry_interval=5000
    ))

    # Initialize generator
    generator = SensorDataGenerator()

    # Calculate total data points
    total_seconds = (END_DATE - START_DATE).total_seconds()
    total_intervals = int(total_seconds / DATA_INTERVAL_SECONDS)
    total_points = total_intervals * len(DEVICE_IDS) * 5  # 5 measurement types

    logger.info(f"Total intervals: {total_intervals:,}")
    logger.info(f"Total data points to generate: {total_points:,}")

    current_time = START_DATE
    points_written = 0
    batch_points = []
    last_log_time = datetime.now()
    start_gen_time = datetime.now()

    try:
        while current_time <= END_DATE:
            # Generate data for each device
            for device_idx, device_id in enumerate(DEVICE_IDS):
                # Apply skip rate for data distribution
                # Device 3 < Device 5 < Device 4 = Device 2 = Device 1
                skip_rate = DEVICE_SKIP_RATES.get(device_idx, 0.0)
                if random.random() < skip_rate:
                    continue  # Skip this data point for this device

                # Use current time for all devices (no offset)
                sample_time = current_time

                # Generate sensor values
                temp = generator.get_temperature(sample_time, device_idx)
                humidity = generator.get_humidity(sample_time, device_idx, temp)
                nh3 = generator.get_nh3(sample_time, temp, humidity)
                h2s = generator.get_h2s(nh3)
                pressure = generator.get_pressure(sample_time)

                # Create data points for each measurement type
                measurements = [
                    ("temperature", temp, "°C"),
                    ("humidity", humidity, "%"),
                    ("nh3", nh3, "ppm"),
                    ("h2s", h2s, "ppm"),
                    ("pressure", pressure, "hPa")
                ]

                for mtype, value, unit in measurements:
                    point = Point("sensor_data") \
                        .tag("farm_id", FARM_ID) \
                        .tag("device_id", device_id) \
                        .tag("device_type", DEVICE_TYPE) \
                        .tag("measurement_type", mtype) \
                        .tag("unit", unit) \
                        .field("value", float(value)) \
                        .time(current_time)

                    batch_points.append(point)
                    points_written += 1

            # Write batch if large enough
            if len(batch_points) >= BATCH_SIZE:
                write_api.write(bucket=INFLUXDB_BUCKET, record=batch_points)
                batch_points = []

                # Log progress every 30 seconds
                if (datetime.now() - last_log_time).total_seconds() >= 30:
                    progress = points_written / total_points * 100
                    elapsed = (datetime.now() - start_gen_time).total_seconds()
                    rate = points_written / elapsed if elapsed > 0 else 0
                    eta_seconds = (total_points - points_written) / rate if rate > 0 else 0
                    eta_hours = eta_seconds / 3600

                    logger.info(
                        f"Progress: {progress:.2f}% | "
                        f"Points: {points_written:,}/{total_points:,} | "
                        f"Current: {current_time} | "
                        f"Rate: {rate:.0f} pts/s | "
                        f"ETA: {eta_hours:.1f}h"
                    )
                    last_log_time = datetime.now()

            # Move to next interval
            current_time += timedelta(seconds=DATA_INTERVAL_SECONDS)

        # Write remaining points
        if batch_points:
            write_api.write(bucket=INFLUXDB_BUCKET, record=batch_points)

        # Close connections
        write_api.close()
        client.close()

        total_time = (datetime.now() - start_gen_time).total_seconds() / 3600
        logger.info("=" * 60)
        logger.info(f"Data generation completed!")
        logger.info(f"Total points written: {points_written:,}")
        logger.info(f"Total time: {total_time:.2f} hours")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error during data generation: {e}")
        raise
    finally:
        try:
            write_api.close()
            client.close()
        except:
            pass


if __name__ == "__main__":
    generate_data()

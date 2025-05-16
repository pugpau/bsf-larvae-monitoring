# Data Flow

This document describes the data flow within the BSF Larvae Monitoring System.

## Sensor Data Flow

```mermaid
sequenceDiagram
    participant Sensor as Sensor Device
    participant MQTT as MQTT Broker
    participant Backend as FastAPI Backend
    participant InfluxDB as InfluxDB
    participant Frontend as Frontend App
    
    Sensor->>MQTT: Publish sensor data
    MQTT->>Backend: Message received
    Backend->>Backend: Parse and validate data
    Backend->>InfluxDB: Write data to database
    Frontend->>Backend: Request sensor data
    Backend->>InfluxDB: Query data
    InfluxDB->>Backend: Return query results
    Backend->>Frontend: Return formatted data
    Frontend->>Frontend: Display data
```

## Substrate Management Flow

```mermaid
sequenceDiagram
    participant Frontend as Frontend App
    participant Backend as FastAPI Backend
    participant Database as Database
    
    Frontend->>Backend: Create substrate type
    Backend->>Backend: Validate data
    Backend->>Database: Store substrate type
    Database->>Backend: Confirmation
    Backend->>Frontend: Response
    
    Frontend->>Backend: Create substrate batch
    Backend->>Backend: Validate data
    Backend->>Database: Store substrate batch
    Database->>Backend: Confirmation
    Backend->>Frontend: Response
    
    Frontend->>Backend: Update batch status
    Backend->>Backend: Validate data
    Backend->>Database: Update status
    Backend->>Database: Record change history
    Database->>Backend: Confirmation
    Backend->>Frontend: Response
```

## MQTT Topic Structure

The system uses the following MQTT topic structure:

```
bsf/{farm_id}/{device_type}/{device_id}
```

Example topics:
- `bsf/farm001/temperature/device001`
- `bsf/farm001/humidity/device002`
- `bsf/farm001/pressure/device003`

## MQTT Payload Format

```json
{
  "timestamp": "2023-01-01T00:00:00Z",
  "measurements": {
    "temperature": 25.5,
    "humidity": 60,
    "pressure": 1013.25
  }
}
```

## InfluxDB Data Model

The system uses InfluxDB to store time-series data with the following structure:

- Measurement: `sensor_data`
- Tags:
  - `farm_id`: The ID of the farm
  - `device_id`: The ID of the device
  - `device_type`: The type of device (e.g., temperature, humidity)
- Fields: Varies depending on the sensor type (e.g., temperature, humidity, pressure)
- Time: Timestamp of the measurement

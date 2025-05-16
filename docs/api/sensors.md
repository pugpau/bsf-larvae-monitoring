# Sensors API

The Sensors API provides endpoints for retrieving and managing sensor data.

## Base URL

```
/sensors
```

## Endpoints

### Get Sensor Data

```
GET /sensors/data
```

Retrieves sensor data with optional filters.

#### Query Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| farm_id | string | Filter by farm ID |
| device_id | string | Filter by device ID |
| device_type | string | Filter by device type |
| measurement_type | string | Filter by measurement type (e.g., temperature) |
| start_time | string | Start time for query range (ISO format) |
| end_time | string | End time for query range (ISO format) |
| limit | integer | Maximum number of records to return (default: 100) |

#### Response

```json
[
  {
    "time": "2023-01-01T00:00:00Z",
    "farm_id": "farm123",
    "device_id": "device456",
    "device_type": "temperature_sensor",
    "field": "temperature",
    "value": 25.5
  }
]
```

### Get Device Sensor Data

```
GET /sensors/data/{farm_id}/{device_id}
```

Retrieves sensor data for a specific device.

#### Path Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| farm_id | string | The farm ID |
| device_id | string | The device ID |

#### Query Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| device_type | string | Filter by device type |
| measurement_type | string | Filter by measurement type (e.g., temperature) |
| start_time | string | Start time for query range (ISO format) |
| end_time | string | End time for query range (ISO format) |
| limit | integer | Maximum number of records to return (default: 100) |

#### Response

Same as GET /sensors/data

### Get Latest Farm Data

```
GET /sensors/latest/{farm_id}
```

Gets the latest sensor readings for all devices in a farm.

#### Path Parameters

| Parameter | Type | Description |
| --------- | ---- | ----------- |
| farm_id | string | The farm ID |

#### Response

```json
{
  "device123": {
    "device_type": "temperature_sensor",
    "last_updated": "2023-01-01T00:00:00Z",
    "measurements": {
      "temperature": 25.5,
      "humidity": 60
    }
  }
}
```

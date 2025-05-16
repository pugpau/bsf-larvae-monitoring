# Backend Setup Guide

This guide provides instructions for setting up the backend components of the BSF Larvae Monitoring System.

## Prerequisites

- Python 3.10 or higher
- InfluxDB 2.7+
- EMQX MQTT Broker 5.0+

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/pugpau/bsf-larvae-monitoring.git
   cd bsf-larvae-monitoring
   ```

2. Set up a Python virtual environment:

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Create a `.env` file in the backend directory with the following variables:

```
# Server settings
PORT=8000
LOG_LEVEL=info

# InfluxDB settings
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=your_organization
INFLUXDB_BUCKET=bsf_monitoring

# MQTT settings
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
MQTT_USERNAME=your_mqtt_username
MQTT_PASSWORD=your_mqtt_password
MQTT_TLS_ENABLED=false
# If TLS is enabled, set these:
# MQTT_CA_CERTS=/path/to/ca.crt
# MQTT_CLIENT_CERT=/path/to/client.crt
# MQTT_CLIENT_KEY=/path/to/client.key
```

## Running the Backend

Start the FastAPI server:

```bash
python -m src.main
```

The API will be available at `http://localhost:8000`.

## API Documentation

The FastAPI documentation is available at `http://localhost:8000/docs`.

## Testing

Run the tests:

```bash
pytest
```

## InfluxDB Setup

1. Install InfluxDB 2.x
2. Create a new organization and bucket
3. Generate an API token with read/write access to the bucket
4. Update the `.env` file with your InfluxDB configuration

## MQTT Broker Setup

1. Install EMQX MQTT Broker
2. Configure authentication (username/password)
3. Update the `.env` file with your MQTT configuration

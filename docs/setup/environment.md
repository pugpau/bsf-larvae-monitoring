# Environment Configuration Guide

This guide provides details about the environment variables used in the BSF Larvae Monitoring System.

## Backend Environment Variables

| Variable | Description | Default | Required |
| -------- | ----------- | ------- | -------- |
| PORT | The port to run the backend server | 8000 | No |
| LOG_LEVEL | The log level (debug, info, warning, error) | info | No |
| INFLUXDB_URL | The URL of the InfluxDB server | | Yes |
| INFLUXDB_TOKEN | The InfluxDB API token | | Yes |
| INFLUXDB_ORG | The InfluxDB organization | | Yes |
| INFLUXDB_BUCKET | The InfluxDB bucket | | Yes |
| MQTT_BROKER_HOST | The hostname of the MQTT broker | | Yes |
| MQTT_BROKER_PORT | The port of the MQTT broker | 1883 | No |
| MQTT_USERNAME | The MQTT username | | No |
| MQTT_PASSWORD | The MQTT password | | No |
| MQTT_TLS_ENABLED | Whether to use TLS for MQTT | false | No |
| MQTT_CA_CERTS | The path to the CA certificates | | Only if TLS enabled |
| MQTT_CLIENT_CERT | The path to the client certificate | | Only if TLS enabled |
| MQTT_CLIENT_KEY | The path to the client key | | Only if TLS enabled |

## Frontend Environment Variables

| Variable | Description | Default | Required |
| -------- | ----------- | ------- | -------- |
| REACT_APP_API_BASE_URL | The base URL of the backend API | | Yes |

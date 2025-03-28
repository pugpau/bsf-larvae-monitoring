import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

# Load .env file from the root directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MQTT Settings
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_TLS_ENABLED: bool = False
    MQTT_CA_CERTS: Optional[str] = None
    MQTT_CLIENT_CERT: Optional[str] = None
    MQTT_CLIENT_KEY: Optional[str] = None

    # InfluxDB Settings
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: str = "default_token" # Provide a default or ensure it's set
    INFLUXDB_ORG: str = "default_org"     # Provide a default or ensure it's set
    INFLUXDB_BUCKET: str = "bsf_data"

    # API Settings
    ERP_API_ENDPOINT: Optional[str] = None
    ERP_API_KEY: Optional[str] = None

    # Application Settings
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "default_secret_key" # Ensure a strong default or generation mechanism

    # Control System Settings
    CONTROL_SYSTEM_API_ENDPOINT: Optional[str] = None
    CONTROL_SYSTEM_API_KEY: Optional[str] = None

    # Define the location of the .env file if needed explicitly
    # class Config:
    #     env_file = '.env'
    #     env_file_encoding = 'utf-8'

# Instantiate settings
settings = Settings()

# Example usage (can be removed later)
if __name__ == "__main__":
    print("MQTT Broker Host:", settings.MQTT_BROKER_HOST)
    print("InfluxDB URL:", settings.INFLUXDB_URL)
    print("InfluxDB Org:", settings.INFLUXDB_ORG)
    print("Log Level:", settings.LOG_LEVEL)
import os
from dotenv import load_dotenv
from typing import Optional

# Load .env file from the root directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # MQTT Settings
        self.MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "localhost")
        self.MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        self.MQTT_USERNAME: Optional[str] = os.getenv("MQTT_USERNAME")
        self.MQTT_PASSWORD: Optional[str] = os.getenv("MQTT_PASSWORD")
        self.MQTT_TLS_ENABLED: bool = os.getenv("MQTT_TLS_ENABLED", "false").lower() in ("true", "1", "yes")
        self.MQTT_CA_CERTS: Optional[str] = os.getenv("MQTT_CA_CERTS")
        self.MQTT_CLIENT_CERT: Optional[str] = os.getenv("MQTT_CLIENT_CERT")
        self.MQTT_CLIENT_KEY: Optional[str] = os.getenv("MQTT_CLIENT_KEY")

        # InfluxDB Settings
        self.INFLUXDB_URL: str = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.INFLUXDB_TOKEN: str = os.getenv("INFLUXDB_TOKEN", "default_token")
        self.INFLUXDB_ORG: str = os.getenv("INFLUXDB_ORG", "default_org")
        self.INFLUXDB_BUCKET: str = os.getenv("INFLUXDB_BUCKET", "bsf_data")

        # PostgreSQL Settings
        self.POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
        self.POSTGRES_USER: str = os.getenv("POSTGRES_USER", "bsf_user")
        self.POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "bsf_password")
        self.POSTGRES_DB: str = os.getenv("POSTGRES_DB", "bsf_system")
        self.DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

        # API Settings
        self.ERP_API_ENDPOINT: Optional[str] = os.getenv("ERP_API_ENDPOINT")
        self.ERP_API_KEY: Optional[str] = os.getenv("ERP_API_KEY")

        # Application Settings
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key")

        # Control System Settings
        self.CONTROL_SYSTEM_API_ENDPOINT: Optional[str] = os.getenv("CONTROL_SYSTEM_API_ENDPOINT")
        self.CONTROL_SYSTEM_API_KEY: Optional[str] = os.getenv("CONTROL_SYSTEM_API_KEY")

        # Construct DATABASE_URL if not provided
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )


# Instantiate settings
settings = Settings()

# Example usage (can be removed later)
if __name__ == "__main__":
    print("MQTT Broker Host:", settings.MQTT_BROKER_HOST)
    print("InfluxDB URL:", settings.INFLUXDB_URL)
    print("InfluxDB Org:", settings.INFLUXDB_ORG)
    print("Log Level:", settings.LOG_LEVEL)
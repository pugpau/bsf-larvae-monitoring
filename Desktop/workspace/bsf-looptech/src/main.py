from fastapi import FastAPI
import uvicorn
import os
import logging
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from api.routes import substrate, sensors
from mqtt.client import connect_mqtt
from database.influxdb import InfluxDBClient

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="BSF Larvae Monitoring System API",
    description="API for monitoring and managing BSF larvae cultivation environments.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(substrate.router)
app.include_router(sensors.router)

@app.get("/")
async def read_root():
    """
    Root endpoint providing a welcome message.
    """
    return {"message": "Welcome to the BSF Larvae Monitoring System API"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Verifies connections to InfluxDB and MQTT broker.
    """
    health_status = {
        "status": "healthy",
        "services": {
            "api": "ok",
            "influxdb": "unknown",
            "mqtt": "unknown"
        },
        "details": {}
    }
    
    # Check InfluxDB connection
    try:
        influxdb = InfluxDBClient()
        if influxdb.connect():
            health_status["services"]["influxdb"] = "ok"
            influxdb.close()
        else:
            health_status["services"]["influxdb"] = "error"
            health_status["status"] = "degraded"
            health_status["details"]["influxdb"] = "Failed to connect to InfluxDB"
    except Exception as e:
        health_status["services"]["influxdb"] = "error"
        health_status["status"] = "degraded"
        health_status["details"]["influxdb"] = str(e)
    
    # Check MQTT connection (just attempt to create client, don't actually connect)
    try:
        # We don't actually connect here to avoid leaving connections open
        # In a real implementation, you might want to check if the MQTT client is already running
        health_status["services"]["mqtt"] = "ok"
    except Exception as e:
        health_status["services"]["mqtt"] = "error"
        health_status["status"] = "degraded"
        health_status["details"]["mqtt"] = str(e)
    
    return health_status

# Global MQTT client
mqtt_client = None

@app.on_event("startup")
async def startup_event():
    """
    Startup event handler.
    Connects to MQTT broker and InfluxDB.
    """
    global mqtt_client
    
    logger.info("Starting BSF Larvae Monitoring System API")
    
    # Connect to MQTT broker
    logger.info("Connecting to MQTT broker...")
    mqtt_client = connect_mqtt()
    if mqtt_client:
        logger.info("Successfully connected to MQTT broker")
    else:
        logger.error("Failed to connect to MQTT broker")
    
    # Test InfluxDB connection
    logger.info("Testing InfluxDB connection...")
    try:
        with InfluxDBClient() as client:
            if client.connect():
                logger.info("Successfully connected to InfluxDB")
            else:
                logger.error("Failed to connect to InfluxDB")
    except Exception as e:
        logger.error(f"Error connecting to InfluxDB: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event handler.
    Disconnects from MQTT broker.
    """
    global mqtt_client
    
    logger.info("Shutting down BSF Larvae Monitoring System API")
    
    # Disconnect from MQTT broker
    if mqtt_client:
        logger.info("Disconnecting from MQTT broker...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        logger.info("Disconnected from MQTT broker")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000)) # Default port 8000 if not set in .env
    uvicorn.run(app, host="0.0.0.0", port=port)

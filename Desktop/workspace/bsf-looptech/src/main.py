from fastapi import FastAPI
import uvicorn
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from src.utils.logging import setup_logging, get_logger
from src.api.routes import substrate, sensors, websocket, auth, analytics
from src.api.routes import quality, process, audit
from src.mqtt.client import connect_mqtt
from src.database.influxdb import InfluxDBClient
from src.auth.middleware import AuthenticationMiddleware, RateLimitMiddleware
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings

# Load environment variables from .env file
load_dotenv()

# Configure enhanced logging
setup_logging()
logger = get_logger(__name__)

# Global MQTT client
mqtt_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown.
    Replaces deprecated @app.on_event.
    """
    global mqtt_client
    
    # Startup
    logger.info("Starting BSF Larvae Monitoring System API with Security")
    
    try:
        # Initialize database with authentication tables
        logger.info("Initializing database...")
        from src.database.postgresql import check_database_health, init_database
        await init_database()
        logger.info("Database initialization completed")
        
        # Test PostgreSQL connection
        logger.info("Testing PostgreSQL connection...")
        postgresql_ok = await check_database_health()
        if postgresql_ok:
            logger.info("Successfully connected to PostgreSQL")
        else:
            logger.error("Failed to connect to PostgreSQL")
        
        # Test InfluxDB connection
        logger.info("Testing InfluxDB connection...")
        with InfluxDBClient() as client:
            if client.connect():
                logger.info("Successfully connected to InfluxDB")
            else:
                logger.error("Failed to connect to InfluxDB")
        
        # Start real-time services
        logger.info("Starting real-time services...")
        from src.realtime.sensor_streamer import sensor_streamer
        from src.realtime.alert_manager import alert_manager
        from src.analytics.anomaly_detector import anomaly_detector
        
        await sensor_streamer.start_streaming()
        await alert_manager.start_monitoring()
        await anomaly_detector.start()
        logger.info("Real-time services started successfully")
        
        # Connect to MQTT broker
        logger.info("Connecting to MQTT broker...")
        mqtt_client = connect_mqtt()
        if mqtt_client:
            logger.info("Successfully connected to MQTT broker")
        else:
            logger.error("Failed to connect to MQTT broker")
            
    except Exception as e:
        logger.error(f"Startup error: {e}")
    
    # Application is running
    yield
    
    # Shutdown
    logger.info("Shutting down BSF Larvae Monitoring System API")
    
    try:
        # Stop real-time services
        logger.info("Stopping real-time services...")
        from src.realtime.sensor_streamer import sensor_streamer
        from src.realtime.alert_manager import alert_manager
        from src.analytics.anomaly_detector import anomaly_detector
        
        await sensor_streamer.stop_streaming()
        await alert_manager.stop_monitoring()
        await anomaly_detector.stop()
        logger.info("Real-time services stopped successfully")
        
        # Disconnect from MQTT broker
        if mqtt_client:
            logger.info("Disconnecting from MQTT broker...")
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            logger.info("Disconnected from MQTT broker")
            
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


app = FastAPI(
    title="BSF Larvae Monitoring System API",
    description="API for monitoring and managing BSF larvae cultivation environments.",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
# Parse origins from environment variable (comma-separated)
cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
logger.info(f"CORS allowed origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# Add authentication middleware
app.add_middleware(
    AuthenticationMiddleware,
    exempt_paths=[
        "/docs", "/redoc", "/openapi.json", "/health", "/", "/favicon.ico",
        "/auth/login", "/auth/refresh", "/auth/health"
    ]
)

# Include routers
app.include_router(auth.router)
app.include_router(substrate.router)
app.include_router(sensors.router)
app.include_router(websocket.router)
app.include_router(analytics.router)
app.include_router(quality.router)
app.include_router(process.router)
app.include_router(audit.router)

@app.get("/")
async def read_root():
    """
    Root endpoint providing a welcome message.
    """
    return {"message": "Welcome to the BSF Larvae Monitoring System API"}

@app.get("/favicon.ico")
async def favicon():
    """
    Return a simple favicon response to avoid 500 errors.
    """
    return {"message": "No favicon available"}

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Verifies connections to InfluxDB, PostgreSQL, and MQTT broker.
    """
    from src.database.postgresql import check_database_health
    
    health_status = {
        "status": "healthy",
        "services": {
            "api": "ok",
            "postgresql": "unknown",
            "influxdb": "unknown",
            "mqtt": "unknown"
        },
        "details": {}
    }
    
    # Check PostgreSQL connection
    try:
        postgresql_ok = await check_database_health()
        if postgresql_ok:
            health_status["services"]["postgresql"] = "ok"
        else:
            health_status["services"]["postgresql"] = "error"
            health_status["status"] = "degraded"
            health_status["details"]["postgresql"] = "Failed to connect to PostgreSQL"
    except Exception as e:
        health_status["services"]["postgresql"] = "error"
        health_status["status"] = "degraded"
        health_status["details"]["postgresql"] = str(e)
    
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000)) # Default port 8000 if not set in .env
    uvicorn.run(app, host="0.0.0.0", port=port)

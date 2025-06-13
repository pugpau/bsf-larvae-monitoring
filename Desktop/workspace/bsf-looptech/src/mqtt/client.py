import paho.mqtt.client as mqtt
import logging
import ssl
import os
import re
import asyncio
from src.config import settings
import json
# Import sensor service for data processing
from src.sensors.service import SensorService
# Import real-time streaming services
from src.realtime.sensor_streamer import sensor_streamer
# alert_manager import will be done at runtime to avoid circular imports

logging.basicConfig(level=settings.LOG_LEVEL.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Regular expression to parse MQTT topic structure: bsf/{farm_id}/{device_type}/{device_id}
TOPIC_PATTERN = r"bsf/([^/]+)/([^/]+)/([^/]+)"

# Initialize sensor service
sensor_service = SensorService()

def on_connect(client, userdata, flags, rc):
    """Callback function for when the client connects to the MQTT broker."""
    if rc == 0:
        logger.info("Connected successfully to MQTT Broker.")
        # Subscribe to relevant topics upon connection
        # Example: Subscribe to all sensor data topics
        topic = "bsf/+/+/+" 
        client.subscribe(topic, qos=1)
        logger.info(f"Subscribed to topic: {topic}")
    else:
        logger.error(f"Failed to connect to MQTT Broker, return code {rc}")

def on_disconnect(client, userdata, rc):
    """Callback function for when the client disconnects from the MQTT broker."""
    logger.warning(f"Disconnected from MQTT Broker with result code {rc}")
    # Implement reconnection logic if needed, Paho handles basic reconnection

def on_message(client, userdata, msg):
    """Callback function for when a message is received from the MQTT broker."""
    logger.info(f"Received message on topic {msg.topic}: {msg.payload.decode('utf-8')}")
    try:
        # Parse topic to extract farm_id, device_type, and device_id
        match = re.match(TOPIC_PATTERN, msg.topic)
        if not match:
            logger.error(f"Invalid topic format: {msg.topic}")
            return
        
        # Decode payload
        payload_dict = json.loads(msg.payload.decode('utf-8'))
        logger.debug(f"Decoded payload: {payload_dict}")
        
        # Real-time processing: Stream data to WebSocket clients
        asyncio.create_task(sensor_streamer.process_mqtt_message(msg.topic, payload_dict))
        
        # Alert processing would be integrated here in the future
        # Currently handled through sensor_streamer which includes alert evaluation
        
        # Process message using sensor service
        success = sensor_service.process_mqtt_message(msg.topic, payload_dict)
        if success:
            logger.info(f"Successfully processed message from topic {msg.topic}")
        else:
            logger.error(f"Failed to process message from topic {msg.topic}")

    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON payload from topic {msg.topic}")
    except Exception as e:
        logger.error(f"Error processing message from topic {msg.topic}: {e}")

def create_mqtt_client():
    """Creates and configures the MQTT client."""
    client_id = f"bsf-backend-client-{os.getpid()}" # Unique client ID
    client = mqtt.Client(client_id=client_id)

    # Assign callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Set username and password if provided
    if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
        client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

    # Configure TLS if enabled
    if settings.MQTT_TLS_ENABLED:
        try:
            client.tls_set(
                ca_certs=settings.MQTT_CA_CERTS,
                certfile=settings.MQTT_CLIENT_CERT,
                keyfile=settings.MQTT_CLIENT_KEY,
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=ssl.PROTOCOL_TLSv1_2 # Adjust TLS version if needed
            )
            # For self-signed certificates, you might need:
            # client.tls_insecure_set(True) 
            logger.info("TLS enabled for MQTT connection.")
        except Exception as e:
            logger.error(f"Failed to configure TLS: {e}")
            # Decide how to handle TLS configuration errors (e.g., exit or try non-TLS)
            return None

    return client

def connect_mqtt():
    """Connects the MQTT client to the broker and starts the loop."""
    client = create_mqtt_client()
    if client:
        try:
            client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)
            # Start the network loop in a non-blocking way
            client.loop_start() 
            logger.info("MQTT client loop started.")
            return client
        except Exception as e:
            logger.error(f"Could not connect to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}: {e}")
            return None
    return None

# Example of how to use the client (can be run standalone for testing)
if __name__ == "__main__":
    logger.info("Starting MQTT client test...")
    mqtt_client = connect_mqtt()
    
    if mqtt_client:
        # Keep the script running to maintain the connection
        try:
            while True:
                pass # Keep main thread alive
        except KeyboardInterrupt:
            logger.info("Disconnecting MQTT client...")
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            logger.info("MQTT client disconnected.")
    else:
        logger.error("Failed to start MQTT client.")

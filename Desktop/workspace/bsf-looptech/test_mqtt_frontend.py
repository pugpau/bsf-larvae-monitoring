#!/usr/bin/env python3
"""
Test MQTT connection with frontend credentials
"""
import paho.mqtt.client as mqtt
import ssl
import time

def on_connect(client, userdata, flags, rc):
    print(f"Frontend connected with result code {rc}")
    if rc == 0:
        print("Successfully connected to MQTT broker as frontend")
        # Subscribe to sensor data
        client.subscribe("bsf/+/devices/+/data", qos=1)
        client.subscribe("bsf/+/sensors/+", qos=1)
        print("Subscribed to sensor data topics")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    print(f"Frontend received: {msg.topic} - {str(msg.payload.decode())}")

def test_frontend_connection():
    print("Testing MQTT frontend connection...")
    
    client = mqtt.Client()
    client.username_pw_set("bsf_frontend", "BSF_Frontend_2025_Secure!")
    
    # Set up TLS
    client.tls_set(ca_certs="config/mqtt/certs/ca.crt", 
                   cert_reqs=ssl.CERT_REQUIRED,
                   tls_version=ssl.PROTOCOL_TLSv1_2)
    client.tls_insecure_set(True)  # For self-signed certificates
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        print("Connecting frontend to localhost:8883...")
        client.connect("localhost", 8883, 60)
        client.loop_start()
        
        # Send a test command
        time.sleep(2)
        client.publish("bsf/farm1/devices/GAS-001/commands", 
                      '{"command": "get_status", "timestamp": "2025-07-02T09:00:00Z"}')
        print("Published test command to device")
        
        time.sleep(3)
        client.loop_stop()
        client.disconnect()
        print("Frontend test completed")
        
    except Exception as e:
        print(f"Frontend connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_frontend_connection()
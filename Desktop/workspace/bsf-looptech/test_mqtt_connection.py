#!/usr/bin/env python3
"""
Test MQTT TLS connection
"""
import paho.mqtt.client as mqtt
import ssl
import time
import sys

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    if rc == 0:
        print("Successfully connected to MQTT broker")
        client.publish("bsf/test/data", "Hello from Python TLS test!")
    else:
        print(f"Failed to connect, return code {rc}")

def on_publish(client, userdata, mid):
    print(f"Message {mid} published successfully")

def on_message(client, userdata, msg):
    print(f"Received message: {msg.topic} {str(msg.payload)}")

def test_tls_connection():
    print("Testing MQTT TLS connection...")
    
    client = mqtt.Client()
    client.username_pw_set("bsf_device", "BSF_Device_2025_Secure!")
    
    # Enable detailed logging
    client.enable_logger()
    
    # Set up TLS
    try:
        client.tls_set(ca_certs="config/mqtt/certs/ca.crt", 
                       cert_reqs=ssl.CERT_REQUIRED,
                       tls_version=ssl.PROTOCOL_TLSv1_2)
        # For self-signed certificates
        client.tls_insecure_set(True)
        print("TLS configuration set successfully")
    except Exception as e:
        print(f"TLS setup failed: {e}")
        return
    
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_message = on_message
    
    try:
        print("Connecting to localhost:8883...")
        result = client.connect("localhost", 8883, 60)
        print(f"Connection result: {result}")
        client.loop_start()
        time.sleep(5)
        client.loop_stop()
        client.disconnect()
        print("TLS test completed")
    except Exception as e:
        print(f"TLS connection failed: {e}")
        import traceback
        traceback.print_exc()

def test_plain_connection():
    print("Testing MQTT plain connection...")
    
    client = mqtt.Client()
    client.username_pw_set("bsf_device", "BSF_Device_2025_Secure!")
    
    client.on_connect = on_connect
    client.on_publish = on_publish
    client.on_message = on_message
    
    try:
        print("Connecting to localhost:1883...")
        client.connect("localhost", 1883, 60)
        client.loop_start()
        time.sleep(3)
        client.loop_stop()
        client.disconnect()
        print("Plain connection test completed")
    except Exception as e:
        print(f"Plain connection failed: {e}")

if __name__ == "__main__":
    print("MQTT Connection Test")
    print("=" * 50)
    
    # Test plain connection first
    test_plain_connection()
    
    print("\n" + "=" * 50)
    
    # Test TLS connection
    test_tls_connection()
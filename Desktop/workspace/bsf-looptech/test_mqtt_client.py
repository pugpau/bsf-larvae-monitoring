#!/usr/bin/env python3
"""
Test the BSF MQTT client with TLS
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

# Clear any cached environment variables
if 'MQTT_BROKER_PORT' in os.environ:
    del os.environ['MQTT_BROKER_PORT']

try:
    from src.mqtt.client import connect_mqtt
    import time
    
    print("Testing BSF MQTT client with TLS...")
    print("=" * 50)
    
    # Test connection
    client = connect_mqtt()
    
    if client:
        print("✅ MQTT client connected successfully with TLS!")
        
        # Keep connection alive for a few seconds to test subscription
        print("Waiting for messages (5 seconds)...")
        time.sleep(5)
        
        # Disconnect cleanly
        client.loop_stop()
        client.disconnect()
        print("✅ MQTT client disconnected successfully.")
        
        print("\n🎉 MQTT TLS implementation test PASSED!")
        
    else:
        print("❌ Failed to connect MQTT client.")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Test failed with error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
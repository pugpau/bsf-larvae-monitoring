#!/bin/bash

# BSF-LoopTech MQTT User Password Creation Script

set -e

MQTT_DIR="config/mqtt"
PASSWORD_FILE="$MQTT_DIR/password.txt"

echo "Creating MQTT user passwords..."

# Create bsf_device user
echo "Creating bsf_device user..."
expect -c "
spawn mosquitto_passwd -c $PASSWORD_FILE bsf_device
expect \"Password:\"
send \"BSF_Device_2025_Secure!\r\"
expect \"Reenter password:\"
send \"BSF_Device_2025_Secure!\r\"
expect eof
"

# Add bsf_admin user
echo "Adding bsf_admin user..."
expect -c "
spawn mosquitto_passwd $PASSWORD_FILE bsf_admin
expect \"Password:\"
send \"BSF_Admin_2025_Ultra_Secure!\r\"
expect \"Reenter password:\"
send \"BSF_Admin_2025_Ultra_Secure!\r\"
expect eof
"

# Set appropriate permissions
chmod 600 "$PASSWORD_FILE"

echo "Password file created successfully at $PASSWORD_FILE"
echo "Users created:"
echo "  - bsf_device (for IoT devices)"
echo "  - bsf_admin (for administrators)"
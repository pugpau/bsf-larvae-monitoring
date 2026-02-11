#!/usr/bin/env python3
"""
Production security hardening script
"""

import os
import secrets
import string
import subprocess
import shutil
from pathlib import Path

def generate_strong_password(length=32):
    """Generate a cryptographically strong password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_secret_key():
    """Generate a new secret key."""
    return secrets.token_urlsafe(32)

def secure_production():
    """Apply production security hardening."""
    
    print("🔒 BSF-LoopTech Production Security Hardening")
    print("=" * 50)
    
    # Generate new passwords and keys
    new_db_password = generate_strong_password()
    new_mqtt_password = generate_strong_password()
    new_secret_key = generate_secret_key()
    
    print("\n✅ Generated new security credentials:")
    print(f"   Database password: {new_db_password}")
    print(f"   MQTT password: {new_mqtt_password}")
    print(f"   Secret key: {new_secret_key}")
    
    # Create secure production environment file
    env_content = f'''# BSF-LoopTech 本番環境設定ファイル (セキュア版)
# 生成日時: {subprocess.check_output(['date']).decode().strip()}

# === アプリケーション設定 ===
ENVIRONMENT=production
LOG_LEVEL=WARNING
SECRET_KEY={new_secret_key}

# === データベース設定 ===
DATABASE_URL=postgresql+asyncpg://bsf_user:{new_db_password}@postgres:5432/bsf_system
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=bsf_user
POSTGRES_PASSWORD={new_db_password}
POSTGRES_DB=bsf_system

# === InfluxDB設定 ===
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN={generate_secret_key()}
INFLUXDB_ORG=bsf_org
INFLUXDB_BUCKET=bsf_data

# === MQTT設定（本番 - TLS有効） ===
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=8883
MQTT_TLS_ENABLED=true
MQTT_CA_CERTS=/app/certs/ca.crt
MQTT_CLIENT_CERT=/app/certs/mqtt-client.crt
MQTT_CLIENT_KEY=/app/certs/mqtt-client.key
MQTT_USERNAME=bsf-backend
MQTT_PASSWORD={new_mqtt_password}

# === API設定 ===
API_BASE_URL=https://your-domain.com
REACT_APP_API_BASE_URL=https://your-domain.com
REACT_APP_MQTT_WS_URL=wss://your-domain.com:9001

# === セキュリティ設定 ===
CORS_ORIGINS=["https://your-domain.com"]
ALLOWED_HOSTS=["your-domain.com"]

# === 機械学習設定 ===
ML_MODEL_PATH=/app/model_registry/models
ML_TRAINING_ENABLED=true
ML_PREDICTION_THRESHOLD=0.85

# === 監視・ログ設定 ===
MONITORING_ENABLED=true
LOG_RETENTION_DAYS=30
BACKUP_ENABLED=true
BACKUP_INTERVAL=24h

# === Docker Compose用変数 ===
COMPOSE_PROJECT_NAME=bsf-looptech
COMPOSE_FILE=docker-compose.prod.yml
'''
    
    # Write secure environment file
    with open('.env.production.secure', 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Secure environment file created: .env.production.secure")
    
    # Create gitignore entries
    gitignore_entries = [
        "# Production security files",
        ".env.production.secure",
        ".env.local",
        "*.key",
        "*.pem",
        "certs/*.key",
        "config/mqtt/certs/*.key",
        "fix_admin_password.py"
    ]
    
    print(f"\n📝 Security recommendations:")
    print(f"   1. Copy .env.production.secure to your production server")
    print(f"   2. Rename it to .env on the production server") 
    print(f"   3. Delete .env.production.secure from this repository")
    print(f"   4. Add the following to .gitignore:")
    for entry in gitignore_entries:
        print(f"      {entry}")
    
    print(f"\n🚨 CRITICAL: Change the admin password!")
    print(f"   Current password: Admin123456!")
    print(f"   Recommended: Use a password manager to generate a strong password")
    
    return {
        'db_password': new_db_password,
        'mqtt_password': new_mqtt_password,
        'secret_key': new_secret_key
    }

if __name__ == "__main__":
    credentials = secure_production()
    
    print(f"\n🔐 Security hardening completed!")
    print(f"   Next steps: Review PRODUCTION_CHECKLIST.md")
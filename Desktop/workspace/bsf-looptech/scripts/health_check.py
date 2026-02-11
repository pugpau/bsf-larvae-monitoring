#!/usr/bin/env python3
"""
BSF-LoopTech Health Check Script for Docker Container
"""

import sys
import requests
import logging
from typing import bool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_api_health() -> bool:
    """Check if the API is responding"""
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"API health check failed: {e}")
        return False

def check_database_connection() -> bool:
    """Check if database connection is available"""
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        return response.status_code == 200
    except requests.RequestException as e:
        logger.error(f"Database health check failed: {e}")
        return False

def main():
    """Main health check function"""
    logger.info("Starting health check...")
    
    # Check API
    if not check_api_health():
        logger.error("API health check failed")
        sys.exit(1)
    
    # Check database
    if not check_database_connection():
        logger.error("Database health check failed")
        sys.exit(1)
    
    logger.info("Health check passed")
    sys.exit(0)

if __name__ == "__main__":
    main()
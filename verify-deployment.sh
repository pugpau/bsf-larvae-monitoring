#!/bin/bash

echo "Starting Docker Compose verification..."

docker-compose up -d

echo "Waiting for services to start..."
sleep 30

if [ $(docker-compose ps -q | wc -l) -ne 4 ]; then
  echo "Error: Not all services are running"
  docker-compose ps
  exit 1
fi

echo "Checking backend health..."
BACKEND_HEALTH=$(curl -s http://localhost:8000/health)
if [[ $BACKEND_HEALTH != *"healthy"* ]]; then
  echo "Error: Backend health check failed"
  echo $BACKEND_HEALTH
  exit 1
fi

echo "Checking frontend accessibility..."
FRONTEND_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost)
if [ $FRONTEND_CHECK -ne 200 ]; then
  echo "Error: Frontend accessibility check failed"
  echo "HTTP Status: $FRONTEND_CHECK"
  exit 1
fi

echo "Verification completed successfully!"
exit 0

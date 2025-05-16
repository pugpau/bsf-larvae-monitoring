# BSF Larvae Monitoring System Deployment Guide

This guide provides instructions for deploying the BSF Larvae Monitoring System in various environments.

## Contents

- [Local Development](#local-development)
- [Docker Compose Deployment](#docker-compose-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [CI/CD Pipeline](#cicd-pipeline)

## Local Development

### Prerequisites

- Docker
- Docker Compose

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/pugpau/bsf-larvae-monitoring.git
   cd bsf-larvae-monitoring
   ```

2. Create a `.env` file with the following variables:

   ```
   INFLUXDB_USERNAME=admin
   INFLUXDB_PASSWORD=password
   INFLUXDB_ORG=bsf-organization
   INFLUXDB_TOKEN=your-influxdb-token
   MQTT_ADMIN_PASSWORD=admin-password
   ```

3. Start the development environment:

   ```bash
   docker-compose up -d
   ```

4. Access the application:

   - Frontend: http://localhost
   - Backend API: http://localhost:8000
   - InfluxDB UI: http://localhost:8086
   - MQTT Dashboard: http://localhost:18083

## Docker Compose Deployment

For simple production deployments, you can use Docker Compose:

1. Clone the repository on your production server:

   ```bash
   git clone https://github.com/pugpau/bsf-larvae-monitoring.git
   cd bsf-larvae-monitoring
   ```

2. Create a `.env` file with production values:

   ```
   INFLUXDB_USERNAME=admin
   INFLUXDB_PASSWORD=strong-password
   INFLUXDB_ORG=bsf-organization
   INFLUXDB_TOKEN=your-production-token
   MQTT_ADMIN_PASSWORD=strong-admin-password
   ```

3. Start the production environment:

   ```bash
   docker-compose up -d
   ```

4. Set up a reverse proxy (like Nginx or Traefik) to handle SSL termination.

## Kubernetes Deployment

For scalable production deployments, use Kubernetes:

1. Update the configuration in `k8s/config.yaml` with your production values.

2. Apply the Kubernetes manifests:

   ```bash
   kubectl apply -f k8s/config.yaml
   kubectl apply -f k8s/backend-deployment.yaml
   kubectl apply -f k8s/frontend-deployment.yaml
   kubectl apply -f k8s/ingress.yaml
   ```

3. Set up external dependencies:

   ```bash
   # Install InfluxDB using Helm
   helm repo add influxdata https://helm.influxdata.com/
   helm install bsf-influxdb influxdata/influxdb2

   # Install EMQX using Helm
   helm repo add emqx https://repos.emqx.io/charts
   helm install bsf-mqtt emqx/emqx
   ```

## CI/CD Pipeline

The project includes a GitHub Actions workflow for CI/CD:

1. Push changes to the main branch to trigger the pipeline.

2. The pipeline will:
   - Run backend tests
   - Run frontend tests
   - Build Docker images
   - Push images to GitHub Container Registry

3. For automatic deployment to Kubernetes, you can extend the workflow with:

   ```yaml
   deploy:
     needs: [build-and-push]
     runs-on: ubuntu-latest
     steps:
     - uses: actions/checkout@v3
     
     - name: Set up kubectl
       uses: azure/setup-kubectl@v3
       
     - name: Set Kubernetes context
       uses: azure/k8s-set-context@v3
       with:
         kubeconfig: ${{ secrets.KUBECONFIG }}
         
     - name: Deploy to Kubernetes
       run: |
         kubectl apply -f k8s/config.yaml
         kubectl apply -f k8s/backend-deployment.yaml
         kubectl apply -f k8s/frontend-deployment.yaml
         kubectl apply -f k8s/ingress.yaml
         kubectl rollout restart deployment bsf-backend
         kubectl rollout restart deployment bsf-frontend
   ```

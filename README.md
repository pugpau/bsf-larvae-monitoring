# BSF Larvae Monitoring System

A comprehensive IoT monitoring and optimization system for BSF (Black Soldier Fly) larvae cultivation environments.

## Documentation

- [API Documentation](./docs/api/README.md)
- [Setup Guide](./docs/setup/README.md)
- [Design Documentation](./docs/design/README.md)
- [Deployment Guide](./docs/deployment/README.md)

## Features

- Environment sensor data collection
- Real-time monitoring
- Advanced data processing and analysis
- Substrate composition management
- Automatic control functions

## Project Structure

```
bsf-larvae-monitoring/
├── frontend/          # React frontend application
│   ├── src/           # Source files
│   │   ├── api/       # API client
│   │   ├── components/# React components
│   ├── package.json   # Frontend dependencies
│
├── backend/           # FastAPI backend application
│   ├── src/           # Source files
│   │   ├── api/       # API routes
│   │   ├── database/  # Database access
│   │   ├── mqtt/      # MQTT client
│   │   ├── substrate/ # Substrate management
│   ├── main.py        # FastAPI application
│   ├── requirements.txt # Backend dependencies
```

## Quick Start

### Prerequisites

- Docker
- Docker Compose

### Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/pugpau/bsf-larvae-monitoring.git
   cd bsf-larvae-monitoring
   ```

2. Start the development environment:

   ```bash
   docker-compose up -d
   ```

3. Access the application:

   - Frontend: http://localhost
   - Backend API: http://localhost:8000

### Manual Setup

#### Frontend Setup

```bash
cd frontend
npm install
npm start
```

#### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python -m src.main
```

## Testing

### Frontend Tests

```bash
cd frontend
npm test
```

### Backend Tests

```bash
cd backend
pytest
```

## Environment Variables

### Frontend

Create a `.env.development` file in the frontend directory:

```
REACT_APP_API_BASE_URL=http://localhost:8000
```

### Backend

Create a `.env` file in the backend directory:

```
PORT=8000
LOG_LEVEL=info
```

## Deployment

For detailed deployment instructions, see the [Deployment Guide](./docs/deployment/README.md).

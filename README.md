# BSF Larvae Monitoring System

A comprehensive IoT monitoring and optimization system for BSF (Black Soldier Fly) larvae cultivation environments.

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

## Setup Instructions

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

### Backend Setup

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

# Frontend Setup Guide

This guide provides instructions for setting up the frontend components of the BSF Larvae Monitoring System.

## Prerequisites

- Node.js 16 or higher
- npm or yarn

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/pugpau/bsf-larvae-monitoring.git
   cd bsf-larvae-monitoring
   ```

2. Install dependencies:

   ```bash
   cd frontend
   npm install  # or yarn install
   ```

## Configuration

Create a `.env.development` file in the frontend directory with the following variables:

```
REACT_APP_API_BASE_URL=http://localhost:8000
```

## Running the Frontend

Start the development server:

```bash
npm start  # or yarn start
```

The frontend will be available at `http://localhost:3000`.

## Building for Production

Build the frontend for production:

```bash
npm run build  # or yarn build
```

## Testing

Run the tests:

```bash
npm test  # or yarn test
```

# Second Brain — Frontend (React + Vite)

This is the dashboard UI for the Second Brain app. Built with **React 18** + **Vite**, using Vanilla CSS with a dark glassmorphism design.

## Setup

```bash
# Install dependencies
npm install

# Copy env file and edit if needed
cp .env.example .env

# Start dev server
npm run dev
```

The app runs on **http://localhost:5173** and connects to the Python backend at `http://127.0.0.1:8000` by default.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend API URL |

## Build for Production

```bash
npm run build
```

See the [root README](../README.md) for full project documentation.

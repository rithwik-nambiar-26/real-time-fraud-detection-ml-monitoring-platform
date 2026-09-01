# Real-Time Fraud Detection & ML Monitoring Platform

A production-style platform for real-time credit card fraud detection with ML model serving, drift monitoring, and a live operations dashboard.

## Features

- **Real-time scoring** — REST API and WebSocket stream for transaction fraud scoring
- **ML pipeline** — Synthetic data generation, feature engineering, and Random Forest training
- **Model monitoring** — Prediction distribution, latency, throughput, drift detection, and alert thresholds
- **Live dashboard** — React UI with fraud alerts, metrics charts, and transaction feed
- **Docker-ready** — Single-command deployment via Docker Compose

## Architecture

```
┌─────────────┐     HTTP/WS      ┌──────────────────┐
│   React     │ ◄──────────────► │   FastAPI        │
│  Dashboard  │                  │   Backend        │
└─────────────┘                  └────────┬─────────┘
                                          │
                              ┌───────────┼───────────┐
                              ▼           ▼           ▼
                         ML Model    SQLite DB   Monitor Store
```

## Quick Start

### Local Development

```bash
# 1. Backend setup
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python -m ml.train            # Train model
uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev

# 3. Simulate transactions
cd backend
python -m scripts.simulate_transactions
```

Open http://localhost:5173 for the dashboard and http://localhost:8000/docs for API docs.

### Docker

```bash
docker compose up --build
```

- Dashboard: http://localhost:5173
- API: http://localhost:8000

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/score` | Score a single transaction |
| POST | `/api/v1/score/batch` | Score multiple transactions |
| GET | `/api/v1/transactions` | List recent scored transactions |
| GET | `/api/v1/metrics` | ML monitoring metrics |
| GET | `/api/v1/alerts` | Active monitoring alerts |
| WS | `/ws/transactions` | Live transaction stream |

## Project Structure

```
├── backend/
│   ├── app/           # FastAPI application
│   ├── ml/            # Training pipeline & artifacts
│   ├── scripts/       # Simulation & utilities
│   └── tests/         # Backend tests
├── frontend/          # React dashboard
├── docker-compose.yml
└── README.md
```

## License

MIT

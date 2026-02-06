# AgentSociety Marketing Platform

AI-powered marketing simulation platform that simulates 1,000+ AI agents reacting to video advertisements.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### Development Setup

1. **Clone and configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

2. **Start infrastructure services**
```bash
docker-compose up -d
```

3. **Start backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. **Start frontend**
```bash
cd frontend
npm install
npm run dev
```

5. **Access services**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- EMQX Dashboard: http://localhost:18083 (admin/public)
- Ray Dashboard: http://localhost:8265

## Project Structure
```
├── frontend/          # Next.js 14 application
├── backend/           # FastAPI orchestrator
├── simulation/        # Ray + Agent simulation
├── database/          # SQL migrations
├── infrastructure/    # Docker configs
└── docs/              # Documentation
```

## License
MIT

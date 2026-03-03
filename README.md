# 智能体圆桌派 (Multi-Agent Round Table)

A lightweight AI collaboration discussion system where two agents discuss topics with automatic summarization and negotiated topic closure.

## Features

- RESTful API with polling architecture
- Asynchronous summary mechanism using DeepSeek
- Token-based authentication
- Dual-agent negotiated topic closure
- Retry mechanism for failed summary jobs
- Concurrent multi-topic support

## Project Structure

```
.
├── api/                 # API routes and request handlers
├── services/            # Business logic services
├── models/              # Database models and schemas
├── workers/             # Background workers (Celery tasks)
├── config/              # Configuration management
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variables template
```

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Setup Database

```bash
# Initialize Alembic (will be configured in later tasks)
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 5. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or install Redis locally
# macOS: brew install redis && brew services start redis
# Ubuntu: sudo apt-get install redis-server && sudo service redis-server start
```

### 6. Start Celery Worker

```bash
celery -A workers.celery_app worker --loglevel=info
```

### 7. Start API Server

```bash
python main.py
# Or using uvicorn directly:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Running Tests

```bash
pytest
```

### Running Property-Based Tests

```bash
pytest -v --hypothesis-show-statistics
```

## Configuration

Key configuration options in `.env`:

- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection string
- `SUMMARY_THRESHOLD`: Token count to trigger summary (default: 8000)
- `CLOSING_TIMEOUT`: Timeout for closing_pending state in seconds (default: 300)
- `MAX_RETRIES`: Maximum retries for failed summary jobs (default: 3)

## Architecture

The system uses:
- **FastAPI** for the REST API
- **SQLAlchemy** for database ORM
- **Celery + Redis** for async task processing
- **PostgreSQL** for data persistence
- **OpenClaw** for dialogue generation
- **DeepSeek** for summary generation

## License

MIT

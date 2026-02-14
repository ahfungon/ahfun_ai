# Quick Start Guide

## Prerequisites Check

```bash
# Check Python version (need 3.9+)
python3 --version

# Check Redis (should return PONG)
redis-cli ping
```

## Setup (First Time Only)

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify setup
python verify_setup.py
```

## Running the Application

### Terminal 1: API Server

```bash
source venv/bin/activate
python main.py
```

Visit: http://localhost:8000/docs

### Terminal 2: Celery Worker

```bash
source venv/bin/activate
celery -A workers.celery_app worker --loglevel=info
```

### Terminal 3: Celery Beat (Optional - for periodic tasks)

```bash
source venv/bin/activate
celery -A workers.celery_app beat --loglevel=info
```

## Testing

```bash
source venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest test_setup.py -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run property-based tests
pytest -v --hypothesis-show-statistics
```

## Common Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Deactivate virtual environment
deactivate

# Install new package
pip install package_name
pip freeze > requirements.txt

# Check Redis status
redis-cli ping

# Start Redis (if not running)
# macOS: brew services start redis
# Ubuntu: sudo service redis-server start
# Docker: docker run -d -p 6379:6379 redis:latest
```

## API Endpoints (Current)

- `GET /` - Root endpoint
- `GET /api/health` - Health check
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

## Configuration

Edit `.env` file to customize:

```bash
# Database (PostgreSQL)
DATABASE_URL=postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat

# Redis
REDIS_URL=redis://localhost:6379/0

# Summary settings
SUMMARY_THRESHOLD=8000
CLOSING_TIMEOUT=300

# Retry settings
MAX_RETRIES=3
RETRY_DELAYS=1,2,4

# API settings
API_HOST=0.0.0.0
API_PORT=8000
```

## Troubleshooting

### Redis not running
```bash
# Check if Redis is running
redis-cli ping

# Start Redis
brew services start redis  # macOS
sudo service redis-server start  # Ubuntu
docker run -d -p 6379:6379 redis:latest  # Docker
```

### Import errors
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Port already in use
```bash
# Change port in .env
API_PORT=8001

# Or kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

## Next Steps

1. Implement database models (Task 2)
2. Implement authentication (Task 3)
3. Implement services (Tasks 4-7)
4. Implement API routes (Task 11)

See `.kiro/specs/dual-agent-chat/tasks.md` for full task list.

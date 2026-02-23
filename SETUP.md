# Setup Guide - Dual Agent Chat Platform

This guide will help you set up the development environment for the Dual Agent Chat Platform.

## Prerequisites

- Python 3.9 or higher
- Redis (for task queue)
- PostgreSQL (required for database)

## Quick Start

### 1. Clone and Navigate to Project

```bash
cd /path/to/dual-agent-chat
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

The `.env` file has been created with default settings. It uses:
- PostgreSQL database (required)
- Redis on localhost:6379
- Default configuration values

To customize, edit `.env`:

```bash
# Edit configuration as needed
nano .env
```

### 5. Start Redis

Redis is required for the task queue. If not already running:

**Using Docker:**
```bash
docker run -d -p 6379:6379 redis:latest
```

**On macOS:**
```bash
brew install redis
brew services start redis
```

**On Ubuntu:**
```bash
sudo apt-get install redis-server
sudo service redis-server start
```

### 6. Verify Setup

Run the verification script to ensure everything is configured correctly:

```bash
python verify_setup.py
```

You should see all checks passing with ✓ marks.

## Running the Application

### Start API Server

```bash
# Activate virtual environment
source venv/bin/activate

# Start the API server
python main.py

# Or using uvicorn directly with auto-reload:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Start Celery Worker

In a separate terminal:

```bash
# Activate virtual environment
source venv/bin/activate

# Start Celery worker
celery -A workers.celery_app worker --loglevel=info
```

### Start Celery Beat (for periodic tasks)

In another terminal (for scheduled tasks like timeout checks):

```bash
# Activate virtual environment
source venv/bin/activate

# Start Celery beat
celery -A workers.celery_app beat --loglevel=info
```

## Project Structure

```
.
├── api/                    # API routes and request handlers
│   └── __init__.py
├── services/               # Business logic services
│   └── __init__.py
├── models/                 # Database models and schemas
│   ├── __init__.py
│   └── database.py        # Database connection setup
├── workers/                # Background workers (Celery tasks)
│   ├── __init__.py
│   ├── celery_app.py      # Celery configuration
│   └── tasks.py           # Celery task definitions
├── config/                 # Configuration management
│   ├── __init__.py
│   └── settings.py        # Application settings
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (created from .env.example)
├── .env.example            # Environment variables template
├── verify_setup.py         # Setup verification script
└── README.md               # Project documentation
```

## Development Workflow

### 1. Database Migrations (Task 2)

After implementing database models:

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

### 2. Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run property-based tests with statistics
pytest -v --hypothesis-show-statistics
```

### 3. Code Quality

```bash
# Format code (if using black)
black .

# Lint code (if using flake8)
flake8 .

# Type checking (if using mypy)
mypy .
```

## Configuration Options

Key environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://dual_agent_user:dual_agent_pass@localhost:5432/dual_agent_chat` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SUMMARY_THRESHOLD` | Token count to trigger summary | `8000` |
| `CLOSING_TIMEOUT` | Timeout for closing_pending (seconds) | `300` |
| `MAX_RETRIES` | Max retries for failed summary jobs | `3` |
| `RETRY_DELAYS` | Retry delays in seconds | `1,2,4` |
| `CELERY_MAX_CONCURRENT_TASKS` | Max concurrent Celery tasks | `5` |
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |

## Troubleshooting

### Redis Connection Error

If you see "Redis connection failed":
1. Check if Redis is running: `redis-cli ping`
2. Start Redis if needed (see step 5 above)
3. Verify Redis URL in `.env` matches your Redis instance

### Import Errors

If you see import errors:
1. Ensure virtual environment is activated: `source venv/bin/activate`
2. Reinstall dependencies: `pip install -r requirements.txt`

### Database Errors

If you see database errors:
1. Check `DATABASE_URL` in `.env`
2. Ensure PostgreSQL is running: `brew services list | grep postgresql`
3. Ensure database exists and credentials are correct

## Next Steps

After setup is complete:

1. **Task 2**: Implement database models and schemas
2. **Task 3**: Implement authentication middleware
3. **Task 4**: Implement TopicService
4. Continue with remaining tasks in `.kiro/specs/dual-agent-chat/tasks.md`

## Support

For issues or questions:
1. Check the task list: `.kiro/specs/dual-agent-chat/tasks.md`
2. Review requirements: `.kiro/specs/dual-agent-chat/requirements.md`
3. Review design: `.kiro/specs/dual-agent-chat/design.md`

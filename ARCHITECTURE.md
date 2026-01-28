# Architecture Documentation

## Overview

This application follows a clean layered architecture pattern:

```
Route -> Controller -> Service -> Repository -> Model
```

## Directory Structure

```
├── .env.example          # Environment variables template
├── config.py             # Configuration management
├── database.py           # Database connection & session management
├── app_v2.py            # Main application entry point
│
├── models/              # Data models (SQLAlchemy)
│   ├── __init__.py
│   └── package.py       # Package model
│
├── repositories/        # Data access layer
│   ├── __init__.py
│   └── package_repository.py  # Package DB operations
│
├── services/            # Business logic layer
│   ├── __init__.py
│   └── package_service.py     # Package business logic
│
├── controllers/         # Request handling layer
│   ├── __init__.py
│   └── package_controller.py  # Package HTTP handlers
│
└── routes/              # API routes
    ├── __init__.py
    └── simple_api_v2.py        # PyPI Simple API routes
```

## Layer Responsibilities

### 1. Routes (`routes/`)
- Define URL endpoints
- Handle HTTP request/response
- Minimal logic - delegates to controllers
- **Example**: `/simple/<package_name>/`

### 2. Controllers (`controllers/`)
- Process HTTP requests
- Validate input
- Call services
- Format responses (JSON, Problem Details RFC 9457)
- **No database access**

### 3. Services (`services/`)
- Business logic
- Orchestrate multiple repository calls
- Transaction management
- **No HTTP concerns**

### 4. Repositories (`repositories/`)
- Database operations (CRUD)
- Query construction
- Data mapping
- **Single responsibility per repository**

### 5. Models (`models/`)
- SQLAlchemy ORM models
- Database schema definition
- Data validation

## Configuration

### Environment Variables

Create `.env` file based on `.env.example`:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/database

# PyPI Server
PYPI_SERVER_URL=http://pypiserver:8080
PYPI_USERNAME=username
PYPI_PASSWORD=password

# Hyperplane (for scanner jobs)
HYPERPLANE_GRAPHQL_URL=http://hyperplane-core/graphql
HYPERPLANE_USERNAME=user
HYPERPLANE_PASSWORD=pass
HYPERPLANE_USER_ID=user-id
HYPERPLANE_USER_EMAIL=user@example.com

# Application
FLASK_ENV=production
LOG_LEVEL=INFO
```

### Configuration Management

All configuration is centralized in `config.py`:

```python
from config import Config

# Access configuration
db_url = Config.DATABASE_URL
pypi_url = Config.PYPI_SERVER_URL
```

## Database

### SQLAlchemy Setup

```python
from database import get_db_session

# Using context manager (recommended)
with get_db_session() as session:
    # Automatic commit/rollback
    package = session.query(Package).first()

# Or get session directly
session = get_session()
```

### Models

```python
from models import Package

# Package model fields:
# - id: Primary key
# - package_name: Unique package identifier
# - status: 'pending', 'safe', 'vulnerable', 'error'
# - vulnerability_info: JSON blob
# - created_at, updated_at: Timestamps
```

## Example Usage

### Adding a New Endpoint

1. **Create Route** (`routes/my_route.py`):
```python
from flask import Blueprint
from controllers import MyController

my_bp = Blueprint('my', __name__)

@my_bp.route('/my-endpoint')
def my_endpoint():
    controller = MyController(service)
    return controller.handle_request()
```

2. **Create Controller** (`controllers/my_controller.py`):
```python
class MyController:
    def __init__(self, service):
        self.service = service

    def handle_request(self):
        result = self.service.do_something()
        return jsonify(result)
```

3. **Create Service** (`services/my_service.py`):
```python
class MyService:
    def __init__(self, repository):
        self.repository = repository

    def do_something(self):
        data = self.repository.get_data()
        # Business logic here
        return processed_data
```

4. **Create Repository** (`repositories/my_repository.py`):
```python
class MyRepository:
    def __init__(self, session):
        self.db = session

    def get_data(self):
        return self.db.query(MyModel).all()
```

## Security Best Practices

### 1. No Sensitive Data in Logs

```python
# ❌ Bad
logger.info(f"Password: {password}")

# ✅ Good
logger.info("Authentication successful")
```

### 2. Use Environment Variables

```python
# ❌ Bad
PASSWORD = "hardcoded_password"

# ✅ Good
PASSWORD = os.getenv('PASSWORD')
```

### 3. Minimal Logging

```python
# ❌ Bad - Too verbose
logger.debug(f"Request headers: {request.headers}")
logger.debug(f"Request body: {request.data}")

# ✅ Good - Essential only
logger.info(f"Package request: {package_name}")
```

## Testing

### Unit Testing Example

```python
def test_package_service():
    # Mock repository
    mock_repo = Mock()
    mock_repo.find_by_name.return_value = Package(status='safe')

    # Test service
    service = PackageService(mock_repo)
    status, info = service.check_package_status('requests')

    assert status == 'safe'
```

## Migration from Old Architecture

### Old Code:
```python
# Direct database calls in routes
@app.route('/package')
def package():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM packages")
    return jsonify(cursor.fetchall())
```

### New Code:
```python
# Layered architecture
@simple_api_bp.route('/<package_name>/')
def simple_package(package_name):
    controller = PackageController(service)
    return controller.check_package(package_name)
```

## Benefits

1. **Separation of Concerns**: Each layer has single responsibility
2. **Testability**: Easy to mock dependencies
3. **Maintainability**: Changes isolated to specific layers
4. **Scalability**: Easy to add new features
5. **Security**: Centralized configuration, minimal logging
6. **Reusability**: Services/repositories can be reused

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your values

# Run application
python app_v2.py
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app_v2.py"]
```

### Environment Variables in Kubernetes

```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: db-secret
        key: url
  - name: PYPI_USERNAME
    valueFrom:
      secretKeyRef:
        name: pypi-secret
        key: username
```

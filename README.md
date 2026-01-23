# Python Library Scanner API

A modular Flask-based proxy server for PyPI with RFC 9457 (Problem Details) support for enhanced error reporting to modern Python package installers.

## Features

- **Modular Architecture**: Clean separation of concerns using Flask Blueprints
- **RFC 9457 Support**: Standards-compliant error responses for modern tools (uv, future pip versions)
- **PyPI Proxy**: Transparent proxying to internal PyPI servers (PEP 503)
- **Comprehensive Logging**: Detailed request/response logging for debugging
- **Environment Configuration**: Easy deployment with environment variables
- **Health Check Endpoints**: Monitor service status
- **JSON API**: RESTful endpoints for package information

## Project Structure

```
python-libary-scanner/
├── app.py              # Main Flask application entry point
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── run.sh             # Deployment script
└── routes/            # Route modules (Flask Blueprints)
    ├── __init__.py    # Blueprint exports
    ├── health.py      # Health check endpoints
    ├── simple_api.py  # PyPI Simple API (PEP 503 + RFC 9457)
    ├── packages.py    # Package file downloads
    └── api.py         # JSON API for package information
```

## API Endpoints

### Health Check
- `GET /` - Service information and available endpoints
- `GET /health` - Health status check

### PyPI Simple Repository API (PEP 503)
- `GET /simple/<package_name>/` - Package links for pip installation

### Package Downloads
- `GET /packages/<filename>` - Download package files

### Package Information API
- `GET /api/package/<name>` - Get package metadata
- `GET /api/package/<name>/versions` - List all available versions
- `GET /api/search?q=<query>` - Search packages

## RFC 9457 (Problem Details)

When a package is not found or being scanned, the API returns RFC 9457 compliant responses that modern tools can display to users:

### Response Format

```json
{
  "type": "about:blank",
  "title": "Package Scanning in Progress",
  "status": 503,
  "detail": "Package 'example-package' is currently being scanned and will be available soon. Please try again in 2-3 minutes.",
  "instance": "/simple/example-package/"
}
```

### Response Headers
- `Content-Type: application/problem+json`
- `Retry-After: 180` (3 minutes)

### Compatibility

| Tool | Behavior |
|------|----------|
| **uv** (modern) | Displays the `detail` message to users |
| **pip** (current) | Sees 503 status, respects `Retry-After`, auto-retries |
| **pip** (future) | Will support RFC 9457 and display custom messages |

## Installation

### Local Development

```bash
# Clone the repository
git clone <repository-url>
cd python-libary-scanner

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Kubernetes Deployment

```bash
# Run the deployment script
./run.sh
```

The script will:
1. Create a virtual environment
2. Install dependencies
3. Start the Flask server on port 5000

## Configuration

All configuration is centralized in `config.py` and can be overridden via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PYPI_SERVER_URL` | Internal PyPI server URL | `http://pypiserver.hyperplane-pypiserver.svc.cluster.local:8080` |
| `FLASK_HOST` | Flask server host | `0.0.0.0` |
| `FLASK_PORT` | Flask server port | `5000` |
| `FLASK_DEBUG` | Debug mode | `True` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Example Configuration

```bash
# Set custom PyPI server
export PYPI_SERVER_URL="http://my-pypi-server.com"

# Change port
export FLASK_PORT=8080

# Enable verbose logging
export LOG_LEVEL=DEBUG

# Run application
python app.py
```

## Usage

### With pip

```bash
# Install a package
pip install --index-url http://<server-url>:8787/simple/ --trusted-host <server-host> <package-name>

# Example (internal Kubernetes)
pip install --index-url http://hyperplane-service-23d774.hyperplane-pipelines.svc.cluster.local:8787/simple/ --trusted-host hyperplane-service-23d774.hyperplane-pipelines.svc.cluster.local apache-libcloud

# Install specific version
pip install --index-url http://<server-url>/simple/ --trusted-host <server-host> apache-libcloud==3.8.0
```

### With uv (Modern Python Package Installer)

```bash
uv pip install --index-url http://<server-url>/simple/ <package-name>
```

**When a package is being scanned, uv will display:**
```
Error: Package 'example-package' is currently being scanned and will be available soon. Please try again in 2-3 minutes.
```

### API Usage Examples

```bash
# Get package information
curl http://localhost:5000/api/package/numpy

# List package versions
curl http://localhost:5000/api/package/pandas/versions

# Search for packages
curl http://localhost:5000/api/search?q=flask

# Health check
curl http://localhost:5000/health
```

### Using Python

```python
import requests

# Get package info
response = requests.get('http://localhost:5000/api/package/requests')
print(response.json())

# Get versions
response = requests.get('http://localhost:5000/api/package/flask/versions')
versions = response.json()
print(f"Total versions: {versions['total_versions']}")
print(f"Latest: {versions['latest_version']}")
```

## Development

### Adding New Routes

1. Create a new file in `routes/` directory:

```python
# routes/my_feature.py
from flask import Blueprint, jsonify

my_bp = Blueprint('my_feature', __name__, url_prefix='/my-prefix')

@my_bp.route('/endpoint')
def my_endpoint():
    return jsonify({"message": "Hello"})
```

2. Export it in `routes/__init__.py`:

```python
from .my_feature import my_bp
__all__ = ['health_bp', 'simple_api_bp', 'packages_bp', 'api_bp', 'my_bp']
```

3. Register it in `app.py`:

```python
from routes import health_bp, simple_api_bp, packages_bp, api_bp, my_bp
app.register_blueprint(my_bp)
```

### Testing

```bash
# Test configuration
python -c "from config import PYPI_SERVER_URL; print(PYPI_SERVER_URL)"

# Validate Python syntax
python -m py_compile routes/*.py

# Run with verbose logging
LOG_LEVEL=DEBUG python app.py
```

## Architecture Benefits

1. **Modularity**: Each feature is isolated in its own module
2. **Scalability**: Easy to add new routes without modifying existing code
3. **Maintainability**: Clear separation of concerns
4. **Testability**: Individual modules can be tested independently
5. **Configuration Management**: Centralized, environment-based settings
6. **Standards Compliance**: RFC 9457 for future-proof error handling

## Logging

The application logs all requests and responses for debugging:

```
2026-01-23 18:51:54 - routes.simple_api - INFO - === Incoming Request from pip ===
2026-01-23 18:51:54 - routes.simple_api - INFO - Package: example-package
2026-01-23 18:51:54 - routes.simple_api - INFO - Request Headers: {...}
2026-01-23 18:51:54 - routes.simple_api - INFO - Response status: 404
2026-01-23 18:51:54 - routes.simple_api - WARNING - Package not found, scanning in progress
```

## Deployment

### Kubernetes

The service is deployed in the Hyperplane platform:

- **Service**: `hyperplane-service-23d774.hyperplane-pipelines.svc.cluster.local`
- **Port**: `8787` (external) → `5000` (internal)
- **Namespace**: `hyperplane-pipelines`

### Viewing Logs

```bash
# View Flask application logs
kubectl logs -n hyperplane-pipelines -l app=hyperplane-service-23d774 -c d2v-pipeline

# Follow logs in real-time
kubectl logs -n hyperplane-pipelines -l app=hyperplane-service-23d774 -c d2v-pipeline -f

# Get last 50 lines
kubectl logs -n hyperplane-pipelines -l app=hyperplane-service-23d774 -c d2v-pipeline --tail=50
```

## Error Handling

The API returns appropriate HTTP status codes:

| Status | Description |
|--------|-------------|
| `200` | Success |
| `404` | Package not found |
| `500` | Internal server error |
| `503` | Service unavailable (package being scanned) |

All error responses follow RFC 9457 format with `application/problem+json` content type.

## Technologies

- Flask 3.0.0
- Flask-CORS 4.0.0
- Requests 2.31.0
- Python 3.10+

## Future Enhancements

- [ ] Package caching layer
- [ ] Advanced search functionality
- [ ] Package security scanning integration
- [ ] Metrics and monitoring endpoints (Prometheus)
- [ ] Rate limiting
- [ ] Authentication/Authorization
- [ ] WebSocket support for real-time updates

## Contributing

1. Follow the modular structure
2. Add tests for new features
3. Update documentation
4. Use RFC 9457 for error responses
5. Keep configuration in `config.py`
6. Add comprehensive logging

## License

MIT

## Support

For issues or questions:

1. Check the logs:
   ```bash
   kubectl logs -n hyperplane-pipelines -l app=hyperplane-service-23d774 -c d2v-pipeline
   ```

2. Verify service status:
   ```bash
   curl http://localhost:5000/health
   ```

3. Contact your system administrator

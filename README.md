# Python Library Scanner API

A Flask-based proxy API that provides endpoints to retrieve Python package information from PyPI (Python Package Index).

## Features

- Get detailed information about Python packages
- Retrieve all available versions of a package
- Search for packages by name
- CORS enabled for cross-origin requests
- Health check endpoint

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd python-libary-scanner
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Start the Flask server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Root
- **GET** `/`
  - Returns API information and available endpoints

### Health Check
- **GET** `/health`
  - Returns server health status

### Get Package Information
- **GET** `/api/package/<package_name>`
  - Returns detailed information about a specific package
  - Example: `http://localhost:5000/api/package/flask`
  - Response includes: name, version, summary, description, author, license, etc.

### Get Package Versions
- **GET** `/api/package/<package_name>/versions`
  - Returns all available versions of a package
  - Example: `http://localhost:5000/api/package/requests/versions`
  - Response includes: total version count, list of versions, latest version

### Search Packages
- **GET** `/api/search?q=<query>`
  - Search for packages by name
  - Example: `http://localhost:5000/api/search?q=flask`
  - Returns matching package information

## Example Requests

Using curl:

```bash
# Get package info
curl http://localhost:5000/api/package/numpy

# Get package versions
curl http://localhost:5000/api/package/pandas/versions

# Search for a package
curl http://localhost:5000/api/search?q=django

# Health check
curl http://localhost:5000/health
```

Using Python:

```python
import requests

# Get package info
response = requests.get('http://localhost:5000/api/package/requests')
print(response.json())

# Get versions
response = requests.get('http://localhost:5000/api/package/flask/versions')
print(response.json())
```

## Error Handling

The API returns appropriate HTTP status codes:
- `200` - Success
- `400` - Bad Request (missing required parameters)
- `404` - Package not found
- `500` - Internal server error

## Technologies

- Flask 3.0.0
- Flask-CORS 4.0.0
- Requests 2.31.0

## License

MIT

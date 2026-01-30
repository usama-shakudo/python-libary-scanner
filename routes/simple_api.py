"""
PyPI Simple Repository API routes (PEP 503)
Clean architecture: Route -> Controller -> Service -> Repository -> Model
"""

import logging
import requests
from flask import Blueprint, Response, g, request
from config import Config
from database import get_session
from controllers.package_controller import PackageController
from utils.version_parser import parse_python_version, parse_package_and_version

logger = logging.getLogger(__name__)
simple_api_bp = Blueprint('simple_api', __name__, url_prefix='/simple')

# -----------------------
# DB session management
# -----------------------

@simple_api_bp.before_request
def open_db_session():
    """Open a DB session before each request"""
    g.db = get_session()


@simple_api_bp.after_request
def commit_db_session(response):
    """Commit the DB session after successful request"""
    db = getattr(g, "db", None)
    if db is not None:
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
    return response


@simple_api_bp.teardown_request
def close_db_session(exception=None):
    """Close the DB session after each request"""
    db = getattr(g, "db", None)
    if db is not None:
        if exception:
            db.rollback()
        db.close()


# -----------------------
# Routes
# -----------------------

@simple_api_bp.route('/<package_name>/')
def simple_package(package_name: str):
    """
    Simple Repository API - Package Links (PEP 503)
    Uses PackageController with per-request DB session
    """
    # Extract User-Agent header for Python version
    user_agent = request.headers.get('User-Agent', '')
    python_version = parse_python_version(user_agent)

    # Parse package name and version from request
    parsed_name, version = parse_package_and_version(package_name)

    controller = PackageController.create_with_db()
    return controller.get_package(parsed_name, version, python_version)


@simple_api_bp.route('/')
def simple_index():
    """
    Simple Repository API - Index
    Lists all available packages (proxy to PyPI server)
    """
    try:
        response = requests.get(f"{Config.PYPI_SERVER_URL}/simple/", timeout=10)
        # Filter headers to avoid problematic ones like Transfer-Encoding
        headers = {k: v for k, v in response.headers.items()
                   if k.lower() not in ("transfer-encoding", "content-encoding")}
        return Response(response.content, status=response.status_code, headers=headers)
    except Exception as e:
        logger.error(f"PyPI server error: {e}", exc_info=True)
        return Response("Service temporarily unavailable", status=503)

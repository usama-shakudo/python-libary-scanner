"""
Package download routes
Handles package file downloads from PyPI server
"""

from flask import Blueprint, request, Response
import requests
import logging

from config import Config

packages_bp = Blueprint('packages', __name__, url_prefix='/packages')
logger = logging.getLogger(__name__)


@packages_bp.route('/<path:filename>')
def download_package(filename: str):
    """
    Package file download endpoint
    Proxies package files from the PyPI server
    """
    try:
        # Log all incoming request headers from pip
        logger.info(f"=== Incoming Package Download Request ===")
        logger.info(f"Filename: {filename}")
        logger.info(f"Request Headers: {dict(request.headers)}")
        logger.info(f"Request Method: {request.method}")
        logger.info(f"Request Remote Address: {request.remote_addr}")

        # Proxy from PyPI server
        url = f"{Config.PYPI_SERVER_URL}/packages/{filename}"
        logger.info(f"Proxying to: {url}")

        response = requests.get(url, stream=True, timeout=30)

        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")

        if response.status_code == 404:
            logger.warning(f"Package file not found: {filename}")
            return Response("File not found", status=404)

        response.raise_for_status()

        # Stream the file back to the client
        return Response(
            response.iter_content(chunk_size=8192),
            content_type=response.headers.get('content-type', 'application/octet-stream'),
            headers={
                'Content-Disposition': response.headers.get('content-disposition', ''),
                'Content-Length': response.headers.get('content-length', '')
            }
        )

    except requests.RequestException as e:
        logger.error(f"Failed to download package file {filename}: {str(e)}")
        return Response(f"Error downloading file: {str(e)}", status=500)

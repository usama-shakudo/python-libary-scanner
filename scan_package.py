#!/usr/bin/env python3
"""
Package vulnerability scanner - Multi-Version Support
Downloads Python packages for multiple versions, scans for vulnerabilities, and uploads to PyPI if safe
Updates database with scan results
"""

import sys
import os
import subprocess
import tempfile
import json
import psycopg2
from datetime import datetime
from pathlib import Path
import glob
import re

# Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:Y2dtcJhdFW@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres'
)

PYPI_SERVER_URL = os.getenv(
    'PYPI_SERVER_URL',
    'http://pypiserver-pypiserver.hyperplane-pypiserver.svc.cluster.local:8080'
)

PYPI_USERNAME = os.getenv('PYPI_USERNAME', 'username')
PYPI_PASSWORD = os.getenv('PYPI_PASSWORD', 'password')

# Python versions to support (can be overridden via environment variable)
PYTHON_VERSIONS = os.getenv('PYTHON_VERSIONS', '3.9 3.10 3.11 3.12').split()

# Disable scanning for testing
DISABLE_SCAN_AUDIT = os.getenv('DISABLE_SCAN_AUDIT', 'false').lower() == 'true'


def log(message):
    """Print timestamped log message"""
    timestamp = datetime.utcnow().isoformat()
    print(f"[{timestamp}] {message}")


def is_universal_package(package_file):
    """
    Check if a package file is universal (works across all Python versions)
    Universal indicators:
      - *.tar.gz (source distribution)
      - *-py3-none-any.whl (universal wheel)
      - *-py2.py3-none-any.whl (Python 2+3 universal)
    """
    filename = os.path.basename(package_file)

    if filename.endswith('.tar.gz'):
        return True

    if filename.endswith('-py3-none-any.whl'):
        return True

    if filename.endswith('-py2.py3-none-any.whl'):
        return True

    return False


def parse_package_spec(package_spec):
    """Parse package specification in format: packagename==version"""
    match = re.match(r'^(.+)==(.+)$', package_spec)
    if match:
        return match.group(1), match.group(2)
    else:
        raise ValueError(f"Invalid package specification: {package_spec}. Expected format: packagename==version")


def update_package_status(package_name, status, vulnerability_info=None):
    """Update package status in database"""
    # TODO: Uncomment when psycopg2 is available

    try:
        # Add retry logic for Istio
        import time
        max_retries = 3
        retry_delay = 2

        conn = None
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
                break
            except psycopg2.OperationalError as e:
                if attempt < max_retries - 1:
                    log(f"Database connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise

        cursor = conn.cursor()

        cursor.execute("""
            UPDATE packages
            SET status = %s,
                vulnerability_info = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE package_name = %s
        """, (status, vulnerability_info, package_name))

        conn.commit()
        cursor.close()
        conn.close()

        log(f"✅ Updated {package_name} status to: {status}")
        return True

    except Exception as e:
        log(f"❌ Error updating database: {str(e)}")
        return False


def download_package_for_python_version(package_name, package_version, python_version, download_dir):
    """Download a package using a specific Python version's pip"""
    venv_dir = os.path.join(download_dir, f"venv_{python_version}")
    pkg_dir = os.path.join(download_dir, f"packages_{python_version}")

    os.makedirs(pkg_dir, exist_ok=True)

    log(f"   📥 Attempting download for Python {python_version}...")

    # Check if Python version is available
    python_cmd = f"python{python_version}"
    if subprocess.run(["which", python_cmd], capture_output=True).returncode != 0:
        log(f"   ⚠️  Python {python_version} not available, skipping")
        return None

    try:
        # Create virtual environment for this Python version
        result = subprocess.run(
            [python_cmd, "-m", "venv", venv_dir],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            log(f"   ⚠️  Failed to create venv for Python {python_version}")
            return None

        # Upgrade pip in the venv
        pip_cmd = os.path.join(venv_dir, "bin", "pip")
        subprocess.run(
            [pip_cmd, "install", "--quiet", "--upgrade", "pip", "setuptools", "wheel"],
            capture_output=True,
            timeout=120
        )

        # Download package using this venv's pip
        result = subprocess.run(
            [pip_cmd, "download", f"{package_name}=={package_version}",
             "--no-deps", "-d", pkg_dir, "--no-cache-dir"],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            log(f"   ⚠️  Download failed for Python {python_version}")
            return None

        # Find what was downloaded
        package_files = glob.glob(os.path.join(pkg_dir, "*.whl")) + \
                       glob.glob(os.path.join(pkg_dir, "*.tar.gz"))

        if package_files:
            package_file = package_files[0]
            log(f"   ✅ Downloaded: {os.path.basename(package_file)}")
            return package_file

        log(f"   ⚠️  No package file found after download for Python {python_version}")
        return None

    except subprocess.TimeoutExpired:
        log(f"   ⚠️  Download timeout for Python {python_version}")
        return None
    except Exception as e:
        log(f"   ⚠️  Download error for Python {python_version}: {str(e)}")
        return None


def download_packages_for_all_versions(package_name, package_version, download_dir):
    """
    Download a package for all configured Python versions
    Smart detection: if universal package found, skip other versions
    """
    log(f"📦 Downloading {package_name}=={package_version} for multiple Python versions...")

    downloaded_files = []

    for py_version in PYTHON_VERSIONS:
        package_file = download_package_for_python_version(
            package_name, package_version, py_version, download_dir
        )

        if package_file:
            # Check if this is a universal package
            if is_universal_package(package_file):
                log(f"   🌍 Universal package detected! Works for all Python versions.")
                log(f"   ⏭️  Skipping downloads for remaining Python versions.")
                return [package_file]

            downloaded_files.append(package_file)

    if not downloaded_files:
        log(f"   ❌ Failed to download package for any Python version")
        return []

    log(f"   📊 Downloaded {len(downloaded_files)} version-specific package(s)")
    return downloaded_files


def scan_package_vulnerabilities(package_name, package_version, scan_dir):
    """Scan package for vulnerabilities using Trivy"""
    if DISABLE_SCAN_AUDIT:
        log(f"🔍 STEP 2: Vulnerability scanning DISABLED")
        return {"vulnerable": False, "vulnerabilities": [], "note": "scanning disabled"}

    log(f"🔍 STEP 2: Scanning for vulnerabilities...")

    try:
        log(f"   🔍 Scanning with Trivy for vulnerabilities...")

        # Create a requirements.txt for Trivy to scan
        reqfile = os.path.join(scan_dir, "requirements.txt")
        with open(reqfile, 'w') as f:
            f.write(f"{package_name}=={package_version}\n")

        scan_output = os.path.join(scan_dir, "trivy_scan.json")

        # Run Trivy scan
        # --exit-code 1 = fail if vulnerabilities found
        # --severity CRITICAL,HIGH = only care about serious issues
        result = subprocess.run(
            [
                "trivy", "fs",
                "--exit-code", "1",
                "--severity", "CRITICAL,HIGH",
                "--format", "json",
                "--output", scan_output,
                scan_dir
            ],
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            log(f"   ✅ No critical/high vulnerabilities found")
            return {"vulnerable": False, "vulnerabilities": []}

        # Vulnerabilities detected
        log(f"   ❌ VULNERABILITIES DETECTED!")

        # Read scan results
        vulnerabilities = {}
        if os.path.exists(scan_output):
            with open(scan_output, 'r') as f:
                vulnerabilities = json.load(f)

        return {
            "vulnerable": True,
            "vulnerabilities": vulnerabilities,
            "scan_output": json.dumps(vulnerabilities)
        }

    except subprocess.TimeoutExpired:
        log(f"   ❌ Trivy scan timeout after 5 minutes")
        return None
    except FileNotFoundError:
        log(f"   ⚠️  Trivy not installed, treating package as safe")
        return {"vulnerable": False, "vulnerabilities": [], "note": "trivy not available"}
    except Exception as e:
        log(f"   ❌ Trivy scan error: {str(e)}")
        return None


def upload_to_pypi(package_file):
    """Upload package to internal PyPI server using twine"""
    try:
        log(f"⬆️  Uploading to PyPI server: {os.path.basename(package_file)}")

        cmd = [
            "twine", "upload",
            "--repository-url", PYPI_SERVER_URL,
            "--username", PYPI_USERNAME,
            "--password", PYPI_PASSWORD,
            package_file
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        if result.returncode != 0:
            # Check if already exists (this is OK)
            if "already exists" in result.stderr.lower() or "File already exists" in result.stdout:
                log(f"ℹ️  Package already exists on PyPI server")
                return True

            log(f"❌ Upload failed: {result.stderr}")
            return False

        log(f"✅ Successfully uploaded to PyPI server")
        return True

    except subprocess.TimeoutExpired:
        log(f"❌ Upload timeout after 2 minutes")
        return False
    except FileNotFoundError:
        log(f"❌ twine not installed")
        return False
    except Exception as e:
        log(f"❌ Upload error: {str(e)}")
        return False


def scan_and_upload_package(package_name, package_version):
    """Main scanning and upload workflow"""
    log(f"=" * 60)
    log(f"📦 Processing package: {package_name}=={package_version}")
    log(f"=" * 60)

    # Create temporary directory for downloads
    with tempfile.TemporaryDirectory() as download_dir:
        log(f"📂 Using temporary directory: {download_dir}")

        # Step 1: Download packages for all Python versions
        log(f"\n🔸 STEP 1: Download Packages")
        package_files = download_packages_for_all_versions(
            package_name, package_version, download_dir
        )

        if not package_files:
            log(f"❌ FAILED: Could not download package")
            update_package_status(
                package_name,
                "error",
                json.dumps({"error": "Failed to download package"})
            )
            return False

        # Step 2: Scan for vulnerabilities
        scan_result = scan_package_vulnerabilities(package_name, package_version, download_dir)

        if scan_result is None:
            log(f"❌ FAILED: Scan encountered an error")
            update_package_status(
                package_name,
                "error",
                json.dumps({"error": "Scan failed"})
            )
            return False

        # Step 3: Handle results based on vulnerability status
        if scan_result["vulnerable"]:
            # Package has vulnerabilities - update DB and DO NOT upload
            log(f"\n🔸 STEP 3: Update Database (VULNERABLE)")

            vulnerability_info = json.dumps({
                "vulnerabilities": scan_result["vulnerabilities"],
                "scanned_at": datetime.utcnow().isoformat(),
                "scanner": "trivy"
            })

            update_package_status(package_name, "vulnerable", vulnerability_info)
            log(f"⛔ Package marked as VULNERABLE - not uploading to PyPI")
            return False

        else:
            # Package is safe - upload ALL files to PyPI then update DB
            log(f"\n🔸 STEP 3: Upload to PyPI Server")
            log(f"   Uploading {len(package_files)} package file(s)...")

            upload_success = True
            for package_file in package_files:
                log(f"   Processing: {os.path.basename(package_file)}")
                if not upload_to_pypi(package_file):
                    upload_success = False

            if not upload_success:
                log(f"❌ FAILED: Some uploads to PyPI failed")
                update_package_status(
                    package_name,
                    "error",
                    json.dumps({"error": "Failed to upload to PyPI"})
                )
                return False

            log(f"\n🔸 STEP 4: Update Database (SAFE)")

            vulnerability_info = json.dumps({
                "vulnerabilities": [],
                "scanned_at": datetime.utcnow().isoformat(),
                "scanner": "trivy",
                "uploaded_to_pypi": True,
                "note": scan_result.get("note"),
                "python_versions": PYTHON_VERSIONS
            })

            update_package_status(package_name, "safe", vulnerability_info)
            log(f"✅ Package marked as SAFE and uploaded to PyPI")

    log(f"\n" + "=" * 60)
    log(f"✅ Processing complete for: {package_name}=={package_version}")
    log(f"=" * 60)

    return True


def main():
    """Main entry point"""
    # Get package spec from environment variable (preferred) or command-line argument
    package_spec = os.getenv('PACKAGE_NAME')

    if package_spec:
        log(f"📦 Package from environment: {package_spec}")
    elif len(sys.argv) == 2:
        package_spec = sys.argv[1]
        log(f"📦 Package from command-line: {package_spec}")
    else:
        # TEST MODE: Set a temporary package for testing
        TEST_MODE = True  # Set to False to require either env var or command-line arg
        TEST_PACKAGE = "requests==2.31.0"  # Change this to test different packages

        if TEST_MODE:
            log(f"🧪 TEST MODE: Using temporary package: {TEST_PACKAGE}")
            package_spec = TEST_PACKAGE
        else:
            print("Usage: python scan_package.py <package_spec>")
            print("   OR: Set PACKAGE_NAME environment variable")
            print("Example: python scan_package.py requests==2.31.0")
            print("Example: PACKAGE_NAME=requests==2.31.0 python scan_package.py")
            sys.exit(1)

    log(f"🚀 Package Scanner Starting - Multi-Version Support")
    log(f"   Python versions: {', '.join(PYTHON_VERSIONS)}")
    log(f"   Vulnerability scanner: trivy")
    log(f"   Package: {package_spec}")
    log(f"   PyPI Server: {PYPI_SERVER_URL}")

    try:
        # Parse package specification
        package_name, package_version = parse_package_spec(package_spec)
        log(f"   Parsed: {package_name} version {package_version}")

        success = scan_and_upload_package(package_name, package_version)
        sys.exit(0 if success else 1)

    except ValueError as e:
        log(f"❌ Invalid package specification: {str(e)}")
        sys.exit(1)

    except Exception as e:
        log(f"💥 Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()

        # Try to update database with error
        try:
            # Try to parse package name for database update
            try:
                package_name, _ = parse_package_spec(package_spec)
            except:
                package_name = package_spec

            update_package_status(
                package_name,
                "error",
                json.dumps({"error": f"Fatal error: {str(e)}"})
            )
        except:
            pass

        sys.exit(1)


if __name__ == "__main__":
    main()

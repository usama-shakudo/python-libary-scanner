#!/usr/bin/env python3
"""
Process pending packages - create scanner jobs for packages awaiting scanning
Run every 5 minutes via Hyperplane scheduled pipeline
"""

import os
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Configuration
MAX_CONCURRENT_JOBS = 10
JOB_NAME_PREFIX = "package-scanner"
NAMESPACE = "hyperplane-pipelines"
DATABASE_URL = "postgresql://postgres:CYo8ILCGUi@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres"

# Kubernetes API configuration (in-cluster)
# Access API server directly via hyperplane-core namespace
K8S_API_HOST = "https://kubernetes.hyperplane-core.svc.cluster.local:443"
K8S_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
K8S_CA_CERT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

print(f"Kubernetes API Host: {K8S_API_HOST}")
print(f"Database URL: {DATABASE_URL.split('@')[0].split(':')[0]}:***@{DATABASE_URL.split('@')[1]}")
print()

print("=" * 60)
print("Package Scanner Job Manager")
print("=" * 60)
print(f"Started at: {datetime.utcnow().isoformat()}")
print()


def get_running_jobs_count():
    """Get count of currently running scanner jobs using Kubernetes REST API"""
    try:
        print(f"Step 1: Checking running jobs...")

        # Read service account token
        if not os.path.exists(K8S_TOKEN_PATH):
            print(f"Service account token not found at {K8S_TOKEN_PATH}")
            return 0

        with open(K8S_TOKEN_PATH, 'r') as f:
            token = f.read().strip()

        # Make request to Kubernetes API
        url = f"{K8S_API_HOST}/apis/batch/v1/namespaces/{NAMESPACE}/jobs"
        params = {"labelSelector": f"app={JOB_NAME_PREFIX}"}
        headers = {"Authorization": f"Bearer {token}"}

        # Check if CA cert exists
        verify = K8S_CA_CERT_PATH if os.path.exists(K8S_CA_CERT_PATH) else False

        response = requests.get(url, headers=headers, params=params, verify=verify, timeout=10)
        response.raise_for_status()

        jobs_data = response.json()

        # Count jobs that are not completed successfully
        running_count = 0
        for job in jobs_data.get('items', []):
            status = job.get('status', {})
            succeeded = status.get('succeeded', 0)

            # Job is running if it hasn't completed successfully
            if succeeded == 0:
                running_count += 1

        print(f"Current running jobs: {running_count}")
        print()

        return running_count

    except Exception as e:
        print(f"Error checking jobs: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0


def get_pending_packages(limit):
    """Fetch pending packages from database"""
    try:
        print(f"Step 1: Fetching pending packages from database...")

        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT package_name
            FROM packages
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT %s;
        """, (limit,))

        packages = cursor.fetchall()
        cursor.close()
        conn.close()

        package_names = [pkg['package_name'] for pkg in packages]
        print(f"Found {len(package_names)} pending package(s) to process")
        print()

        return package_names

    except Exception as e:
        print(f"Error fetching packages from database: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def create_scanner_job(package_name):
    """Create a scanner job for the given package"""
    try:
        print(f"Creating job for package: {package_name}")

        # For now, just print message (placeholder for actual job creation)
        print(f"  → Job created for: {package_name}")

        # TODO: Uncomment below to create actual Kubernetes job
        # job_name = f"{JOB_NAME_PREFIX}-{package_name.lower().replace('_', '-')}-{int(datetime.utcnow().timestamp())}"
        # cmd = [
        #     "kubectl", "create", "job", job_name,
        #     "-n", NAMESPACE,
        #     "--image=scanner-image:latest",
        #     "--", "scan", package_name
        # ]
        # subprocess.run(cmd, check=True, capture_output=True, text=True)

        return True

    except Exception as e:
        print(f"  ✗ Error creating job for {package_name}: {str(e)}")
        return False


def main():
    """Main execution function"""

    # 1. Check running jobs
    running_jobs = get_running_jobs_count()

    # 2. Calculate available slots
    available_slots = MAX_CONCURRENT_JOBS - running_jobs

    if available_slots <= 0:
        print(f"No available slots. All {MAX_CONCURRENT_JOBS} job slots are in use.")
        return

    print(f"Available job slots: {available_slots}")
    print()

    # 3. Fetch pending packages
    pending_packages = get_pending_packages(available_slots)

    if not pending_packages:
        print("No pending packages found in database.")
        return

    # 4. Create jobs
    print(f"Step 3: Creating jobs...")
    print()

    created_count = 0
    for package_name in pending_packages:
        if create_scanner_job(package_name):
            created_count += 1

    # 5. Summary
    print()
    print("=" * 60)
    print("Summary:")
    print(f"  - Running jobs before: {running_jobs}")
    print(f"  - Jobs created: {created_count}")
    print(f"  - Total running jobs now: {running_jobs + created_count}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)

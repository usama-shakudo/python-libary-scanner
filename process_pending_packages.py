#!/usr/bin/env python3
"""
Process pending packages - create scanner jobs for packages awaiting scanning
Run every 5 minutes via Hyperplane scheduled pipeline
"""

import os
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Configuration
MAX_CONCURRENT_JOBS = 10
JOB_NAME_PREFIX = "package"
NAMESPACE = "hyperplane-pipelines"
DATABASE_URL = "postgresql://postgres:CYo8ILCGUi@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres"

# Scanner Docker image
SCANNER_IMAGE = os.getenv("SCANNER_IMAGE", "gcr.io/devsentient-infra/custom/hnb/custom/pypiscanningjob:latest")

# Keycloak Authentication (for GraphQL API)
REALM = os.getenv("HYPERPLANE_REALM", "Hyperplane")
CLIENT_ID = os.getenv("HYPERPLANE_CLIENT_ID", "istio")
HYPERPLANE_DOMAIN = os.getenv("HYPERPLANE_DOMAIN", "")
HYPERPLANE_USERNAME = os.getenv("HYPERPLANE_USERNAME", "")
HYPERPLANE_PASSWORD = os.getenv("HYPERPLANE_PASSWORD", "")
HYPERPLANE_REFRESH_TOKEN = os.getenv("HYPERPLANE_REFRESH_TOKEN", None)
HYPERPLANE_GRAPHQL_URL = os.getenv("HYPERPLANE_GRAPHQL_URL", "http://api-server.hyperplane-core.svc.cluster.local/graphql")
HYPERPLANE_USER_ID = os.getenv("HYPERPLANE_USER_ID", "")
HYPERPLANE_USER_EMAIL = os.getenv("HYPERPLANE_USER_EMAIL", "")
HYPERPLANE_VC_SERVER_ID = os.getenv("HYPERPLANE_VC_SERVER_ID", "")

# Kubernetes API configuration (in-cluster)
# Use standard Kubernetes service DNS (verified working in hyperplane-pipelines pods)
K8S_API_HOST = "https://kubernetes.default.svc:443"
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

        # Make request to Kubernetes API with retry logic for Istio initialization
        url = f"{K8S_API_HOST}/apis/batch/v1/namespaces/{NAMESPACE}/jobs"
        params = {"labelSelector": f"hyperplane.dev/app-name={JOB_NAME_PREFIX}"}
        headers = {"Authorization": f"Bearer {token}"}

        # Check if CA cert exists
        verify = K8S_CA_CERT_PATH if os.path.exists(K8S_CA_CERT_PATH) else False

        # Retry logic for Istio sidecar initialization
        import time
        max_retries = 3
        retry_delay = 2  # seconds

        response = None
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, params=params, verify=verify, timeout=10)
                response.raise_for_status()
                break
            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"Connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise

        if not response:
            raise Exception("Failed to connect to Kubernetes API after retries")

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
        print(f"Defaulting to 0 running jobs")
        import traceback
        traceback.print_exc()
        return 0


def get_pending_packages(limit):
    """Fetch pending packages from database"""
    try:
        print(f"Step 2: Fetching pending packages from database...")

        # Add connection timeout and retry for Istio sidecar initialization
        print(f"Waiting for Istio sidecar to initialize...")
        import time
        max_retries = 3
        retry_delay = 2  # seconds

        conn = None
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
                print(f"Successfully connected to database")
                break
            except psycopg2.OperationalError as e:
                if attempt < max_retries - 1:
                    print(f"Connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise

        if not conn:
            raise Exception("Failed to connect to database after retries")

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


def get_shakudo_token():
    """
    Generate JWT token via Keycloak/OpenID Connect
    If refresh token is provided, use it to obtain a new access token
    """
    if not HYPERPLANE_DOMAIN:
        print("  ⚠️  HYPERPLANE_DOMAIN not set, cannot authenticate")
        return None, None

    if not HYPERPLANE_USERNAME and not HYPERPLANE_REFRESH_TOKEN:
        print("  ⚠️  Either USERNAME/PASSWORD or REFRESH_TOKEN required")
        return None, None

    token_endpoint = f"https://{HYPERPLANE_DOMAIN}/auth/realms/{REALM}/protocol/openid-connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    if HYPERPLANE_REFRESH_TOKEN:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": HYPERPLANE_REFRESH_TOKEN,
            "client_id": CLIENT_ID
        }
    else:
        data = {
            "grant_type": "password",
            "username": HYPERPLANE_USERNAME,
            "password": HYPERPLANE_PASSWORD,
            "client_id": CLIENT_ID
        }

    try:
        response = requests.post(token_endpoint, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        res = response.json()
        access_token = res['access_token']
        new_refresh_token = res.get('refresh_token', HYPERPLANE_REFRESH_TOKEN)
        return access_token, new_refresh_token
    except requests.exceptions.RequestException as err:
        print(f"  ✗ Failed to get token: {err}")
        return None, None


def create_scanner_job_graphql(package_name):
    """
    Create a scanner job using Hyperplane GraphQL API
    This makes jobs appear in Hyperplane UI
    """
    try:
        print(f"Creating job via GraphQL for package: {package_name}")

        # Get authentication token
        print(f"  Getting authentication token...")
        access_token, _ = get_shakudo_token()

        if not access_token:
            print(f"  ✗ Failed to obtain access token")
            return False

        if not HYPERPLANE_USER_ID or not HYPERPLANE_USER_EMAIL:
            print(f"  ✗ Missing HYPERPLANE_USER_ID or HYPERPLANE_USER_EMAIL")
            return False

        # Generate unique job name
        timestamp = int(datetime.utcnow().timestamp())
        safe_name = package_name.split('==')[0].lower().replace('_', '-').replace('.', '-')
        job_name = f"scanner-{safe_name}-{timestamp}"

        # Build simplified pod spec (no git needed, scan_package.py must be in Docker image)
        pod_spec = {
            "priorityClassName": "shakudo-job-default",
            "restartPolicy": "Never",
            "serviceAccountName": "gcr-pipelines",
            "containers": [{
                "name": "scanner",
                "image": SCANNER_IMAGE,
                "command": ["/bin/sh", "-c"],
                "args": [f"python3 /app/scan_package.py '{package_name}'"],
                "env": [
                    {"name": "DATABASE_URL", "value": DATABASE_URL},
                    {"name": "PYPI_SERVER_URL", "value": os.getenv("PYPI_SERVER_URL", "http://pypiserver.hyperplane-pypiserver.svc.cluster.local:8080")},
                    {"name": "PYPI_USERNAME", "value": os.getenv("PYPI_USERNAME", "username")},
                    {"name": "PYPI_PASSWORD", "value": os.getenv("PYPI_PASSWORD", "password")},
                    {"name": "PYTHON_VERSIONS", "value": os.getenv("PYTHON_VERSIONS", "3.9 3.10 3.11 3.12")}
                ],
                "resources": {
                    "limits": {"cpu": "2000m", "memory": "2Gi"},
                    "requests": {"cpu": "500m", "memory": "512Mi"}
                }
            }]
        }

        # GraphQL mutation
        mutation = """
        mutation createPipelineJobWithAlerting($jobName: String!, $type: String!, $imageHash: String, $noHyperplaneCommands: Boolean, $debuggable: Boolean!, $notificationsEnabled: Boolean, $notificationTargetIds: [String!], $timeout: Int!, $activeTimeout: Int, $maxRetries: Int!, $yamlPath: String!, $workingDir: String!, $noGitInit: Boolean, $hyperplaneVCServerId: HyperplaneVCServerWhereUniqueInput, $hyperplaneSecrets: [HyperplaneSecretWhereUniqueInput!], $branchName: String, $commitId: String, $parameters: ParameterCreateNestedManyWithoutPipelineJobInput, $hyperplaneUserId: String!, $hyperplaneUserEmail: String!, $group: String, $podSpec: String, $cloudSqlProxyEnabled: Boolean, $pipelineType: String) {
          createPipelineJobWithAlerting(
            input: {jobName: $jobName, jobType: $type, imageHash: $imageHash, noHyperplaneCommands: $noHyperplaneCommands, debuggable: $debuggable, notificationsEnabled: $notificationsEnabled, notificationTargetIds: $notificationTargetIds, timeout: $timeout, activeTimeout: $activeTimeout, maxRetries: $maxRetries, pipelineYamlPath: $yamlPath, workingDir: $workingDir, noGitInit: $noGitInit, hyperplaneVCServer: {connect: $hyperplaneVCServerId}, hyperplaneSecrets: {connect: $hyperplaneSecrets}, branchName: $branchName, commitId: $commitId, parameters: $parameters, hyperplaneUser: {connect: {id: $hyperplaneUserId}}, hyperplaneUserEmail: $hyperplaneUserEmail, group: $group, podSpec: $podSpec, cloudSqlProxyEnabled: $cloudSqlProxyEnabled, pipelineType: $pipelineType}
          ) {
            id
            jobName
            status
          }
        }
        """

        variables = {
            "jobName": job_name,
            "type": "package-scanner",
            "imageHash": "",
            "noHyperplaneCommands": True,  # We run Python directly, no Hyperplane commands
            "debuggable": False,
            "notificationsEnabled": False,
            "notificationTargetIds": [],
            "timeout": 3600,
            "activeTimeout": 3600,
            "maxRetries": 2,
            "yamlPath": "scan_package.py",
            "workingDir": "/app",
            "noGitInit": True,  # scan_package.py must be in Docker image
            "hyperplaneVCServerId": {"id": HYPERPLANE_VC_SERVER_ID} if HYPERPLANE_VC_SERVER_ID else None,
            "hyperplaneSecrets": [],
            "branchName": "",
            "commitId": "",
            "parameters": {"create": []},
            "hyperplaneUserId": HYPERPLANE_USER_ID,
            "hyperplaneUserEmail": HYPERPLANE_USER_EMAIL,
            "group": "",
            "podSpec": json.dumps(pod_spec),
            "cloudSqlProxyEnabled": False,
            "pipelineType": "BASH"
        }

        payload = {
            "operationName": "createPipelineJobWithAlerting",
            "query": mutation,
            "variables": variables
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.post(HYPERPLANE_GRAPHQL_URL, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                print(f"  ✗ GraphQL errors: {result['errors']}")
                return False

            job_data = result.get("data", {}).get("createPipelineJobWithAlerting", {})
            print(f"  ✓ Job created: {job_data.get('id')} - {job_data.get('status')}")
            return True
        else:
            print(f"  ✗ HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def create_scanner_job(package_name):
    """Create a scanner job for the given package using Kubernetes REST API (fallback)"""
    try:
        print(f"Creating job for package: {package_name}")

        # Read service account token
        if not os.path.exists(K8S_TOKEN_PATH):
            print(f"  ✗ Service account token not found")
            return False

        with open(K8S_TOKEN_PATH, 'r') as f:
            token = f.read().strip()

        # Generate unique job name
        # Remove version (==x.y.z) and sanitize for Kubernetes naming
        safe_name = package_name.split('==')[0].lower().replace('_', '-').replace('.', '-')
        timestamp = int(datetime.utcnow().timestamp())
        job_name = f"{JOB_NAME_PREFIX}-{safe_name}-{timestamp}"

        # Create Kubernetes Job manifest
        job_manifest = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "namespace": NAMESPACE,
                "labels": {
                    "hyperplane.dev/app-name": JOB_NAME_PREFIX,
                    "package": safe_name
                }
            },
            "spec": {
                "ttlSecondsAfterFinished": 3600,  # Clean up after 1 hour
                "backoffLimit": 2,  # Retry up to 2 times
                "template": {
                    "metadata": {
                        "labels": {
                            "hyperplane.dev/app-name": JOB_NAME_PREFIX,
                            "package": safe_name
                        }
                    },
                    "spec": {
                        "restartPolicy": "Never",
                        "serviceAccountName": "package-scanner-scan",
                        "containers": [{
                            "name": "scanner",
                            "image": "gcr.io/devsentient-infra/custom/hnb/custom/pypiscanningjob:latest",
                            "command": ["python3", "/app/scan_package.py", package_name],
                            "env": [
                                {
                                    "name": "DATABASE_URL",
                                    "value": DATABASE_URL
                                },
                                {
                                    "name": "PYPI_SERVER_URL",
                                    "value": os.getenv("PYPI_SERVER_URL", "http://pypiserver.hyperplane-pypiserver.svc.cluster.local:8080")
                                },
                                {
                                    "name": "PYPI_USERNAME",
                                    "value": os.getenv("PYPI_USERNAME", "username")
                                },
                                {
                                    "name": "PYPI_PASSWORD",
                                    "value": os.getenv("PYPI_PASSWORD", "password")
                                },
                                {
                                    "name": "PYTHON_VERSIONS",
                                    "value": os.getenv("PYTHON_VERSIONS", "3.9 3.10 3.11 3.12")
                                }
                            ],
                            "resources": {
                                "requests": {
                                    "memory": "512Mi",
                                    "cpu": "500m"
                                },
                                "limits": {
                                    "memory": "2Gi",
                                    "cpu": "2000m"
                                }
                            }
                        }]
                    }
                }
            }
        }

        # Create job via Kubernetes API
        url = f"{K8S_API_HOST}/apis/batch/v1/namespaces/{NAMESPACE}/jobs"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        verify = K8S_CA_CERT_PATH if os.path.exists(K8S_CA_CERT_PATH) else False

        # Retry logic for Istio
        import time
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=job_manifest,
                    verify=verify,
                    timeout=10
                )

                if response.status_code == 201:
                    print(f"  ✓ Job created: {job_name}")
                    return True
                elif response.status_code == 409:
                    print(f"  ℹ️  Job already exists: {job_name}")
                    return True
                else:
                    print(f"  ✗ Failed to create job (HTTP {response.status_code}): {response.text}")
                    if attempt < max_retries - 1:
                        print(f"  Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                    else:
                        return False

            except requests.exceptions.ConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"  Connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    raise

        return False

    except Exception as e:
        print(f"  ✗ Error creating job for {package_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution function"""

    # 1. Check running jobs (with Istio retry logic)
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

    # Choose GraphQL API (recommended) or Kubernetes REST API
    use_graphql = os.getenv("USE_GRAPHQL_API", "true").lower() == "false"

    created_count = 0
    for package_name in pending_packages:
        # Use GraphQL API by default (appears in Hyperplane UI)
        if use_graphql:
            success = create_scanner_job_graphql(package_name)
        else:
            # Fallback to Kubernetes REST API
            success = create_scanner_job(package_name)

        if success:
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

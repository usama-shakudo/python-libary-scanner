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
DATABASE_URL = "postgresql://postgres:Y2dtcJhdFW@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres"

# Scanner Docker image
SCANNER_IMAGE = os.getenv("SCANNER_IMAGE", "gcr.io/devsentient-infra/custom/hnb/custom/pypiscanningjob:latestv3")
HYPERPLANE_GRAPHQL_URL = os.getenv("HYPERPLANE_GRAPHQL_URL", "http://api-server.hyperplane-core.svc.cluster.local/graphql")
HYPERPLANE_USER_ID = os.getenv("HYPERPLANE_USER_ID", "3630abbd-289b-4d78-85d0-fcf7bcb3cc81")
HYPERPLANE_USER_EMAIL = os.getenv("HYPERPLANE_USER_EMAIL", "shakudo-admin@shakudo.io")
HYPERPLANE_VC_SERVER_ID = os.getenv("HYPERPLANE_VC_SERVER_ID", "c4be4cb1-9623-4d00-abcb-b472e9a4f192")


print(f"GraphQL API URL: {HYPERPLANE_GRAPHQL_URL}")
print(f"Database URL: {DATABASE_URL.split('@')[0].split(':')[0]}:***@{DATABASE_URL.split('@')[1]}")
print()

print("=" * 60)
print("Package Scanner Job Manager")
print("=" * 60)
print(f"Started at: {datetime.utcnow().isoformat()}")
print()

def count_jobs_advanced(
    prefix=None,
    status=None,
    job_type=None,
    immediate_only=False,
    exclude_statuses=None
):
    """
    Advanced job counting with multiple filters

    Args:
        prefix: Job name prefix
        status: Filter by status (pending, in progress, done, etc.)
        job_type: Filter by job type (basic, pythonimage, etc.)
        immediate_only: Only count immediate jobs
        exclude_statuses: List of statuses to exclude
    """

    where_conditions = {"AND": []}

    # Add prefix filter
    if prefix:
        where_conditions["AND"].append({
            "jobName": {
                "startsWith": prefix,
                "mode": "insensitive"
            }
        })

    # Add status filter
    if status:
        where_conditions["AND"].append({
            "status": {"equals": status}
        })

    # Exclude certain statuses
    if exclude_statuses:
        where_conditions["AND"].append({
            "status": {"notIn": exclude_statuses}
        })

    # Add job type filter
    if job_type:
        where_conditions["AND"].append({
            "jobType": {"equals": job_type}
        })

    # Add immediate filter
    if immediate_only:
        where_conditions["AND"].append({
            "schedule": {"equals": "immediate"}
        })

    query = """
    query countJobs($whereClause: PipelineJobWhereInput!) {
        countJobs(whereOveride: $whereClause)
    }
    """

    variables = {
        "whereClause": where_conditions
    }

    response = requests.post(
        HYPERPLANE_GRAPHQL_URL,
        json={
            "operationName": "countJobs",
            "query": query,
            "variables": variables
        }
    )

    if response.status_code == 200:
        try:
            result = response.json()
            if "errors" in result:
                print("GraphQL Errors:")
                print(json.dumps(result["errors"], indent=2))
                return None

            count = result.get("data", {}).get("countJobs")
            return count
        except Exception as e:
            print(f"Error: {e}")
            return None
    else:
        print(f"Error: {response.status_code}")
        return None


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
            SELECT package_name, version, python_version
            FROM packages
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT %s;
        """, (limit,))

        packages = cursor.fetchall()
        cursor.close()
        conn.close()

        print(f"Found {len(packages)} pending package(s) to process")
        print()

        return packages

    except Exception as e:
        print(f"Error fetching packages from database: {str(e)}")
        import traceback
        traceback.print_exc()
        return []




def create_scanner_job_graphql(package):
    """
    Create a scanner job using Hyperplane GraphQL API
    This makes jobs appear in Hyperplane UI

    Args:
        package: Dict with keys: package_name, version, python_version
    """
    try:
        # Extract package info
        package_name = package['package_name']
        version = package.get('version') or 'latest'
        python_version = package.get('python_version') or '3.11'  # Default to 3.11

        # Construct full package spec: packagename==version
        package_spec = f"{package_name}=={version}" if version != 'latest' else package_name

        print(f"Creating job via GraphQL for package: {package_spec} (Python {python_version})")

        # Generate unique job name
        timestamp = int(datetime.utcnow().timestamp())
        safe_name = package_name.lower().replace('_', '-').replace('.', '-')
        safe_version = version.replace('.', '-')
        job_name = f"pythonPakcageScanner-{safe_name}-{safe_version}-py{python_version.replace('.', '')}-{timestamp}"

        # Build pod spec matching working configuration
        pod_spec = {
            "priorityClassName": "shakudo-job-default",
            "restartPolicy": "Never",
            "serviceAccountName": "gcr-pipelines",
            "nodeSelector": {
                "hyperplane.dev/nodeType": "hyperplane-system-pool"
            },
            "tolerations": [{
                "effect": "NoSchedule",
                "key": "purpose",
                "operator": "Equal",
                "value": "pipelines"
            }],
            "volumes": [
                {
                    "name": "gke-service-account-json",
                    "secret": {
                        "secretName": "service-account-key-pipelines-dccri9ba"
                    }
                },
                {
                    "name": "gitrepo",
                    "emptyDir": {}
                },
                {
                    "name": "github-key",
                    "secret": {
                        "secretName": "python-package-scanner-deploy-key",
                        "defaultMode": 400
                    }
                }
            ],
            "securityContext": {
                "fsGroup": 65533
            },
            "initContainers": [
                {
                    "name": "node-ip-monitor",
                    "image": "gcr.io/devsentient-infra/dev/add-pod-label-container:edbe221f844dc6d7e47ed6a7c8163c71192ef838",
                    "command": ["/bin/bash"],
                    "args": ["-c", "python3 /usr/local/bin/add_node_ip_label.py"],
                    "env": [
                        {
                            "name": "NODE_IP",
                            "valueFrom": {"fieldRef": {"fieldPath": "status.hostIP"}}
                        },
                        {
                            "name": "NODE_NAME",
                            "valueFrom": {"fieldRef": {"fieldPath": "spec.nodeName"}}
                        },
                        {
                            "name": "POD_NAME",
                            "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}
                        },
                        {
                            "name": "POD_NAMESPACE",
                            "valueFrom": {"fieldRef": {"fieldPath": "metadata.namespace"}}
                        },
                        {
                            "name": "HYPERPLANE__DEFAULT_NAMESPACE",
                            "value": "hyperplane-core"
                        }
                    ]
                },
                {
                    "name": "git-sync-init",
                    "image": SCANNER_IMAGE,
                    "command": ["/bin/sh"],
                    "args": [
                        "-c",
                        f"mkdir -p /root/.ssh && cp /etc/git-secret/* /root/.ssh/ && chmod 400 /root/.ssh/id_rsa && "
                        f"((GIT_SSH_COMMAND=\"ssh -o StrictHostKeyChecking=no\" git clone --depth 1 "
                        f"git@git-server-python-package-scanner.hyperplane-pipelines.svc.cluster.local:/tmp/git/monorepo /tmp/git/monorepo) || "
                        f"(GIT_SSH_COMMAND=\"ssh -o StrictHostKeyChecking=no\" git clone --depth 1 --branch main "
                        f"git@github.com:usama-shakudo/python-libary-scanner.git /tmp/git/monorepo)) && "
                        f"echo \"Running from commit: $(cd /tmp/git/monorepo && git rev-parse HEAD 2>/dev/null || echo 'could not print commit id')\""
                    ],
                    "volumeMounts": [
                        {"name": "gitrepo", "mountPath": "/tmp/git"},
                        {"name": "github-key", "mountPath": "/etc/git-secret", "readOnly": True}
                    ],
                    "resources": {
                        "limits": {"cpu": "200m", "memory": "512Mi"}
                    }
                }
            ],
            "containers": [
                {
                    "name": "d2v-pipeline",
                    "image": SCANNER_IMAGE,
                    "workingDir": "/tmp/git/monorepo/",
                    "command": ["/bin/sh"],
                    "args": [
                        "-c",
                        "env > /etc/environment && "
                        "echo $SERVICE_ACCOUNT_KEY_CONTENT > /etc/service_account_key_content && "
                        "chmod +x /tmp/git/monorepo/scan_package.py && "
                        "/tmp/git/monorepo/scan_package.py"
                    ],
                    "env": [
                        {"name": "PACKAGE_NAME", "value": package_spec},
                        {"name": "PYTHON_VERSION", "value": python_version},
                        {"name": "DATABASE_URL", "value": DATABASE_URL},
                        {"name": "PYPI_SERVER_URL", "value": os.getenv("PYPI_SERVER_URL", "http://pypiserver-pypiserver.hyperplane-pypiserver.svc.cluster.local:8080")},
                        {"name": "PYPI_USERNAME", "value": os.getenv("PYPI_USERNAME", "username")},
                        {"name": "PYPI_PASSWORD", "value": os.getenv("PYPI_PASSWORD", "password")},
                        {"name": "MY_POD_NAME", "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}},
                        {"name": "MY_POD_NAMESPACE", "valueFrom": {"fieldRef": {"fieldPath": "metadata.namespace"}}},
                        {"name": "MY_NODE_IP", "valueFrom": {"fieldRef": {"fieldPath": "status.podIP"}}},
                        {"name": "HYPERPLANE_JOB_CHECKED_COMMIT_ID", "value": ""},
                        {"name": "HYPERPLANE_JOB_CHECKED_BRANCH_NAME", "value": "main"},
                        {"name": "HYPERPLANE_JOB_DEBUGGABLE", "value": "false"},
                        {"name": "PIPELINES_USER", "value": "usama"},
                        {"name": "USER_EMAIL", "value": "usama@shakudo.io"},
                        {"name": "HYPERPLANE_JOB_PIPELINE_YAML_PATH", "value": "scan_package.py"}
                    ],
                    "volumeMounts": [
                        {"name": "gitrepo", "mountPath": "/tmp/git"},
                        {"name": "gke-service-account-json", "mountPath": "/etc/gke-service-account-json", "readOnly": True}
                    ],
                    "resources": {
                        "limits": {"cpu": "500m", "memory": "2Gi"},
                        "requests": {"cpu": "500m", "memory": "2Gi"}
                    }
                },
                {
                    "name": "sidecar-terminator",
                    "image": "gcr.io/devsentient-infra/dev/sidecar-terminator:0f74575067e596d757590ee7e5a7536eb5ab53e7",
                    "ports": [{"name": "http", "containerPort": 9092, "protocol": "TCP"}],
                    "env": [
                        {"name": "MY_POD_NAME", "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}}},
                        {"name": "MY_POD_NAMESPACE", "valueFrom": {"fieldRef": {"fieldPath": "metadata.namespace"}}}
                    ],
                    "resources": {"requests": {"cpu": "64m"}}
                }
            ]
        }

        # GraphQL mutation
        mutation = """
        mutation createPipelineJobWithAlerting($jobName: String!, $type: String!, $imageHash: String, $noHyperplaneCommands: Boolean, $debuggable: Boolean!, $notificationsEnabled: Boolean, $notificationTargetIds: [String!], $timeout: Int!, $activeTimeout: Int, $maxRetries: Int!, $schedule: String, $timezone: String, $yamlPath: String!, $workingDir: String!, $noGitInit: Boolean, $runParallel: Boolean, $hyperplaneVCServerId: HyperplaneVCServerWhereUniqueInput, $billingProjectId: BillingProjectWhereUniqueInput, $hyperplaneSecrets: [HyperplaneSecretWhereUniqueInput!], $branchName: String, $commitId: String, $parameters: ParameterCreateNestedManyWithoutPipelineJobInput, $hyperplaneUserId: String!, $hyperplaneUserEmail: String!, $group: String, $podSpec: String, $hyperplaneServiceAccountId: HyperplaneServiceAccountWhereUniqueInput, $cloudSqlProxyEnabled: Boolean, $hyperplaneCloudSqlProxyId: String, $pipelineType: String) {
          createPipelineJobWithAlerting(
            input: {jobName: $jobName, jobType: $type, imageHash: $imageHash, noHyperplaneCommands: $noHyperplaneCommands, debuggable: $debuggable, notificationsEnabled: $notificationsEnabled, runParallel: $runParallel, notificationTargetIds: $notificationTargetIds, timeout: $timeout, activeTimeout: $activeTimeout, maxRetries: $maxRetries, schedule: $schedule, pipelineYamlPath: $yamlPath, workingDir: $workingDir, noGitInit: $noGitInit, hyperplaneVCServer: {connect: $hyperplaneVCServerId}, billingProject: {connect: $billingProjectId}, hyperplaneSecrets: {connect: $hyperplaneSecrets}, branchName: $branchName, commitId: $commitId, parameters: $parameters, timezone: $timezone, hyperplaneUser: {connect: {id: $hyperplaneUserId}}, hyperplaneUserEmail: $hyperplaneUserEmail, group: $group, podSpec: $podSpec, hyperplaneServiceAccount: {connect: $hyperplaneServiceAccountId}, cloudSqlProxyEnabled: $cloudSqlProxyEnabled, hyperplaneCloudSqlProxyId: $hyperplaneCloudSqlProxyId, pipelineType: $pipelineType}
          ) {
            id
            jobName
            status
            statusReason
          }
        }
        """

        variables = {
            "jobName": job_name,
            "type": "python_base_image",
            "imageHash": "",
            "noHyperplaneCommands": False,  # Must be False for proper execution
            "debuggable": False,
            "notificationsEnabled": False,
            "notificationTargetIds": [],
            "timeout": 3600,  # 1 hour timeout
            "activeTimeout": 3600,
            "maxRetries": 2,
            "schedule": "immediate",  # Important: Mark as immediate job
            "yamlPath": "scan_package.py",  # Just for reference
            "workingDir": "/tmp/git/monorepo/",
            "noGitInit": True,  # Important: We don't need git
            "hyperplaneVCServerId": {
                "id": HYPERPLANE_VC_SERVER_ID
            },
            "branchName": "main",
            "commitId": "",
            "parameters": {
                "create": []
            },
            "hyperplaneUserId": HYPERPLANE_USER_ID,
            "hyperplaneUserEmail": HYPERPLANE_USER_EMAIL,
            "group": "",
            "podSpec": json.dumps(pod_spec),  # Pod spec as JSON string
            "hyperplaneSecrets": [],
            "cloudSqlProxyEnabled": False,
            "pipelineType": "BASH"
        }

        payload = {
            "operationName": "createPipelineJobWithAlerting",
            "query": mutation,
            "variables": variables
        }

        # Running without authentication (in-cluster access)
        headers = {
            "Content-Type": "application/json"
        }

        response = requests.post(HYPERPLANE_GRAPHQL_URL, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            if "errors" in result:
                print(f"  ✗ GraphQL errors: {result['errors']}")
                return False

            job_data = result.get("data", {}).get("createPipelineJobWithAlerting", {})
            print(f"  ✓ Job created: {job_data.get('id')}")
            print(f"     Status: {job_data.get('status')}")
            if job_data.get('statusReason'):
                print(f"     Status Reason: {job_data.get('statusReason')}")
            return True
        else:
            print(f"  ✗ HTTP {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False




def main():
    """Main execution function"""

    # 1. Check running jobs (with Istio retry logic)
    prefix = "scanner"
    status = "in progress"

    print(f"\n🔢 Advanced Count:")
    print(f"   Prefix: {prefix}")
    if status:
        print(f"   Status: {status}")

    running_jobs = count_jobs_advanced(
        prefix=prefix,
        status=status,
        job_type="",
        immediate_only=True
    )

    if running_jobs is not None:
        print(f"\n   Result: {running_jobs} jobs")



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
    for package in pending_packages:
        # Use GraphQL API (appears in Hyperplane UI)
        success = create_scanner_job_graphql(package)

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

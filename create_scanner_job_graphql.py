#!/usr/bin/env python3
"""
Create scanner jobs via Hyperplane GraphQL API with automatic token authentication
"""

import os
import json
import requests
from datetime import datetime

# Keycloak Authentication Configuration (DISABLED - Running without auth)
# REALM = os.getenv("HYPERPLANE_REALM", "Hyperplane")
# CLIENT_ID = os.getenv("HYPERPLANE_CLIENT_ID", "istio")
# HYPERPLANE_DOMAIN = os.getenv("HYPERPLANE_DOMAIN", "")  # Required: your-domain.com
# USERNAME = os.getenv("HYPERPLANE_USERNAME", "")  # Required
# PASSWORD = os.getenv("HYPERPLANE_PASSWORD", "")  # Required
# REFRESH_TOKEN = os.getenv("HYPERPLANE_REFRESH_TOKEN", None)

# Hyperplane GraphQL Configuration
HYPERPLANE_GRAPHQL_URL = os.getenv("HYPERPLANE_GRAPHQL_URL", "http://api-server.hyperplane-core.svc.cluster.local/graphql")
HYPERPLANE_USER_ID = os.getenv("HYPERPLANE_USER_ID", "0e71f618-bff9-49a7-a77e-81d201503fe1")
HYPERPLANE_USER_EMAIL = os.getenv("HYPERPLANE_USER_EMAIL", "shakudo-admin@shakudo.io")
HYPERPLANE_VC_SERVER_ID = os.getenv("HYPERPLANE_VC_SERVER_ID", "654cabbc-0b09-416b-8efa-b880a5a343571")

# Scanner Configuration
SCANNER_IMAGE = os.getenv("SCANNER_IMAGE", "gcr.io/devsentient-infra/custom/hnb/custom/pypiscanningjob:latest")
DATABASE_URL = "postgresql://postgres:Y2dtcJhdFW@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres"


# Authentication disabled - running without Keycloak token
# def get_shakudo_token():
#     """
#     Generate JWT token via Keycloak/OpenID Connect
#     If refresh token is provided, use it to obtain a new access token
#     """
#     if not HYPERPLANE_DOMAIN:
#         raise ValueError("HYPERPLANE_DOMAIN environment variable is required")
#
#     if not USERNAME and not REFRESH_TOKEN:
#         raise ValueError("Either HYPERPLANE_USERNAME/PASSWORD or HYPERPLANE_REFRESH_TOKEN is required")
#
#     token_endpoint = f"https://{HYPERPLANE_DOMAIN}/auth/realms/{REALM}/protocol/openid-connect/token"
#     headers = {"Content-Type": "application/x-www-form-urlencoded"}
#
#     if REFRESH_TOKEN:
#         data = {
#             "grant_type": "refresh_token",
#             "refresh_token": REFRESH_TOKEN,
#             "client_id": CLIENT_ID
#         }
#     else:
#         data = {
#             "grant_type": "password",
#             "username": USERNAME,
#             "password": PASSWORD,
#             "client_id": CLIENT_ID
#         }
#
#     try:
#         response = requests.post(token_endpoint, data=data, headers=headers, timeout=10)
#         response.raise_for_status()
#         res = response.json()
#         access_token = res['access_token']
#         new_refresh_token = res.get('refresh_token', REFRESH_TOKEN)
#         return access_token, new_refresh_token
#     except requests.exceptions.RequestException as err:
#         print(f"Failed to get token: {err}")
#         return None, None


def create_scanner_job_graphql(package_name):
    """Create a scanner job using Hyperplane GraphQL API"""

    # Generate unique job name
    timestamp = int(datetime.utcnow().timestamp())
    safe_name = package_name.split('==')[0].lower().replace('_', '-').replace('.', '-')
    job_name = f"scanner-{safe_name}-{timestamp}"

    # Build the pod spec - this is the actual container configuration
    pod_spec = {
        "priorityClassName": "shakudo-job-default",
        "restartPolicy": "Never",
        "serviceAccountName": "package-scanner-scan",
        "nodeSelector": {
           
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
            }
        ],
        "securityContext": {
            "fsGroup": 65533
        },
        "containers": [{
            "name": "scanner",
            "image": SCANNER_IMAGE,
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
                },
                {
                    "name": "MY_POD_NAME",
                    "valueFrom": {
                        "fieldRef": {
                            "fieldPath": "metadata.name"
                        }
                    }
                },
                {
                    "name": "MY_POD_NAMESPACE",
                    "valueFrom": {
                        "fieldRef": {
                            "fieldPath": "metadata.namespace"
                        }
                    }
                }
            ],
            "volumeMounts": [
                {
                    "name": "gke-service-account-json",
                    "mountPath": "/etc/gke-service-account-json",
                    "readOnly": True
                }
            ],
            "resources": {
                "limits": {
                    "cpu": "2000m",
                    "memory": "2Gi"
                },
                "requests": {
                    "cpu": "500m",
                    "memory": "512Mi"
                }
            }
        }]
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

    # Variables for the mutation
    variables = {
        "jobName": job_name,
        "type": "python_base_image",
        "imageHash": "",
        "noHyperplaneCommands": True,  # Important: We're not using Hyperplane commands
        "debuggable": False,
        "notificationsEnabled": False,
        "notificationTargetIds": [],
        "timeout": 3600,  # 1 hour timeout
        "activeTimeout": 3600,
        "maxRetries": 2,
        "yamlPath": "scan_package.py",  # Just for reference
        "workingDir": "/tmp/git/monorepo/",
        "noGitInit": True,  # Important: We don't need git
        "hyperplaneSecrets": [],
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
        "cloudSqlProxyEnabled": False,
        "pipelineType": "BASH"
    }

    # Running without authentication (in-cluster access)
    print(f"Creating scanner job via GraphQL: {job_name}")
    print(f"  Package: {package_name}")

    # Make the GraphQL request (no authentication required for in-cluster)
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "operationName": "createPipelineJobWithAlerting",
        "query": mutation,
        "variables": variables
    }

    try:

        response = requests.post(
            HYPERPLANE_GRAPHQL_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            if "errors" in result:
                print(f"  ✗ GraphQL errors: {result['errors']}")
                return False

            job_data = result.get("data", {}).get("createPipelineJobWithAlerting", {})
            print(f"  ✓ Job created: {job_data.get('id')}")
            print(f"     Status: {job_data.get('status')}")
            return True
        else:
            print(f"  ✗ HTTP error {response.status_code}: {response.text}")
            return False

    except Exception as e:
        print(f"  ✗ Error creating job: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Test
    import sys
    TEST_MODE = True  # Set to False to require command line argument
    TEST_PACKAGE = "requests==2.31.0"  # Change this to test different packages

    if TEST_MODE and len(sys.argv) == 1:
        log(f"🧪 TEST MODE: Using temporary package: {TEST_PACKAGE}")
        package_spec = TEST_PACKAGE
        create_scanner_job_graphql(TEST_PACKAGE)
    elif len(sys.argv) != 2:
        print("Usage: python scan_package.py <package_spec>")
        print("Example: python scan_package.py requests==2.31.0")
        sys.exit(1)
    else:
        package_spec = sys.argv[1]
   
#!/usr/bin/env python3
"""
Diagnostic script to check network connectivity and permissions
Run this in the scheduled job container to diagnose issues
"""

import os
import socket
import sys

print("=" * 60)
print("CONNECTIVITY DIAGNOSTIC")
print("=" * 60)
print()

# Check 1: Service Account Token
print("1. Checking Service Account Token...")
token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
if os.path.exists(token_path):
    print(f"   ✓ Token file exists at {token_path}")
    try:
        with open(token_path, 'r') as f:
            token = f.read().strip()
            print(f"   ✓ Token length: {len(token)} characters")
    except Exception as e:
        print(f"   ✗ Error reading token: {e}")
else:
    print(f"   ✗ Token file NOT found at {token_path}")
print()

# Check 2: CA Certificate
print("2. Checking CA Certificate...")
ca_path = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
if os.path.exists(ca_path):
    print(f"   ✓ CA cert exists at {ca_path}")
else:
    print(f"   ✗ CA cert NOT found at {ca_path}")
print()

# Check 3: Namespace
print("3. Checking Namespace...")
namespace_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
if os.path.exists(namespace_path):
    with open(namespace_path, 'r') as f:
        namespace = f.read().strip()
        print(f"   ✓ Running in namespace: {namespace}")
else:
    print(f"   ✗ Namespace file NOT found")
print()

# Check 4: DNS Resolution
print("4. Checking DNS Resolution...")
hosts_to_check = [
    "kubernetes.default.svc",
    "supabase-postgresql.hyperplane-supabase.svc.cluster.local"
]

for host in hosts_to_check:
    try:
        ip = socket.gethostbyname(host)
        print(f"   ✓ {host} → {ip}")
    except socket.gaierror as e:
        print(f"   ✗ {host} → DNS resolution failed: {e}")
print()

# Check 5: Network Connectivity
print("5. Checking Network Connectivity...")
connections_to_check = [
    ("kubernetes.default.svc", 443),
    ("supabase-postgresql.hyperplane-supabase.svc.cluster.local", 5432)
]

for host, port in connections_to_check:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            print(f"   ✓ {host}:{port} → Connected successfully")
        else:
            print(f"   ✗ {host}:{port} → Connection failed (error code: {result})")
    except Exception as e:
        print(f"   ✗ {host}:{port} → Error: {e}")
print()

# Check 6: Environment Variables
print("6. Checking Environment Variables...")
env_vars = [
    "DATABASE_URL",
    "KUBERNETES_SERVICE_HOST",
    "KUBERNETES_SERVICE_PORT"
]

for var in env_vars:
    value = os.getenv(var)
    if value:
        # Mask password in DATABASE_URL
        if var == "DATABASE_URL" and ":" in value:
            parts = value.split("@")
            if len(parts) > 1:
                value = f"{parts[0].split(':')[0]}:***@{parts[1]}"
        print(f"   ✓ {var} = {value}")
    else:
        print(f"   ✗ {var} not set")
print()

# Check 7: Test Kubernetes API
print("7. Testing Kubernetes API Access...")
try:
    import requests

    with open(token_path, 'r') as f:
        token = f.read().strip()

    headers = {"Authorization": f"Bearer {token}"}
    verify = ca_path if os.path.exists(ca_path) else False

    # Try to access the API
    response = requests.get(
        "https://kubernetes.default.svc/api/v1/namespaces",
        headers=headers,
        verify=verify,
        timeout=10
    )

    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ Successfully accessed Kubernetes API")
    elif response.status_code == 403:
        print(f"   ⚠ Connected but Forbidden (RBAC permissions issue)")
    else:
        print(f"   ✗ Unexpected response: {response.text[:200]}")

except Exception as e:
    print(f"   ✗ Error accessing Kubernetes API: {e}")
print()

# Check 8: Test Database Connection
print("8. Testing Database Connection...")
try:
    import psycopg2

    DATABASE_URL = "postgresql://postgres:CYo8ILCGUi@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres"

    conn = psycopg2.connect(DATABASE_URL)
    print(f"   ✓ Successfully connected to database")

    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"   ✓ PostgreSQL version: {version[:80]}...")

    cursor.close()
    conn.close()

except ImportError:
    print(f"   ⚠ psycopg2 not installed")
except Exception as e:
    print(f"   ✗ Database connection failed: {e}")
print()

print("=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)

#!/bin/bash
set -e

# Configuration
MAX_CONCURRENT_JOBS=10
JOB_NAME_PREFIX="package-scanner"
NAMESPACE="hyperplane-pipelines"
DATABASE_URL="postgresql://postgres:CYo8ILCGUi@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres"

echo "=================================================="
echo "Package Scanner Job Manager"
echo "=================================================="
echo ""

# 1. Check current running jobs
echo "Step 1: Checking running jobs..."
RUNNING_JOBS=$(kubectl get jobs -n "$NAMESPACE" -l app="$JOB_NAME_PREFIX" --field-selector status.successful=0 -o json | jq '.items | length')

if [ -z "$RUNNING_JOBS" ]; then
    RUNNING_JOBS=0
fi

echo "Current running jobs: $RUNNING_JOBS"
echo ""

# 2. Calculate available slots
AVAILABLE_SLOTS=$((MAX_CONCURRENT_JOBS - RUNNING_JOBS))

if [ "$AVAILABLE_SLOTS" -le 0 ]; then
    echo "No available slots. All $MAX_CONCURRENT_JOBS job slots are in use."
    exit 0
fi

echo "Available job slots: $AVAILABLE_SLOTS"
echo ""

# 3. Fetch pending packages from database
echo "Step 2: Fetching pending packages from database..."

PENDING_PACKAGES=$(psql "$DATABASE_URL" -t -c "
    SELECT package_name
    FROM packages
    WHERE status = 'pending'
    ORDER BY created_at ASC
    LIMIT $AVAILABLE_SLOTS;
")

if [ -z "$PENDING_PACKAGES" ]; then
    echo "No pending packages found in database."
    exit 0
fi

# Convert to array
PACKAGE_ARRAY=()
while IFS= read -r line; do
    # Trim whitespace
    trimmed=$(echo "$line" | xargs)
    if [ -n "$trimmed" ]; then
        PACKAGE_ARRAY+=("$trimmed")
    fi
done <<< "$PENDING_PACKAGES"

PACKAGE_COUNT=${#PACKAGE_ARRAY[@]}
echo "Found $PACKAGE_COUNT pending package(s) to process"
echo ""

# 4. Create jobs for pending packages
echo "Step 3: Creating jobs..."
echo ""

CREATED_COUNT=0
for package_name in "${PACKAGE_ARRAY[@]}"; do
    echo "Creating job for package: $package_name"

    # For now, just print message (placeholder for actual job creation)
    echo "  → Job created for: $package_name"

    # TODO: Uncomment below to create actual Kubernetes job
    # JOB_NAME="${JOB_NAME_PREFIX}-$(echo "$package_name" | tr '[:upper:]' '[:lower:]' | tr '_' '-')-$(date +%s)"
    # kubectl create job "$JOB_NAME" -n "$NAMESPACE" --image=scanner-image:latest -- scan "$package_name"

    CREATED_COUNT=$((CREATED_COUNT + 1))
done

echo ""
echo "=================================================="
echo "Summary:"
echo "  - Running jobs before: $RUNNING_JOBS"
echo "  - Jobs created: $CREATED_COUNT"
echo "  - Total running jobs now: $((RUNNING_JOBS + CREATED_COUNT))"
echo "=================================================="

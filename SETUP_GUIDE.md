# Service Account and Network Configuration Guide

This guide explains how to configure RBAC permissions and network policies for the scheduled package scanner job.

## Overview

The scheduled job needs:
1. **RBAC permissions** to read/list jobs via Kubernetes API
2. **Network access** to Supabase PostgreSQL across namespaces
3. **Service account** configured in the scheduled job

## Step 1: Apply RBAC Configuration

Apply the RBAC configuration to create the service account and permissions:

```bash
kubectl apply -f k8s-rbac-config.yaml
```

This creates:
- `package-scanner-sa` ServiceAccount in `hyperplane-pipelines` namespace
- `job-reader` Role with permissions to list jobs
- `job-creator` Role with permissions to create jobs (optional)
- RoleBindings to link the service account with the roles

**Verify:**
```bash
kubectl get serviceaccount package-scanner-sa -n hyperplane-pipelines
kubectl get role job-reader -n hyperplane-pipelines
kubectl get rolebinding package-scanner-job-reader -n hyperplane-pipelines
```

## Step 2: Configure Network Policies

### Option A: Apply Network Policies (Recommended for Production)

First, ensure namespaces have the correct labels:

```bash
# Label the namespaces
kubectl label namespace hyperplane-pipelines name=hyperplane-pipelines --overwrite
kubectl label namespace hyperplane-supabase name=hyperplane-supabase --overwrite
```

Then apply the network policies:

```bash
kubectl apply -f k8s-network-policy.yaml
```

**Verify:**
```bash
kubectl get networkpolicy -n hyperplane-pipelines
kubectl get networkpolicy -n hyperplane-supabase
```

### Option B: Temporarily Allow All Egress (For Testing)

If network policies are causing issues during testing:

```bash
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-all-egress
  namespace: hyperplane-pipelines
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - podSelector: {}
        - namespaceSelector: {}
EOF
```

## Step 3: Configure PostgreSQL to Accept Cross-Namespace Connections

Check if PostgreSQL is configured to accept connections from other namespaces:

```bash
# Check PostgreSQL configuration
kubectl exec -n hyperplane-supabase <postgresql-pod-name> -- psql -U postgres -c "SHOW listen_addresses;"
```

The `listen_addresses` should be `'*'` or include the cluster IP range.

### Check pg_hba.conf

```bash
kubectl exec -n hyperplane-supabase <postgresql-pod-name> -- cat /var/lib/postgresql/data/pg_hba.conf
```

Ensure there's a line like:
```
host    all    all    0.0.0.0/0    md5
```

## Step 4: Update Hyperplane Scheduled Job Configuration

Update your Hyperplane scheduled job to use the service account:

### In Hyperplane UI:

1. Go to your scheduled pipeline configuration
2. Find the **Advanced Settings** or **Pod Template** section
3. Add or update:
   - **Service Account**: `package-scanner-sa`
   - **Labels**: Add `app: package-scanner`

### If Using YAML Configuration:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: process-pending-packages
  namespace: hyperplane-pipelines
spec:
  schedule: "*/5 * * * *"  # Every 5 minutes
  jobTemplate:
    spec:
      template:
        metadata:
          labels:
            app: package-scanner  # Important for network policies
        spec:
          serviceAccountName: package-scanner-sa  # Use the service account
          containers:
            - name: scanner
              image: your-image:tag
              command: ["python3", "/tmp/git/monorepo/process_pending_packages.py"]
              env:
                - name: DATABASE_URL
                  value: "postgresql://postgres:CYo8ILCGUi@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres"
          restartPolicy: OnFailure
```

## Step 5: Test Connectivity

Run the diagnostic script to verify everything is configured correctly:

```bash
# Create a test job
kubectl create job test-connectivity \
  --image=your-image:tag \
  --serviceaccount=package-scanner-sa \
  -n hyperplane-pipelines \
  -- python3 /tmp/git/monorepo/diagnose_connectivity.py

# Check logs
kubectl logs -n hyperplane-pipelines job/test-connectivity
```

## Troubleshooting

### Issue 1: "Connection Refused" to Supabase

**Check DNS resolution:**
```bash
kubectl run -it --rm debug --image=busybox --restart=Never -n hyperplane-pipelines -- \
  nslookup supabase-postgresql.hyperplane-supabase.svc.cluster.local
```

**Check connectivity:**
```bash
kubectl run -it --rm debug --image=postgres:13 --restart=Never -n hyperplane-pipelines -- \
  psql "postgresql://postgres:CYo8ILCGUi@supabase-postgresql.hyperplane-supabase.svc.cluster.local:5432/postgres" -c "SELECT version();"
```

### Issue 2: Kubernetes API Access Denied

**Check service account token:**
```bash
kubectl describe sa package-scanner-sa -n hyperplane-pipelines
kubectl get secret -n hyperplane-pipelines | grep package-scanner-sa
```

**Test API access:**
```bash
kubectl run -it --rm debug --image=alpine/curl --restart=Never \
  --serviceaccount=package-scanner-sa -n hyperplane-pipelines -- sh -c '\
  TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token) && \
  curl -k -H "Authorization: Bearer $TOKEN" \
    https://kubernetes.default.svc/apis/batch/v1/namespaces/hyperplane-pipelines/jobs'
```

### Issue 3: Network Policy Blocking Traffic

**Temporarily disable network policies:**
```bash
kubectl delete networkpolicy allow-supabase-access -n hyperplane-pipelines
kubectl delete networkpolicy allow-pipelines-ingress -n hyperplane-supabase
```

**Check if the issue resolves, then adjust policies accordingly.**

## Verification Checklist

- [ ] ServiceAccount `package-scanner-sa` created in `hyperplane-pipelines`
- [ ] Role and RoleBinding applied
- [ ] Namespaces labeled correctly
- [ ] NetworkPolicies applied (if using)
- [ ] PostgreSQL accepts connections from cluster IPs
- [ ] Scheduled job configured with `serviceAccountName: package-scanner-sa`
- [ ] Scheduled job pods have label `app: package-scanner`
- [ ] DNS resolution works for `supabase-postgresql.hyperplane-supabase.svc.cluster.local`
- [ ] Can connect to PostgreSQL from test pod
- [ ] Can access Kubernetes API with service account token

## Next Steps

After configuration:

1. Trigger the scheduled job manually or wait for next run
2. Check logs: `kubectl logs -n hyperplane-pipelines <job-pod-name>`
3. Verify the script can:
   - List running jobs via Kubernetes API
   - Connect to Supabase database
   - Fetch pending packages
   - Create scanner jobs (placeholder)

## Additional Resources

- [Kubernetes RBAC Documentation](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)
- [Kubernetes Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [PostgreSQL Connection Configuration](https://www.postgresql.org/docs/current/runtime-config-connection.html)

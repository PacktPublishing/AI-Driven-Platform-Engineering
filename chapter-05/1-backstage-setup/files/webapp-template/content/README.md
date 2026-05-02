# ${{ values.name }}

${{ values.description }}

## Deployment

Deployed via ArgoCD GitOps.

- **Namespace:** `${{ values.namespace }}`
- **Replicas:** ${{ values.minReplicas }} - ${{ values.maxReplicas }}

## Access

```bash
kubectl port-forward -n ${{ values.namespace }} svc/${{ values.name }} 8080:80
```

Open http://localhost:8080

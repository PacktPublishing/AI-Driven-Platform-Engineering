# Lab 2: Inspect the Cluster with a Diagnostics Agent

Add a Cluster Diagnostics Agent that reads the live state of an application. By the end, it will explain application health using Deployments, Pods, events, and logs as evidence, with read-only access across namespaces. The agent connects to the upstream [`containers/kubernetes-mcp-server`](https://github.com/containers/kubernetes-mcp-server), configured with the `core` toolset and read-only mode.

## Inspect the tools and application boundary

```bash
cd "$BOOK_REPO/chapter-07/2-cluster-diagnostics"

sed -n '/image:/,/volumeMounts:/p' "$BOOK_REPO/chapter-07/2-cluster-diagnostics/files/components-repo/agent-platform/k8s/cluster-mcp-deployment.yaml"
```

This displays the MCP container configuration. Look for the upstream image and the `--read-only`, `--stateless`, `--toolsets core`, and `--disable-multi-cluster` flags.

```bash
cat "$BOOK_REPO/chapter-07/2-cluster-diagnostics/files/components-repo/agent-platform/k8s/cluster-mcp-rbac.yaml"
```

This shows the ServiceAccount's ClusterRole and ClusterRoleBinding. The same server identity can read diagnostic objects and Pod logs in any namespace, but it has no write, Secret, or exec permission.

```bash
sed -n '/system_prompt=/,/tools=cluster_tools()/p' "$BOOK_REPO/chapter-07/2-cluster-diagnostics/files/agent/app/agent.py"
```

This shows the diagnostics agent's instructions and its tool list. The agent uses the upstream resource and Pod tools directly; the namespace and resource names come from the diagnostic request. Chapter 8 adds application ownership and per-user checks.

The upstream tool names are `resources_get`, `resources_list`, `pods_list_in_namespace`, `pods_get`, `pods_log`, and `events_list`. The caller supplies the application namespace for namespaced queries. Logs may contain sensitive application output, so the MCP remains read-only and does not receive Secret access. Chapter 8 adds user-aware authorization and tenant checks.

## Build and ship through GitOps

Use a single platform when building and importing the images. Set `KIND_PLATFORM` to `linux/arm64` for Apple Silicon or `linux/amd64` for Intel/AMD systems. This avoids multi-platform manifest issues and works with the kind node architecture.

```bash
: "${KIND_PLATFORM:?Set KIND_PLATFORM as shown in Lab 1}"
docker pull --platform "$KIND_PLATFORM" quay.io/containers/kubernetes_mcp_server:v0.0.66
docker build --platform "$KIND_PLATFORM" -t agent-runtime:0.7.2 "$BOOK_REPO/chapter-07/2-cluster-diagnostics/files/agent/"
docker image save --platform "$KIND_PLATFORM" -o /tmp/kubernetes-mcp.tar \
  quay.io/containers/kubernetes_mcp_server:v0.0.66
kind load image-archive /tmp/kubernetes-mcp.tar --name agentic-platform
docker image save --platform "$KIND_PLATFORM" -o /tmp/agent-runtime.tar agent-runtime:0.7.2
kind load image-archive /tmp/agent-runtime.tar --name agentic-platform
rm /tmp/kubernetes-mcp.tar /tmp/agent-runtime.tar
```

Copy the Kubernetes manifests into the components repository for the reviewed GitOps change:

```bash
cp "$BOOK_REPO/chapter-07/2-cluster-diagnostics/files/components-repo/agent-platform/k8s/"*.yaml \
  "$COMPONENTS_REPO/agent-platform/k8s/"
```

Preserve your Lab 1 model-provider settings in the new runtime Deployment. Commit and open the PR from the terminal:

```bash
cd "$COMPONENTS_REPO"
git checkout -b chapter-07/lab-2
git add agent-platform/k8s/
git commit -m "chapter 7 lab 2: Kubernetes diagnostics agent"
git push -u origin HEAD
gh pr create --fill
# Review the PR checks and diff from the terminal, then merge it.
gh pr merge --merge --delete-branch
```

After the merge, refresh the ApplicationSet and wait for ArgoCD to sync the updated manifests:

```bash
kubectl -n argocd annotate applicationset backstage-app-discovery \
  argocd.argoproj.io/application-set-refresh=true --overwrite
kubectl -n argocd get application agent-platform -w
```

The Application may already show `Synced` and `Healthy` from Lab 1. Confirm that this lab's resources are present and that the runtime image changed before checking rollout status:

```bash
kubectl -n agent-platform get deployment agent-runtime cluster-mcp \
  -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[0].image'
kubectl -n agent-platform get pods \
  -o custom-columns='NAME:.metadata.name,IMAGE:.spec.containers[0].image,STATUS:.status.phase'
```

The expected images are `agent-runtime:0.7.2` and `quay.io/containers/kubernetes_mcp_server:v0.0.66`. 

Wait for the pods to be ready, set a timeout so a failed rollout returns control to the terminal:

```bash
kubectl -n agent-platform rollout status deployment/cluster-mcp --timeout=60s
kubectl -n agent-platform rollout status deployment/agent-runtime --timeout=60s
```

<details>
<summary>Troubleshooting a CrashLoopBackOff</summary>

If `agent-runtime` enters `CrashLoopBackOff` with `httpx.ConnectError`, check that the MCP Service has a ready endpoint and that the runtime can reach it:

```bash
kubectl -n agent-platform get endpoints cluster-mcp
kubectl -n agent-platform exec deploy/agent-runtime -- python -c \
  "import socket; socket.create_connection(('cluster-mcp', 8080), 3); print('cluster-mcp reachable')"
kubectl -n agent-platform logs deploy/cluster-mcp --tail=50
```

The runtime retries MCP startup while the server becomes ready, and the MCP Deployment has an HTTP readiness check. If the endpoint check succeeds, restart the runtime once so it retries against the ready server:

```bash
kubectl -n agent-platform rollout restart deployment/agent-runtime
```

</details>

## Ask for evidence

Keep the port-forward running in a separate terminal:

```bash
kubectl -n agent-platform port-forward svc/agent-runtime 18080:80
```

```bash
curl --fail-with-body http://localhost:18080/invoke \
  -H 'Content-Type: application/json' \
  -d '{"intent":"Inspect my-first-app. Explain its health with evidence and any uncertainty.","session_id":"chapter07-diagnosis"}'
kubectl -n my-first-app get pods
```

Compare the agent's observations with the cluster. A healthy application should produce a healthy report, not an invented fault. An image-pull failure should reference the actual image and event. Ask it to apply a fix: it has no mutation tool and should explain that limitation.

Continue to [Lab 3](../3-gitops-mcp/README.md).

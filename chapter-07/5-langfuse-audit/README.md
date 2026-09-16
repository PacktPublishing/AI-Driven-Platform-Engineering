# Lab 5: Langfuse Traces and Hash-Chained Audit Log

Add observability to the coordinator, diagnostics agent, and GitOps agent from Labs 3–4. The existing Backstage chat and upstream MCP servers stay in place; this lab adds Langfuse traces and a persistent audit log to follow requests across agents and tools. The hash chain helps detect edits but does not make the log immutable.


```mermaid
flowchart TD
    Chat["Existing Backstage chat"] --> Coordinator["Platform Coordinator"]
    Coordinator -->|Tool call| Diagnostics["Cluster Diagnostics Agent"]
    Coordinator -->|Tool call| GitOps["GitOps Change Agent"]
    Diagnostics --> KubernetesMCP["Upstream Kubernetes MCP"]
    GitOps --> GitHubMCP["Official GitHub MCP"]
    Coordinator -.-> Hooks["Tracing and audit hooks on each agent"]
    Diagnostics -.-> Hooks
    GitOps -.-> Hooks
    Hooks --> Langfuse["Langfuse: traces linked by session"]
    Hooks --> Audit["Persistent audit log: linked hashes"]
```

## Inspect the observability hooks

`platform_coordinator.py` attaches tracing and audit hooks to the coordinator and both specialists. Each specialist retains its own prompt and MCP connection:

```bash
cat "$BOOK_REPO/chapter-07/5-langfuse-audit/files/agent/app/platform_coordinator.py"
```

`hooks_langfuse.py` records agent invocations and tool spans, linked by session ID:

```bash
cat "$BOOK_REPO/chapter-07/5-langfuse-audit/files/agent/app/hooks_langfuse.py"
```

`audit.py` records the agent, session, tool, and before/after events on a persistent volume. Each record includes the previous record's hash:

```bash
cat "$BOOK_REPO/chapter-07/5-langfuse-audit/files/agent/app/audit.py"
```

## Build and load the runtime image

Use the same platform as your kind nodes (`linux/arm64` for Apple Silicon or `linux/amd64` for Intel/AMD):

```bash
: "${KIND_PLATFORM:?Set KIND_PLATFORM to linux/arm64 or linux/amd64}"
docker build --platform "$KIND_PLATFORM" -t agent-runtime:0.7.5 \
  "$BOOK_REPO/chapter-07/5-langfuse-audit/files/agent/"
docker image save --platform "$KIND_PLATFORM" \
  -o /tmp/agent-runtime.tar agent-runtime:0.7.5
kind load image-archive /tmp/agent-runtime.tar --name agentic-platform
rm /tmp/agent-runtime.tar
```

The Kubernetes and GitHub MCP servers from Labs 2–3 are reused.

## Prepare Langfuse credentials

Create the namespace and database Secret if absent. Rerunning these commands preserves the password used by the existing database:

```bash
kubectl create namespace langfuse --dry-run=client -o yaml | kubectl apply -f -
if ! kubectl -n langfuse get secret langfuse-db >/dev/null 2>&1; then
  PG_PASS=$(openssl rand -hex 16)
  kubectl -n langfuse create secret generic langfuse-db \
    --from-literal=POSTGRES_USER=langfuse \
    --from-literal=POSTGRES_PASSWORD="$PG_PASS" \
    --from-literal=DATABASE_URL="postgresql://langfuse:${PG_PASS}@langfuse-postgres:5432/langfuse"
  unset PG_PASS
fi
```

Create Langfuse's application secrets once as well:

```bash
if ! kubectl -n langfuse get secret langfuse-app >/dev/null 2>&1; then
  kubectl -n langfuse create secret generic langfuse-app \
    --from-literal=NEXTAUTH_SECRET="$(openssl rand -hex 32)" \
    --from-literal=SALT="$(openssl rand -hex 16)"
fi
```

## Deploy through GitOps

Copy the Langfuse manifests and fill in the GitHub owner exported in the prerequisites:

```bash
: "${GITHUB_USERNAME:?Set GITHUB_USERNAME as shown in the prerequisites}"
mkdir -p "$COMPONENTS_REPO/langfuse"
cp -r "$BOOK_REPO/chapter-07/5-langfuse-audit/files/components-repo/langfuse/"* \
  "$COMPONENTS_REPO/langfuse/"
sed -i.bak "s/YOUR_USERNAME/$GITHUB_USERNAME/g" \
  "$COMPONENTS_REPO/langfuse/argocd/application.yaml"
rm "$COMPONENTS_REPO/langfuse/argocd/application.yaml.bak"
```

Copy the updated runtime Deployment and audit volume. Retain your existing model settings, GitHub repository name/default branch, and Backstage URL when reviewing the diff. The Deployment keeps the GitHub and Backstage Secret references from Labs 3–4:

```bash
cp "$BOOK_REPO/chapter-07/5-langfuse-audit/files/components-repo/agent-platform/k8s/"*.yaml \
  "$COMPONENTS_REPO/agent-platform/k8s/"
sed -i.bak "s/YOUR_USERNAME/$GITHUB_USERNAME/g" \
  "$COMPONENTS_REPO/agent-platform/k8s/deployment.yaml"
rm "$COMPONENTS_REPO/agent-platform/k8s/deployment.yaml.bak"
cd "$COMPONENTS_REPO"
git diff -- agent-platform/k8s/deployment.yaml
```

Create and merge the deployment PR:

```bash
cd "$COMPONENTS_REPO"
git checkout -b chapter-07/lab-5
git add langfuse/ agent-platform/k8s/
git commit -m "chapter 7 lab 5: add agent tracing and audit log"
git push -u origin HEAD
gh pr create --fill
gh pr view
gh pr merge --merge --delete-branch
```

Request an ArgoCD refresh:

```bash
kubectl -n argocd annotate applicationset backstage-app-discovery \
  argocd.argoproj.io/application-set-refresh=true --overwrite
kubectl -n argocd annotate application agent-platform \
  argocd.argoproj.io/refresh=hard --overwrite
```

Check that the runtime's desired and running images both show `agent-runtime:0.7.5`, and wait for the new pod and Langfuse pods to be ready. An earlier `Synced` status alone does not prove the new image is running:

```bash
kubectl -n agent-platform get deployment agent-runtime \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl -n agent-platform get pods -l app=agent-runtime \
  -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image,READY:.status.containerStatuses[0].ready
kubectl -n langfuse get pods -w
```

Press Ctrl+C when Langfuse and Postgres are ready. Repeat the runtime checks if ArgoCD has not yet applied the update.

## Connect the agents to Langfuse

In a separate terminal, open the Langfuse port-forward:

```bash
kubectl -n langfuse port-forward svc/langfuse 13000:3000
```

Open [Langfuse](http://localhost:13000), create an account and project, then create API keys under **Project settings → API keys**. Reuse your existing project when repeating the lab.

Create the runtime Secret with those keys:

```bash
kubectl -n agent-platform create secret generic agent-langfuse-keys \
  --from-literal=LANGFUSE_PUBLIC_KEY="pk-lf-..." \
  --from-literal=LANGFUSE_SECRET_KEY="sk-lf-..." \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n agent-platform rollout restart deployment/agent-runtime
kubectl -n agent-platform rollout status deployment/agent-runtime --timeout=90s
```

The restart loads the new environment variables. Stop the previous runtime port-forward and restart it in a separate terminal:

```bash
kubectl -n agent-platform port-forward svc/agent-runtime 18080:80
```

## Follow a request across agents

In the existing Backstage Chat Assistant, start a new conversation and ask: **“Inspect my-first-app's live state, then read its deployment manifest from Git and explain whether they agree. Do not change anything.”** No Backstage configuration change is needed.

For a terminal request with an explicit session ID, use:

```bash
curl --fail-with-body http://localhost:18080/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "intent": "Inspect my-first-app live state, then read its deployment manifest from Git and explain whether they agree. Do not change anything.",
    "session_id": "lab5-observability"
  }'
```

In Langfuse, filter by the conversation's session ID (`lab5-observability` for the terminal request). Look for `coordinator.invoke`, `diagnostics.invoke`, and `gitops.invoke`, with tool spans beneath each trace. The GitOps agent reads through `get_file_contents`; Kubernetes reads use the upstream MCP tools. If a specialist was not called, ask explicitly for its part in the same conversation. A healthy application needs no repair PR.

Inspect the audit log:

```bash
kubectl -n agent-platform exec deploy/agent-runtime -- cat /state/audit/AUDIT.log
```

Tool calls produce before/after records containing the agent and session IDs, `hash`, and `prev_hash`. Verify the chain:

```bash
kubectl -n agent-platform exec -i deploy/agent-runtime -- python3 - <<'PY'
import hashlib
import json

previous = '0' * 64
count = 0
with open('/state/audit/AUDIT.log') as stream:
    for count, line in enumerate(stream, 1):
        record = json.loads(line)
        digest = record.pop('hash')
        body = json.dumps(record, sort_keys=True, separators=(',', ':'))
        if record.get('prev_hash') != previous or hashlib.sha256(body.encode()).hexdigest() != digest:
            raise SystemExit(f'Chain verification failed at record {count}')
        previous = digest
if not count:
    raise SystemExit('Audit log is empty: invoke a tool first')
print(f'Chain OK: {count} records')
PY
```

This checks internal consistency. Someone with write access could rewrite the entire chain or remove its tail; Chapter 8 discusses trusted evidence and these limits.

<details>
<summary>Troubleshooting</summary>

**Traces are missing:** inspect the runtime logs:

```bash
kubectl -n agent-platform logs deployment/agent-runtime --tail=100
```

Look for `telemetry: langfuse client active`. If credentials are missing, create `agent-langfuse-keys` and restart the runtime. This lab pins the Langfuse SDK to `2.60.10` for its v2 trace/span API; it does not use the OTLP endpoint.

**Runtime waits for MCP servers:** it retains Lab 3's 15-attempt connection retries and five-minute startup probe. If attempts are exhausted, see the MCP startup troubleshooting at the end of [Lab 3](../3-gitops-mcp/README.md).

**Catalog search returns 401:** keep the matching Backstage service token configured in Backstage and in `agent-backstage-read`, as described in Lab 4.

**GitHub requests fail:** check that the runtime Deployment retains the `GITHUB_PERSONAL_ACCESS_TOKEN` Secret reference and the repository owner, name, and default branch from Lab 3.

**Audit log is missing:** make a request that calls a tool. The file is created on the first recorded tool call.

**Langfuse is not ready:** inspect the pod events and logs. The database must be ready first; rerunning setup must not replace its password.

</details>

Continue to [Chapter 8: Security](../../chapter-08/README.md).

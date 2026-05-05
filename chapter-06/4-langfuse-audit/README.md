# Lab 4: Langfuse Traces + Hash-Chained Audit Log

The agent works. Now we want to see what it's doing — every reasoning step, every tool call, every token, with a per-session view that survives across restarts. The chapter argues for two layers:

- **Langfuse** — LLM-aware tracing. Per-trace prompts, responses, tool calls, latency, token counts, costs. Read it like a debugger.
- **Hash-chained audit log** — append-only, tamper-evident record of every tool call. Read it like a black-box flight recorder.

Both run inside the cluster. Langfuse goes in its own `langfuse` namespace; the audit log lives on a PVC mounted into the agent.

## Prerequisites

- Lab 2 completed (agent + gitops-mcp running in `agent-platform`).
- Lab 3 completed (chat plugin in Backstage proxies to the agent).
- ~2 GB free for the Langfuse + Postgres pods.

## Architecture

```
agent-platform ns                              langfuse ns
+----------------------------+                +-----------------------+
| agent-runtime v0.3.x       |                | langfuse (v2.x)       |
|   ├─ AlwaysPRHook (Lab 2)  |                |  Next.js UI + API     |
|   ├─ AuditHook (Lab 4) ────┼──> /state/     |                       |
|   │                         |     audit/    |  langfuse Python SDK  |
|   │                         |     AUDIT.log |  -> /api/public/      |
|   └─ LangfuseStrandsHook ───┼──────────────>|     ingestion          |
|                            |                +-----------------------+
| gitops-mcp (Lab 2)         |                | langfuse-postgres     |
+----------------------------+                +-----------------------+
```

The agent's `LangfuseStrandsHook` subscribes to four Strands hook events:

| Event | What we record in Langfuse |
|---|---|
| `BeforeInvocationEvent` | Start a trace named `<agent_id>.invoke`, tagged with `session_id`, `user_id`. |
| `BeforeToolCallEvent` | Open a span named `tool:<tool_name>` with the tool args as input. |
| `AfterToolCallEvent` | End the span with `ok: true/false`. |
| `AfterInvocationEvent` | Finalize the trace and `flush()`. |

`session_id` and `user_id` flow from the `/invoke` request body via Python `ContextVar`s set in `main.py` so the hook (which doesn't see the FastAPI request directly) can read them when starting the trace.

The `AuditHook` writes one JSON line per `BeforeToolCallEvent` and one per `AfterToolCallEvent` to `/state/audit/AUDIT.log`. Each record carries `prev_hash` (SHA-256 of the previous record's body) and its own `hash`. Tampering with any record invalidates the chain from that record onward. The chapter calls this *immutability*; here it's a 60-line Python module.

## Step 1: Build the new images

```bash
cd files/agent
docker build -t agent-runtime:0.3.2 .
kind load docker-image agent-runtime:0.3.2 --name agentic-platform
```

Compared to Lab 2 the agent gains four files: `audit.py` (hash-chained log + AuditHook), `telemetry.py` (Langfuse client init), `hooks_langfuse.py` (Strands → Langfuse bridge), `request_context.py` (ContextVar carry for session/user). The Dockerfile is unchanged.

## Step 2: Pre-create the Langfuse Secrets

Three Secrets are created out-of-band (none in git):

```bash
# Database password + connection string
PG_PASS=$(openssl rand -hex 16)
kubectl create namespace langfuse --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic langfuse-db -n langfuse \
  --from-literal=POSTGRES_USER=langfuse \
  --from-literal=POSTGRES_PASSWORD="$PG_PASS" \
  --from-literal=DATABASE_URL="postgresql://langfuse:${PG_PASS}@langfuse-postgres:5432/langfuse" \
  --dry-run=client -o yaml | kubectl apply -f -

# NextAuth secrets for the Langfuse UI
kubectl create secret generic langfuse-app -n langfuse \
  --from-literal=NEXTAUTH_SECRET="$(openssl rand -hex 32)" \
  --from-literal=SALT="$(openssl rand -hex 16)" \
  --dry-run=client -o yaml | kubectl apply -f -

unset PG_PASS
```

## Step 3: Ship Langfuse + the agent update through GitOps

Copy `files/components-repo/langfuse/` to your `backstage-components` repo and the updated `files/components-repo/agent-platform/k8s/` files (the agent's `deployment.yaml` + the new `pvc-audit.yaml`). Open one PR with both folders, merge.

Within ~3 minutes ArgoCD's ApplicationSet creates a new `langfuse` Application (the namespace + Postgres + Langfuse v2 image, two pods total) and refreshes the agent runtime to v0.3.x.

```bash
kubectl -n langfuse get pods -w
# langfuse-postgres-...   1/1 Running
# langfuse-...            1/1 Running   (Langfuse may restart 1-2 times waiting for Postgres)
```

## Step 4: Bootstrap Langfuse and create API keys

Langfuse v2 doesn't auto-provision keys. Open the UI once to set up the org, project, and keys:

```bash
kubectl -n langfuse port-forward svc/langfuse 13000:3000 &
```

In your browser at http://localhost:13000:

1. Sign up — the first user becomes the org owner.
2. Create a new project (e.g., `agent-platform`).
3. Project settings → API keys → Create new API keys.
4. Copy the **public key** (`pk-lf-...`) and **secret key** (`sk-lf-...`).

Give them to the agent through a Secret in `agent-platform`:

```bash
kubectl create secret generic agent-langfuse-keys \
  -n agent-platform \
  --from-literal=LANGFUSE_PUBLIC_KEY="pk-lf-..." \
  --from-literal=LANGFUSE_SECRET_KEY="sk-lf-..." \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n agent-platform rollout restart deploy/agent-runtime
```

## Step 5: Verify

```bash
kubectl -n agent-platform port-forward svc/agent-runtime 18080:80 &
curl -sS -X POST http://localhost:18080/invoke \
  -H 'Content-Type: application/json' \
  -d '{
    "intent": "Use read_file on my-first-app/k8s/deployment.yaml and tell me the image tag.",
    "session_id": "lab4-smoke",
    "user_id": "user:default/guest"
  }'
```

In the Langfuse UI, refresh the **Traces** page. You should see:

- A trace named `platform-ops.invoke` with `session: lab4-smoke` and `user: user:default/guest`.
- Inside it, a span named `tool:read_file` with the duration of the gitops-mcp call.

Then check the audit log:

```bash
kubectl -n agent-platform exec deploy/agent-runtime -- cat /state/audit/AUDIT.log
```

Two JSON lines for the read_file call (one `before_tool`, one `after_tool`), each with a `hash` and `prev_hash`. Verify the chain:

```bash
kubectl -n agent-platform exec deploy/agent-runtime -- python3 -c "
import json, hashlib
prev = '0' * 64
ok = True
with open('/state/audit/AUDIT.log') as f:
  for line in f:
    rec = json.loads(line)
    digest = rec.pop('hash')
    body = json.dumps(rec, sort_keys=True, separators=(',',':'))
    if hashlib.sha256(body.encode()).hexdigest() != digest:
      print('BAD CHAIN'); ok = False
    if rec.get('prev_hash') != prev:
      print('BAD prev_hash'); ok = False
    prev = digest
print('chain OK' if ok else 'chain BROKEN')
"
```

Tamper-evidence test: edit any record's `tool` field with `kubectl exec ... vi`, re-run the verifier. Output flips to `BAD CHAIN`.

## What Chapter 6 sections this exercises

| Section | What you can now see |
|---|---|
| *Observability and Audit* | Langfuse trace per session, span per tool call, with input args + duration. Add prompt/response capture in production. |
| Immutability sub-discussion | Hash-chained file. Tamper detection in 60 lines of Python. |
| *Bounded blast radius* | The audit log records every PR open the agent attempted *plus* whatever the AlwaysPRHook rejected — the rejection trail is part of the audit, not just the success trail. |
| *Going to Production: What Changes* | The chapter table maps "Local Langfuse + append-only audit file" to "Langfuse Cloud + S3 with Object Lock". This lab is the local half of that row. |

## Why we chose Langfuse v2 + the Python SDK (not OTLP)

Langfuse v3 supports OpenTelemetry's OTLP HTTP endpoint natively, and Strands ships first-class OTel instrumentation — that's the path the chapter narrates. We picked v2 here because it ships in **two pods** (Langfuse + Postgres) instead of v3's six (Postgres + ClickHouse + Redis + MinIO + langfuse-web + langfuse-worker). For a kind-cluster reference build, two pods is enough to demonstrate the architecture; the chapter's *Going to production* table substitutes Langfuse Cloud or self-hosted v3 at scale anyway.

The trade-off: Langfuse v2 hasn't shipped the OTLP collector endpoint yet (`/api/public/otel/v1/traces` returns 404), so we use the official `langfuse` Python SDK directly — same trace structure, same UI, traces export over HTTP to `/api/public/ingestion`. Switching to v3 + OTLP later is mechanical: drop the SDK, add `OTEL_EXPORTER_OTLP_ENDPOINT` + `OTEL_EXPORTER_OTLP_HEADERS` env vars, delete the `LangfuseStrandsHook`. Strands does the rest.

## Troubleshooting

**Traces don't appear in the UI** — make sure both `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are in the `agent-langfuse-keys` Secret and that the pod was restarted after the Secret was applied (`kubectl rollout restart`). Then check `kubectl logs deploy/agent-runtime | grep langfuse`. You want to see `telemetry: langfuse client active`. If you see `langfuse disabled (env vars not set)` the Secret isn't being injected.

**`Failed to export span batch code: 404, reason: Not Found`** — you're running an OTLP-only setup against Langfuse v2. Either upgrade to v3 or use the SDK approach in this lab (which is what `agent-runtime:0.3.2` does).

**Langfuse pod restarts a few times at startup** — this is normal. It retries while Postgres comes up. Two restarts and steady state is healthy.

**Audit log is missing** — the agent only creates `/state/audit/AUDIT.log` the first time a tool fires. Make a request that uses a tool (`read_file` is the simplest).

## What's next

Lab 5 is the end-to-end demo walkthrough: break my-first-app, ask the Platform Agent in Backstage to fix it, watch the trace in Langfuse, verify the audit chain. With Labs 0–4 in place, every step has a concrete artifact to point at.

# Lab 3: An MCP Server Over the Live Cluster

This is §4.10 made real. The chapter wraps a "list deployments" API as an MCP tool; here that tool queries your **live** kind cluster. Where RAG (Lab 2) answers *"how was this solved before?"*, MCP answers *"what is true right now?"* — and you'll watch the difference directly.

## What you build

A FastMCP server ([`app/server.py`](./files/mcp/app/server.py)) exposing one tool, `list_deployments`, that returns the live health of deployments in the cluster — including the pod-level reason (`CrashLoopBackOff`, `ImagePullBackOff`, …) when something is wrong. It runs over **stdio**, the way MCP hosts (Claude Desktop, Cursor) launch servers — and the way the chapter's example runs.

## Step 1: Create something unhealthy

So the server has something interesting to report, deploy a deliberately broken app. It crashes on startup — the exact CrashLoopBackOff the Lab 2 runbook explains:

```bash
kubectl apply -f files/broken-app.yaml
kubectl get pods -n broken-demo -w
# Wait until STATUS shows CrashLoopBackOff (~30-60s), then Ctrl-C.
```

## Step 2: Set up the environment

```bash
cd files/mcp
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

The server reads your **kubeconfig** — the same context `kubectl` uses (`kind-agentic-platform`). No in-cluster deployment, no credentials beyond what `kubectl` already has.

## Step 3: Call the tool (no AI host required)

A tiny demo client launches the server over stdio and calls the tool, so you can see it work without Claude Desktop:

```bash
python client_demo.py --unhealthy
```

```json
Tools exposed by the server:
  - list_deployments: List Kubernetes deployments and their live health.

Calling list_deployments({'only_unhealthy': True}) ...

{
  "namespace": "broken-demo",
  "name": "payment-processor",
  "desired": 1,
  "ready": 0,
  "available": 0,
  "healthy": false,
  "owner": "payments-team",
  "pod_reasons": ["CrashLoopBackOff"]
}
```

Drop `--unhealthy` to list every deployment (you'll see ArgoCD, pgvector, etc., all healthy). Fix or delete the broken app and call again — the answer changes immediately. **That's the MCP property: never stale.** A RAG index would still be reporting the old state until you re-embedded.

## Step 4 (optional): Wire it into Claude Desktop / Cursor

The demo client just stands in for a real MCP host. To use it from Claude Desktop, add to its MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "platform-cluster": {
      "command": "/absolute/path/to/files/mcp/.venv/bin/python",
      "args": ["-m", "app.server"],
      "cwd": "/absolute/path/to/files/mcp"
    }
  }
}
```

Then ask Claude *"which deployments are unhealthy right now?"* and it will call the tool and answer from live data. Cursor uses the same shape in its MCP settings.

## RAG vs MCP, side by side

You now have both halves of the chapter running. Ask each the question it's built for:

| Question | Tool | Where the answer comes from |
|---|---|---|
| "How do I fix a CrashLoopBackOff?" | **RAG** (Lab 2) | `runbooks/crashloopbackoff.md` — durable knowledge |
| "Which deployments are unhealthy right now?" | **MCP** (Lab 3) | the live cluster — current truth |

And notice they compose: MCP tells you `payment-processor` is in CrashLoopBackOff *right now*; RAG tells you what CrashLoopBackOff *means and how to fix it*. That's the chapter's closing point — **RAG for accumulated wisdom, MCP for live system truth** — and a production agent (Chapter 7) uses both.

## Cleanup

```bash
kubectl delete -f files/broken-app.yaml
```

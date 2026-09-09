# Lab 4: Adding Kubernetes MCP Actions

This lab covers creating custom actions that allow the AI assistant to query Kubernetes resources.

## Prerequisites

- Completed Lab 1, Lab 2, and Lab 3

## Overview

We'll register four Kubernetes actions with the AI assistant:
- `kubectl_get_pods` - List pods in a namespace
- `kubectl_get_deployments` - List deployments in a namespace
- `kubectl_get_services` - List services in a namespace
- `kubectl_describe_pod` - Get detailed pod information

---

## Step 1: Install Dependencies

> **Note:** `@backstage/plugin-mcp-actions-backend` was already installed and registered in Lab 2 (the GenAI plugin needs it for service ref resolution). Here we only add `zod`, which the kubectl actions module uses to declare its input schema.

```bash
yarn workspace backend add zod
```

---

## Step 2: Add the Kubectl Actions Module

Create the modules directory and copy the file:

```bash
mkdir -p packages/backend/src/modules
cp ../ai-driven-platform-engineering/chapter-05/4-add-kubernetes-actions/files/kubectl-mcp-actions.ts packages/backend/src/modules/
```

Your backend should now have:

```
packages/backend/src/
├── index.ts
└── modules/
    └── kubectl-mcp-actions.ts
```

---

## Step 3: Register the Module

Edit `packages/backend/src/index.ts` and add (after the lines from Lab 2):

```typescript
// Add kubectl actions module (chapter-05 lab 4)
backend.add(import('./modules/kubectl-mcp-actions'));
```

**Your complete backend index.ts should look like:**
```typescript
import { createBackend } from '@backstage/backend-defaults';

const backend = createBackend();

// ... existing plugins ...

// MCP actions registry (added in Lab 2; required by aws-genai)
backend.add(import('@backstage/plugin-mcp-actions-backend'));

// GenAI plugin (added in Lab 2)
backend.add(import('@aws/genai-plugin-for-backstage-backend'));
backend.add(import('@aws/genai-plugin-langgraph-agent-for-backstage'));

// Kubectl actions module (chapter-05 lab 4)
backend.add(import('./modules/kubectl-mcp-actions'));

backend.start();
```

---

## Step 4: Update Plugin Sources

Add `mcp-actions` to the `backend.actions.pluginSources` in `app-config.yaml`:

```yaml
backend:
  actions:
    pluginSources:
      - 'catalog'      # Enables catalog actions
      - 'aws-genai'    # Enables genai core actions
      - 'mcp-actions'  # Enables MCP actions (kubectl)
```

---

## Step 5: Add Actions to the Agent

Update `app-config.yaml` to include the Kubernetes actions:

```yaml
genai:
  registerCoreActions: true
  agents:
    general:
      description: General chat assistant
      prompt: >
        You are an expert in platform engineering and answer questions 
        in a succinct and easy to understand manner.
        
        Answers should always be well-structured and use well-formed Markdown.
        
        The current user is {username} and you can provide that information if asked.
      langgraph:
        messagesMaxTokens: 150000
        bedrock:
          modelId: 'global.anthropic.claude-sonnet-4-5-20250929-v1:0'
          region: us-west-2
      actions:
        # Catalog actions (from Lab 3)
        - get-catalog-entity
        - search-catalog
        - search-techdocs
        # Kubernetes actions
        - kubectl_get_pods
        - kubectl_get_deployments
        - kubectl_get_services
        - kubectl_describe_pod
```

---

## Step 6: Configure Kubernetes Access

Ensure kubectl is configured:

```bash
# Verify kubectl works
kubectl get ns
```

---

## Step 7: Test the Kubernetes Integration

```bash
NODE_OPTIONS=--no-node-snapshot yarn start
```

Open the AI Assistant (`http://localhost:3000/assistant/general`) and try:

- "What pods are running in the my-first-app namespace?"
- "Show me all deployments in my-first-app"
- "Are there any pods in CrashLoopBackOff state?"

---

## Step 8 (optional): Call the same actions from an MCP client

Everything so far has gone through the chat assistant, which reaches these actions in process. The
same registrations are also published as MCP tools over HTTP, and this step calls them from outside
Backstage. Nothing in the earlier steps depends on this, so treat it as optional.

### Grant an external client a token

External callers need credentials. Add a static token to `app-config.local.yaml`:

```yaml
backend:
  auth:
    externalAccess:
      - type: static
        options:
          token: ${MCP_CLIENT_TOKEN}
          subject: mcp-client
```

Generate one and restart the backend:

```bash
export MCP_CLIENT_TOKEN=$(node -e "console.log(require('crypto').randomBytes(24).toString('base64'))")
yarn workspace backend start
```

### Talk to the endpoint

The plugin serves MCP at `/api/mcp-actions/v1` using the streamable HTTP transport. Open the
session:

```bash
curl -s -X POST http://localhost:7007/api/mcp-actions/v1 \
  -H "Authorization: Bearer $MCP_CLIENT_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2025-06-18","capabilities":{},
        "clientInfo":{"name":"my-client","version":"1.0"}}}'
```

The server identifies itself, and the version it reports is the plugin version you pinned:

```
{"result":{"protocolVersion":"2025-06-18","capabilities":{"tools":{}},
 "serverInfo":{"name":"backstage","version":"0.1.9"}},"jsonrpc":"2.0","id":1}
```

List what it publishes with `"method":"tools/list"`, then call one:

```bash
curl -s -X POST http://localhost:7007/api/mcp-actions/v1 \
  -H "Authorization: Bearer $MCP_CLIENT_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{
        "name":"kubectl_get_pods","arguments":{"namespace":"argocd"}}}'
```

The reply carries the kubectl output under a `result` key, which is the output schema the action
declared in Step 2. That is why the action returns `{ output: { result } }` rather than a bare
string: the registry validates the return value against that schema.

Responses arrive as server-sent events, so each JSON payload is prefixed with `data: `. Strip that
prefix before parsing.

### Point a real client at it

Raw JSON-RPC proves the endpoint works, but it is not how anyone would use it day to day. Any
MCP-native client can consume this server, and the wiring is the same shape in all of them: a URL,
a transport, and an auth header. We will use Claude Code below purely because it is quick to
demonstrate. Nothing in this lab depends on that choice, so substitute whichever client you already
run.

Most clients read a JSON config file. In Claude Code's case that is `.mcp.json`, in the root of
whatever project you want to use it from:

```json
{
  "mcpServers": {
    "backstage": {
      "type": "http",
      "url": "http://localhost:7007/api/mcp-actions/v1",
      "headers": {
        "Authorization": "Bearer ${MCP_CLIENT_TOKEN}"
      }
    }
  }
}
```

The `${MCP_CLIENT_TOKEN}` reference is expanded from your environment when the client starts, so the
token never lands in the file and never reaches version control. Export it in the shell you launch
from, using the same variable you set earlier in this step.

A project-scoped server is approved once on first use: start the client in that directory and accept
the prompt. If you would rather register it just for yourself and skip the approval, Claude Code
also takes it from the command line:

```bash
claude mcp add --transport http backstage http://localhost:7007/api/mcp-actions/v1 \
  --header "Authorization: Bearer $MCP_CLIENT_TOKEN"
```

Either way, listing the configured servers should show it connected:

```
backstage: http://localhost:7007/api/mcp-actions/v1 (HTTP) - Connected
```

From there the actions are ordinary tools. Ask the client something that needs the cluster, such as
which pods are running in the argocd namespace, and it will call `kubectl_get_pods` and answer from
live state. The registration you wrote in Step 2 is now serving a client that has never heard of
Backstage, which is the whole point of the second door.

### What this shows, and one warning

The assistant and the MCP client end up at the same registered actions by different routes. The
assistant is bound to a named list in `app-config.yaml`; the MCP endpoint publishes what the
registry holds.

Those two surfaces are not the same size, and this is the part worth pausing on. Our agent is bound
to seven read-only actions. Running `tools/list` against the endpoint on this setup returns
thirteen tools, including `register-entity` and `unregister-entity`, which mutate the catalog.
Opening this endpoint therefore exposes more than the assistant can reach, so treat the token as a
credential with real scope: keep it out of version control, give it to one client, and review what
`tools/list` returns before you hand it to anyone.

---

## Troubleshooting

### "kubectl not found"
- Ensure kubectl is installed and in PATH

### "Unable to connect to the server"
- Verify KUBECONFIG is set correctly
- Check network connectivity to the cluster
- For EKS: ensure AWS credentials are available

### Actions not appearing
- Verify the module is registered in index.ts
- Check that action names in app-config.yaml match exactly
- Ensure `@backstage/plugin-mcp-actions-backend` is installed

---

## Summary

Your AI assistant can now:
- ✅ Answer general questions
- ✅ Search your software catalog
- ✅ Retrieve entity details
- ✅ Search documentation
- ✅ Query Kubernetes pods, deployments, and services
- ✅ Describe specific pods

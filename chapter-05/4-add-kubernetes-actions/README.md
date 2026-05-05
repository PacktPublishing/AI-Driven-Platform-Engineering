# Lab 4: Adding Kubernetes MCP Actions

This lab covers creating custom actions that allow the AI assistant to query Kubernetes resources.

## Prerequisites

- Completed Lab 3 (Catalog actions working)
- kubectl configured to access your Kubernetes cluster

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
          modelId: 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'
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

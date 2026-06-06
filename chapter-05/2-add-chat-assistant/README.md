# Lab 2: Adding the AI Chat Assistant

This lab covers adding the AWS GenAI plugin to enable an AI-powered chat interface in Backstage.

## Prerequisites

- Completed Lab 1 (Backstage with GitOps), including the `package.json` `resolutions` block from [`../1-backstage-setup/files/package-resolutions.json`](../1-backstage-setup/files/package-resolutions.json) — the chat plugin's transitive dependencies (especially `@langchain/ollama` and `@backstage/plugin-mcp-actions-backend`) are pinned there
- AWS account with Bedrock access enabled and AWS credentials configured, OR
- OpenAI API key (see the [plugin documentation](https://github.com/awslabs/genai-for-backstage) for OpenAI configuration)

## Overview

We'll add a chat assistant that can answer general questions. At this stage, it won't have access to Backstage data yet - that comes in the next lab.

The GenAI plugin's `agent-langgraph` module depends on a service ref (`alpha.core.actionsRegistry`) that is provided by `@backstage/plugin-mcp-actions-backend`. We install both plugins together here even though the chapter introduces the MCP actions module formally in Lab 4 — without it, the GenAI plugin will refuse to start.

> **Note:** This guide uses AWS Bedrock as the LLM provider. The plugin also supports OpenAI as an alternative.

---

## Step 1: Install Backend Dependencies

```bash
yarn workspace backend add \
  @aws/genai-plugin-for-backstage-backend \
  @aws/genai-plugin-langgraph-agent-for-backstage \
  @backstage/plugin-mcp-actions-backend
```

## Step 2: Register Backend Plugins

Edit `packages/backend/src/index.ts` and add the following before `backend.start()`:

```typescript
// MCP actions registry (provides core.actionsRegistry; required by aws-genai)
backend.add(import('@backstage/plugin-mcp-actions-backend'));

// GenAI plugin
backend.add(import('@aws/genai-plugin-for-backstage-backend'));
backend.add(import('@aws/genai-plugin-langgraph-agent-for-backstage'));
```

The `mcp-actions-backend` import has to come **before** the GenAI plugin imports, because the GenAI plugin's startup hooks resolve the actions registry service from it.

---

## Step 3: Install Frontend Dependencies

```bash
yarn workspace app add @aws/genai-plugin-for-backstage
```

## Step 4: Add Frontend Route

Edit `packages/app/src/App.tsx`:

**Add the import at the top:**
```typescript
import { AgentChatPage } from '@aws/genai-plugin-for-backstage';
```

**Add the route inside `<FlatRoutes>`:**
```typescript
<Route path="/assistant/:agentName" element={<AgentChatPage />} />
```

## Step 5: Add Sidebar Navigation

Edit `packages/app/src/components/Root/Root.tsx`:

**Add the import:**
```typescript
import { ChatIcon } from '@backstage/core-components';
```

**Add the sidebar item (inside the `<SidebarGroup>` with other navigation items):**
```typescript
<SidebarItem icon={ChatIcon} to="assistant/general" text="Chat Assistant"/>
```

---

## Step 6: Configure the GenAI Agent

Edit `app-config.yaml` and add the genai configuration:

```yaml
genai:
  agents:
    general: # This matches the URL in the frontend
      description: General chat assistant
      prompt: >
        You are an expert in platform engineering and answer questions in a succinct and easy to understand manner.

        Answers should always be well-structured and use well-formed Markdown.

        The current user is {username} and you can provide that information if asked.
      langgraph:
        messagesMaxTokens: 150000 # Set based on context of chosen model, prune message history based on number of tokens
        # Use appropriate snippet for your model provider
        bedrock:
          modelId: 'global.anthropic.claude-sonnet-4-5-20250929-v1:0'
          region: us-west-2
        # openai:
        #   apiKey: ${OPENAI_API_KEY}
```

> **Note:** At this stage, we're NOT adding any `actions` to the agent. The assistant can only answer general questions.

---

## Step 7: Set AWS Credentials

Set environment variables:

```bash
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_REGION=us-west-2
```

---

## Step 8: Test the Chat Assistant

```bash
# From the root directory
NODE_OPTIONS=--no-node-snapshot yarn start
```

1. Open `http://localhost:3000`
2. Click on "Chat Assistant" in the sidebar (or go to `http://localhost:3000/assistant/general`)
3. Try asking: "What is Backstage?"
4. The assistant should respond with general knowledge

### What Works at This Stage

✅ General questions about technology, programming, platform engineering
✅ Markdown-formatted responses
✅ Conversation history within a session

### What Doesn't Work Yet

❌ Questions about your catalog ("What services do we have?")
❌ Searching documentation
❌ Kubernetes queries

---

## Troubleshooting

### "Access Denied" or Bedrock errors
- Verify your AWS credentials are correct
- Ensure Bedrock is enabled in your AWS account
- Check that the model ID is available in your region

### Chat interface not appearing
- Check browser console for errors
- Verify the frontend plugin is installed
- Ensure the route is added to App.tsx

### Backend startup errors
- Check that **all three** backend plugins are installed (mcp-actions-backend, genai-plugin-for-backstage-backend, genai-plugin-langgraph-agent-for-backstage) and registered in `packages/backend/src/index.ts`
- Verify the imports in index.ts are correct
- If you see `Service or extension point dependencies of plugin 'aws-genai' are missing for the following ref(s): serviceRef{alpha.core.actions}`, the `mcp-actions-backend` plugin is missing or registered after the GenAI plugin
- If you see `Service or extension point dependencies of plugin 'X' are missing for the following ref(s): serviceRef{alpha.core.metrics}` for catalog/scaffolder/mcp-actions, your `package.json` `resolutions` are not pinned — re-apply [`../1-backstage-setup/files/package-resolutions.json`](../1-backstage-setup/files/package-resolutions.json) and run `yarn install`
- If you see `ERR_PACKAGE_PATH_NOT_EXPORTED ./utils/uuid` from `@langchain/ollama`, your `@langchain/*` resolutions are missing or not applied — `yarn install` after fixing `package.json`

---

## Summary

You now have a basic AI chat assistant in Backstage. It can answer general questions but doesn't have access to your Backstage data yet.

---

## Next Steps

In Lab 3, we'll give the assistant access to the Backstage catalog.

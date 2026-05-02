# Lab 2: Adding the AI Chat Assistant

This lab covers adding the AWS GenAI plugin to enable an AI-powered chat interface in Backstage.

## Prerequisites

- Completed Lab 1 (Backstage with GitOps)
- AWS account with Bedrock access enabled and AWS credentials configured, OR
- OpenAI API key (see the [plugin documentation](https://github.com/awslabs/genai-for-backstage) for OpenAI configuration)

## Overview

We'll add a chat assistant that can answer general questions. At this stage, it won't have access to Backstage data yet - that comes in the next lab.

> **Note:** This guide uses AWS Bedrock as the LLM provider. The plugin also supports OpenAI as an alternative.

---

## Step 1: Install Backend Dependencies

```bash
yarn workspace backend add @aws/genai-plugin-for-backstage-backend @aws/genai-plugin-langgraph-agent-for-backstage
```

## Step 2: Register Backend Plugins

Edit `packages/backend/src/index.ts` and add the following before `backend.start()`:

```typescript
// Add GenAI Plugin
backend.add(import('@aws/genai-plugin-for-backstage-backend'));
backend.add(import('@aws/genai-plugin-langgraph-agent-for-backstage'));
```

**Complete `packages/backend/src/index.ts` should look like:**

```typescript
import { createBackend } from '@backstage/backend-defaults';

const backend = createBackend();

backend.add(import('@backstage/plugin-app-backend'));
backend.add(import('@backstage/plugin-proxy-backend'));
backend.add(import('@backstage/plugin-scaffolder-backend'));
backend.add(import('@backstage/plugin-scaffolder-backend-module-github'));
backend.add(import('@backstage/plugin-techdocs-backend'));
backend.add(import('@backstage/plugin-auth-backend'));
backend.add(import('@backstage/plugin-auth-backend-module-guest-provider'));
backend.add(import('@backstage/plugin-catalog-backend'));
backend.add(import('@backstage/plugin-catalog-backend-module-scaffolder-entity-model'));
backend.add(import('@backstage/plugin-permission-backend'));
backend.add(import('@backstage/plugin-permission-backend-module-allow-all-policy'));
backend.add(import('@backstage/plugin-search-backend'));
backend.add(import('@backstage/plugin-search-backend-module-catalog'));
backend.add(import('@backstage/plugin-search-backend-module-techdocs'));

// Add GenAI Plugin
backend.add(import('@aws/genai-plugin-for-backstage-backend'));
backend.add(import('@aws/genai-plugin-langgraph-agent-for-backstage'));

backend.start();
```

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
          modelId: 'anthropic.claude-3-5-sonnet-20241022-v2:0'
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
- Check that both backend plugins are installed
- Verify the imports in index.ts are correct

---

## Summary

You now have a basic AI chat assistant in Backstage. It can answer general questions but doesn't have access to your Backstage data yet.

---

## Next Steps

In Lab 3, we'll give the assistant access to the Backstage catalog.

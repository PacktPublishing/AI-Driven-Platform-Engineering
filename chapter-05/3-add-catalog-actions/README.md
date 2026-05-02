# Lab 3: Adding Backstage Catalog Actions

This lab covers giving the AI assistant access to your Backstage catalog by registering built-in actions.

## Prerequisites

- Completed Lab 2 (Chat Assistant installed)
- Components in your catalog (from Lab 1 template)

## Overview

We'll enable three built-in actions that are already available in Backstage:
- **`get-catalog-entity`**: Fetch a specific entity by kind/namespace/name
- **`search-catalog`**: Search across all catalog entities
- **`search-techdocs`**: Search technical documentation

No additional packages are required - we just need to configure the actions.

---

## Step 1: Configure Plugin Sources

Edit `app-config.yaml` and add the `backend.actions` section:

```yaml
backend:
  # ... existing backend config ...
  actions:
    pluginSources:
      - 'catalog'      # Enables catalog actions
      - 'aws-genai'    # Enables genai core actions
```

---

## Step 2: Enable Core Actions and Add Catalog Actions

Update the `genai` section in `app-config.yaml` to add `registerCoreActions` and the `actions` list:

```yaml
genai:
  registerCoreActions: true  # Important: registers built-in actions
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
        - get-catalog-entity  # Fetch specific entity by kind/namespace/name
        - search-catalog      # Search across all catalog entities
        - search-techdocs     # Search technical documentation
```

> **Note:** The `registerCoreActions: true` flag registers several actions related to "core" Backstage functions like the catalog and TechDocs. These are provided by the GenAI plugin until upstream Backstage makes general implementations available.

---

## Step 3: Test the Catalog Integration

```bash
NODE_OPTIONS=--no-node-snapshot yarn start
```

Open the AI Assistant (`http://localhost:3000/assistant/general`) and try these queries:

### Search the Catalog
```
What components do we have in the catalog?
```

### Get Specific Entity
```
Tell me about the my-first-app component
```

---

## Action Details

| Action | Description | Example Use |
|--------|-------------|-------------|
| `get-catalog-entity` | Retrieves a specific entity | "Get details about my-first-app" |
| `search-catalog` | Searches all entities | "Find all services owned by guest" |
| `search-techdocs` | Searches documentation | "How do I deploy to production?" |

## Troubleshooting

### "Action not found" errors
- Ensure `registerCoreActions: true` is set
- Verify action names match exactly (case-sensitive)
- Check that `backend.actions.pluginSources` includes `catalog` and `aws-genai`

### Empty search results
- Verify you have entities in your catalog
- Check that the catalog backend is running
- Try a broader search term

### TechDocs search not working
- Ensure TechDocs is configured and indexed
- Verify the search backend is running

---

## Summary

Your AI assistant can now:
- ✅ Answer general questions
- ✅ Search your software catalog
- ✅ Retrieve specific entity details
- ✅ Search technical documentation

---

## Next Steps

In Lab 4, we'll add Kubernetes actions so the assistant can query your cluster.

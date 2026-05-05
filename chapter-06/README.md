# Chapter 6: From Insight to Action with Strands

This chapter takes the read-only chat assistant from Chapter 5 across the boundary it stopped at: **action**. The agent moves out of Backstage, becomes a service of its own, and proposes changes through the same GitOps flow your platform already uses.

The labs build a minimum production-grade agent end-to-end:

| Lab | What you build | Chapter section |
|---|---|---|
| **0 — Prerequisites** | Verify the Chapter 5 stack is alive (kind cluster, Backstage, ArgoCD, ApplicationSet, components repo) | — |
| **1 — Strands runtime** | A FastAPI service wrapping a Strands `Agent`, with file-based identity (`SOUL.md`, `IDENTITY.md`, `USER.md`, `MEMORY.md`) — deployed *through* the ArgoCD ApplicationSet you set up in Chapter 5 | *A Strands Agent as a Service* + *Memory in two layers* |
| **2 — GitOps MCP server** | One MCP server: clones the components repo, edits a YAML, opens a PR. Plus one skill (`scale-deployment`) and one Strands hook (always-PR, never-apply-direct) | *Domain-Scoped MCP Servers* + *Skills as Procedural Knowledge* + *Governed Writes via Hooks* |
| **3 — Langfuse + audit log** | Local Langfuse (in-cluster) collecting OpenTelemetry traces from the agent, plus a hash-chained append-only audit log | *Observability and Audit* |
| **4 — End-to-end demo** | Drive the full loop: ask the agent to scale `my-first-app`, watch the PR open, merge, ArgoCD reconcile, and trace it all in Langfuse | — |

## What we deliberately keep out

The chapter argues that production agents need four MCPs (catalog, gitops, cluster-ops, observability), self-invocation via an event bus, and identity propagation across hops. The labs build only what's needed to demonstrate the loop end-to-end:

- **One MCP, not four.** `gitops-mcp` is the bridge from observation to action, and the chapter says so explicitly. The other three are conceptual extensions of the same pattern; the architecture in Lab 2 makes adding them mechanical.
- **No self-invocation.** The agent runs synchronously from an HTTP request. The cron-triggered loop with `agent_action` filtering is documented in the chapter and left as an extension exercise.
- **Identity propagation is single-tenant.** The agent runs under one ServiceAccount with one GitHub PAT. Multi-tenant identity propagation (OIDC token exchange, `AssumeRoleWithWebIdentity`) is covered in Chapter 9.

What does land in the labs covers every concept the chapter promises end-to-end at least once.

## What we reuse from Chapter 5

The `ApplicationSet` you applied in [chapter-05/1-backstage-setup](../chapter-05/1-backstage-setup/files/argocd-applicationset.yaml) auto-discovers any folder in your `backstage-components` repo with `*/argocd/application.yaml`. **That's the deploy channel for everything in this chapter.** You will not run `kubectl apply` directly. Every component lands in the cluster the same way `my-first-app` did: PR → merge → ArgoCD.

There's a recursive moment worth noticing as you go through the labs: *the platform you built in Chapter 5 is what deploys the agent that consumes it in Chapter 6.* That is the chapter's thesis made literal.

## Defaults

- **Cluster:** kind (works offline; matches the chapter's "from kind cluster bootstrap")
- **LLM provider:** Amazon Bedrock with Claude Sonnet 4.5 by default; Anthropic API direct documented as a fallback for readers without AWS access
- **Backstage:** stays on the host (`yarn start`, as in Chapter 5). The agent reaches it via `host.docker.internal`
- **GitHub:** the same `backstage-components` repo and PAT you set up in [chapter-05/1-backstage-setup](../chapter-05/1-backstage-setup/README.md)

Override any of these via environment variables documented in each lab's README.

## Start here

```bash
cd 0-prereqs
```

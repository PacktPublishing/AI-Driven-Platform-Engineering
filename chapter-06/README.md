# Chapter 6: From Insight to Action with Strands

This chapter takes the read-only chat assistant from Chapter 5 across the boundary it stopped at: **action**. The agent moves out of Backstage, becomes a service of its own, and proposes changes through the same GitOps flow your platform already uses.

The labs build a minimum production-grade agent end-to-end:

| Lab | What you build | Chapter section |
|---|---|---|
| **0 — Prerequisites** | Verify the Chapter 5 stack is alive (kind cluster, Backstage, ArgoCD, ApplicationSet, components repo) | — |
| **1 — Strands runtime** | A FastAPI service wrapping a Strands `Agent`, with file-based identity (`SOUL.md`, `IDENTITY.md`, `USER.md`, `MEMORY.md`) — deployed *through* the ArgoCD ApplicationSet you set up in Chapter 5 | *A Strands Agent as a Service* + *Memory in two layers* |
| **2 — GitOps MCP + skill + hook** | One MCP server: clones the components repo, edits a YAML, opens a PR. Plus one skill (`fix-image-tag`) and one Strands hook (`AlwaysPRHook`) | *Domain-Scoped MCP Servers* + *Skills as Procedural Knowledge* + *Governed Writes via Hooks* |
| **3 — Backstage strands-proxy module** | Backstage backend module that registers `strands-proxy` as a new agent type with the Chapter 5 GenAI plugin, so the chat sidebar can talk to the agent over HTTP | *Where We Are Going* (Figure 6.3) |
| **4 — Langfuse + audit log** | Local Langfuse (in-cluster) collecting traces from the agent via the Langfuse Python SDK, plus a hash-chained append-only audit log on a PVC | *Observability and Audit* |
| **5 — End-to-end demo walk-through** | Drive the full loop with everything live: break `my-first-app`, ask the Platform Agent to fix it from the Backstage chat, watch the PR open, merge, see the trace in Langfuse, verify the audit chain | — |

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

## Terminals you'll keep open

By Lab 4 you have several long-running things on different terminals. Plan for at least three:

| Terminal | What runs there | When |
|---|---|---|
| 1 | `yarn start` for the Backstage app on the host (Chapter 5) | Always — Lab 3 onwards needs the chat UI |
| 2 | `kubectl -n agent-platform port-forward svc/agent-runtime 18080:80` | Lab 1 onwards (Backstage backend hits this in Lab 3) |
| 3 | `kubectl -n langfuse port-forward svc/langfuse 13000:3000` | Lab 4 onwards |
| 4 | Free for `kubectl get`, `curl`, `git`, `gh` | All the time |

`tmux` or your editor's terminal split is fine; just don't close the port-forwards mid-lab — they exit the moment you do, and the symptoms downstream (chat hanging, traces not arriving) look unrelated.

## Start here

```bash
cd 0-prereqs
```

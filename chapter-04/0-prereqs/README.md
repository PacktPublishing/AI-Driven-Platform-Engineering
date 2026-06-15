# Lab 0: Prerequisites

This lab deploys nothing. It confirms your environment is ready for the RAG and MCP labs.

## 1. The shared cluster

Chapter 4 runs on the same kind cluster as the rest of the book, but it does **not** need ArgoCD or Backstage (those arrive in Chapter 5). If you haven't created the cluster yet:

```bash
cd ../../00-cluster-setup
SKIP_ARGOCD=1 ./setup-cluster.sh
cd -
```

Confirm it's reachable:

```bash
kubectl cluster-info --context kind-agentic-platform
```

Already created the full cluster for Chapter 5/6? That works too — nothing here conflicts.

## 2. Python 3.11+

The RAG pipeline (Lab 2) and the MCP server (Lab 3) are Python. You need Python 3.11 or newer:

```bash
python3 --version   # 3.11+
```

Each lab ships its own `requirements.txt`. We recommend a virtualenv per lab (the labs tell you when).

## 3. What runs where

To keep this chapter focused on *concepts* (RAG and MCP) rather than deployment machinery — which Chapters 5 and 6 cover in depth — only the stateful piece runs in the cluster:

| Component | Where it runs | Why |
|---|---|---|
| **Postgres + pgvector** | In-cluster (kind), reached via NodePort | It's infrastructure; natural to run on the cluster |
| **RAG ingestion + API** (Lab 2) | Locally, in a Python venv | Concept-focused; talks to pgvector over the NodePort |
| **MCP server** (Lab 3) | Locally, over stdio | This is exactly how MCP hosts (Claude Desktop, Cursor) launch servers; it queries the *live* cluster via your kubeconfig |

No image building, no registry, no `kind load`. Just `kubectl apply` for pgvector and `python` for the rest.

## 4. LLM credentials (generation only)

Embeddings run locally and need no credentials. *Generation* (turning retrieved context into an answer) needs one of:

- **Bedrock (recommended):** `aws sts get-caller-identity` succeeds, and a Claude model is enabled in your region. Set `AWS_REGION` and (optionally) `BEDROCK_MODEL_ID`.
- **Anthropic API:** export `ANTHROPIC_API_KEY`. Set `LLM_PROVIDER=anthropic`.

You can run Lab 2's *ingestion and retrieval* with no LLM credentials at all — the API will return the retrieved context and tell you generation is disabled. You only need credentials to get a synthesized answer.

## You're ready when

- `kubectl cluster-info --context kind-agentic-platform` works.
- `python3 --version` is 3.11+.
- You have Bedrock or Anthropic access (or accept retrieval-only mode for now).

Move on to [Lab 1](../1-knowledge-corpus/README.md).

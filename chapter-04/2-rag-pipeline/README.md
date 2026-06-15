# Lab 2: A Local RAG Pipeline

This is the chapter's RAG section (§4.9) made real — and built to run on your laptop instead of on Kinesis, Lambda, and OpenSearch. You'll stand up a vector store, embed the Lab 1 corpus into it, and ask questions that get answered *from your runbooks* rather than from the model's training data.

## The six components, mapped

The chapter says every RAG system has six parts. Here's where each one lives:

| Chapter component | In this lab |
|---|---|
| **Knowledge Sources** | The Lab 1 corpus (`../1-knowledge-corpus/corpus/`) |
| **Ingestion & Embeddings** | [`app/ingest.py`](./files/rag/app/ingest.py) + [`app/embeddings.py`](./files/rag/app/embeddings.py) (fastembed, local) |
| **Vector Database** | Postgres + pgvector, in-cluster ([`pgvector/pgvector.yaml`](./files/pgvector/pgvector.yaml)) |
| **Retriever** | [`app/store.py`](./files/rag/app/store.py) — cosine search in pgvector |
| **LLM** | [`app/llm.py`](./files/rag/app/llm.py) — Bedrock Claude or Anthropic |
| **Orchestration Layer** | [`app/api.py`](./files/rag/app/api.py) — the `/ask` endpoint that ties it together |

## Step 1: Deploy the vector store

Postgres-with-pgvector is the only piece that runs in the cluster:

```bash
kubectl apply -f files/pgvector/pgvector.yaml
kubectl rollout status deployment/pgvector -n rag-demo --timeout=180s
```

The Service is a NodePort, so it's reachable from your host at `localhost:30900` (mapped by [`00-cluster-setup/kind-config.yaml`](../../00-cluster-setup/kind-config.yaml)). No port-forward needed.

## Step 2: Set up the Python environment

```bash
cd files/rag
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> First run downloads the local embedding model (`BAAI/bge-small-en-v1.5`, ~100MB) — no cloud credentials required for embeddings.

## Step 3: Ingest the corpus

```bash
python -m app.ingest
```

Expected output:

```
Loading corpus from .../chapter-04/1-knowledge-corpus/corpus ...
  18 chunks from 6 documents
Embedding with provider='local' ...
  embedding dimension: 384
Writing to pgvector ...
Done. 18 chunks stored. Re-run any time to refresh.
```

`ingest` is idempotent — it drops and rebuilds the table each run, so you can edit the corpus and re-ingest freely. (Dropping the table on each run also means switching embedding providers, which changes the vector dimension, just works.)

## Step 4: Ask questions

Configure generation (optional but recommended). Embeddings are local; *generation* needs one provider:

```bash
# Option A — Bedrock (recommended)
export LLM_PROVIDER=bedrock
export AWS_REGION=us-east-1
# (BEDROCK_MODEL_ID defaults to a Claude Sonnet model; override if needed)

# Option B — Anthropic API
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Option C — no credentials: retrieval-only (you still see the sources)
export LLM_PROVIDER=none
```

Start the API:

```bash
uvicorn app.api:app --port 8000
```

Ask the question from §4.9:

```bash
curl -s -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "Why does a pod end up in CrashLoopBackOff and how do I fix it?"}' | jq
```

With generation enabled you get a grounded answer **plus the exact sources it used**:

```json
{
  "question": "Why does a pod end up in CrashLoopBackOff...",
  "answer": "CrashLoopBackOff means the container keeps exiting... (1) read --previous logs ... [grounded in runbooks/crashloopbackoff.md]",
  "generation_provider": "bedrock",
  "sources": [
    {"source": "runbooks/crashloopbackoff.md", "doc_type": "runbook", "owner": "platform-team", "score": 0.83}
  ]
}
```

The `sources` array is the point. This isn't a chatbot guessing — every answer is traceable to a document your platform team owns. Try the other questions too:

```bash
curl -s -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "What are the mandatory labels every workload must have?"}' | jq '.sources'
# -> blueprints/tagging-and-labels.md

curl -s -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "What caused the payment processor outage in March?"}' | jq '.sources'
# -> postmortems/2026-03-payment-processor-outage.md
```

`GET /healthz` shows chunk count and which providers are active.

## What this shows — and where it stops

RAG just answered questions from durable, owned knowledge: runbooks, a postmortem, blueprints. That's its sweet spot — *accumulated wisdom*.

Now ask it: **"Which deployments are unhealthy right now?"** It can't know. Nothing in the corpus describes the current state of your cluster, and even if you'd embedded a snapshot, it would be stale the moment a pod restarted. That's the wall the chapter describes — and exactly the gap [Lab 3](../3-mcp-server/README.md) closes with MCP.

## Cleanup

```bash
kubectl delete -f files/pgvector/pgvector.yaml   # removes the rag-demo namespace and PVC
```

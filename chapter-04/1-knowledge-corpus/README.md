# Lab 1: The Knowledge Corpus

Before you can make organizational knowledge consumable by AI, you need organizational knowledge that's worth consuming. This lab gives you a small but **structured** corpus — the kind §4.6–4.7 argue for: every artifact has an owner, a type, and a consistent shape.

You don't run anything here. You read the corpus, understand why it's structured the way it is, and then Lab 2 turns it into something an AI can retrieve over.

## What's in `corpus/`

```
corpus/
├── runbooks/
│   ├── crashloopbackoff.md      # the canonical "why is my pod restarting?" runbook
│   ├── oomkilled.md             # memory-limit failures
│   └── imagepullbackoff.md      # bad image refs / missing pull secrets
├── postmortems/
│   └── 2026-03-payment-processor-outage.md
└── blueprints/
    ├── standard-service.md      # the approved way to deploy a service
    └── tagging-and-labels.md    # mandatory labels / tags
```

Three kinds of knowledge, mirroring the chapter:

- **Runbooks** — durable "how to handle X" procedures. The bread and butter of operational knowledge.
- **Postmortems** — what went wrong once, why, and what changed. Cumulative organizational memory.
- **Blueprints** — the standards and guardrails (§4.3): the approved way to do something.

## Why the structure matters

Every file starts with the same metadata block:

```markdown
---
type: runbook | postmortem | blueprint
title: ...
owner: <team that stands behind this>
tags: [...]
---
```

This is the standardization §4.6 calls for. It's not bureaucracy — it's what lets Lab 2's ingestion attach consistent metadata to every chunk, and what would let a real system filter ("only retrieve runbooks owned by the platform team") later. When every team invents its own format, AI can only help locally; consistent shape is what lets it scale across the org.

Two things to notice as you read:

1. **The CrashLoopBackOff runbook is the payoff for Lab 2.** When you ask the RAG API "why does a pod end up in CrashLoopBackOff and how do I fix it?", the answer should be grounded in [`corpus/runbooks/crashloopbackoff.md`](./corpus/runbooks/crashloopbackoff.md) — not the model's training data. You'll be able to see the source it used.
2. **The postmortem links back to runbooks.** That's the knowledge *flow* from §4.6: a resolved incident feeds a postmortem, which points to (and sharpens) the standard runbooks. Durable knowledge compounds.

## Extending it

This corpus is deliberately small so you can reason about what the model retrieves. To see RAG behave differently, drop more markdown files into `corpus/` and re-run Lab 2's ingestion — the pipeline picks up everything under `corpus/` recursively.

Move on to [Lab 2](../2-rag-pipeline/README.md).

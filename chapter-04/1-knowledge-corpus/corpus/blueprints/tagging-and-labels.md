---
type: blueprint
title: Mandatory labels and tags
owner: platform-team
tags: [blueprint, standard, labels, tags, cost-allocation, governance]
---

# Blueprint: Mandatory Labels and Tags

Consistent labels are what let humans and AI reason across the whole estate — "show me everything the payments team owns," "which services are in production." Without them, the catalog is noise.

## Required Kubernetes labels

Every workload **must** carry:

| Label | Meaning | Example |
|---|---|---|
| `app.kubernetes.io/name` | The service name | `payment-processor` |
| `app.kubernetes.io/part-of` | The larger system it belongs to | `checkout` |
| `owner` | The team accountable for it | `payments-team` |
| `environment` | Deployment environment | `production` |

## Required cloud tags (for cloud resources)

| Tag | Meaning |
|---|---|
| `Owner` | Accountable team |
| `Environment` | `production` / `staging` / `dev` |
| `CostCenter` | For cost allocation |

## Why this matters for AI

When every resource is labeled consistently, an AI assistant can answer ownership and blast-radius questions directly from cluster state — and an MCP server (Chapter 4, Lab 3) can filter live deployments by `owner` or `environment`. Inconsistent labels collapse that capability back to guesswork.

## Related

- [standard-service blueprint](./standard-service.md)

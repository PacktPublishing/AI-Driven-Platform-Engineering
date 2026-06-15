---
type: blueprint
title: Standard service deployment
owner: platform-team
tags: [blueprint, standard, deployment, resources, probes, guardrails]
---

# Blueprint: Standard Service

This is the approved way to deploy a service. AI assistants should recommend *this* pattern rather than hand-rolling raw manifests — it encodes the guardrails the platform team stands behind.

## Mandatory requirements

Every service deployed to a shared cluster **must**:

1. **Declare resource requests and limits** for CPU and memory. No exceptions — a container without a memory limit can starve its neighbors. (See the [OOMKilled runbook](../runbooks/oomkilled.md).)
2. **Define a readiness probe and a liveness probe.** Readiness gates traffic; liveness restarts a wedged container. A missing readiness probe means traffic hits pods that aren't ready.
3. **Carry the mandatory labels** from the [tagging-and-labels blueprint](./tagging-and-labels.md).
4. **Pull images from an approved registry** by digest or immutable tag — never `:latest`.
5. **Run as non-root** with a read-only root filesystem where possible.

## Reference shape

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 256Mi
readinessProbe:
  httpGet: { path: /healthz, port: 8080 }
  initialDelaySeconds: 5
livenessProbe:
  httpGet: { path: /healthz, port: 8080 }
  initialDelaySeconds: 15
```

## How AI should use this

When a developer asks "how do I deploy a new service?", the grounded answer is: *use this blueprint* — set requests/limits, add both probes, apply the standard labels, pin the image. The model becomes an advocate for platform standards instead of generating raw, ungoverned YAML.

## Related

- [tagging-and-labels blueprint](./tagging-and-labels.md)
- [OOMKilled runbook](../runbooks/oomkilled.md)

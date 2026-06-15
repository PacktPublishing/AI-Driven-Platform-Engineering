---
type: runbook
title: Diagnosing OOMKilled containers
owner: platform-team
tags: [kubernetes, memory, oomkilled, resources, troubleshooting]
---

# Runbook: OOMKilled

## Symptom

A container is terminated with `Reason: OOMKilled`. You'll see it in:

```bash
kubectl describe pod <pod> -n <namespace>
# Last State:  Terminated
#   Reason:    OOMKilled
#   Exit Code: 137
```

Exit code `137` = `128 + 9` (SIGKILL). The kernel's OOM killer terminated the process because it exceeded its cgroup memory limit. Repeated OOMKills present as [CrashLoopBackOff](./crashloopbackoff.md).

## Diagnosis

```bash
# Current vs limit (requires metrics-server, installed by 00-cluster-setup)
kubectl top pod <pod> -n <namespace>

# What is the limit?
kubectl get pod <pod> -n <namespace> -o jsonpath='{.spec.containers[*].resources.limits.memory}'
```

Ask: is the limit too low for legitimate load, or is the app leaking? A container that OOMs minutes after start under steady traffic is usually under-provisioned; one that OOMs after hours of slow growth is usually leaking.

## Fixes

1. **Under-provisioned** — raise `resources.limits.memory` (and `requests.memory` to match real usage). Set requests to typical usage, limits to peak.
2. **Leak** — capture a heap profile before the kill; fix the leak. Raising the limit only delays the crash.
3. **JVM / runtime not container-aware** — older runtimes ignore cgroup limits and size heaps off host memory. Set `-XX:MaxRAMPercentage` (JVM) or the runtime's container-aware flag.

## Standard

All workloads must declare memory `requests` and `limits` — see the [standard-service blueprint](../blueprints/standard-service.md). A container with no limit can starve its neighbors instead of being cleanly OOMKilled.

## Related

- [CrashLoopBackOff runbook](./crashloopbackoff.md)
- [standard-service blueprint](../blueprints/standard-service.md)

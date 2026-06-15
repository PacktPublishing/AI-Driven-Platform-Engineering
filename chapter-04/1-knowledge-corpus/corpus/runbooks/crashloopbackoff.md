---
type: runbook
title: Diagnosing and fixing CrashLoopBackOff
owner: platform-team
tags: [kubernetes, pods, crashloopbackoff, troubleshooting]
---

# Runbook: CrashLoopBackOff

## Symptom

A pod shows `STATUS: CrashLoopBackOff` in `kubectl get pods`. The container starts, exits, and Kubernetes restarts it with exponential backoff (10s, 20s, 40s, … up to 5m). The restart counter climbs.

`CrashLoopBackOff` is **not** a root cause — it's Kubernetes telling you the container keeps exiting. Your job is to find *why* it exits.

## First commands

```bash
# What is the restart count and how long has it been looping?
kubectl get pod <pod> -n <namespace>

# The single most useful command: logs from the PREVIOUS (crashed) container.
kubectl logs <pod> -n <namespace> --previous

# Events often name the cause directly (OOMKilled, failed mount, etc.)
kubectl describe pod <pod> -n <namespace>
```

## Common root causes and fixes

1. **Application error on startup** — the process exits non-zero (bad config, missing env var, failed DB connection). Fix: read `--previous` logs; correct the config or secret. This is the most common cause.
2. **OOMKilled** — the container exceeded its memory limit and was killed. `describe` shows `Last State: Terminated, Reason: OOMKilled`. Fix: raise `resources.limits.memory`, or fix the leak. See the [OOMKilled runbook](./oomkilled.md).
3. **Failing liveness probe** — the probe fails, Kubernetes restarts the container before it's ready. Fix: increase `initialDelaySeconds`, or correct the probe path/port.
4. **Bad command/entrypoint** — the image's command exits immediately (e.g. a script that runs once and returns). Fix: the container must run a long-lived process in the foreground.
5. **Missing dependency at boot** — the app needs a database or sidecar that isn't ready. Fix: add readiness gating / init containers, or make startup resilient with retries.

## Escalation

If `--previous` logs are empty and `describe` shows no clear reason, the container may be crashing before it can log. Try overriding the entrypoint to `sleep 3600` and `kubectl exec` in to inspect the environment manually.

## Related

- [OOMKilled runbook](./oomkilled.md)
- [ImagePullBackOff runbook](./imagepullbackoff.md)
- Postmortem: [2026-03 payment-processor outage](../postmortems/2026-03-payment-processor-outage.md) — a CrashLoopBackOff caused by a network-policy change.

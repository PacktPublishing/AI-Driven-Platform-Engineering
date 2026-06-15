---
type: postmortem
title: payment-processor CrashLoopBackOff after network-policy change
owner: payments-team
tags: [postmortem, crashloopbackoff, network-policy, production, payment-processor]
incident_date: 2026-03-16
severity: SEV2
---

# Postmortem: payment-processor outage (2026-03-16)

## Summary

On 2026-03-16 the `payment-processor` service in the `production` namespace entered `CrashLoopBackOff` and stopped processing payments for **42 minutes**. Root cause was a NetworkPolicy change that blocked the pod's egress to the database. Customer impact: ~3% of checkout attempts failed during the window.

## Timeline (UTC)

- **15:00** — A NetworkPolicy update was merged and rolled out to `production`, tightening egress rules.
- **15:30** — `payment-processor` pods began failing their startup database connection and exiting non-zero.
- **15:32** — Pods entered `CrashLoopBackOff`; checkout error rate climbed.
- **15:38** — On-call paged. Followed the [CrashLoopBackOff runbook](../runbooks/crashloopbackoff.md): `kubectl logs --previous` showed `connection timed out` to the database host.
- **15:55** — Correlated the symptom with the 15:00 NetworkPolicy change (the only recent change). Reverted the policy.
- **16:12** — Pods recovered; error rate returned to baseline. Incident closed.

## Root cause

The new NetworkPolicy's egress allowlist did not include the database's namespace/port. `payment-processor` opens its DB connection at startup and exits if it fails — so a blocked egress surfaced as a crash loop, not a slow degradation.

## What went well

- The CrashLoopBackOff runbook took the responder straight to `--previous` logs, which named the failure (`connection timed out`) immediately.

## What went wrong

- NetworkPolicy changes had no staging/canary gate; the change hit all of `production` at once.
- The app exits hard on a startup DB failure instead of retrying, converting a transient/network issue into a crash loop.

## Action items

1. **Gate NetworkPolicy changes** behind the same canary process as app deploys. (owner: platform-team)
2. **Make startup DB connection resilient** — retry with backoff instead of exiting. (owner: payments-team)
3. **Add a runbook cross-link**: the [CrashLoopBackOff runbook](../runbooks/crashloopbackoff.md) now lists "recent NetworkPolicy change" as cause #6 to check. (owner: platform-team)

## Related

- [CrashLoopBackOff runbook](../runbooks/crashloopbackoff.md)

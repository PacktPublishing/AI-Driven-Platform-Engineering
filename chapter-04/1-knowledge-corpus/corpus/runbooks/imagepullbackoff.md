---
type: runbook
title: Diagnosing ImagePullBackOff / ErrImagePull
owner: platform-team
tags: [kubernetes, images, imagepullbackoff, registry, troubleshooting]
---

# Runbook: ImagePullBackOff

## Symptom

A pod is stuck in `ImagePullBackOff` or `ErrImagePull`. The container never starts because the kubelet can't pull the image.

## Diagnosis

```bash
kubectl describe pod <pod> -n <namespace>
# Look at Events for the specific reason:
#   "manifest unknown"        -> wrong tag / image doesn't exist
#   "pull access denied"      -> private registry, missing/invalid credentials
#   "no such host"            -> wrong registry hostname / DNS
```

## Common root causes and fixes

1. **Typo'd image or tag** — `myimage:lateset`, or a tag that was never pushed. Fix: correct the reference; verify with `docker pull` / `crane manifest`.
2. **Private registry without an imagePullSecret** — the registry needs auth the cluster doesn't have. Fix: create a `kubernetes.io/dockerconfigjson` secret and reference it in `imagePullSecrets`.
3. **Rate limiting** — Docker Hub anonymous pull limits. Fix: authenticate, or mirror the image to your own registry.
4. **Local image not loaded into kind** — on kind, an image built locally isn't visible to the cluster until you load it. Fix: `kind load docker-image <image> --name agentic-platform` and set `imagePullPolicy: IfNotPresent`. (This is exactly how Labs 2 and 3 ship their images.)

## kind-specific note

`kind load docker-image` copies an image from your host's Docker into the cluster's containerd. If you rebuild the image, you must `kind load` it again — the cluster does not see your host rebuilds automatically.

## Related

- [CrashLoopBackOff runbook](./crashloopbackoff.md)

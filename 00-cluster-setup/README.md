# Lab 0 (shared): Local Cluster Setup

Every chapter in this book runs against **one local Kubernetes cluster** you create here, on your own machine. It's a [kind](https://kind.sigs.k8s.io/) cluster — Kubernetes running inside Docker — so it works offline and costs nothing. You set it up once and reuse it across Chapters 4, 5, and 6.

> **Already have a cluster?** Amazon EKS or any other Kubernetes cluster works too, as long as it can pull images and you can `kubectl apply`. If you go that route, skip the `kind` step below and just run `metrics-server` + ArgoCD against your cluster. For EKS see [Getting Started](https://docs.aws.amazon.com/eks/latest/userguide/getting-started.html) and the managed [ArgoCD capability](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html).

## What this gives you

| Component | Why |
|---|---|
| **kind cluster** `agentic-platform` | The substrate everything deploys onto |
| **Metrics Server** | Required by the HPA in the Chapter 5 web-app template |
| **ArgoCD** (`v3.0.21`) | The GitOps deploy channel used in Chapters 5 and 6 |
| **NodePorts** 30080/30443/30900/30901 | Forwarded to `localhost` for the chapter demos |

## Prerequisites

- [Docker](https://docs.docker.com/get-started/get-docker/) — running
- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

## One command

```bash
cd 00-cluster-setup
./setup-cluster.sh
```

This is idempotent — re-running it is safe; it skips anything already in place. It will:

1. Create the kind cluster `agentic-platform` (from [`kind-config.yaml`](./kind-config.yaml)).
2. Install Metrics Server and patch it for kind's self-signed kubelet certs.
3. Install ArgoCD and wait for it to be ready.

Want just the cluster without ArgoCD (e.g. you're only doing Chapter 4)?

```bash
SKIP_ARGOCD=1 ./setup-cluster.sh
```

## Verify

```bash
./verify.sh
```

Reports pass/fail for the cluster, Metrics Server, ArgoCD, the `host.docker.internal` bridge (how in-cluster agents reach Backstage on your host), and — if you export `GITHUB_USERNAME` and `GITHUB_TOKEN` — your GitHub PAT against the `backstage-components` repo.

```bash
GITHUB_USERNAME=your-username GITHUB_TOKEN=github_pat_... ./verify.sh
```

## After setup: ArgoCD (Chapters 5 & 6)

Get the admin password:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

Open the UI (optional):

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
# https://localhost:8080  (user: admin)
```

The GitOps **ApplicationSet** that watches your `backstage-components` repo lives with Chapter 5 — apply it after you've replaced `YOUR_USERNAME`:

```bash
kubectl apply -f ../chapter-05/1-backstage-setup/files/argocd-applicationset.yaml
```

See [chapter-05/1-backstage-setup](../chapter-05/1-backstage-setup/README.md) Part 2/3 for the GitHub repo, PAT, and credentials wiring.

## Tear down

```bash
./teardown.sh
```

Deletes the kind cluster and everything in it. Your Backstage app on the host and your GitHub repo are untouched.

## Files

| File | Purpose |
|---|---|
| [`kind-config.yaml`](./kind-config.yaml) | Cluster definition + NodePort mappings |
| [`setup-cluster.sh`](./setup-cluster.sh) | Idempotent create + metrics-server + ArgoCD |
| [`verify.sh`](./verify.sh) | Read-only environment checks |
| [`teardown.sh`](./teardown.sh) | Delete the cluster |

# Lab 0: Prerequisites

This lab does not deploy anything. It checks that the Chapter 5 stack is healthy and that your environment can reach the cluster the way the agent will need to in the next labs. If everything passes, move on to Lab 1.

## What you need from Chapter 5

You should already have, from Chapter 5:

1. The shared local cluster from [`00-cluster-setup`](../../00-cluster-setup/README.md) — a **kind** cluster with Metrics Server and **ArgoCD** (in the `argocd` namespace) already installed. EKS or any other cluster works as long as it can pull images and you can `kubectl apply`.
2. Backstage running on the host (`yarn start` in your `my-backstage-app` directory).
3. The `ApplicationSet` named `backstage-app-discovery` from [chapter-05/1-backstage-setup/files/argocd-applicationset.yaml](../../chapter-05/1-backstage-setup/files/argocd-applicationset.yaml) applied to the cluster.
4. A GitHub repository (the `backstage-components` repo from Chapter 5) that the ApplicationSet polls.
5. At least one app deployed through the GitOps flow (e.g., `my-first-app`). This is what proves the loop works.

If any of these are missing, run [`00-cluster-setup/setup-cluster.sh`](../../00-cluster-setup/README.md) and walk back through Chapter 5's Part 3 (Configure ArgoCD) and Part 5 (Test the Complete Flow) before continuing.

## Verification checklist

### 1. Run the shared environment check

The cluster, Metrics Server, ArgoCD, the ApplicationSet, the `host.docker.internal` bridge, and your GitHub PAT are all checked by the shared script from [`00-cluster-setup`](../../00-cluster-setup/README.md):

```bash
GITHUB_USERNAME=your-username GITHUB_TOKEN=github_pat_... \
  ../../00-cluster-setup/verify.sh
```

Everything should report ✓ (the host-bridge check will warn unless Backstage is already running with `yarn start` — that's fine here; Lab 3 is the first lab that needs it).

> On Linux without Docker Desktop, `host.docker.internal` may not resolve. The simplest workaround is to run Backstage inside the same kind network or behind a NodePort. We do not cover that path here.

### 2. The GitOps loop produced at least one app

`verify.sh` confirms the ApplicationSet *exists*; this confirms it actually *shipped* something:

```bash
kubectl -n argocd get applications
# You should see my-first-app (or whatever you created in Chapter 5).
```

If this is empty, walk through [chapter-05/1-backstage-setup](../../chapter-05/1-backstage-setup/README.md) Part 5 first. The agent in Lab 1 will use this same ApplicationSet to ship itself, so it has to work.

The PAT (checked above) needs `Contents: read/write`, `Pull requests: read/write`, `Metadata: read-only` on the `backstage-components` repo — `gitops-mcp` uses it in Lab 2 to open PRs. That's the same permission set Chapter 5 already required.

### 3. LLM credentials

You have one of:

- **Bedrock (recommended):** `aws sts get-caller-identity` succeeds, and `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (or whatever model you used in Chapter 5 Lab 3) is enabled in the region you're using. If Claude Opus 4.7 is enabled in your account, you can use that instead — set `BEDROCK_MODEL_ID` in Lab 1.
- **Anthropic API:** an `ANTHROPIC_API_KEY` you can export.

You will set these as a Kubernetes Secret in Lab 1.

## What changes from Chapter 5

The Chapter 5 demo runs the chat loop **inside** Backstage as the `@aws/genai-plugin-for-backstage` plugin. That plugin stays installed and working — we do not remove it. The agent we build in Lab 1 is a **second** consumer of the platform, alongside the chat plugin, exposed as an HTTP service. You'll see the architecture shift live as you go.

## You're ready when

- `verify.sh` reports ✓ for the cluster, Metrics Server, ArgoCD, and the ApplicationSet, and the GitOps loop has shipped at least one app.
- You can describe in one sentence what the ArgoCD ApplicationSet does: *"It watches `*/argocd/application.yaml` files in `backstage-components` and creates an ArgoCD `Application` for each one."* That is the only deploy mechanism we will use in this chapter.

Move on to [Lab 1](../1-strands-runtime/README.md).

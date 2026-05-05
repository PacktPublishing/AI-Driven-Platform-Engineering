# Lab 0: Prerequisites

This lab does not deploy anything. It checks that the Chapter 5 stack is healthy and that your environment can reach the cluster the way the agent will need to in the next labs. If everything passes, move on to Lab 1.

## What you need from Chapter 5

You should already have, from Chapter 5:

1. A running Kubernetes cluster — we recommend **kind** for this chapter so the labs are reproducible offline. EKS or any other cluster works as long as it can pull container images and you can `kubectl apply`.
2. Backstage running on the host (`yarn start` in your `my-backstage-app` directory).
3. **ArgoCD** installed in the `argocd` namespace.
4. The `ApplicationSet` named `backstage-app-discovery` from [chapter-05/1-backstage-setup/files/argocd-applicationset.yaml](../../chapter-05/1-backstage-setup/files/argocd-applicationset.yaml) applied to the cluster.
5. A GitHub repository (the `backstage-components` repo from Chapter 5) that the ApplicationSet polls.
6. At least one app deployed through the GitOps flow (e.g., `my-first-app`). This is what proves the loop works.

## If you don't have a kind cluster yet

```bash
# Install kind if needed: https://kind.sigs.k8s.io/docs/user/quick-start/

cat <<EOF | kind create cluster --name agentic-platform --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 30080
    hostPort: 30080
    listenAddress: "127.0.0.1"
  - containerPort: 30443
    hostPort: 30443
    listenAddress: "127.0.0.1"
EOF
```

Then re-run Chapter 5's Part 3 (Install ArgoCD) and Part 5 (Test the Complete Flow) against this cluster before continuing.

## Verification checklist

Run each of these. They should all pass.

### 1. ArgoCD is running

```bash
kubectl -n argocd get pods
# Every pod should be Running.
```

### 2. The ApplicationSet exists

```bash
kubectl -n argocd get applicationset backstage-app-discovery
```

If this is missing, re-apply [chapter-05/1-backstage-setup/files/argocd-applicationset.yaml](../../chapter-05/1-backstage-setup/files/argocd-applicationset.yaml) (with `YOUR_USERNAME` replaced).

### 3. The GitOps loop produced at least one app

```bash
kubectl -n argocd get applications
# You should see my-first-app (or whatever you created in Chapter 5).
```

If this is empty, walk through [chapter-05/1-backstage-setup](../../chapter-05/1-backstage-setup/README.md) Part 5 first. The agent in Lab 1 will use this same ApplicationSet to ship itself, so it has to work.

### 4. Backstage on the host is reachable from the cluster

The agent will run in-cluster and call Backstage on your host machine. On kind, the bridge is `host.docker.internal`. Test it:

```bash
kubectl run -it --rm curl --image=curlimages/curl --restart=Never -- \
  curl -sS http://host.docker.internal:7007/api/catalog/entities -m 5 | head -c 200
```

If you see JSON (or an authentication error from Backstage), the bridge works. If you get `Could not resolve host`, your kind version may be too old; recreate the cluster with the latest `kind`.

> On Linux without Docker Desktop, `host.docker.internal` may not resolve. Either upgrade Docker, or pass `--network host` semantics differently — the simplest workaround is to run Backstage inside the same kind network or behind a NodePort. We do not cover that path here.

### 5. GitHub PAT is still valid

The PAT you created in [chapter-05/1-backstage-setup](../../chapter-05/1-backstage-setup/README.md) Step 2 is what `gitops-mcp` will use in Lab 2 to open PRs. Verify it still works:

```bash
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/YOUR_USERNAME/backstage-components | jq .full_name
# Expected: "YOUR_USERNAME/backstage-components"
```

The PAT needs `Contents: read/write`, `Pull requests: read/write`, `Metadata: read-only` on the `backstage-components` repo. That's the same permission set Chapter 5 already required.

### 6. LLM credentials

You have one of:

- **Bedrock (recommended):** `aws sts get-caller-identity` succeeds, and `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (or whatever model you used in Chapter 5 Lab 3) is enabled in the region you're using. If Claude Opus 4.7 is enabled in your account, you can use that instead — set `BEDROCK_MODEL_ID` in Lab 1.
- **Anthropic API:** an `ANTHROPIC_API_KEY` you can export.

You will set these as a Kubernetes Secret in Lab 1.

## What changes from Chapter 5

The Chapter 5 demo runs the chat loop **inside** Backstage as the `@aws/genai-plugin-for-backstage` plugin. That plugin stays installed and working — we do not remove it. The agent we build in Lab 1 is a **second** consumer of the platform, alongside the chat plugin, exposed as an HTTP service. You'll see the architecture shift live as you go.

## You're ready when

- All six checks above pass.
- You can describe in one sentence what the ArgoCD ApplicationSet does: *"It watches `*/argocd/application.yaml` files in `backstage-components` and creates an ArgoCD `Application` for each one."* That is the only deploy mechanism we will use in this chapter.

Move on to [Lab 1](../1-strands-runtime/README.md).

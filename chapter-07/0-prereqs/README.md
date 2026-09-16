# Lab 0: Prerequisites

Verify that the Chapter 5 platform, GitHub credential, and model access are ready for the agent labs. By the end, you will have confirmed that the cluster is reachable and `my-first-app` is deployed through ArgoCD.

## What you need from Chapter 5

- The kind cluster with Metrics Server, ArgoCD, and the `backstage-app-discovery` ApplicationSet.
- The existing Backstage app and a local clone of `backstage-components`.
- `my-first-app` deployed through GitOps in namespace `my-first-app`.
- The GitHub PAT in `argocd/github-creds`, with keys `url` (repository URL) and `password` (PAT). The PAT needs Contents and Pull requests read/write access. If you skipped this Secret for a public repository, complete [Chapter 5’s GitHub credential step](../../chapter-05/1-backstage-setup/README.md#step-5-configure-github-credentials-required-for-private-repos).

Also have Docker, kind, kubectl, curl, jq, Git, GitHub CLI, and either working Bedrock credentials with model access or an `ANTHROPIC_API_KEY`.

> [!NOTE]
> The labs reuse Chapter 5’s PAT. In production, use a dedicated token with least-privilege access to the components repository, keep ArgoCD’s credential read-only, and require PR reviews without agent bypass.

## Repository paths

Set these once in your terminal, using the paths to your local clones. The labs reuse them; repeat the exports in any new terminal.

```bash
export BOOK_REPO=/absolute/path/to/ai-driven-platform-engineering-book
export COMPONENTS_REPO=/absolute/path/to/backstage-components
export GITHUB_USERNAME="$(kubectl -n argocd get secret github-creds -o json \
  | jq -er '.data.url | @base64d | capture("^https://github\\.com/(?<owner>[A-Za-z0-9-]+)/").owner')"
: "${GITHUB_USERNAME:?Could not read the repository owner from argocd/github-creds}"
```

## Create the lab credentials

Create the namespace for the runtime credentials:

```bash
kubectl create namespace agent-platform --dry-run=client -o yaml | kubectl apply -f -
```

Create the model credential used by the runtime. Bedrock is the default:

```bash
kubectl create secret generic agent-llm-credentials \
  -n agent-platform --dry-run=client -o yaml \
  --from-literal=AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  --from-literal=AWS_REGION="${AWS_REGION:-us-west-2}" \
  | kubectl apply -f -
```

<details>
<summary>Anthropic alternative</summary>

Create the same Secret with this key and set `LLM_PROVIDER=anthropic` in the runtime Deployment:

```bash
kubectl create secret generic agent-llm-credentials \
  -n agent-platform --dry-run=client -o yaml \
  --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  | kubectl apply -f -
```

</details>

Export the Chapter 5 PAT and create the GitHub MCP credential. The token is never printed:

```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="$(kubectl -n argocd get secret github-creds -o json \
  | jq -er '.data.password | @base64d')"
: "${GITHUB_PERSONAL_ACCESS_TOKEN:?Could not read the GitHub token from argocd/github-creds}"
kubectl -n agent-platform create secret generic gitops-mcp-github \
  --from-literal=GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_PERSONAL_ACCESS_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -
```


## Verify

Run the shared checks:

```bash
"$BOOK_REPO/00-cluster-setup/verify.sh" --github-secret argocd/github-creds
kubectl -n argocd get applications
```

The script reads the repository and token from the Secret automatically. It checks repository read access; confirm write permissions separately. Expect the platform checks to pass and `my-first-app` to be Synced and Healthy. A Backstage connection warning is acceptable until Lab 4, when Backstage must be running and reachable from the cluster.

Continue to [Lab 1](../1-strands-runtime/README.md).

#!/usr/bin/env bash
#
# Delete the local kind cluster. This removes everything — ArgoCD, deployed
# apps, the agent, Langfuse, the RAG demo. Your Backstage app on the host and
# your GitHub repo are untouched.
#
# Usage: ./teardown.sh
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-agentic-platform}"

if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  echo "Deleting kind cluster '$CLUSTER_NAME'..."
  kind delete cluster --name "$CLUSTER_NAME"
  echo "Done."
else
  echo "No kind cluster named '$CLUSTER_NAME' found — nothing to do."
fi

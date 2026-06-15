#!/usr/bin/env bash
#
# Stand up the local cluster the whole book runs on:
#   - a kind cluster named "agentic-platform"
#   - the Kubernetes Metrics Server (needed for HPA in Chapter 5)
#   - ArgoCD (needed for the GitOps flow in Chapters 5 and 6)
#
# Safe to re-run: every step checks for existing state before acting.
#
# Usage:
#   ./setup-cluster.sh              # cluster + metrics-server + ArgoCD
#   SKIP_ARGOCD=1 ./setup-cluster.sh  # cluster + metrics-server only
#
# Requirements: docker, kind, kubectl (see README.md).
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-agentic-platform}"
ARGOCD_VERSION="${ARGOCD_VERSION:-v3.0.21}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }
ok()   { printf '\033[1;32m  ✓\033[0m %s\n' "$1"; }

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' not found on PATH. See README.md." >&2; exit 1; }
}

require docker
require kind
require kubectl

# 1) kind cluster -------------------------------------------------------------
if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
  ok "kind cluster '$CLUSTER_NAME' already exists"
else
  info "Creating kind cluster '$CLUSTER_NAME'"
  kind create cluster --name "$CLUSTER_NAME" --config "$SCRIPT_DIR/kind-config.yaml"
fi

kubectl cluster-info --context "kind-${CLUSTER_NAME}" >/dev/null
ok "kubectl context kind-${CLUSTER_NAME} is reachable"

# 2) Metrics Server -----------------------------------------------------------
# Required by the HPA shipped with the Chapter 5 web-app template.
# The --kubelet-insecure-tls patch is needed because kind's kubelet serving
# certs are self-signed.
if kubectl get deployment metrics-server -n kube-system >/dev/null 2>&1; then
  ok "metrics-server already installed"
else
  info "Installing metrics-server"
  kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
  kubectl patch deployment metrics-server -n kube-system --type='json' \
    -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
  kubectl rollout status deployment/metrics-server -n kube-system --timeout=180s
fi

# 3) ArgoCD -------------------------------------------------------------------
if [[ "${SKIP_ARGOCD:-0}" == "1" ]]; then
  info "SKIP_ARGOCD=1 set — skipping ArgoCD install"
else
  if kubectl get namespace argocd >/dev/null 2>&1; then
    ok "argocd namespace already exists"
  else
    info "Installing ArgoCD ${ARGOCD_VERSION}"
    kubectl create namespace argocd
    kubectl apply -n argocd -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"
  fi
  info "Waiting for ArgoCD server to be ready"
  kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
  ok "ArgoCD is ready"
fi

echo
info "Cluster '$CLUSTER_NAME' is up."
echo "Next:"
echo "  - Run ./verify.sh to sanity-check the environment."
if [[ "${SKIP_ARGOCD:-0}" != "1" ]]; then
  echo "  - ArgoCD admin password:"
  echo "      kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo"
  echo "  - Apply the ApplicationSet (replace YOUR_USERNAME first):"
  echo "      kubectl apply -f ../chapter-05/1-backstage-setup/files/argocd-applicationset.yaml"
fi

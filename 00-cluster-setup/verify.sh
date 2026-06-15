#!/usr/bin/env bash
#
# Sanity-check the local environment before starting a chapter's labs.
# This is the runnable version of the Chapter 6 "Lab 0 / Prerequisites" checks.
# It deploys nothing — it only reads state and reports pass/fail.
#
# Usage:
#   ./verify.sh                      # cluster + metrics-server + ArgoCD checks
#   GITHUB_USERNAME=me ./verify.sh   # also check the GitHub PAT against backstage-components
set -uo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-agentic-platform}"
fail=0

pass()  { printf '\033[1;32m  ✓\033[0m %s\n' "$1"; }
warn()  { printf '\033[1;33m  !\033[0m %s\n' "$1"; }
bad()   { printf '\033[1;31m  ✗\033[0m %s\n' "$1"; fail=1; }
group() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }

# 1) Cluster reachable --------------------------------------------------------
group "Cluster"
if kubectl cluster-info --context "kind-${CLUSTER_NAME}" >/dev/null 2>&1; then
  pass "kind-${CLUSTER_NAME} is reachable"
  kubectl config use-context "kind-${CLUSTER_NAME}" >/dev/null 2>&1
else
  bad "kind-${CLUSTER_NAME} is not reachable — run ./setup-cluster.sh"
  echo "Aborting further checks." && exit 1
fi

# 2) Metrics Server -----------------------------------------------------------
group "Metrics Server (HPA support)"
if kubectl get deployment metrics-server -n kube-system >/dev/null 2>&1; then
  if kubectl top nodes >/dev/null 2>&1; then
    pass "metrics-server is serving metrics"
  else
    warn "metrics-server installed but not serving yet (give it ~30s)"
  fi
else
  bad "metrics-server missing — run ./setup-cluster.sh"
fi

# 3) ArgoCD -------------------------------------------------------------------
group "ArgoCD"
if kubectl -n argocd get deployment argocd-server >/dev/null 2>&1; then
  not_running=$(kubectl -n argocd get pods --no-headers 2>/dev/null | grep -cv 'Running\|Completed' || true)
  if [[ "$not_running" == "0" ]]; then
    pass "all ArgoCD pods are Running"
  else
    warn "$not_running ArgoCD pod(s) not Running yet"
  fi
  if kubectl -n argocd get applicationset backstage-app-discovery >/dev/null 2>&1; then
    pass "ApplicationSet 'backstage-app-discovery' exists"
  else
    warn "ApplicationSet 'backstage-app-discovery' not applied yet (Chapter 5, Part 3)"
  fi
else
  bad "ArgoCD not installed — run ./setup-cluster.sh"
fi

# 4) Host bridge (agent in-cluster -> Backstage on host) ----------------------
group "Host bridge (host.docker.internal)"
# curl writes only the HTTP code to stdout (-s, no -S); on connection failure
# it prints nothing and the code is 000. Strip everything but the trailing digits.
bridge_raw=$(kubectl run verify-bridge --image=curlimages/curl --restart=Never -i --rm --quiet -- \
  curl -s -o /dev/null -w '%{http_code}' http://host.docker.internal:7007/api/catalog/entities -m 5 2>/dev/null || true)
code=$(printf '%s' "$bridge_raw" | tr -dc '0-9' | tail -c 3)
if [[ -n "$code" && "$code" != "000" ]]; then
  pass "host.docker.internal:7007 reachable from in-cluster (HTTP $code)"
else
  warn "could not reach Backstage on host.docker.internal:7007 — is 'yarn start' running? (only needed from Chapter 5 Lab 3)"
fi

# 5) GitHub PAT (optional) ----------------------------------------------------
group "GitHub PAT (optional)"
if [[ -n "${GITHUB_USERNAME:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
  repo=$(curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
    "https://api.github.com/repos/${GITHUB_USERNAME}/backstage-components" | grep -o '"full_name": *"[^"]*"' | head -1 || true)
  if [[ -n "$repo" ]]; then
    pass "PAT can read ${GITHUB_USERNAME}/backstage-components"
  else
    bad "PAT cannot read ${GITHUB_USERNAME}/backstage-components — check token scopes"
  fi
else
  warn "set GITHUB_USERNAME and GITHUB_TOKEN to check the PAT (needed from Chapter 5)"
fi

echo
if [[ "$fail" == "0" ]]; then
  printf '\033[1;32mEnvironment looks good.\033[0m\n'
else
  printf '\033[1;31mOne or more required checks failed — see ✗ above.\033[0m\n'
  exit 1
fi

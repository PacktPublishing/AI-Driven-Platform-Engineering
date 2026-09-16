#!/usr/bin/env bash
#
# Sanity-check the local environment before starting a chapter's labs.
# This is the runnable version of the Chapter 7 "Lab 0 / Prerequisites" checks.
# It deploys nothing — it only reads state and reports pass/fail.
#
# Usage:
#   ./verify.sh                      # cluster + metrics-server + ArgoCD checks
#   ./verify.sh --github-secret argocd/github-creds  # require this Secret
#   GITHUB_USERNAME=me GITHUB_TOKEN=... ./verify.sh  # optional override
set -uo pipefail

require_github=false
github_secret=argocd/github-creds
explicit_github_secret=false
usage() { printf 'Usage: %s [--github-secret NAMESPACE/NAME] [--require-github]\n' "$0"; }
while [[ $# -gt 0 ]]; do
  case "$1" in
    --github-secret)
      if [[ $# -lt 2 || ! "$2" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?/[a-z0-9]([a-z0-9.-]*[a-z0-9])?$ ]]; then
        printf 'Expected --github-secret NAMESPACE/NAME\n' >&2; exit 2
      fi
      github_secret="$2"
      explicit_github_secret=true
      require_github=true
      shift 2 ;;
    --require-github) require_github=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done
github_secret_namespace="${github_secret%%/*}"
github_secret_name="${github_secret#*/}"
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

# 5) An explicit Secret takes precedence over environment credentials.
group "GitHub credential"
(
  # Keep credentials local to this check; never trace or print their values.
  set +x
  token="${GITHUB_TOKEN:-}"
  repository="${GITHUB_USERNAME:+${GITHUB_USERNAME}/backstage-components}"
  if "$explicit_github_secret"; then
    token=""
    repository=""
  fi
  if [[ -z "$token" || -z "$repository" ]]; then
    if ! command -v jq >/dev/null 2>&1; then
      if "$require_github"; then bad "jq is required to read $github_secret"; exit 1; fi
      warn "install jq to check the Chapter 5 GitHub credential"; exit 0
    fi
    if ! credential=$(kubectl -n "$github_secret_namespace" get secret "$github_secret_name" -o json 2>/dev/null); then
      if "$require_github"; then bad "cannot read $github_secret; verify the Secret exists and you have access"; exit 1; fi
      warn "cannot read $github_secret; skipping GitHub check"; exit 0
    fi
    if [[ -z "$token" ]]; then
      token=$(printf '%s' "$credential" | jq -er '.data.password | select(type == "string" and length > 0) | @base64d') || exit 1
    fi
    if [[ -z "$repository" ]]; then
      repository=$(printf '%s' "$credential" | jq -er '.data.url | @base64d |
        capture("^https://github\\.com/(?<repo>[A-Za-z0-9-]+/[A-Za-z0-9_.-]+)/?$").repo |
        sub("\\.git$"; "")') || exit 1
    fi
    unset credential
  fi
  if [[ -z "$token" || ! "$repository" =~ ^[A-Za-z0-9-]+/[A-Za-z0-9_.-]+$ || "$token" == *$'\n'* || "$token" == *$'\r'* ]]; then
    bad "invalid GitHub token or repository configuration"; exit 1
  fi
  # Pass the Authorization header on stdin, not as a process argument.
  code=$(printf 'Authorization: Bearer %s\n' "$token" | curl -s --max-time 15 \
    --header @- -o /dev/null -w '%{http_code}' "https://api.github.com/repos/$repository") || code=000
  unset token
  if [[ "$code" == 200 ]]; then
    pass "GitHub credential can read $repository (write permissions must be confirmed separately)"
  else
    bad "GitHub repository check failed (HTTP $code); check token access and expiry"; exit 1
  fi
) || { bad "GitHub credential validation failed"; fail=1; }

echo
if [[ "$fail" == "0" ]]; then
  printf '\033[1;32mEnvironment looks good.\033[0m\n'
else
  printf '\033[1;31mOne or more required checks failed — see ✗ above.\033[0m\n'
  exit 1
fi

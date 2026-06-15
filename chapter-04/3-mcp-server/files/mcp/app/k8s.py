"""Live cluster queries, kept separate from the MCP wiring so the logic is
easy to read and test on its own.

The whole point of this lab: these functions return the state of the cluster
*right now*. There is no embedding, no snapshot, no staleness — every call hits
the Kubernetes API.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

from kubernetes import client, config


@dataclass
class DeploymentStatus:
    namespace: str
    name: str
    desired: int
    ready: int
    available: int
    healthy: bool
    owner: str
    # When unhealthy, the container waiting reasons we found on its pods
    # (e.g. "CrashLoopBackOff", "ImagePullBackOff") — the bridge back to RAG.
    pod_reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


_loaded = False


def _ensure_config() -> None:
    global _loaded
    if not _loaded:
        # Uses your local kubeconfig (the same context kubectl uses).
        config.load_kube_config()
        _loaded = True


def _pod_waiting_reasons(core: client.CoreV1Api, namespace: str, selector: str) -> list[str]:
    # A crash-looping container cycles through waiting (CrashLoopBackOff) ->
    # running -> terminated very quickly, so the current state alone is racy.
    # We also read last_state so the reason is reported even when we catch the
    # container in a brief "running" window between restarts.
    reasons: set[str] = set()
    pods = core.list_namespaced_pod(namespace, label_selector=selector)
    for pod in pods.items:
        for cs in (pod.status.container_statuses or []):
            for state in (cs.state, cs.last_state):
                if not state:
                    continue
                if state.waiting and state.waiting.reason:
                    reasons.add(state.waiting.reason)
                if state.terminated and state.terminated.reason:
                    reasons.add(state.terminated.reason)
    return sorted(reasons)


def list_deployments(namespace: str | None = None, only_unhealthy: bool = False) -> list[dict]:
    """Return the status of deployments in the cluster, live.

    namespace: limit to one namespace; None = all namespaces.
    only_unhealthy: return only deployments whose ready count < desired.
    """
    _ensure_config()
    apps = client.AppsV1Api()
    core = client.CoreV1Api()

    if namespace:
        deps = apps.list_namespaced_deployment(namespace).items
    else:
        deps = apps.list_deployment_for_all_namespaces().items

    results: list[DeploymentStatus] = []
    for d in deps:
        desired = d.spec.replicas or 0
        ready = d.status.ready_replicas or 0
        available = d.status.available_replicas or 0
        healthy = desired > 0 and ready >= desired
        owner = (d.metadata.labels or {}).get("owner", "unknown")

        reasons: list[str] = []
        if not healthy and d.spec.selector and d.spec.selector.match_labels:
            selector = ",".join(f"{k}={v}" for k, v in d.spec.selector.match_labels.items())
            try:
                reasons = _pod_waiting_reasons(core, d.metadata.namespace, selector)
            except client.ApiException:
                reasons = []

        results.append(
            DeploymentStatus(
                namespace=d.metadata.namespace,
                name=d.metadata.name,
                desired=desired,
                ready=ready,
                available=available,
                healthy=healthy,
                owner=owner,
                pod_reasons=reasons,
            )
        )

    if only_unhealthy:
        results = [r for r in results if not r.healthy]
    return [r.to_dict() for r in results]

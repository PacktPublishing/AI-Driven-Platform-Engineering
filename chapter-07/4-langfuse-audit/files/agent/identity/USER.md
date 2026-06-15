# User

This file holds preferences for the user (or team) the agent serves. It is loaded into the system prompt at startup. Edit it in the components repository — ArgoCD will redeploy the ConfigMap, and the next invocation will pick up the change.

## Default user

- The default invoker is the `guest` user from Chapter 5's Backstage setup.
- They own components in the `my-first-app` namespace and any namespace they create through the Backstage `Web App with Kubernetes Deployment` template.

## Conventions this user prefers

- Pull requests are titled `[agent] <verb> <resource> in <namespace>` (e.g., `[agent] scale checkout in my-first-app`).
- The PR body includes a short rationale and a link back to the conversation that produced it, when one is available.
- Replica counts above 5 require an explicit confirmation from the user before the agent opens a PR.

# Lab 1: Setting Up Backstage with GitOps

This lab covers creating a Backstage application with GitHub integration, ArgoCD for GitOps, and a Web App template that deploys to Kubernetes.

## Prerequisites

- **Node.js 22.x** (required by `isolated-vm`, a transitive dependency of the MCP actions backend used in Lab 4)
- **Yarn 4.x** (Backstage 0.7.x scaffolds use yarn 4 via Corepack — `corepack enable` if needed)
- GitHub account with a Personal Access Token (PAT)
- kubectl installed and configured
- A Kubernetes cluster (IF you want to use Amazon EKS see [Getting Started](https://docs.aws.amazon.com/eks/latest/userguide/getting-started.html)). You can also create a kind cluster for local testing.
- Metrics Server installed on your cluster (required for HPA)

### In case you want to use kind cluster for local testing

- Install [Docker](https://docs.docker.com/get-started/get-docker/)
- Install [kind](https://kind.sigs.k8s.io/docs/user/quick-start/)

```bash
# 

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

---

## Part 1: Create Backstage App

### Step 1: Create a New Backstage App

> **⚠️ Pin to `@backstage/create-app@0.7.9`.** The labs that follow rely on the legacy frontend system (`<FlatRoutes>` + `Root.tsx` with `<SidebarItem>`). Versions `0.8.x+` scaffold the new frontend system (`createApp({ features: [...] })`), and the Lab 2 / Lab 4 file edits will not apply.

```bash
npx @backstage/create-app@0.7.9

# When prompted, enter your app name (e.g., "my-backstage-app")
cd my-backstage-app
```

### Step 2: Pin Backstage package versions

The Backstage ecosystem moves quickly. As of this writing, releases `1.49.0+` declare a service ref `alpha.core.metrics` that no current factory provides — so plugins like `catalog-backend@3.5.0+`, `scaffolder-backend@3.4.0+`, and `mcp-actions-backend@0.1.10+` will fail to start with `Service or extension point dependencies of plugin 'X' are missing for the following ref(s): serviceRef{alpha.core.metrics}`.

To avoid this, pin the entire `@backstage/*` galaxy to release **1.48.0** via `yarn` resolutions. Open the root `package.json` and replace the existing `resolutions` block with the contents of [`files/package-resolutions.json`](./files/package-resolutions.json) — that file ships a coherent snapshot of all 193 `@backstage/*` packages plus the `@langchain/*` pins required by the chat plugin in Lab 2.

```bash
# From the root of your Backstage app:
# 1) open package.json in your editor
# 2) replace the "resolutions" block with the contents of:
cat ../ai-driven-platform-engineering/chapter-05/1-backstage-setup/files/package-resolutions.json
# (or pull it from the book repo and copy in)
```

Then install:

```bash
yarn install
```

### Step 3: Verify the Installation

```bash
NODE_OPTIONS=--no-node-snapshot yarn start
```

Open `http://localhost:3000` - you should see the Backstage welcome page.

---

## Part 2: Configure GitHub Integration

### Step 1: Create a GitHub Repository

Create a new repository on GitHub (e.g., `backstage-components`) that will store components created from Backstage templates. This repository can be private.

**Important:** Initialize the repository with a README file (check "Add a README file" when creating, or add one manually). The repository cannot be empty - Backstage needs at least one commit to create pull requests.

### Step 2: Create a GitHub Personal Access Token

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Configure the token:
   - **Token name:** backstage-token (or any name you prefer)
   - **Expiration:** Choose an appropriate expiration
   - **Repository access:** Select "Only select repositories" and choose the repository you created for Backstage components (e.g., `backstage-components`)
4. Set the following permissions:
   - **Actions:** Read-only
   - **Commit statuses:** Read-only
   - **Contents:** Read and write
   - **Issues:** Read and write
   - **Metadata:** Read-only (automatically selected)
   - **Pull requests:** Read and write
5. Click "Generate token" and copy it

### Step 3: Configure Backstage

The `app-config.yaml` already includes the GitHub integration that reads the token from an environment variable:

```yaml
integrations:
  github:
    - host: github.com
      token: ${GITHUB_TOKEN}
```

Add your token to `app-config.local.yaml` (this file is gitignored):

```yaml
integrations:
  github:
    - host: github.com
      token: github_pat_your_token_here
```

---

## Part 3: Install ArgoCD

> **Note:** We're installing ArgoCD manually for this tutorial. If you're using Amazon EKS, we recommend checking out the [EKS Capabilities](https://docs.aws.amazon.com/eks/latest/userguide/capabilities.html) with the managed ArgoCD feature.

### Step 1: Install ArgoCD on Your Cluster

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v3.0.21/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
```

### Step 2: Get Admin Password

```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### Step 3: Access ArgoCD UI (Optional)

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Open https://localhost:8080 (username: `admin`, password from Step 2)

### Step 4: Create ApplicationSet for Auto-Discovery

Edit the file `files/argocd-applicationset.yaml` and replace `YOUR_USERNAME` with your GitHub username to reflect the GitHub repository you just created and then apply:

```bash
kubectl apply -f files/argocd-applicationset.yaml
```

### Step 5: Configure GitHub Credentials (Required for Private Repos)

If your `backstage-components` repository is private, ArgoCD needs credentials to access it:

```bash
# Create a repository secret with your GitHub credentials (replace YOUR_USERNAME and token)
kubectl create secret generic github-creds -n argocd \
  --from-literal=type=git \
  --from-literal=url=https://github.com/YOUR_USERNAME/backstage-components \
  --from-literal=username=YOUR_USERNAME \
  --from-literal=password=github_pat_your_token_here

# Label it so ArgoCD recognizes it as a repository secret
kubectl label secret github-creds -n argocd argocd.argoproj.io/secret-type=repository
```

> **Tip:** You can reuse the same GitHub token you created for Backstage.

---

## Part 4: Add the Web App Template

### Step 1: Copy the Template to Your Backstage App

Copy the `files/webapp-template/` folder to your Backstage app's `examples/` directory:

```bash
cp -r files/webapp-template/ /path/to/my-backstage-app/examples/webapp-template/
```

Your Backstage app should now have:

```
my-backstage-app/
└── examples/
    └── webapp-template/
        ├── template.yaml
        └── content/
            ├── catalog-info.yaml
            ├── README.md
            ├── argocd/
            │   └── application.yaml
            └── k8s/
                ├── configmap.yaml
                ├── deployment.yaml
                ├── hpa.yaml
                └── service.yaml
```

### Step 2: Register the Template in Backstage

Add to `app-config.yaml`:

```yaml
catalog:
  locations:
    # ... existing locations ...

    # Web App Kubernetes template
    - type: file
      target: ../../examples/webapp-template/template.yaml
      rules:
        - allow: [Template]

    # Auto-discover components from GitHub (replace YOUR_USERNAME)
    - type: url
      target: https://github.com/YOUR_USERNAME/backstage-components/blob/main/*/catalog-info.yaml
      rules:
        - allow: [Component]
```

> Replace `YOUR_USERNAME` with your GitHub username.

---

## Part 5: Test the Complete Flow

### Step 1: Start Backstage

```bash
NODE_OPTIONS=--no-node-snapshot yarn start
```

### Step 2: Create a New Web App

1. Open `http://localhost:3000`
2. Click "Create..." in the sidebar
3. Select "Web App with Kubernetes Deployment"
4. Fill in the form (you will need to click Next to see all fields):
   - **Name:** `my-first-app`
   - **Description:** `My first Backstage-deployed app`
   - **Owner:** Keep `user:default/guest` for now
   - **Namespace:** `my-first-app` (change from default)
   - **GitHub Owner:** Your GitHub username 
   - **Repository Name:** `backstage-components` (or the repository name you created earlier)
5. Click "Create"

### Step 3: Merge the Pull Request

1. Go to your GitHub repository
2. Review and merge the Pull Request created by Backstage

### Step 4: Watch ArgoCD Deploy

> **Note:** ArgoCD's ApplicationSet controller polls for changes every 3 minutes by default. After merging the PR, it may take up to 3 minutes for the application to appear.

```bash
# Check ArgoCD applications (may take a few minutes to appear)
kubectl get applications -n argocd

# Watch the deployment once the application is created
kubectl get pods -n my-first-app -w
```

You can also monitor progress in the ArgoCD UI:
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
Then open https://localhost:8080 (username: `admin`, password from Part 3 Step 2).

### Step 5: Access the Application

```bash
kubectl port-forward svc/my-first-app 8080:80 -n my-first-app
```

Open http://localhost:8080 to see your deployed application!

---

## Summary

You now have:
- ✅ Backstage with GitHub integration
- ✅ ArgoCD with auto-discovery ApplicationSet
- ✅ Web App template for GitOps deployments
- ✅ Complete flow: Template → PR → Merge → Auto-deploy

**Next Steps**: In Lab 2, we'll add the AI Chat Assistant.

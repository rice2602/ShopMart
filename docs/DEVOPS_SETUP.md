# DevOps & Local Kubernetes Deployment Guide

This guide provides instructions to run the containerized ShopMart Observability Web Dashboard locally in a Kubernetes environment using Minikube and configure it with ArgoCD for GitOps deployment syncs.

---

## Prerequisites
1. [Minikube](https://minikube.sigs.k8s.io/) or [Kind](https://kind.sigs.k8s.io/) installed locally.
2. [kubectl](https://kubernetes.io/docs/tasks/tools/) CLI tool.
3. [Docker](https://www.docker.com/) running locally.

---

## Step 1: Start Minikube & Enable Ingress
Initialize your local Kubernetes cluster and enable the NGINX Ingress Controller addon:
```bash
minikube start --driver=docker
minikube addons enable ingress
```

---

## Step 2: Configure Local Docker Environment
Configure your terminal shell to use the Docker daemon inside Minikube. This allows you to build container images directly into the Kubernetes cluster registry without pushing them to an external registry:

*   **Windows PowerShell:**
    ```powershell
    & minikube -p minikube docker-env | Invoke-Expression
    ```
*   **macOS / Linux Bash:**
    ```bash
    eval $(minikube -p minikube docker-env)
    ```

---

## Step 3: Build the Observability App Image
Navigate to the directory containing the Dockerfile and build the container image:
```bash
cd devops/observability-app
docker build -t shopmart-observability:latest .
```

---

## Step 4: Deploy Manifests to Kubernetes
Apply the unified configuration manifest to deploy the ConfigMap, Service, Deployment, Ingress routing, and Horizontal Pod Autoscaler (HPA):
```bash
cd ../k8s
kubectl apply -f shopmart-observability.yaml
```

Verify that all resources are initialized and running:
```bash
kubectl get all
kubectl get hpa
```

---

## Step 5: Configure Host Routing
To access the application through the Ingress controller hostname, add a host routing mapping.

1. Open your hosts file (`C:\Windows\System32\drivers\etc\hosts` on Windows or `/etc/hosts` on Unix) as administrator/sudo.
2. Append the following entry:
   ```text
   127.0.0.1  shopmart.local
   ```
3. Start the Minikube network tunnel in a separate, active terminal session:
   ```bash
   minikube tunnel
   ```
4. Open your browser and navigate to: `http://shopmart.local`

---

## Step 6: GitOps Application Deployment with ArgoCD
To practice GitOps practices by syncing your Kubernetes manifests directly from your remote Git repository:

1. **Install ArgoCD:**
   ```bash
   kubectl create namespace argocd
   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
   ```
2. **Define the Application Manifest:**
   Save the following specification as `argocd-app.yaml` (replace `<your-username>` with your GitHub repository URL):
   ```yaml
   apiVersion: argoproj.io/v1alpha1
   kind: Application
   metadata:
     name: shopmart-observability
     namespace: argocd
   spec:
     project: default
     source:
       repoURL: 'https://github.com/<your-username>/ShopMart.git'
       targetRevision: HEAD
       path: devops/k8s
     destination:
       server: 'https://kubernetes.default.svc'
       namespace: default
     syncPolicy:
       automated:
         prune: true
         selfHeal: true
   ```
3. **Apply the Application Configuration:**
   ```bash
   kubectl apply -f argocd-app.yaml
   ```
   ArgoCD will monitor your repository and automatically redeploy the pod replicas whenever changes are committed to your Kubernetes config files.

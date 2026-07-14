# ShopMart Sales Data Pipeline & DevOps Platform

An automated, serverless data pipeline on AWS built with Python, Terraform, GitHub Actions, Docker, and Kubernetes. This repository is designed to demonstrate cloud architecture, event-driven data engineering, infrastructure automation (IaC), CI/CD pipelines, and cloud observability dashboard deployments.

---

## Project Structure

```text
ShopMart/
├── .github/                  # GitHub Actions Workflows & Templates
│   ├── workflows/
│   │   ├── ci.yml            # CI: linting, python unit testing, terraform checks
│   │   └── cd.yml            # CD: AWS Lambda deployment, terraform provisions
│   └── pull_request_template.md
│
├── data/                     # Local Simulation Storage
│   ├── raw/                  # Simulates incoming POS CSV drops
│   ├── processed/            # Cleaned data in date-partitioned Parquet format
│   └── quarantine/           # Isolated corrupted data and validation logs
│
├── devops/                   # Containerized Observability Microservices
│   ├── k8s/
│   │   └── shopmart-observability.yaml  # Unified K8s configurations
│   └── observability-app/
│       ├── templates/        # Dashboard HTML interface
│       ├── app.py            # Flask telemetry collector & simulator
│       ├── Dockerfile        # Container image build file
│       └── requirements.txt
│
├── docs/                     # Guides and Architectural Specifications
│   ├── ARCHITECTURE.md       # Diagram, 3 ADRs, and 3 Failure Scenarios
│   ├── AWS_SETUP.md          # Manual AWS Management Console walk-through
│   └── DEVOPS_SETUP.md       # Local Kubernetes (Minikube) & ArgoCD GitOps guide
│
├── iac/                      # Infrastructure as Code (Terraform)
│   ├── main.tf               # Provisions S3 buckets, DynamoDB, SNS, IAM, Lambda
│   ├── variables.tf          # Terraform customization inputs
│   └── outputs.tf            # Deployment telemetry attributes
│
├── src/                      # Core Code
│   └── pipeline.py           # ETL ingestion, cleaning, validation, and AWS handler
│
├── tests/                    # Quality Assurance Suite
│   └── test_pipeline.py      # 6 Pytest automated validation cases
│
└── README.md                 # Project entry point
```

---

## Detailed Documentation Guides

To explore individual sections of the project, refer to these guides:
*   [Architecture Design Document](docs/ARCHITECTURE.md): System layout, Data lifecycle, 3 ADRs, and 3 Failure scenarios.
*   [AWS Console Hands-On Guide](docs/AWS_SETUP.md): Step-by-step setup of S3, DynamoDB, SNS, IAM, Lambda, and Athena on the AWS Management Console (Free Tier compliant).
*   [DevOps & Kubernetes Guide](docs/DEVOPS_SETUP.md): Running the observability dashboard inside Minikube/Kind and GitOps deployment via ArgoCD.

---

## Quickstart Instructions

### 1. Run Automated Ingestion Tests
Ensure Python 3.11 is installed, install dependencies, and execute the test runner:
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest -v
```

### 2. Run Local Observability Dashboard
To start the Flask monitoring application and simulate CSV data ingestion:
```bash
# Run server
python devops/observability-app/app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser. Click **Simulate Happy Upload** to generate test data files and trigger the pipeline.

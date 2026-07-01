import os
import json

def generate_devops_config(config_type: str, project_dir: str, params: dict = None) -> dict:
    """
    Generates industry-standard, production-ready DevOps configuration files
    for Docker, AWS, Kafka, Kubernetes, and CI/CD pipelines.
    """
    os.makedirs(project_dir, exist_ok=True)
    if params is None:
        params = {}

    app_name = params.get("app_name", "my-app").lower().replace(" ", "-")
    port = params.get("port", 3000)
    db_type = params.get("db_type", "postgresql")
    aws_region = params.get("aws_region", "us-east-1")
    ecr_registry = params.get("ecr_registry", "123456789012.dkr.ecr.us-east-1.amazonaws.com")
    kafka_topic = params.get("kafka_topic", "telemetry-events")
    
    generated_files = []

    if config_type == "docker":
        # 1. Multi-stage Production Dockerfile (Node/Next.js default)
        dockerfile_content = f"""# --- Stage 1: Build ---
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# --- Stage 2: Production Run ---
FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/package.json ./package.json

USER nextjs
EXPOSE {port}
ENV PORT {port}
CMD ["node", "server.js"]
"""
        # 2. Docker Compose with App, DB, and local Kafka cluster (KRaft mode)
        compose_content = f"""version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "{port}:{port}"
    environment:
      - PORT={port}
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/postgres
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
    depends_on:
      - db
      - kafka

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  # Kafka with KRaft (no Zookeeper needed, modern & fast!)
  kafka:
    image: confluentinc/cp-kafka:7.4.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: 'CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT'
      KAFKA_ADVERTISED_LISTENERS: 'PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:29092'
      KAFKA_OFFICES_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_PROCESS_ROLES: 'broker,controller'
      KAFKA_CONTROLLER_QUORUM_VOTERS: '1@kafka:29093'
      KAFKA_LISTENERS: 'PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:29093,PLAINTEXT_HOST://0.0.0.0:29092'
      KAFKA_INTER_BROKER_LISTENER_NAME: 'PLAINTEXT'
      KAFKA_CONTROLLER_LISTENER_NAMES: 'CONTROLLER'
      KAFKA_LOG_DIRS: '/tmp/kraft-combined-logs'
      CLUSTER_ID: 'MkU3OEVBNTcwNTJENDM2Qk'

volumes:
  pgdata:
"""
        dockerignore_content = """node_modules
.next
out
build
.git
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
npm-debug.log*
yarn-debug.log*
yarn-error.log*
"""
        with open(os.path.join(project_dir, "Dockerfile"), "w") as f:
            f.write(dockerfile_content)
        with open(os.path.join(project_dir, "docker-compose.yml"), "w") as f:
            f.write(compose_content)
        with open(os.path.join(project_dir, ".dockerignore"), "w") as f:
            f.write(dockerignore_content)
            
        generated_files.extend(["Dockerfile", "docker-compose.yml", ".dockerignore"])

    elif config_type == "kubernetes":
        # Production-grade K8s manifests (Deployment, Service, Ingress, ConfigMap)
        k8s_deployment = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_name}
  labels:
    app: {app_name}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
      - name: {app_name}
        image: {ecr_registry}/{app_name}:latest
        ports:
        - containerPort: {port}
        resources:
          limits:
            cpu: "500m"
            memory: "512Mi"
          requests:
            cpu: "250m"
            memory: "256Mi"
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1001
        readinessProbe:
          httpGet:
            path: /api/health
            port: {port}
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /api/health
            port: {port}
          initialDelaySeconds: 15
          periodSeconds: 10
        envFrom:
        - configMapRef:
            name: {app_name}-config
---
apiVersion: v1
kind: Service
metadata:
  name: {app_name}-service
spec:
  selector:
    app: {app_name}
  ports:
  - protocol: TCP
    port: 80
    targetPort: {port}
  type: ClusterIP
"""
        k8s_ingress = f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app_name}-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - {app_name}.example.com
    secretName: {app_name}-tls
  rules:
  - host: {app_name}.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: {app_name}-service
            port:
              number: 80
"""
        k8s_configmap = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {app_name}-config
data:
  NODE_ENV: "production"
  PORT: "{port}"
  KAFKA_BOOTSTRAP_SERVERS: "kafka-service:9092"
"""
        # Strimzi Kafka Operator deploy manifest for K8s
        k8s_kafka = f"""apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: devops-kafka
spec:
  kafka:
    version: 3.4.0
    replicas: 3
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
      - name: tls
        port: 9093
        type: internal
        tls: true
    config:
      offsets.topic.replication.factor: 3
      transaction.state.log.replication.factor: 3
      transaction.state.log.min.isr: 2
      default.replication.factor: 3
      min.insync.replicas: 2
      inter.broker.listener.name: plain
    storage:
      type: persistent-claim
      size: 100Gi
      class: gp2
  zookeeper:
    replicas: 3
    storage:
      type: persistent-claim
      size: 10Gi
      class: gp2
  entityOperator:
    topicOperator: {{}}
    userOperator: {{}}
---
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: {kafka_topic}
  labels:
    strimzi.io/cluster: devops-kafka
spec:
  partitions: 3
  replications: 3
  config:
    retention.ms: 7200000
    segment.bytes: 1073741824
"""
        k8s_dir = os.path.join(project_dir, "kubernetes")
        os.makedirs(k8s_dir, exist_ok=True)
        
        with open(os.path.join(k8s_dir, "deployment.yaml"), "w") as f:
            f.write(k8s_deployment)
        with open(os.path.join(k8s_dir, "ingress.yaml"), "w") as f:
            f.write(k8s_ingress)
        with open(os.path.join(k8s_dir, "configmap.yaml"), "w") as f:
            f.write(k8s_configmap)
        with open(os.path.join(k8s_dir, "kafka.yaml"), "w") as f:
            f.write(k8s_kafka)
            
        generated_files.extend(["kubernetes/deployment.yaml", "kubernetes/ingress.yaml", "kubernetes/configmap.yaml", "kubernetes/kafka.yaml"])

    elif config_type == "aws":
        # Terraform AWS provision EKS, VPC, ECR
        tf_vpc = f"""provider "aws" {{
  region = "{aws_region}"
}}

module "vpc" {{
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "{app_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["{aws_region}a", "{aws_region}b", "{aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = true

  tags = {{
    Environment = "production"
    Application = "{app_name}"
  }}
}}
"""
        tf_eks = f"""module "eks" {{
  source  = "terraform-aws-modules/eks/aws"
  version = "19.15.0"

  cluster_name    = "{app_name}-eks-cluster"
  cluster_version = "1.27"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {{
    primary = {{
      min_size     = 2
      max_size     = 5
      desired_size = 3

      instance_types = ["t3.medium"]
      capacity_type  = "ON_DEMAND"
    }}
  }}

  tags = {{
    Environment = "production"
    Application = "{app_name}"
  }}
}}
"""
        tf_ecr = f"""resource "aws_ecr_repository" "app_repo" {{
  name                 = "{app_name}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {{
    scan_on_push = true
  }}

  tags = {{
    Environment = "production"
    Application = "{app_name}"
  }}
}}
"""
        terraform_dir = os.path.join(project_dir, "terraform")
        os.makedirs(terraform_dir, exist_ok=True)
        
        with open(os.path.join(terraform_dir, "vpc.tf"), "w") as f:
            f.write(tf_vpc)
        with open(os.path.join(terraform_dir, "eks.tf"), "w") as f:
            f.write(tf_eks)
        with open(os.path.join(terraform_dir, "ecr.tf"), "w") as f:
            f.write(tf_ecr)
            
        generated_files.extend(["terraform/vpc.tf", "terraform/eks.tf", "terraform/ecr.tf"])

    elif config_type == "cicd":
        # Production-grade GitHub Actions CI/CD pipeline
        github_action = f"""name: CI/CD Production Deployment

on:
  push:
    branches: [ main ]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout Code
      uses: actions/checkout@v3

    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'

    - name: Install Dependencies
      run: npm ci

    - name: Run Linter
      run: npm run lint --if-present

    - name: Run Tests
      run: npm test --if-present

  build-and-push-docker:
    needs: build-and-test
    runs-on: ubuntu-latest
    steps:
    - name: Checkout Code
      uses: actions/checkout@v3

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{{{ secrets.AWS_ACCESS_KEY_ID }}}}
        aws-secret-access-key: ${{{{ secrets.AWS_SECRET_ACCESS_KEY }}}}
        aws-region: {aws_region}

    - name: Log in to AWS ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1

    - name: Build, tag, and push image to AWS ECR
      env:
        ECR_REGISTRY: {ecr_registry}
        ECR_REPOSITORY: {app_name}
        IMAGE_TAG: ${{{{ github.sha }}}}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG -t $ECR_REGISTRY/$ECR_REPOSITORY:latest .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest

  deploy-to-k8s:
    needs: build-and-push-docker
    runs-on: ubuntu-latest
    steps:
    - name: Checkout Code
      uses: actions/checkout@v3

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{{{ secrets.AWS_ACCESS_KEY_ID }}}}
        aws-secret-access-key: ${{{{ secrets.AWS_SECRET_ACCESS_KEY }}}}
        aws-region: {aws_region}

    - name: Update Kubeconfig
      run: aws eks update-kubeconfig --name {app_name}-eks-cluster --region {aws_region}

    - name: Deploy Manifests to EKS
      run: |
        kubectl apply -f kubernetes/configmap.yaml
        kubectl apply -f kubernetes/deployment.yaml
        kubectl apply -f kubernetes/ingress.yaml
        # Dynamically update container image tag to trigger rolling update
        kubectl set image deployment/{app_name} {app_name}={ecr_registry}/{app_name}:${{{{ github.sha }}}}
"""
        github_dir = os.path.join(project_dir, ".github", "workflows")
        os.makedirs(github_dir, exist_ok=True)
        
        with open(os.path.join(github_dir, "ci-cd.yml"), "w") as f:
            f.write(github_action)
            
        generated_files.extend([".github/workflows/ci-cd.yml"])

    return {
        "success": True,
        "config_type": config_type,
        "project_dir": project_dir,
        "files_created": generated_files,
        "message": f"Successfully created {len(generated_files)} production-grade {config_type.upper()} configuration files."
    }

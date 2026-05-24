# HoneyManager MVP (Minimum Viable Product)

**Course:** CENG433 - Cloud Computing  
**Team Members:** Sina Erdem Özdemir - 21050151019, Bilge Oğuz - 21050151023    
**Demo Video:** [Insert Unlisted YouTube Link Here]  
**GitHub Repository:** https://github.com/SinaErdem/HoneyManager-MVP/tree/main/HoneyManager-MVP

This project is a simplified, cloud-native prototype (MVP) of the distributed honeypot management system, HoneyManager, developed for a Cloud Computing course assignment. It is designed in strict adherence to the **12-Factor App** principles.

## 1. Architectural Design and 12-Factor App Compliance

The project is designed according to the microservices architecture to ensure high availability and scalability in a cloud environment. The system consists of three main components:

1.  **Stateless API (Flask + SQLAlchemy):** A central REST API that receives incoming cyber attack logs and writes them to the database. **(Statelessness Principle)**
2.  **Sensor (Python Script):** An independent component that asynchronously POSTs mock honeypot data (e.g., SSH Brute Force attempts) to the central API at regular intervals.
3.  **Database (PostgreSQL):** The central log storage unit.

### How 12-Factor App Principles Were Applied
*   **I. Codebase:** All services are managed within a single codebase but in isolated subdirectories (`api/`, `sensor/`).
*   **III. Config:** No sensitive data (database passwords, API endpoints, etc.) is hard-coded within the source code. All configuration is injected from the outside via *Environment Variables* (`.env`).
*   **VI. Processes:** The API application (Flask/Gunicorn) is designed to be completely *stateless*. It does not store any data on the local file system; all persistent data is stored on the backend PostgreSQL (Backing Service).
*   **VII. Port Binding:** The Flask application exposes its own port (5000) as an independent web service.
*   **XI. Logs:** Application logs are treated as event streams and printed to the standard output (stdout/stderr).

---

## 2. Local Environment Setup

The project is configured with `docker-compose` for local testing.

```bash
# To spin up the services:
docker-compose up --build -d

# To verify the API is running:
# http://localhost:5000/api/health

# To view the collected logs:
# http://localhost:5000/api/logs

# To monitor the sensor logs:
docker-compose logs -f sensor
```

---

## 3. AWS Deployment Guide

Deploying this architecture on AWS (Amazon Web Services) using fully-managed services involves the following steps:

### Step 1: Database Infrastructure (AWS RDS)
**Amazon RDS for PostgreSQL** will be used as the persistent data storage unit for our stateless architecture.
1.  Navigate to the RDS service via the AWS Console.
2.  Create a new PostgreSQL instance (e.g., `db.t3.micro`).
3.  Note down the **Endpoint URL**, username, and password of the created RDS instance. This information will be provided to our API service as Environment Variables.

### Step 2: Storing Container Images (AWS ECR)
The Docker images for our API and Sensor services must be built and uploaded to the AWS Elastic Container Registry.
```bash
# Login to ECR (requires AWS CLI)
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.<region>.amazonaws.com

# Create repositories for API and Sensor in ECR
aws ecr create-repository --repository-name honeymanager-api
aws ecr create-repository --repository-name honeymanager-sensor

# Tag and push the images to ECR
docker build -t honeymanager-api ./api
docker tag honeymanager-api:latest <aws_account_id>.dkr.ecr.<region>.amazonaws.com/honeymanager-api:latest
docker push <aws_account_id>.dkr.ecr.<region>.amazonaws.com/honeymanager-api:latest

# Repeat the same build and push process for the Sensor.
```

### Step 3: Running the Applications (AWS ECS - Fargate)
To avoid server management (EC2), the applications will be run on **AWS ECS (Elastic Container Service)** using the serverless compute engine, **AWS Fargate**.
1.  **Creating a Task Definition:**
    *   **API Task:** Select the API image pushed to ECR. Enter the RDS details in the Environment Variables section: `DATABASE_URL = postgresql://<user>:<password>@<rds_endpoint>:5432/postgres`. Set Port Mapping to 5000.
    *   **Sensor Task:** Select the Sensor image pushed to ECR. Enter the API's address in the Environment Variables section: `API_URL = http://<api_load_balancer_dns>:5000/api/logs`.
2.  **Creating a Cluster and Service:**
    *   Create a Cluster on ECS.
    *   Launch the API Task as a Service and place an **Application Load Balancer (ALB)** in front of it for external access.
    *   Launch the Sensor Task as a separate Service within the same Cluster.

*Alternative (Simpler Deployment): To quickly spin up just the API, you can also use the **AWS App Runner** service directly from a GitHub repo or ECR. App Runner automatically handles the Load Balancer and SSL certification.*

### Security and Networking
*   **Security Groups:** The RDS instance should be locked down to only allow traffic on port 5432 coming from the ECS Cluster or the VPC where the API resides. External access to the database must be completely blocked.
*   Only port 80 (HTTP) or 443 (HTTPS) of the Application Load Balancer should be open to the outside world.

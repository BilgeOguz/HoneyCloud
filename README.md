
# HoneyCloud MVP

**Course:** CENG433 - Cloud Computing
**Team Members:** Sina Erdem Özdemir - 21050151019, Bilge Oğuz - 21050151023
**Demo Video:** [Insert Unlisted YouTube Link Here]
**GitHub Repository:** [https://github.com/BilgeOguz/HoneyCloud]

A cloud-native distributed honeypot management system built as an MVP for a Cloud Computing course assignment. The system simulates vulnerable services, attracts malicious network traffic, and ingests/stores attack logs in real time. Designed in strict adherence to the **12-Factor App** methodology.

---

## Architecture Overview

The system consists of three main services:

1. **API** (`api/`) — Stateless Flask REST API that receives attack logs and writes them to PostgreSQL. Exposes a Prometheus `/metrics` endpoint and serves cached responses via Redis.
2. **Sensor** (`sensor/`) — Independent Python process that simulates honeypot nodes by POSTing mock attack events to the API at regular intervals.
3. **Database** — PostgreSQL, running locally via Docker or on AWS RDS in production.

```
[Sensor] --POST /api/logs--> [Flask API] --> [PostgreSQL (RDS)]
                                   |
                              [Redis Cache]
                              [Prometheus /metrics]
                              [Filebeat --> Logstash --> Elasticsearch --> Kibana]
```

---

## Technology Stack

| Component  | Technology                              |
|------------|-----------------------------------------|
| Language   | Python 3.11, Flask 3.0, Gunicorn        |
| Database   | PostgreSQL 15 — AWS RDS in production   |
| Deployment | Docker, AWS ECS Fargate, ALB            |
| CI/CD      | GitHub Actions                          |
| Caching    | Redis 7 — AWS ElastiCache in production |
| Monitoring | Prometheus + prometheus-flask-exporter  |
| Logging    | ELK Stack (Filebeat → Logstash → Elasticsearch → Kibana) |

---

## 12-Factor App Compliance

| # | Factor | Implementation |
|---|--------|----------------|
| I | Codebase | Single Git repo, services isolated in `api/` and `sensor/` |
| II | Dependencies | Pinned in `requirements.txt` for each service |
| III | Config | All config via environment variables — no hardcoded secrets |
| IV | Backing services | PostgreSQL and Redis treated as attached resources via URLs |
| V | Build / release / run | Docker builds the image; GitHub Actions automates the release |
| VI | Processes | Flask is fully stateless — all state lives in PostgreSQL |
| VII | Port binding | Gunicorn binds the port; no external web server required |
| VIII | Concurrency | ECS Fargate scales task count horizontally |
| IX | Disposability | Gunicorn handles fast startup; SIGTERM triggers graceful shutdown |
| X | Dev/prod parity | `docker-compose` uses the same `postgres:15` image as RDS |
| XI | Logs | JSON-structured logs streamed to stdout, collected by Filebeat |
| XII | Admin processes | `db.create_all()` runs as a one-off task at container startup |

---

## Local Setup

### Prerequisites

- Docker and Docker Compose
- Git

### Run locally

```bash
# Clone the repo
git clone https://github.com/SinaErdem/HoneyCloud-MVP.git
cd HoneyCloud-MVP

# Copy environment config
cp .env.example .env

# Start all services (API, Sensor, PostgreSQL, Redis, ELK stack)
docker-compose up --build -d

# Check API health
curl http://localhost:5000/api/health

# View recent attack logs
curl http://localhost:5000/api/logs

# View Prometheus metrics
curl http://localhost:5000/metrics

# Open Kibana dashboard
open http://localhost:5601
```

### Monitor sensor activity

```bash
docker-compose logs -f sensor
```

---

## Project Structure

```
HoneyCloud-MVP/
├── api/
│   ├── app.py              # Flask application factory
│   ├── models.py           # SQLAlchemy Alert model
│   ├── requirements.txt    # API dependencies
│   ├── Dockerfile
│   └── tests/
│       └── test_health.py  # Pytest test suite
├── sensor/
│   ├── sensor.py           # Mock honeypot data generator
│   ├── requirements.txt
│   └── Dockerfile
├── .github/
│   └── workflows/
│       └── ci.yml          # GitHub Actions CI/CD pipeline
├── filebeat.yml            # Filebeat config — ships logs to Logstash
├── logstash.conf           # Logstash pipeline config
├── docker-compose.yml      # Full local environment
└── .env.example            # Environment variable template
```

---

## Environment Variables

| Variable        | Description                          | Example                                           |
|-----------------|--------------------------------------|---------------------------------------------------|
| `DATABASE_URL`  | PostgreSQL connection string         | `postgresql://postgres:pass@db:5432/honeycloud` |
| `REDIS_URL`     | Redis connection string              | `redis://redis:6379/0`                            |
| `API_URL`       | Sensor → API endpoint                | `http://api:5000/api/logs`                        |
| `SLEEP_INTERVAL`| Seconds between sensor log posts     | `5`                                               |
| `FLASK_ENV`     | Flask environment                    | `development` or `production`                     |

---

## API Endpoints

| Method | Endpoint        | Description                        |
|--------|-----------------|------------------------------------|
| GET    | `/api/health`   | Health check — verifies DB connection |
| POST   | `/api/logs`     | Ingest a new attack log            |
| GET    | `/api/logs`     | Retrieve recent logs (cached 60s)  |
| GET    | `/metrics`      | Prometheus metrics endpoint        |

### POST `/api/logs` — required fields

```json
{
  "severity": "high",
  "honeypot_name": "Cowrie-Node-1",
  "source_ip": "192.168.1.100",
  "event_type": "SSH_Login_Failed",
  "honeypot_type": "SSH",
  "description": "Brute force attempt detected",
  "raw_data": "{\"username\": \"root\", \"password\": \"1234\"}"
}
```

---

## CI/CD Pipeline

GitHub Actions runs automatically on every push and pull request to `main`:

1. **Test** — installs dependencies, runs `pytest` against the API
2. **Build** — builds the Docker image to confirm it compiles cleanly

Pipeline config: `.github/workflows/ci.yml`

---

## AWS Deployment Guide

### Step 1 — Database (RDS)

1. Create a PostgreSQL instance on AWS RDS (`db.t3.micro` is sufficient for MVP).
2. Note the endpoint URL, username, and password.
3. Restrict inbound traffic on port 5432 to the ECS VPC only.

### Step 2 — Container Registry (ECR)

```bash
# Authenticate
aws ecr get-login-password --region <region> | \
  docker login --username AWS --password-stdin <account_id>.dkr.ecr.<region>.amazonaws.com

# Create repos
aws ecr create-repository --repository-name honeycloud-api
aws ecr create-repository --repository-name honeycloud-sensor

# Build, tag, and push API image
docker build -t honeycloud-api ./api
docker tag honeycloud-api:latest <account_id>.dkr.ecr.<region>.amazonaws.com/honeycloud-api:latest
docker push <account_id>.dkr.ecr.<region>.amazonaws.com/honeycloud-api:latest

# Repeat for sensor
```

### Step 3 — Deployment (ECS Fargate)

1. Create an ECS Cluster.
2. Create a **Task Definition** for the API:
   - Set `DATABASE_URL` to the RDS endpoint.
   - Set `REDIS_URL` to the ElastiCache endpoint.
   - Map port 5000.
3. Create a **Task Definition** for the Sensor:
   - Set `API_URL` to the ALB DNS name.
4. Launch both as ECS Services.
5. Place an **Application Load Balancer** in front of the API service.
6. Only expose port 80/443 on the ALB to the outside world.

### Security

- RDS: allow port 5432 from ECS VPC only — no public access.
- ElastiCache: allow port 6379 from ECS VPC only.
- ALB: expose port 80 (HTTP) or 443 (HTTPS) to the internet.
- Store all secrets in **AWS Secrets Manager** or ECS task definition environment variables — never in source code.

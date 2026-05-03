# Project 4 — Docker-Based CI/CD Pipeline: Flask on EC2

Automated deployment of a containerized Python Flask application to AWS EC2, with a three-job CI/CD pipeline that tests inside the container, pushes a versioned image to Docker Hub, and deploys with automatic rollback on failure.

---

## The Problem This Solves

Deploying raw code to a server means the server must be manually configured for every application — the right Python version, the right dependencies, the right process manager. Change the app, and the server might need reconfiguring. Move to a new server, and you set it all up again. This project solves that: the application and its entire environment are packaged into a single Docker image. The server only needs Docker installed. What runs in CI is exactly what runs in production — same image, same environment, no drift.

---

## What Was Built

- **Python Flask app** containerized with Docker, served by Gunicorn in production
- **Dockerfile** with explicit layer ordering to maximize build cache efficiency
- **Docker Hub** as the image registry — every successful build produces a versioned, retrievable image
- **Git commit SHA image tagging** — every image is permanently tied to the exact commit that produced it
- **Three-job GitHub Actions pipeline** — test, build-and-push, deploy with explicit job dependencies
- **Tests run inside the container** — pytest executes against the actual image, not a separately configured runner environment
- **EC2 provisioned with Docker only** — no Python, no pip, no Gunicorn installed on the server directly
- **Health check after every deploy** — curl hits the live endpoint to confirm the app is serving traffic
- **Automatic rollback** — if the health check fails, the pipeline pulls the previous SHA-tagged image and redeploys it

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              GitHub Actions Runner          │
│                                             │
│   ┌──────────┐  ┌───────────────────────┐   │
│   │   test   │  │    build-and-push     │   │
│   │          │  │                       │   │
│   │  docker  │  │  docker build         │   │
│   │  build   │  │  tag with git SHA     │   │
│   │  pytest  │  │  push to Docker Hub   │   │
│   └──────────┘  └───────────────────────┘   │
└─────────────────────────┬───────────────────┘
                          │ SSH
                          ▼
┌─────────────────────────────────────────────┐
│                EC2 Instance                 │
│                                             │
│   ┌─────────────────────────────────────┐   │
│   │         Docker                      │   │
│   │                                     │   │
│   │   ┌──────────────────────────────┐  │   │
│   │   │  flask-app-container :5000   │  │   │
│   │   │  image: username/flask-app   │  │   │
│   │   │          :<git-sha>          │  │   │
│   │   └──────────────────────────────┘  │   │
│   └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
          ▲
     Browser / Client
```

EC2 pulls the image from Docker Hub by SHA tag. The server has no knowledge of Python, Flask, or Gunicorn — it just runs containers.

---

## Pipeline Structure

```
push to main
     │
     ▼
┌─────────┐
│  test   │  Runner builds the Docker image.
│         │  Runs pytest inside a container from that image.
│         │  Overrides CMD — runs pytest instead of Gunicorn.
│         │  Fails fast — nothing proceeds if tests fail.
└────┬────┘
     │ needs: test
     ▼
┌───────────────┐
│ build-and-push│  Logs into Docker Hub using GitHub Secrets.
│               │  Builds image tagged with Git commit SHA.
│               │  Also tags as latest for convenience.
│               │  Pushes both tags to Docker Hub.
└───────┬───────┘
        │ needs: build-and-push
        ▼
┌─────────┐
│ deploy  │  Captures previous commit SHA for rollback.
│         │  SSHes into EC2.
│         │  Pulls new image by SHA tag.
│         │  Stops and removes old container.
│         │  Starts new container in detached mode.
│         │  Health check — curl hits live endpoint.
│         │  On failure — pulls previous SHA, redeploys.
└─────────┘
```

**Why three jobs instead of two?** Testing, building, and deploying have different responsibilities and different failure modes. If the build fails, you want to know it was a build problem, not a test problem. If the deploy fails, the tested and versioned image is already safely on Docker Hub. Each job's scope is explicit and failures are immediately diagnosable.

---

## Key Technical Decisions

**1 — Image tagged with Git commit SHA, not just latest**
Every image pushed to Docker Hub carries two tags: `latest` and the full Git commit SHA. `latest` is convenient for normal deploys. The SHA tag is what makes rollback reliable — it permanently identifies the exact code inside the image. If a deploy breaks production, rollback means pulling the previous SHA tag and running it. No git history manipulation on the server. No reinstalling dependencies. Just run the previous image.

**2 — Dockerfile layer ordering for cache efficiency**
`requirements.txt` is copied and dependencies are installed before the application code is copied in. Dependencies change rarely. Application code changes constantly. By separating them into distinct layers, Docker reuses the cached dependency layer on every rebuild where only code changed. A full dependency reinstall only happens when `requirements.txt` actually changes. On a project with many dependencies, this can reduce build time from minutes to seconds.

**3 — Tests run inside the container, not on the raw runner**
The test job builds the image and runs pytest by overriding the container's startup command. This means tests execute in the exact same environment that will be deployed — same Python version, same installed packages, same filesystem structure. Testing on the raw runner with a separate pip install would create a gap between the tested environment and the deployed one. Running inside the container closes that gap entirely.

---

## Local Setup

```bash
git clone https://github.com/Vimukthi-Randunu/ci-cd-project-4.git
cd ci-cd-project-4

# Build the image
docker build -t flask-app .

# Run the container
docker run -p 5000:5000 flask-app

# Run tests inside the container
docker run flask-app pytest
```

App available at `http://localhost:5000`

---

## Part of a Progressive CI/CD Learning Series

This is Project 4 in a series building toward production-grade CI/CD systems:

- **Project 1** — GitHub Actions CI with Jest tests
- **Project 2** — Full CD to EC2 with health checks and rollback
- **Project 3** — Language-agnostic CI/CD with Python Flask
- **Project 4** — Containerization with Docker, image tagging with Git SHA ← this project
- **Project 5** — Multi-container systems, Docker networking, Compose orchestration
- **Project 6** — Staging and production environments, approval gates, environment separation

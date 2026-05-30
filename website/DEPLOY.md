# AWS Deployment Guide (Docker Compose)

This guide explains how to deploy the Art Restoration project to an AWS EC2 instance using Docker.

## 1. Prerequisites
- AWS EC2 instance (Ubuntu recommended, `t3.micro`)
- Security Group rules: Allow SSH (22) and HTTP (80)

## 2. Server Setup
SSH into your instance and install Docker:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
# Log out and log back in for group changes to take effect
```

## 3. Deployment
```bash
git clone <your-repo-url>
cd website
docker-compose up --build -d
```

## 4. Verification
Your app will be running at `http://your-ec2-ip`.
- Frontend: Port 80
- Backend: Port 5000 (proxied via `/api`)

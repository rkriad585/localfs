# Deployment Guide

## Production Considerations

Before deploying to production:

1. Set `DEBUG = False` in `src/localfs/config.py`
2. Use a reverse proxy (nginx, Caddy, Traefik)
3. Enable HTTPS with Let's Encrypt
4. Run with a non-root user
5. Use Docker for isolation

## Option 1: Direct Deployment

```bash
pip install -e .
python -m localfs
```

**Not recommended for production.** Use a process manager instead.

### With systemd

Create `/etc/systemd/system/localfs.service`:

```ini
[Unit]
Description=localfs file sharing service
After=network.target

[Service]
Type=simple
User=localfs
WorkingDirectory=/opt/localfs
ExecStart=/usr/bin/python3 -m localfs
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now localfs
```

### With nginx reverse proxy

```nginx
server {
    listen 80;
    server_name localfs.example.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Option 2: Docker

```bash
docker build -t localfs .
```

### Run

```bash
docker run -d \
    --name localfs \
    -p 5000:5000 \
    --restart unless-stopped \
    localfs
```

### With docker compose

```yaml
services:
  localfs:
    build: .
    ports:
      - "5000:5000"
    restart: unless-stopped
```

```bash
docker compose up -d
```

## Option 3: Cloud Deployment

### With a VPS

1. SSH into your server.
2. Clone the repo.
3. Run with Docker or systemd.
4. Set up nginx + Let's Encrypt.

### With Railway / Render / Fly.io

These platforms support Docker deployments. Use the provided `Dockerfile`.

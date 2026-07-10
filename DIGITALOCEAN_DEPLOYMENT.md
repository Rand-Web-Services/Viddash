# DigitalOcean Droplet Deployment

This is the low-cost production path for Viddash: one Droplet running Caddy, Flask/Gunicorn, Postgres, and Redis with Docker Compose.

## 1. Create the Droplet

Start small and upgrade only when signups justify it.

- Image: Ubuntu LTS
- Size: 1-2 GB RAM to start
- Firewall: allow `22`, `80`, and `443`
- DNS: point your domain or subdomain to the Droplet IP

Example DNS:

```text
app.yourdomain.com -> Droplet IPv4 address
```

## 2. Install Docker

On the Droplet:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"
newgrp docker
```

## 3. Copy the app and configure env

Clone or copy this repo onto the Droplet, then:

```bash
cp env.digitalocean.example .env.production
nano .env.production
```

Set at minimum:

- `VIDDASH_DOMAIN`
- `VIDDASH_PUBLIC_URL`
- `ACME_EMAIL`
- `VIDDASH_SECRET_KEY`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `RESEND_API_KEY`
- `MAIL_FROM`
- `SUPPORT_EMAIL`

The `POSTGRES_PASSWORD` value must match the password embedded in `DATABASE_URL`.

## 4. Configure Google OAuth

In Google Cloud Console, add this redirect URI:

```text
https://app.yourdomain.com/auth/google/callback
```

For local testing, keep:

```text
http://127.0.0.1:5000/auth/google/callback
http://localhost:5000/auth/google/callback
```

## 5. Start production

```bash
docker compose --env-file .env.production -f docker-compose.digitalocean.yml up -d --build
docker compose --env-file .env.production -f docker-compose.digitalocean.yml ps
```

Caddy will request and renew HTTPS certificates automatically.

## 6. Smoke test

```bash
curl -I https://app.yourdomain.com/robots.txt
curl -I https://app.yourdomain.com/signup
docker compose --env-file .env.production -f docker-compose.digitalocean.yml logs --tail=100 viddash
```

Expected:

- `robots.txt` returns `200`
- `/auth/google` redirects to Google after OAuth env vars are set
- The app logs do not show production configuration errors

## 7. Backups

Before real customers, add Postgres backups. The minimum manual backup is:

```bash
docker exec viddash-postgres pg_dump -U viddash viddash > viddash-backup.sql
```

Once signups start, move Postgres to a managed database or automate off-server backups.

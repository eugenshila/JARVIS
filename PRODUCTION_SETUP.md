# JARVIS production setup

This is the low-memory setup for an 8 GB laptop. It runs the API and Next.js in production mode, keeps Postgres and Redis persistent, and does not expose databases to the network.

## 1. Install

Install Docker Desktop (or Docker Engine + Compose), then from the repository root:

```bash
cp .env.example .env
```

Edit `.env` and set strong, unique values for `POSTGRES_PASSWORD`, `JWT_SECRET`, `JARVIS_ENCRYPTION_KEY`, and `CORS_ORIGINS`. Generate secrets with:

```bash
openssl rand -hex 32
```

For local browser use, set:

```env
POSTGRES_PASSWORD=use-a-long-random-password
JWT_SECRET=another-long-random-secret
JARVIS_ENCRYPTION_KEY=another-separate-long-random-secret
CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

Never commit `.env` or provider API keys.

## 2. Build and run

```bash
docker compose -f docker-compose.production.yml up -d --build
```

Open http://localhost:3000. Check services with:

```bash
docker compose -f docker-compose.production.yml ps
docker compose -f docker-compose.production.yml logs -f api
```

The API is only bound to `127.0.0.1:8000`; Postgres and Redis are not published at all.

## 3. Stop and update

```bash
docker compose -f docker-compose.production.yml down
git pull
docker compose -f docker-compose.production.yml up -d --build
```

Do not add `-v` to `down`; volumes contain the database and Redis data.

## Browser security

For a public deployment, put HTTPS in front of the web and API services using a managed reverse proxy or Caddy/Nginx. Use the real HTTPS website in `CORS_ORIGINS`, `NEXT_PUBLIC_API_URL`, and `NEXT_PUBLIC_WS_URL` (`wss://` for WebSockets). Keep Gemini keys server-side. Use a firewall so only ports 80/443 are public. The included local Compose file deliberately binds web/API to localhost and is not a public internet server by itself.

## Performance notes

This configuration uses one API process, production Next.js output, a persistent WebSocket, and Redis capped at 128 MB. Avoid `npm run dev`, `uvicorn --reload`, and rebuilding on every request. Gemini generation time remains dependent on the selected model and network latency.

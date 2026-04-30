---
title: OSMA NPM API
emoji: 📦
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---

# OSMA NPM API

Backend API for the OSMA (Open Source Metadata Aggregator) project.
Serves search and browse queries over 3.8M NPM packages stored in SQLite.

## Endpoints

| Endpoint | Description |
| :--- | :--- |
| `GET /health` | Server status and total package count |
| `GET /stats` | Total count for the frontend stats bar |
| `GET /search?q=react&limit=250` | Ranked search — exact → starts-with → contains |
| `GET /browse?page=1&limit=200` | Paginated browse ordered by package number |
| `GET /rebuild?secret=xxx` | Re-download dataset and rebuild SQLite |

## First Boot

On first startup the server downloads the npm dataset from
`notamitgamer/npm` on HuggingFace and builds a SQLite index.
This takes 1–3 minutes. The `/health` endpoint returns `503` until ready.

## Environment Variables (Secrets)

| Variable | Required | Description |
| :--- | :--- | :--- |
| `HF_TOKEN` | Only if dataset is private | HuggingFace read token |
| `REBUILD_SECRET` | Recommended | Secret key to protect the `/rebuild` endpoint |
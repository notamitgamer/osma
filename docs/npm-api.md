# <img src="https://raw.usercontent.amit.is-a.dev/data.amit.is-a.dev/assets/npm.png" alt="OSMA Icon" width="90" /><br> NPM API

**Base URL:** `https://notamitgamer-osma-npm-api.hf.space`

---

## GET /ping

> Uptime check — always returns 200

Lightweight endpoint for UptimeRobot or health monitors. Does not query the database. Always responds instantly.

**Example Request**

```bash
curl https://notamitgamer-osma-npm-api.hf.space/ping
```

**Example Response**

```json
{
  "ping": "pong"
}
```

---

## GET /health

> Server status + total package count

Returns `200 OK` with package count when the database is ready. Returns `503` if the database is still initializing after a cold start.

**Example Request**

```bash
curl https://notamitgamer-osma-npm-api.hf.space/health
```

**Example Response**

```json
{
  "status": "ok",
  "total_packages": 3881465
}
```

---

## GET /stats

> Dataset metadata and package count

Returns total package count plus metadata about the dataset source and snapshot nature. Intended for display in dashboard stats bars.

**Example Request**

```bash
curl https://notamitgamer-osma-npm-api.hf.space/stats
```

**Example Response**

```json
{
  "total_npm_packages": 3881465,
  "source": "npmjs.com",
  "note": "Snapshot dataset — updated periodically."
}
```

---

## GET /browse

> Paginated package list ordered by package number

Returns packages in stable order by `package_no`. Use `page` and `limit` to paginate through the full dataset.

**Parameters**

| Parameter | Type    | Default | Max | Required | Description             |
|-----------|---------|---------|-----|----------|-------------------------|
| `page`    | integer | 1       | —   | optional | Page number, 1-indexed  |
| `limit`   | integer | 200     | 500 | optional | Rows per page           |

**Example Request**

```bash
curl "https://notamitgamer-osma-npm-api.hf.space/browse?page=1&limit=5"
```

**Example Response**

```json
{
  "page": 1,
  "limit": 5,
  "results": [
    { "no": 1, "name": "--123hoodmane-pyodide", "version": "latest", "url": "https://www.npmjs.com/package/..." },
    ...
  ]
}
```

---

## GET /search

> Ranked search across all packages

Searches package names and returns results ranked by match quality: exact match first (rank `0`), starts-with second (rank `1`), contains last (rank `2`). Results are sorted by rank then alphabetically within each rank.

**Parameters**

| Parameter | Type    | Default | Max       | Required | Description                    |
|-----------|---------|---------|-----------|----------|--------------------------------|
| `q`       | string  | —       | 100 chars | required | Search query. Min 2 characters.|
| `limit`   | integer | 250     | 500       | optional | Max results to return          |

**Example Request**

```bash
curl "https://notamitgamer-osma-npm-api.hf.space/search?q=react&limit=5"
```

**Example Response**

```json
{
  "query": "react",
  "count": 250,
  "results": [
    { "no": 42, "name": "react", "version": "18.3.1", "url": "...", "rank": 0 },
    { "no": 88, "name": "react-dom", "version": "18.3.1", "url": "...", "rank": 1 },
    ...
  ]
}
```

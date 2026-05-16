# <img src="https://raw.usercontent.amit.is-a.dev/data.amit.is-a.dev/assets/pypi.png" alt="OSMA Icon" width="90" /><br> PyPI API

**Base URL:** `https://notamitgamer-osma-pypi-api.hf.space`

---

## GET /ping

> Uptime check — always returns 200

Lightweight endpoint for UptimeRobot or health monitors. Does not query the database. Always responds instantly.

**Example Request**

```bash
curl https://notamitgamer-osma-pypi-api.hf.space/ping
```

**Example Response**

```json
{ "ping": "pong" }
```

---

## GET /health

> Server status + total package count

Returns `200 OK` with package count when database is ready. Returns `503` during cold start initialization.

**Example Request**

```bash
curl https://notamitgamer-osma-pypi-api.hf.space/health
```

**Example Response**

```json
{
  "status": "ok",
  "total_packages": 780432
}
```

---

## GET /stats

> Dataset metadata and package count

Returns total package count and dataset source metadata.

**Example Request**

```bash
curl https://notamitgamer-osma-pypi-api.hf.space/stats
```

**Example Response**

```json
{
  "total_pypi_packages": 780432,
  "source": "pypi.org",
  "note": "Snapshot dataset — updated periodically."
}
```

---

## GET /browse

> Paginated package list ordered by package number

Returns packages in stable order by `package_no`. Paginate using `page` and `limit`.

**Parameters**

| Parameter | Type    | Default | Max | Required | Description            |
|-----------|---------|---------|-----|----------|------------------------|
| `page`    | integer | 1       | —   | optional | Page number, 1-indexed |
| `limit`   | integer | 200     | 500 | optional | Rows per page          |

**Example Request**

```bash
curl "https://notamitgamer-osma-pypi-api.hf.space/browse?page=1&limit=5"
```

**Example Response**

```json
{
  "page": 1,
  "limit": 5,
  "results": [
    { "no": 1, "name": "0", "version": "0.1.0", "url": "https://pypi.org/project/0/" },
    ...
  ]
}
```

---

## GET /search

> Ranked search across all packages

Searches package names and returns results ranked by match quality. Rank `0` = exact, `1` = starts-with, `2` = contains.

**Parameters**

| Parameter | Type    | Default | Max       | Required | Description                    |
|-----------|---------|---------|-----------|----------|--------------------------------|
| `q`       | string  | —       | 100 chars | required | Search query. Min 2 characters.|
| `limit`   | integer | 250     | 500       | optional | Max results to return          |

**Example Request**

```bash
curl "https://notamitgamer-osma-pypi-api.hf.space/search?q=requests&limit=5"
```

**Example Response**

```json
{
  "query": "requests",
  "count": 87,
  "results": [
    { "no": 512, "name": "requests", "version": "2.31.0", "url": "...", "rank": 0 },
    ...
  ]
}
```

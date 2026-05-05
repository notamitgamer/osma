<div align="center">
  <img src="https://raw.usercontent.amit.is-not.cool/data.amit.is-a.dev/assets/osma.png" alt="OSMA Icon" width="120" />

  # OSMA (Open Source Module Archive)

  <p>
    <img src="https://img.shields.io/badge/NPM-3%2C881%2C465_Packages-cb3837?style=for-the-badge&logo=npm" alt="NPM Packages" />
    <img src="https://img.shields.io/badge/PyPI-793%2C648_Packages-3776ab?style=for-the-badge&logo=python&logoColor=white" alt="PyPI Packages" />
    <img src="https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge" alt="License" />
  </p>
</div>

**Registry lookups, without the wait.** OSMA is a lightning-fast, static search archive for querying open-source packages across NPM and PyPI, bypassing live registry bottlenecks.

### Live Explorers & Docs
* **Home:** [data.amit.is-a.dev](https://data.amit.is-a.dev)
* **NPM Explorer:** [data.amit.is-a.dev/npm](https://data.amit.is-a.dev/npm)
* **PyPI Explorer:** [data.amit.is-a.dev/pypi](https://data.amit.is-a.dev/pypi)
* **API Documentation:** [data.amit.is-a.dev/docs](https://data.amit.is-a.dev/docs)
* **GitHub Repository:** [notamitgamer/osma](https://github.com/notamitgamer/osma)

---

## Why I Built OSMA

This project was born out of pure frustration. I found myself constantly needing to look up package details, version numbers, and dependencies. But doing this on the official registries meant dealing with:
1.  **Fastly Security Checks:** Being stalled by CAPTCHAs or security verification screens just to view a text page.
2.  **The Multi-Click Tax:** Clicking through 2-3 different pages just to find the exact version tag or repository link I was looking for.

**The Solution:** I took complete static snapshots of the registries **(2026-04-29 08:45 IST for PyPI and 2026-04-29 09:42 IST for NPM)**. By indexing these frozen lists into a custom backend, OSMA allows users to instantly search and verify packages without ever hitting a live registry rate-limit. *(Note: Clicking a package in the UI will still fetch its extended live details securely via a side-panel).*

---

## How the Backend Works

The backend is powered by **FastAPI**, serving static `.csv` snapshots securely downloaded from HuggingFace datasets. 

* **SQLite Indexing:** On the first boot, the server downloads the multi-gigabyte dataset and builds an optimized, indexed SQLite database (WAL mode). 
* **Speed:** Because the dataset is localized, lookups for searches (`/search`) and chunked pagination (`/browse`) respond in milliseconds.
* **Rate Limiting:** To protect the free-tier infrastructure, strict rate limits (**10 requests/minute, 100 requests/hour**) are enforced via `slowapi`. Developers can bypass this by requesting an `X-Bypass-Token` via a GitHub issue.
* **Ranking Logic:** Search results are strictly ranked:
    1.  `Rank 0`: Exact match
    2.  `Rank 1`: Starts with query
    3.  `Rank 2`: Contains query
* **Limitation:** Because this is an archive, packages published or deleted after April 2026 are not indexed. 

---

## API Endpoints Documentation

The APIs are hosted publicly and support open CORS. No authentication is required for standard usage.

### 1. Health & Stats
* **`GET /health`**
    * **Description:** Checks if the server is alive and returns the total indexed packages. Responds with `503` if the database is still initializing on a cold start.
    * **Response (200):** `{"status": "ok", "total_packages": 3881465}`
* **`GET /ping`** / **`GET /stats`**
    * **Description:** Basic server alive/telemetry routes.

### 2. Browse Packages
* **`GET /browse`**
    * **Description:** Returns packages sequentially, ordered by `package_no`. Used for pagination.
    * **Parameters:** * `page` (int, default `1`): The page number (minimum 1).
        * `limit` (int, default `200`): Items per page (maximum 500).
    * **Response (200):** List of package objects `[{"no": 1, "name": "...", "version": "...", "url": "..."}]`.
    * **Response (429):** Too Many Requests (Rate limit exceeded).

### 3. Search Packages
* **`GET /search`**
    * **Description:** Search packages by name. Returns algorithmically ranked results.
    * **Parameters:**
        * `q` (string, required): The search query (min length: 2 chars).
        * `limit` (int, default `250`): Max results to return (maximum 500).
    * **Response (200):** Ranked list of package objects matching the query.
    * **Response (422):** Validation Error if query is too short.
    * **Response (429):** Too Many Requests (Rate limit exceeded).

### 4. Utility Endpoints
* **`GET /get-bypass`**: Generate a temporary rate limit bypass token (requires `secret` parameter). Send the result as the `X-Bypass-Token` header.
* **`GET /debug-ip`**: View the IP and headers recorded by the API proxy (useful for debugging rate limits).
* **`GET /rebuild`**: Trigger an asynchronous re-download and rebuild of the SQLite database (requires `secret` parameter).

---

## Additional Documentation

Please refer to the following documents for repository guidelines:
* [Contributing](CONTRIBUTING.md)
* [Security Policy](SECURITY.md)
* [Code of Conduct](CODE_OF_CONDUCT.md)

## License

Distributed under the Apache 2.0 License. See `LICENSE` for more information.

---
*Maintained by [Amit Dutta](https://github.com/notamitgamer) | [amit.is-a.dev](https://amit.is-a.dev)*

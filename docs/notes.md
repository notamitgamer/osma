# Notes & Reference

---

## Limits & Notes

### Rate Limits

APIs are strictly rate-limited to **10 requests per minute** and **100 requests per hour** per IP to protect the free-tier infrastructure. Send the `X-Bypass-Token` header to override this.

### Data Freshness

Both datasets are snapshots. NPM frozen `2026-04-29 09:42 IST`. PyPI frozen `2026-04-29 08:45 IST`. Packages published after these dates are not indexed.

### CORS

Both APIs have `Access-Control-Allow-Origin: *`. You can call them directly from any browser-based frontend with no proxy needed.

### Cold Starts

On first boot after a deployment, each server downloads its dataset and builds a SQLite index (~1 min). The `/health` endpoint returns `503` during this window. UptimeRobot prevents this in normal operation.

---

## Response Schema

When querying the `/browse` or `/search` endpoints, the returned `results` array contains objects with the following fields:

| Field     | Type    | Description                                                                                                     |
|-----------|---------|-----------------------------------------------------------------------------------------------------------------|
| `no`      | integer | The stable, sequential ID/rank of the package within the snapshot database.                                     |
| `name`    | string  | The exact, registered name of the package.                                                                      |
| `version` | string  | The version string available at the time the snapshot was taken.                                                |
| `url`     | string  | The absolute link to the package on the official registry website.                                              |
| `rank`    | integer | _(Only in `/search`)_ Match quality: `0` = Exact match, `1` = Starts with query, `2` = Contains query.        |

---

## Common Errors

### `404` Not Found

**Why it happens:** The API URL path is incorrect or misspelled (e.g., trying to access `/searc` instead of `/search`).

### `422` Unprocessable Entity

**Why it happens:** You called the `/search` endpoint without providing the required `q` query parameter, or the search query was less than 2 characters long.

### `429` Too Many Requests

**Why it happens:** You exceeded the 10/min or 100/hour rate limit. The JSON response will include an error string, and the HTTP headers will include a `Retry-After` value indicating how many seconds to wait before retrying.

### `503` Service Unavailable

**Why it happens:** The server was asleep and is experiencing a "Cold Start". It is currently downloading the multi-gigabyte dataset and building the in-memory SQLite index. This is completely normal on free-tier hosting and usually resolves within 1 minute. Please wait and try again.

!!!warning Still having trouble?
If you are experiencing continuous `500 Internal Server Errors` or found a bug, please [open an issue on GitHub](https://github.com/notamitgamer/osma/issues) or contact the maintainer at [mail@amit.is-a.dev](mailto:mail@amit.is-a.dev).
!!!

---

## Frequently Asked Questions

**What exactly is OSMA?**

OSMA (Open Source Module Archive) is a heavily optimized, static API that serves historical snapshots of the NPM and PyPI registries. It allows you to search packages and view base version data instantly without dealing with live registry rate limits or CAPTCHAs.

---

**Why can't I find a package that was published recently?**

The datasets are frozen snapshots taken on April 29, 2026. Any packages published, renamed, or deleted after this specific date will not appear in the search results.

---

**Is there any rate limiting?**

Yes. Because the service is hosted on free-tier infrastructure, strict rate limits of 10 requests per minute and 100 requests per hour per IP are enforced using SlowAPI. If you need this disabled for your application, please open an issue on GitHub to request an `X-Bypass-Token`.

---

**Do I need an API Key or Authentication?**

No. The APIs are completely open, public, and require zero authentication headers or keys for standard usage within the rate limits.

---

**Can I use this API in my frontend app directly?**

Yes. Both the NPM and PyPI APIs are configured with open CORS (`Access-Control-Allow-Origin: *`), meaning browser-based frontend applications can fetch data directly without encountering CORS blocking.

---

**What does the `rank` field mean in the search response?**

The search endpoint sorts results algorithmically based on match strength. A rank of `0` means the query exactly matches the package name. `1` means the package name starts with the query. `2` means the package name contains the query somewhere inside it.

---

**Why does the `/health` endpoint sometimes return a 503 error?**

If the server hasn't been accessed in a while, it goes to sleep. When it wakes up (a "cold start"), it needs about 1–2 minutes to download the multi-gigabyte CSV snapshot and build its memory index. It returns a `503` status while loading.

---

**How many packages are indexed?**

As of the current snapshots, there are roughly 3.88 million NPM packages and 793,000 PyPI packages indexed. You can check the `/stats` endpoint for exact, live metadata.

---

**Are there plans to add other registries like RubyGems or Cargo?**

Right now, the focus is strictly on NPM and PyPI. If there is enough demand, other ecosystems may be considered in the future.

---

**How do I report a vulnerability or bug?**

For general bugs, UI issues, or missing documentation, please open an issue on the [GitHub repository](https://github.com/notamitgamer/osma/issues). For security vulnerabilities, please email [mail@amit.is-a.dev](mailto:mail@amit.is-a.dev) directly instead of opening a public issue.

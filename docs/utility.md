# Utility Endpoints

These endpoints are available on both the NPM and PyPI APIs. Examples below use the NPM base URL.

---

## GET /debug-ip

> Check connection IP and headers

Returns the actual IP address that the API proxy recorded for your request, along with the parsed headers. Helpful for troubleshooting rate limit blocks across networks.

**Example Request**

```bash
curl https://notamitgamer-osma-npm-api.hf.space/debug-ip
```

---

## GET /get-bypass

> Generate a temporary rate limit bypass token

Issues a cryptographically signed bypass token that allows you to skip all rate limits for 1 hour. This endpoint requires the correct `secret` parameter. Include the returned token in subsequent requests as the `X-Bypass-Token` header.

**Parameters**

| Parameter | Type   | Required | Description                  |
|-----------|--------|----------|------------------------------|
| `secret`  | string | required | The developer bypass secret. |

**Example Request**

```bash
curl "https://notamitgamer-osma-npm-api.hf.space/get-bypass?secret=YOUR_SECRET_HERE"
```

**Example Response**

```json
{
  "bypass_token": "1714420000:a1b2c3d4...",
  "valid_for_seconds": 3600,
  "usage": "Send as header: X-Bypass-Token: <token>"
}
```

---

## GET /rebuild

> Trigger an async database rebuild

Forces the server to re-download the latest CSV dataset from HuggingFace and rebuild the SQLite database in the background. Requires the `secret` parameter. Responds with `503` while rebuilding.

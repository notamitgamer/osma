# Quick Start

Because OSMA provides completely open CORS policies and requires no authentication keys, you can start fetching package data immediately from any environment—whether that is a backend script, a CLI tool, or directly inside a browser application.

Below are a few quick examples of how to query the APIs using the most common languages.

---

## JavaScript (Browser & Node.js)

Since CORS is fully open (`Access-Control-Allow-Origin: *`), you can use the native `fetch` API directly in your frontend applications or Node scripts.

This example queries the **NPM** snapshot for the `react` package:

```javascript
// Fetching package details from the OSMA NPM snapshot
async function getPackageVersion(query) {
  const url = `https://notamitgamer-osma-npm-api.hf.space/search?q=${encodeURIComponent(query)}&limit=1`;
  
  try {
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (data.results && data.results.length > 0) {
      const pkg = data.results[0];
      console.log(`${pkg.name} | Version: ${pkg.version} | Rank: ${pkg.rank}`);
      console.log(`Registry Link: ${pkg.url}`);
    } else {
      console.log("Package not found in the April 2026 snapshot.");
    }
  } catch (error) {
    console.error("Failed to fetch OSMA data:", error);
  }
}

// Run the search
getPackageVersion("react");
```

---

## Python

For Python applications, tools, or data analysis scripts, the standard `requests` library makes querying the PyPI snapshot incredibly simple.

This example queries the **PyPI** snapshot for the `requests` package:

```python
import requests

def get_package_version(query):
    # Fetching package details from the OSMA PyPI snapshot
    url = f"[https://notamitgamer-osma-pypi-api.hf.space/search?q=](https://notamitgamer-osma-pypi-api.hf.space/search?q=){query}&limit=1"
    
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for bad status codes
        
        data = response.json()
        
        if data.get("results"):
            pkg = data["results"][0]
            print(f"{pkg['name']} | Version: {pkg['version']} | Rank: {pkg['rank']}")
            print(f"Registry Link: {pkg['url']}")
        else:
            print("Package not found in the April 2026 snapshot.")
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch OSMA data: {e}")

# Run the search
if __name__ == "__main__":
    get_package_version("requests")
```

---

## Command Line (cURL)

If you are building bash scripts or just want to quickly test an endpoint from your terminal, `curl` is the fastest method. 

```bash
# Querying the NPM API for 'express' and piping to jq for readable JSON
curl -s "[https://notamitgamer-osma-npm-api.hf.space/search?q=express&limit=3](https://notamitgamer-osma-npm-api.hf.space/search?q=express&limit=3)" | jq
```

!!!info Rate Limits Apply
Remember that these endpoints are subject to the standard free-tier rate limits (10 requests per minute, 100 per hour). If you are writing a script that loops through hundreds of packages, you will need to request an `X-Bypass-Token`. See the [Utility Endpoints](/utility) page for details.
!!!

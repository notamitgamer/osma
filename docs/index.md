<img src="https://raw.usercontent.amit.is-a.dev/data.amit.is-a.dev/assets/osma.png" alt="OSMA Icon" width="90" /><br>
# OSMA API Reference

_Last updated: May 2, 2026_

!!!info Rate Limit Bypass Access
To ensure service stability, strict rate limits (10 req/min, 100 req/hr) are now enforced. If you are building a tool and require an `X-Bypass-Token` to override these limits, please [open an issue on the GitHub repository](https://github.com/notamitgamer/osma/issues) explaining your specific use case.
!!!

OSMA exposes two REST APIs — one for the NPM package dataset, one for PyPI. Both are identical in structure. All endpoints return JSON and support cross-origin requests (CORS open). No authentication required.

- No auth required
- CORS open
- JSON responses
- Snapshot data — frozen 2026-04-29

---

## Indexed Packages

OSMA is built on top of massive, static snapshots of the world's two largest package registries, frozen in time on **April 29, 2026**. 

Below is the live count of packages successfully indexed and instantly searchable through our localized database:

<div style="display: flex; gap: 16px; margin-top: 24px; margin-bottom: 32px; flex-wrap: wrap;">
    <div style="border: 1px solid #3f3f46; background-color: #18181b; padding: 20px; border-radius: 8px; flex: 1; min-width: 200px;">
        <div style="font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.05em; color: #a1a1aa; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
            <i class="bi bi-box-seam-fill" style="color: #cb3837;"></i> NPM Snapshot
        </div>
        <div id="npm-doc-count" style="font-size: 1.75em; font-weight: 600; color: #f4f4f5; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;">
            <i class="bi bi-arrow-repeat animate-spin inline-block" style="font-size: 0.8em; color: #71717a;"></i>
        </div>
    </div>
    <div style="border: 1px solid #3f3f46; background-color: #18181b; padding: 20px; border-radius: 8px; flex: 1; min-width: 200px;">
        <div style="font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.05em; color: #a1a1aa; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
            <i class="bi bi-file-earmark-code-fill" style="color: #3776ab;"></i> PyPI Snapshot
        </div>
        <div id="pypi-doc-count" style="font-size: 1.75em; font-weight: 600; color: #f4f4f5; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;">
            <i class="bi bi-arrow-repeat animate-spin inline-block" style="font-size: 0.8em; color: #71717a;"></i>
        </div>
    </div>
</div>

*Note: Because this is a localized archive, packages published or deleted after April 2026 will not be reflected in these totals.*

---

## Base URLs

**NPM API**
``` text
https://notamitgamer-osma-npm-api.hf.space
```

**PyPI API**
``` text
https://notamitgamer-osma-pypi-api.hf.space
```

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

<script>
(function enforceOsmaCounters() {
    const NPM_BASE = "https://notamitgamer-osma-npm-api.hf.space";
    const PYPI_BASE = "https://notamitgamer-osma-pypi-api.hf.space";

    // Variables to hold our fetched numbers
    let npmData = null;
    let pypiData = null;

    // 1. Fetch the data exactly ONCE in the background
    fetch(`${NPM_BASE}/health`)
        .then(res => res.json())
        .then(data => npmData = `${data.total_packages.toLocaleString()} packages`)
        .catch(() => npmData = `Offline`);

    fetch(`${PYPI_BASE}/health`)
        .then(res => res.json())
        .then(data => pypiData = `${data.total_packages.toLocaleString()} packages`)
        .catch(() => pypiData = `Offline`);

    // 2. Continually enforce the DOM update (Immune to React/Vue re-renders)
    setInterval(() => {
        const npmEl = document.getElementById('npm-doc-count');
        const pypiEl = document.getElementById('pypi-doc-count');

        // If elements exist and we have data, force the update
        if (npmEl && npmData && !npmEl.innerText.includes(npmData)) {
            npmEl.innerHTML = npmData;
        }
        if (pypiEl && pypiData && !pypiEl.innerText.includes(pypiData)) {
            pypiEl.innerHTML = pypiData;
        }
    }, 500); // Checks every half-second
})();
</script>

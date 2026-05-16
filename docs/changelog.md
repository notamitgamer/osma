# Changelog

All notable changes to OSMA (Open Source Module Archive), its APIs, and its documentation will be documented in this file. 

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to Semantic Versioning for the API routes.

---

## [1.1.0] - 2026-05-02

### Added
- **Interactive Documentation:** Rebuilt the documentation portal using Retype.
- **Live Counters:** Added real-time database indexing statistics to the documentation homepage.
- **Rate Limit Bypass:** Introduced the `/get-bypass` endpoint and the `X-Bypass-Token` header for developer tools requiring heavy throughput.

### Changed
- **Rate Limiting Enforcement:** Implemented strict SlowAPI rate limits (10 req/min, 100 req/hr) to protect the free-tier Hugging Face backend infrastructure.
- **Routing:** Updated CORS policies (`Access-Control-Allow-Origin: *`) to universally support browser-based frontend applications.

---

## [1.0.0] - 2026-04-29

### Added
- **Initial Release:** OSMA goes live.
- **NPM Snapshot:** Successfully extracted and indexed ~3.88 million NPM packages. Database frozen at `2026-04-29 09:42 IST`.
- **PyPI Snapshot:** Successfully extracted and indexed ~793,000 PyPI packages. Database frozen at `2026-04-29 08:45 IST`.
- **Search Engine:** Deployed custom FastAPI backends utilizing in-memory SQLite indexing (WAL mode) to achieve millisecond response times.
- **Ranking Algorithm:** Added custom match-strength sorting logic (Rank 0: Exact match, Rank 1: Starts with, Rank 2: Contains).
- **Core Endpoints:** Launched `/ping`, `/health`, `/stats`, `/browse`, and `/search`.

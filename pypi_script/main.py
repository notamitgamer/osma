import os
import sqlite3
import asyncio
import csv
import logging
import hmac
import hashlib
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from huggingface_hub import hf_hub_download
import httpx

# ── slowapi imports ──────────────────────────────────────────────────────────
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ── Config ────────────────────────────────────────────────────────────────────
# /data is the bucket mount path — persistent across restarts.
# SQLite is built once on first boot and reused on every subsequent restart.
DATA_DIR    = "/data"
DB_PATH     = os.path.join(DATA_DIR, "pypi.db")
HF_REPO_ID  = "notamitgamer/pypi"          # your HuggingFace dataset repo
HF_FILENAME = "pypi.csv"                   # exact filename inside the repo — check your HF repo and update if different
HF_TOKEN    = os.environ.get("HF_TOKEN", "")  # set in Space Secrets if dataset is private

# ── Rate limit + bypass token config ──────────────────────────────────────────
# Random string — set in HF Space Secrets. Used to sign bypass tokens.
BYPASS_TOKEN_SECRET  = os.environ.get("BYPASS_TOKEN_SECRET", "change-me-in-secrets")
# How long a bypass token is valid (seconds)
BYPASS_TOKEN_TTL     = 3600  # 1 hour

# ── Version Cache ─────────────────────────────────────────────────────────────
VERSION_CACHE = {}
VERSION_CACHE_TTL = 86400  # Cache live PyPI versions for 24 hours

async def fetch_live_versions(package_names: list[str]) -> dict:
    """Fetch latest versions from live PyPI API concurrently, with caching."""
    results = {}
    missing = []
    now = time.time()
    for pkg in package_names:
        if pkg in VERSION_CACHE and (now - VERSION_CACHE[pkg]["time"]) < VERSION_CACHE_TTL:
            results[pkg] = VERSION_CACHE[pkg]["version"]
        else:
            missing.append(pkg)

    if missing:
        # Note: Requires `httpx` to be installed (pip install httpx)
        async with httpx.AsyncClient(limits=httpx.Limits(max_connections=50, max_keepalive_connections=10)) as client:
            async def get_v(pkg):
                try:
                    resp = await client.get(f"https://pypi.org/pypi/{pkg}/json", timeout=3.0)
                    if resp.status_code == 200:
                        v = resp.json().get("info", {}).get("version", "unknown")
                    else:
                        v = "unknown"
                except Exception:
                    v = "error"
                VERSION_CACHE[pkg] = {"version": v, "time": time.time()}
                return pkg, v

            fetched = await asyncio.gather(*(get_v(pkg) for pkg in missing))
            for pkg, v in fetched:
                results[pkg] = v

    return results

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("osma")


# ── DB helpers ────────────────────────────────────────────────────────────────
def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def db_ready() -> bool:
    if not os.path.exists(DB_PATH):
        return False
    try:
        conn = get_conn()
        count = conn.execute("SELECT COUNT(*) FROM pypi_packages").fetchone()[0]
        conn.close()
        return count > 0
    except Exception:
        return False


def build_db_from_csv_file(csv_path: str):
    """Read a local CSV file and build SQLite database."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_path = DB_PATH + ".tmp"

    conn = sqlite3.connect(tmp_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pypi_packages (
            package_no   INTEGER PRIMARY KEY,
            package_name TEXT NOT NULL,
            version      TEXT
        )
    """)

    batch  = []
    count  = 0
    with open(csv_path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        log.info(f"CSV header: {header}")
        for row in reader:
            if len(row) < 2:
                continue
            try:
                pkg_no   = int(row[0].strip())
                pkg_name = row[1].strip()
                # Parse the 3rd column (version) if it exists, otherwise default to "unknown"
                pkg_version = row[2].strip() if len(row) > 2 else "unknown"
            except (ValueError, IndexError):
                continue
            batch.append((pkg_no, pkg_name, pkg_version))
            count += 1
            if len(batch) >= 10_000:
                conn.executemany(
                    "INSERT OR REPLACE INTO pypi_packages (package_no, package_name, version) VALUES (?, ?, ?)", batch
                )
                conn.commit()
                batch = []
                if count % 500_000 == 0:
                    log.info(f"  Inserted {count:,} rows...")

    if batch:
        conn.executemany(
            "INSERT OR REPLACE INTO pypi_packages (package_no, package_name, version) VALUES (?, ?, ?)", batch
        )
        conn.commit()

    log.info(f"Building indexes on {count:,} rows...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON pypi_packages(package_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name_lower ON pypi_packages(LOWER(package_name))")
    conn.commit()
    conn.close()

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    os.rename(tmp_path, DB_PATH)
    log.info(f"Database ready at {DB_PATH} with {count:,} packages.")
    return count


async def download_and_build():
    """Download dataset from HuggingFace using huggingface_hub and build SQLite."""
    log.info(f"Downloading {HF_FILENAME} from HuggingFace repo {HF_REPO_ID}...")
    log.info("(Running on HF Spaces — download should complete in ~30–60 seconds)")

    # hf_hub_download caches to ~/.cache/huggingface by default.
    # It returns the local path to the downloaded file.
    csv_path = await asyncio.to_thread(
        hf_hub_download,
        repo_id   = HF_REPO_ID,
        filename  = HF_FILENAME,
        repo_type = "dataset",
        token     = HF_TOKEN or None,
    )

    log.info(f"Download complete. File at: {csv_path}")
    log.info("Building SQLite database...")
    count = await asyncio.to_thread(build_db_from_csv_file, csv_path)
    return count


# ── Startup / lifespan ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    if db_ready():
        conn  = get_conn()
        count = conn.execute("SELECT COUNT(*) FROM pypi_packages").fetchone()[0]
        conn.close()
        log.info(f"Existing database found with {count:,} packages. Skipping download.")
    else:
        log.info("No database found. Starting download from HuggingFace...")
        try:
            await download_and_build()
        except Exception as e:
            log.error(f"Failed to build database: {e}")
            # Server still starts — endpoints will return 503 until DB is ready

    yield   # Server runs here


# ── slowapi limiter ───────────────────────────────────────────────────────────
# HF Spaces sits behind a proxy — real client IP is in X-Forwarded-For,
# not the direct connection address which would be an internal proxy IP.
def get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host or "unknown"

def rate_limit_key(request: Request) -> str:
    """
    If request carries a valid bypass token, return a unique key tied to their IP
    so they get a fresh rate-limit bucket (e.g. another 60/min) instead of being unlimited.
    """
    bypass = request.headers.get("X-Bypass-Token", "")
    if bypass and verify_bypass_token(bypass):
        return f"bypass_{get_real_ip(request)}"
    return get_real_ip(request)

limiter = Limiter(key_func=rate_limit_key)

# ── Bypass token helpers ──────────────────────────────────────────────────────
# A bypass token is: "{expiry_timestamp}:{hmac_signature}"
# Signed with BYPASS_TOKEN_SECRET so it cannot be forged client-side.

def _sign(payload: str) -> str:
    return hmac.new(
        BYPASS_TOKEN_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

def create_bypass_token() -> str:
    expiry = int(time.time()) + BYPASS_TOKEN_TTL
    payload = str(expiry)
    return f"{payload}:{_sign(payload)}"

def verify_bypass_token(token: str) -> bool:
    """Returns True if token is valid and not expired."""
    try:
        payload, sig = token.rsplit(":", 1)
        if not hmac.compare_digest(_sign(payload), sig):
            return False
        return int(time.time()) < int(payload)
    except Exception:
        return False

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="OSMA PYPI API", lifespan=lifespan)

# ── attach limiter and register 429 handler ──────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten to your Firebase domain after testing
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["Retry-After"]
)


def check_db():
    if not db_ready():
        raise HTTPException(
            status_code=503,
            detail="Database is still initializing. Please retry in a few minutes."
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"name": "OSMA PYPI API", "status": "ok", "docs": "/docs"}


@app.get("/debug-ip")
def debug_ip(request: Request):
    return {
        "client_host":      request.client.host,
        "x-forwarded-for":  request.headers.get("X-Forwarded-For"),
        "x-real-ip":        request.headers.get("X-Real-IP"),
        "cf-connecting-ip": request.headers.get("CF-Connecting-IP"),
        "all_headers":      dict(request.headers),
    }


@app.api_route("/ping", methods=["GET", "HEAD"])
def ping():
    return {"ping": "pong"}


@app.get("/get-bypass")
def get_bypass(secret: str = Query(...)):
    """
    Issue a bypass token directly using BYPASS_TOKEN_SECRET.
    Call: GET /get-bypass?secret=your-secret-here
    The returned bypass_token can be sent as X-Bypass-Token header
    to skip rate limiting for BYPASS_TOKEN_TTL seconds.
    """
    expected = os.environ.get("BYPASS_TOKEN_SECRET", "")
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Invalid secret.")
    return {
        "bypass_token": create_bypass_token(),
        "valid_for_seconds": BYPASS_TOKEN_TTL,
        "usage": "Send as header: X-Bypass-Token: <token>"
    }


@app.get("/health")
def health():
    ready = db_ready()
    if not ready:
        return JSONResponse(status_code=503, content={"status": "initializing"})
    conn  = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM pypi_packages").fetchone()[0]
    conn.close()
    return {"status": "ok", "total_packages": count}


@app.get("/stats")
def stats():
    check_db()
    conn  = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM pypi_packages").fetchone()[0]
    conn.close()
    return {
        "total_pypi_packages": count,
        "source": "pypi.org",
        "note": "Snapshot dataset — updated periodically."
    }


@app.get("/browse")
@limiter.limit("10/minute;100/hour")
def browse(
    request: Request,
    page:  int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=500)
):
    """Return packages ordered by package_no, paginated."""
    check_db()
    offset = (page - 1) * limit
    conn   = get_conn()
    rows   = conn.execute(
        "SELECT package_no, package_name, version FROM pypi_packages ORDER BY package_no LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return {
        "page":     page,
        "limit":    limit,
        "results":  [{"no": r["package_no"], "name": r["package_name"], "version": r["version"],
                      "url": f"https://www.pypi.org/pypi/{r['package_name']}"} for r in rows]
    }


@app.get("/search")
@limiter.limit("10/minute;100/hour")
def search(
    request: Request,
    q:     str = Query(..., min_length=2, max_length=100),
    limit: int = Query(250, ge=1, le=500)
):
    """
    Search packages by name with ranked results:
      rank 0 — exact match
      rank 1 — starts with query
      rank 2 — contains query
    Results are sorted by rank then alphabetically within each rank.
    """
    check_db()
    q_lower = q.strip().lower()

    conn = get_conn()

    # Three separate queries — one per rank — then merge.
    # This way the index is always used for ranks 0 and 1.
    # Rank 2 (contains) is a full scan but capped at a small sub-limit.

    exact = conn.execute(
        "SELECT package_no, package_name, version, 0 AS rank FROM pypi_packages WHERE LOWER(package_name) = ? LIMIT 1",
        (q_lower,)
    ).fetchall()

    starts = conn.execute(
        """SELECT package_no, package_name, version, 1 AS rank FROM pypi_packages
           WHERE LOWER(package_name) LIKE ? AND LOWER(package_name) != ?
           ORDER BY package_name LIMIT ?""",
        (q_lower + "%", q_lower, limit)
    ).fetchall()

    # Only fetch 'contains' results to fill remaining slots
    remaining = limit - len(exact) - len(starts)
    contains  = []
    if remaining > 0:
        # Exclude names already captured above
        already = {r["package_name"] for r in exact} | {r["package_name"] for r in starts}
        raw_contains = conn.execute(
            """SELECT package_no, package_name, version, 2 AS rank FROM pypi_packages
               WHERE LOWER(package_name) LIKE ? AND LOWER(package_name) NOT LIKE ?
               ORDER BY package_name LIMIT ?""",
            (f"%{q_lower}%", q_lower + "%", remaining + len(already))
        ).fetchall()
        contains = [r for r in raw_contains if r["package_name"] not in already][:remaining]

    conn.close()

    all_results = list(exact) + list(starts) + list(contains)
    return {
        "query":   q,
        "count":   len(all_results),
        "results": [
            {
                "no":   r["package_no"],
                "name": r["package_name"],
                "version": r["version"],
                "url":  f"https://www.pypi.org/pypi/{r['package_name']}",
                "rank": r["rank"]
            }
            for r in all_results
        ]
    }


@app.get("/rebuild")
async def rebuild(secret: str = Query(...)):
    """
    Trigger a manual re-download and rebuild of the database.
    Protected by a secret key set in REBUILD_SECRET env var.
    Call: GET /rebuild?secret=your-secret-here
    """
    expected = os.environ.get("REBUILD_SECRET", "")
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Invalid secret.")
    asyncio.create_task(download_and_build())
    return {"status": "rebuild started in background"}

import os
import sqlite3
import asyncio
import csv
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from huggingface_hub import hf_hub_download

# ── Config ────────────────────────────────────────────────────────────────────
# /data is the bucket mount path — persistent across restarts.
# SQLite is built once on first boot and reused on every subsequent restart.
DATA_DIR    = "/data"
DB_PATH     = os.path.join(DATA_DIR, "npm.db")
HF_REPO_ID  = "notamitgamer/npm"          # your HuggingFace dataset repo
HF_FILENAME = "npm.csv"                   # exact filename inside the repo — check your HF repo and update if different
HF_TOKEN    = os.environ.get("HF_TOKEN", "")  # set in Space Secrets if dataset is private

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
        count = conn.execute("SELECT COUNT(*) FROM npm_packages").fetchone()[0]
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
        CREATE TABLE IF NOT EXISTS npm_packages (
            package_no   INTEGER PRIMARY KEY,
            package_name TEXT NOT NULL
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
            except (ValueError, IndexError):
                continue
            batch.append((pkg_no, pkg_name))
            count += 1
            if len(batch) >= 10_000:
                conn.executemany(
                    "INSERT OR REPLACE INTO npm_packages VALUES (?, ?)", batch
                )
                conn.commit()
                batch = []
                if count % 500_000 == 0:
                    log.info(f"  Inserted {count:,} rows...")

    if batch:
        conn.executemany(
            "INSERT OR REPLACE INTO npm_packages VALUES (?, ?)", batch
        )
        conn.commit()

    log.info(f"Building indexes on {count:,} rows...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON npm_packages(package_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_name_lower ON npm_packages(LOWER(package_name))")
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
        count = conn.execute("SELECT COUNT(*) FROM npm_packages").fetchone()[0]
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


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="OSMA NPM API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten to your Firebase domain after testing
    allow_methods=["GET"],
    allow_headers=["*"],
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
    return {"name": "OSMA NPM API", "status": "ok", "docs": "/docs"}


@app.get("/ping")
def ping():
    return {"ping": "pong"}


@app.get("/health")
def health():
    ready = db_ready()
    if not ready:
        return JSONResponse(status_code=503, content={"status": "initializing"})
    conn  = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM npm_packages").fetchone()[0]
    conn.close()
    return {"status": "ok", "total_packages": count}


@app.get("/stats")
def stats():
    check_db()
    conn  = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM npm_packages").fetchone()[0]
    conn.close()
    return {
        "total_npm_packages": count,
        "source": "npmjs.com",
        "note": "Snapshot dataset — updated periodically."
    }


@app.get("/browse")
def browse(
    page:  int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=500)
):
    """Return packages ordered by package_no, paginated."""
    check_db()
    offset = (page - 1) * limit
    conn   = get_conn()
    rows   = conn.execute(
        "SELECT package_no, package_name FROM npm_packages ORDER BY package_no LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return {
        "page":     page,
        "limit":    limit,
        "results":  [{"no": r["package_no"], "name": r["package_name"],
                      "url": f"https://www.npmjs.com/package/{r['package_name']}"} for r in rows]
    }


@app.get("/search")
def search(
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
        "SELECT package_no, package_name, 0 AS rank FROM npm_packages WHERE LOWER(package_name) = ? LIMIT 1",
        (q_lower,)
    ).fetchall()

    starts = conn.execute(
        """SELECT package_no, package_name, 1 AS rank FROM npm_packages
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
            """SELECT package_no, package_name, 2 AS rank FROM npm_packages
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
                "url":  f"https://www.npmjs.com/package/{r['package_name']}",
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
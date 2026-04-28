import xmlrpc.client
import json
import os
import time
from datetime import datetime

STATE_FILE = "state/pypi_state.json"
OUTPUT_FILE = "state/pypi_extract.json"
PYPI_RPC_URL = "https://pypi.org/pypi"

def ensure_dirs():
    os.makedirs("state", exist_ok=True)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    # Default to 1 hour ago for the first run to prevent massive full-sync
    return {"last_timestamp": int(time.time()) - 3600}

def save_state(timestamp):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_timestamp": timestamp}, f)

def extract():
    ensure_dirs()
    state = load_state()
    last_timestamp = state.get("last_timestamp")
    
    print(f"[PyPI] Fetching changelog since {last_timestamp}...")
    
    try:
        client = xmlrpc.client.ServerProxy(PYPI_RPC_URL)
        # Returns list of tuples: (name, version, timestamp, action)
        changelog = client.changelog(last_timestamp)
    except Exception as e:
        print(f"[PyPI] Error fetching XML-RPC changelog: {e}")
        return

    results = {}
    new_timestamp = last_timestamp

    for event in changelog:
        pkg_name, version, timestamp, action = event
        if timestamp > new_timestamp:
            new_timestamp = timestamp
            
        # Keep only the latest event for a package in this batch
        if pkg_name not in results:
            dt_iso = datetime.utcfromtimestamp(timestamp).isoformat() + "Z"
            results[pkg_name] = {
                "ecosystem": "pypi",
                "package_name": pkg_name,
                "version": version or "0.0.0",
                "author": "PyPI Contributor", # Full metadata requires HTTP API per package, saving API limits here
                "author_profile_url": "",
                "repo_url": "",
                "registry_url": f"https://pypi.org/project/{pkg_name}/",
                "deprecated": False,
                "first_seen": dt_iso, # Approximation for delta feed
                "last_updated": dt_iso
            }

    output_list = list(results.values())
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_list, f, indent=2)

    save_state(new_timestamp)
    print(f"[PyPI] Extracted {len(output_list)} packages. New timestamp: {new_timestamp}")

if __name__ == "__main__":
    extract()
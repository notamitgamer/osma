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

def get_latest_serial(client):
    try:
        return client.changelog_last_serial()
    except Exception as e:
        print(f"[PyPI] Error fetching last serial: {e}")
        return 0

def load_state(client):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
            
    # First run: get the current max serial to establish a baseline
    print("[PyPI] First run detected. Fetching latest registry serial...")
    serial = get_latest_serial(client)
    return {"last_serial": serial}

def save_state(serial):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_serial": serial}, f)

def extract():
    ensure_dirs()
    client = xmlrpc.client.ServerProxy(PYPI_RPC_URL)
    state = load_state(client)
    last_serial = state.get("last_serial", 0)
    
    print(f"[PyPI] Fetching changelog since serial {last_serial}...")
    
    try:
        # Using the new serial-based method
        changelog = client.changelog_since_serial(last_serial)
    except Exception as e:
        print(f"[PyPI] Error fetching XML-RPC changelog: {e}")
        return

    results = {}
    new_serial = last_serial

    # The new method returns 5 elements per event (includes serial)
    for event in changelog:
        pkg_name, version, timestamp, action, serial = event
        if serial > new_serial:
            new_serial = serial
            
        # Keep only the latest event for a package in this batch
        if pkg_name not in results:
            dt_iso = datetime.utcfromtimestamp(timestamp).isoformat() + "Z"
            results[pkg_name] = {
                "ecosystem": "pypi",
                "package_name": pkg_name,
                "version": version or "0.0.0",
                "author": "PyPI Contributor",
                "author_profile_url": "",
                "repo_url": "",
                "registry_url": f"https://pypi.org/project/{pkg_name}/",
                "deprecated": False,
                "first_seen": dt_iso,
                "last_updated": dt_iso
            }

    output_list = list(results.values())
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output_list, f, indent=2)

    save_state(new_serial)
    print(f"[PyPI] Extracted {len(output_list)} packages. New serial: {new_serial}")

if __name__ == "__main__":
    extract()

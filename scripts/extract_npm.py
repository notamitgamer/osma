import urllib.request
import json
import os
import time

STATE_FILE = "state/npm_state.json"
OUTPUT_FILE = "state/npm_extract.json"
# Using the public NPM registry changes feed
CHANGES_URL = "https://replicate.npmjs.com/_changes?include_docs=true&limit=1000&since={}"

def ensure_dirs():
    os.makedirs("state", exist_ok=True)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
            
    # On first run, get the current max sequence so we track new packages from today
    print("[NPM] First run detected. Fetching latest registry sequence...")
    try:
        req = urllib.request.Request("https://replicate.npmjs.com/", headers={'User-Agent': 'OSMA-ETL-Bot'})
        with urllib.request.urlopen(req) as response:
            latest_seq = json.loads(response.read().decode()).get("update_seq", 0)
            return {"last_seq": latest_seq}
    except Exception as e:
        print(f"[NPM] Error fetching latest sequence: {e}")
        return {"last_seq": 0}

def save_state(seq):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_seq": seq}, f)

def extract():
    ensure_dirs()
    state = load_state()
    last_seq = state.get("last_seq", 0)
    
    url = CHANGES_URL.format(last_seq)
    print(f"[NPM] Fetching delta updates since seq: {last_seq}...")
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'OSMA-ETL-Bot'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f"[NPM] Error fetching data: {e}")
        return

    results = []
    new_seq = last_seq

    for row in data.get("results", []):
        new_seq = row.get("seq", new_seq)
        doc = row.get("doc")
        if not doc or "name" not in doc:
            continue
            
        pkg_name = doc.get("name")
        latest_version = doc.get("dist-tags", {}).get("latest", "0.0.0")
        time_data = doc.get("time", {})
        
        # Determine author
        author_name = "Unknown"
        author_profile = ""
        if isinstance(doc.get("author"), dict):
            author_name = doc["author"].get("name", "Unknown")
        elif isinstance(doc.get("maintainers"), list) and len(doc["maintainers"]) > 0:
            author_name = doc["maintainers"][0].get("name", "Unknown")
            author_profile = f"https://www.npmjs.com/~{author_name}"

        # Determine repo URL
        repo_url = ""
        repo = doc.get("repository")
        if isinstance(repo, dict):
            repo_url = repo.get("url", "")
        elif isinstance(repo, str):
            repo_url = repo
        
        # Clean git:// and ssh:// prefixes for cleaner UI
        if repo_url.startswith("git+"):
            repo_url = repo_url[4:]

        pkg_data = {
            "ecosystem": "npm",
            "package_name": pkg_name,
            "version": latest_version,
            "author": author_name,
            "author_profile_url": author_profile,
            "repo_url": repo_url,
            "registry_url": f"https://www.npmjs.com/package/{pkg_name}",
            "deprecated": False, # Basic assumption, would need deep check inside versions
            "first_seen": time_data.get("created", time.strftime('%Y-%m-%dT%H:%M:%SZ')),
            "last_updated": time_data.get("modified", time.strftime('%Y-%m-%dT%H:%M:%SZ'))
        }
        results.append(pkg_data)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    save_state(new_seq)
    print(f"[NPM] Extracted {len(results)} packages. New seq: {new_seq}")

if __name__ == "__main__":
    extract()

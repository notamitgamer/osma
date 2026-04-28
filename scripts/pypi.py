import urllib.request
import urllib.error
import json
import csv
import os
import time
import concurrent.futures
import threading

def extract_pypi():
    print(f"\n[PyPI] Starting extraction of ALL packages...")
    output_file = "data/pypi.csv"
    
    print("[PyPI] Fetching master package list from Simple API (JSON)...")
    try:
        req = urllib.request.Request(
            'https://pypi.org/simple/', 
            headers={
                'Accept': 'application/vnd.pypi.simple.v1+json',
                'User-Agent': 'OSMA-Local-Extractor'
            }
        )
        with urllib.request.urlopen(req) as response:
            simple_data = json.loads(response.read().decode())
            all_packages = [proj["name"] for proj in simple_data.get("projects", [])]
    except Exception as e:
        print(f"[PyPI] Error getting package list: {e}")
        return

    total_packages = len(all_packages)
    print(f"[PyPI] Total packages found: {total_packages}. Extracting metadata... (STABLE MULTITHREADED)")

    total_fetched = 0
    counter_lock = threading.Lock()
    file_lock = threading.Lock()

    with open(output_file, mode='w', encoding='utf-8') as f:
        f.write('No.,Package Name,Version,Official Link\n')

        def fetch_and_write(pkg_no, pkg_name):
            nonlocal total_fetched
            url = f"https://pypi.org/pypi/{pkg_name}/json"
            
            # --- RETRY LOGIC ---
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'OSMA-Local-Extractor'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        data = json.loads(response.read().decode())
                        
                    info = data.get("info", {})
                    version_raw = info.get("version")
                    version = f"v{version_raw}" if version_raw else "vUnknown"
                    official_link = info.get("package_url", f"https://pypi.org/project/{pkg_name}/")
                    
                    line = f'{pkg_no}, "{pkg_name}", {version}, {official_link}\n'
                    
                    with file_lock:
                        f.write(line)
                        f.flush()
                        
                    with counter_lock:
                        total_fetched += 1
                        if total_fetched % 200 == 0:
                            print(f"[PyPI] Processed {total_fetched} / {total_packages}...")
                    
                    return # Success! Break the retry loop
                        
                except urllib.error.HTTPError as e:
                    if e.code == 404: return # Deleted package, don't retry
                    if e.code in [429, 403, 503]:
                        time.sleep(2 * (attempt + 1)) # Wait longer if throttled
                    continue # Retry for other HTTP errors
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"\n[PyPI] Failed '{pkg_name}' after {max_retries} attempts: {e}")
                    time.sleep(1) # Wait before retry for socket/timeout errors
                    continue

        # Using 200 workers is much more stable for Windows and avoids 10054 errors
        with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
            for i, pkg_name in enumerate(all_packages, 1):
                executor.submit(fetch_and_write, i, pkg_name)

    print(f"[PyPI] Successfully wrote {total_fetched} packages to {output_file}")

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    extract_pypi()
    print("\n✅ All extractions complete! Check the 'data' folder.")
